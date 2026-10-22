"""One-shot run supervisor for the TF-intent chain observation ([kd] -> [gs-res] -> [tf-intent]): single monotonic clock, one child, bounded
sampling, finally reclaim. A keydump-matched target PS header must be followed by a complete [kd-geom] record on the
same frame/pass; the geometry source must contain the target GS. This does not prove the GS executed. Resource lines,
complete dumps, CRASH/FATAL, sampling faults, the 180 s deadline and parent signals keep the audited batch-supervisor
roles and thresholds.
"""

import argparse, hashlib, json, os, re, signal, struct, subprocess, sys, time
from tfintent_parser import TfIntentChain, TARGET_PS, TARGET_GS

T0 = time.monotonic()
STOP = {'requested': None}

def el(): return time.monotonic() - T0

def on_signal(signum, _frame):
    STOP['requested'] = 'parent signal %d' % signum      # record intent only; cleanup does the killing

class SamplingUnavailable(Exception): pass
class LaunchRefused(Exception):
    def __init__(self, kind, why): self.kind = kind; super().__init__(why)
class SupervisorIO(Exception): pass

def sh(cmd, timeout):
    """A bounded sampling call. A non-zero exit, a timeout or an OS error is an error, never a default value."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SamplingUnavailable('sampling command timed out: %s' % cmd[0])
    except OSError as e:
        raise SamplingUnavailable('sampling command failed: %s (%s)' % (cmd[0], e))
    if r.returncode != 0:
        raise SamplingUnavailable('sampling command %s exited %d: %s'
                                  % (cmd[0], r.returncode, (r.stderr or '').strip()[:80]))
    return r

def parse_pagesize(text):
    t = (text or '').strip()
    if not t: raise SamplingUnavailable('sysctl hw.pagesize produced no output')
    try: v = int(t)
    except ValueError: raise SamplingUnavailable('hw.pagesize is not an integer: %r' % t[:40])
    if v <= 0: raise SamplingUnavailable('hw.pagesize is not positive: %d' % v)
    return v

def parse_vmstat(text):
    """Returns (free, inactive, speculative). All three must be present and parseable, or this is an error: a partial
    reading would silently turn into a wrong available figure."""
    vals = {}
    for ln in (text or '').splitlines():
        for key, name in (('Pages free','free'), ('Pages inactive','inactive'), ('Pages speculative','speculative')):
            if ln.startswith(key):
                try: vals[name] = int(ln.split(':')[1].strip().rstrip('.').replace('.',''))
                except (IndexError, ValueError):
                    raise SamplingUnavailable('vm_stat %r is unparsable: %r' % (key, ln[:60]))
    missing = [n for n in ('free','inactive','speculative') if n not in vals]
    if missing: raise SamplingUnavailable('vm_stat is missing %s' % ', '.join(missing))
    if any(v < 0 for v in vals.values()): raise SamplingUnavailable('vm_stat returned a negative page count')
    return vals['free'], vals['inactive'], vals['speculative']

def parse_rss(text):
    t = (text or '').strip()
    if not t: raise SamplingUnavailable('ps produced no output')
    try: v = int(t)
    except ValueError: raise SamplingUnavailable('ps output is not an integer: %r' % t[:40])
    if v < 0: raise SamplingUnavailable('ps returned a negative RSS')
    return v

def pages_and_avail(budget):
    ps = parse_pagesize(sh(['sysctl','-n','hw.pagesize'], budget).stdout)
    free, inactive, spec = parse_vmstat(sh(['vm_stat'], budget).stdout)
    return ps, free, inactive, spec, (free + inactive + spec) * ps // 1048576

def rss_kb(pid, budget):
    return parse_rss(sh(['ps','-o','rss=','-p',str(pid)], budget).stdout)

def complete_dumps(dumpdir, inject):
    if not os.path.isdir(dumpdir): return
    if inject: raise OSError('injected dump read failure')   # test-only, refused unless --test-inject was given
    names = sorted(os.listdir(dumpdir))
    for name in names:
        if not name.endswith('.ctl'): continue
        ctl = os.path.join(dumpdir, name); code = ctl[:-4] + '.code'
        if not os.path.exists(code): continue
        csz = os.path.getsize(ctl); dsz = os.path.getsize(code)
        if csz < 2176 or dsz == 0: continue
        head = open(ctl,'rb').read(0x880)
        if head[:4] != bytes.fromhex('34127698'): continue
        if struct.unpack_from('<I', head, 0x704)[0] != dsz: continue
        yield (name[:-4], ctl, csz, hashlib.sha256(head).hexdigest(), dsz,
               hashlib.sha256(open(code,'rb').read()).hexdigest())

# ---- target acceptance: production [kd] header + [gs-res] record ------------------------------------------------
class TfIntentSupervisor:
    """Dedicated matcher: [kd] -> validated [gs-res] HIT -> [tf-intent] same frame/pass/VS/PS/GS.
    A gs-res HIT alone is never terminal; the chain completes on the matching intent line (any active value)."""
    def __init__(self):
        self.chain = TfIntentChain(TARGET_GS, TARGET_PS)
        self.lines = []; self.hdr = None; self.record = None; self.intent = None
        self.terminal = None; self.result = None
        self.validated = False; self.record_obtained = False; self.intent_obtained = False
    def feed(self, line):
        if line.startswith('[kd]') or line.startswith('[gs-res]') or line.startswith('[dm] [nvn-mtl] [gs-res]') or line.startswith('[tf-intent]'):
            self.lines.append(line)
        t = self.chain.feed(line)
        self.hdr = self.chain.hdr; self.record = self.chain.record; self.intent = self.chain.intent
        self.terminal = self.chain.terminal; self.result = self.chain.result
        self.record_obtained = self.record is not None
        self.intent_obtained = self.intent is not None
        self.validated = self.record_obtained and self.intent_obtained and self.result == 'hit'
        if t is None: return None
        return (self.chain.result, self.chain.terminal)
class LogTail:
    """Incremental line reader: no re-scan of old bytes, partial lines held until their newline arrives."""
    LIMIT = 4 * 1024 * 1024
    def __init__(self, path): self.path = path; self.off = 0; self.buf = b''
    def lines(self):
        try:
            with open(self.path,'rb') as f:
                f.seek(0, os.SEEK_END); size = f.tell()
                if size < self.off: self.off = 0; self.buf = b''      # truncated by someone else: never keep a stale offset
                f.seek(self.off); chunk = f.read(min(size - self.off, self.LIMIT))
                self.off += len(chunk)
        except OSError as x:
            raise SupervisorIO('cannot read log: %s' % x)
        data = self.buf + chunk
        parts = data.split(b'\n'); self.buf = parts.pop()
        if len(self.buf) > 1024 * 1024: raise SupervisorIO('log line over 1 MiB without a newline')
        return [p.decode('utf-8','replace') for p in parts]
    def partial(self):
        return self.buf.decode('utf-8','replace')

def _write_rows(csv_path, rows):
    """Persist the rows taken so far. Called after every sample, before any success decision is finalised on disk."""
    with open(csv_path, 'w') as f:
        f.write('elapsed,pagesize,free_pages,inactive_pages,spec_pages,avail_mb\n')
        for r in rows: f.write('%.3f,%d,%d,%d,%d,%d\n' % r)

def gate(secs, mib, csv_path, sample=None, clock=time.monotonic, sleep=time.sleep):
    """Full-window gate anchored on real sample completion times.

    window_start is the monotonic completion time of the first successful sample, so the first row's elapsed is 0 and a
    slow first sample does not shorten the window. Every sample records its own completion time immediately, before any
    CSV work; success requires that sample's own time minus window_start to be >= secs (and that sample itself >= the
    bar). Log I/O time never counts as a sample and can never satisfy the endpoint: if a write crosses it, another valid
    sample is taken, or a sampling/deadline error refuses the launch. Rows are saved after every sample, so refusals keep
    what was taken. No retry and no waiting for resources.
    """
    sample = sample or pages_and_avail
    rows = []
    if secs <= 0: return rows, None
    ws = None
    n = 0
    while True:
        ps, free, inact, spec, avail = sample(min(1.0, max(0.05, secs)))
        at = clock()                                   # this sample's completion time, before any CSV write
        if ws is None: ws = at
        rows.append((at - ws, ps, free, inact, spec, avail))
        _write_rows(csv_path, rows)
        if avail < mib:
            return rows, 'available %d MiB < %d MiB before launch' % (avail, mib)
        if at - ws >= secs:                            # terminal sample, judged by its own time
            return rows, None
        n += 1
        wait = (ws + n) - clock()
        if wait > 0: sleep(wait)

def _write_evidence(run, sf):
    with open(os.path.join(run,'tfintent.txt'),'w') as f: f.write('\n'.join(sf.lines)+'\n')
    if sf.record or sf.intent:
        with open(os.path.join(run,'tfintent.json'),'w') as jf: json.dump({'header':sf.hdr,'record':sf.record,'intent':sf.intent,'terminal':sf.terminal,'validated':sf.validated,'record_obtained':sf.record_obtained,'intent_obtained':sf.intent_obtained,'matcher_result':sf.result},jf,indent=1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True); ap.add_argument('--patched', required=True)
    ap.add_argument('--run', required=True); ap.add_argument('--secs', type=float, default=180)
    ap.add_argument('--exempt-json', required=True)
    ap.add_argument('--gate-secs', type=float, default=0); ap.add_argument('--gate-mib', type=float, default=3072)
    ap.add_argument('--test-inject', action='append', default=[])
    a = ap.parse_args()
    inj = set(a.test_inject)
    leftover = [k for k in os.environ if k.startswith('IMGSUP_TEST_')]
    if leftover and not inj:
        print('refusing to start: leftover test switch(es) %s; clear them or pass --test-inject' % leftover,
              file=sys.stderr)
        return 2
    exempt = json.load(open(a.exempt_json))
    log = os.path.join(a.run,'boot.log'); dump = os.path.join(a.run,'shdump')
    exc = os.path.join(a.run,'exemptions.txt'); samples = os.path.join(a.run,'samples.csv')
    for s in (signal.SIGTERM, signal.SIGINT): signal.signal(s, on_signal)
    try:
        rows, bad = gate(a.gate_secs, a.gate_mib, os.path.join(a.run,'gate.csv'))
    except SamplingUnavailable as x:
        bad = 'sampling unavailable: %s' % x
    if bad:
        line = 'kind=gate\nreason=not launched: %s\nexit=3\nlaunch=\nfirst_at=\nterm_at=\ngone_at=\n' % bad
        try: open(os.path.join(a.run,'timing.txt'),'w').write(line)   # a refusal must leave a record, not only stdout
        except OSError: pass
        print('kind=gate\nreason=not launched: %s\n' % bad, file=sys.stderr); print('gate: not launched: %s' % bad)
        return 3
    if rows: print('gate: %d samples, min available %d MiB' % (len(rows), min(r[5] for r in rows)))
    seen = set(); kind = 'normal'; reason = ''; first_at = term_at = gone_at = launch_at = None
    child = None; sf = TfIntentSupervisor()
    try:
        with open(exc,'w') as f: f.write('# key\telapsed\tctl_len\tctl_sha\tcode_len\tcode_sha\tfile\n')
        with open(samples,'w') as f: f.write('elapsed,pid,rss_kb,pagesize,free_pages,inactive_pages,spec_pages,avail_mb\n')
        if STOP['requested']: raise LaunchRefused('interrupt', STOP['requested'])
        if el() > a.secs: raise LaunchRefused('normal', 'deadline before launch (%.1f s)' % el())
        launch_at = el()
        child = subprocess.Popen([a.host, a.patched], stdout=open(log,'wb'), stderr=subprocess.STDOUT)
        tail = LogTail(log)
        while True:
            e = el()
            if STOP['requested']: kind, reason = 'interrupt', STOP['requested']; break
            if child.poll() is not None: kind, reason = 'normal', 'host exited'; break
            if e > a.secs: kind, reason = 'normal', 'wall clock %.0fs' % a.secs; break
            try:
                new = tail.lines()
            except SupervisorIO as x:
                kind, reason = 'supervisor-error', str(x); break
            hit = None
            for line in new:
                r = sf.feed(line)
                if r is not None: hit = r
                if 'CRASH' in line or 'FATAL' in line: kind, reason = 'normal', 'crash/FATAL'; break
            if reason:
                if first_at is None: first_at = e
                break
            if hit is not None and 'dump-after-hit' in inj:   # test-only deterministic same-poll dump
                os.makedirs(dump, exist_ok=True)
                ctl=bytearray(2176); ctl[:4]=bytes.fromhex('34127698'); code=b'CODE'
                struct.pack_into('<I',ctl,0x704,len(code))
                open(os.path.join(dump,'nonexempt.ctl'),'wb').write(ctl)
                open(os.path.join(dump,'nonexempt.code'),'wb').write(code)
            if not new:
                for mk in ('CRASH','FATAL'):
                    if mk in tail.partial(): kind, reason = 'normal', 'crash/FATAL'; break
            if reason: break
            blocked = None
            for key, ctl, csz, csha, dsz, dsha in complete_dumps(dump, 'dump-read-error' in inj):
                sp = exempt.get(key)
                if sp and csz == sp['ctl'] and dsz == sp['code'] and csha == sp['ctl_sha'] and dsha == sp['code_sha']:
                    if key not in seen:
                        seen.add(key)
                        with open(exc,'a') as f: f.write('%s\t%.3f\t%d\t%s\t%d\t%s\t%s\n' % (key, e, csz, csha, dsz, dsha, ctl))
                    continue
                blocked = key; break
            if blocked:
                kind='normal'; reason='complete dump: %s' % blocked; first_at=e; dump_event=True
                try:
                    _write_evidence(a.run, sf)
                except OSError as x:
                    kind='supervisor-error'; reason='evidence-write-failed: %s' % x
                break
            if hit is not None:
                kind, reason = hit[0], hit[1]; first_at = e
                try:
                    _write_evidence(a.run, sf)
                except OSError as x:
                    kind='supervisor-error'; reason='evidence-write-failed: %s' % x
                break
            budget = max(0.05, min(1.0, a.secs - e))
            if 'sample-timeout' in inj: sh(['sleep','5'], max(0.05, min(budget, 0.3)))
            if 'sample-nonzero' in inj: sh(['/bin/sh','-c','echo injected >&2; exit 3'], budget)
            if 'sample-empty' in inj: parse_rss('')
            if 'synthetic-sampler' in inj:
                rss,ps,free,inact,spec,avail = 1,16384,1,1,1,4096
            else:
                rss = rss_kb(child.pid, budget)
                ps, free, inact, spec, avail = pages_and_avail(budget)
            with open(samples,'a') as f: f.write('%.3f,%d,%d,%d,%d,%d,%d,%d\n' % (e, child.pid, rss, ps, free, inact, spec, avail))
            if rss > 2097152: kind, reason = 'normal', 'RSS > 2 GiB'; break
            if avail < 1024: kind, reason = 'normal', 'available %d MiB < 1 GiB' % avail; break
            if os.path.isdir(dump) and sum(os.path.getsize(os.path.join(dump,x)) for x in os.listdir(dump)) > 32*1024*1024:
                kind, reason = 'normal', 'dump > 32 MiB'; break
            if os.path.getsize(log) > 64*1024*1024: kind, reason = 'normal', 'log > 64 MiB'; break
            time.sleep(0.2)
    except LaunchRefused as x: kind, reason = x.kind, str(x)
    except SamplingUnavailable as x: kind, reason = 'sampling-error', str(x)
    except KeyboardInterrupt: kind, reason = 'interrupt', 'keyboard interrupt'
    except Exception as x: kind, reason = 'supervisor-error', '%s: %s' % (type(x).__name__, x)
    finally:
        try:
            with open(os.path.join(a.run,'coverage.txt'),'w') as f:
                f.write('kind=%s\nreason=%s\nterminal=%s\n' % (kind, reason, sf.terminal or ''))
                if sf.hdr: f.write('header frame=%d pass=%d fs=%s prim=%d count=%d instances=%d base_instance=%d\n' % (sf.hdr['frame'],sf.hdr['pass_'],sf.hdr['fs'],sf.hdr['prim'],sf.hdr['count'],sf.hdr['instances'],sf.hdr['base_instance']))
                r=sf.record or {}
                f.write('result=%s\nrecord_obtained=%d\nintent_obtained=%d\nvalidated=%d\ngs_present=%s\n' % (sf.result or '', 1 if sf.record_obtained else 0, 1 if sf.intent_obtained else 0, 1 if sf.validated else 0, ('' if not sf.record_obtained else str(r.get('gs_present')))))
                if sf.record: f.write('record_keys=%s\n' % ','.join(r.get('keys',[])))
            with open(os.path.join(a.run,'stop.json'),'w') as jf: json.dump({'kind':kind,'reason':reason,'terminal':sf.terminal,'validated':sf.validated,'record_obtained':sf.record_obtained,'intent_obtained':sf.intent_obtained,'matcher_result':sf.result,'success': bool(kind=='hit' and sf.validated)},jf,indent=1)
        except OSError: pass
        if child is not None:
            try:
                if child.poll() is None:
                    term_at = el(); child.send_signal(signal.SIGTERM)
                    t = time.monotonic()
                    while time.monotonic() - t < 2.0 and child.poll() is None: time.sleep(0.05)
                    if child.poll() is None: child.kill()
                rc = child.wait(); gone_at = el()
            except Exception as x:      # cleanup must not raise out of the finally block
                print('cleanup failed: %s' % x, file=sys.stderr); rc = -1; gone_at = el()
        else:
            rc = -1
        line = 'kind=%s\nreason=%s\nexit=%s\nlaunch=%s\nlaunch_at=%s\nfirst_at=%s\nterm_at=%s\ngone_at=%s\n' % (
            kind, reason, rc, '0.000' if child is not None else '',
            '%.3f' % launch_at if launch_at is not None else '',
            '%.3f' % first_at if first_at is not None else '',
            '%.3f' % term_at if term_at is not None else '', '%.3f' % gone_at if gone_at is not None else '')
        try: open(os.path.join(a.run,'timing.txt'),'w').write(line)
        except OSError: print(line, file=sys.stderr)
        print('%s: %s' % (kind, reason))
    return 0

if __name__ == '__main__':
    sys.exit(main())
