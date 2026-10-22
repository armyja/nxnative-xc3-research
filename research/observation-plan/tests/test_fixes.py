#!/usr/bin/env python3
"""TF-PLAN-FIX smoke: attr sub-lines, prefixes, tokens, u64/i32 domains, supervisor cleanup isolation, run-path volume guard."""
import json, os, re, sys, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import tfintent_parser as tp, supervise_tfintent as sup, launcher

fails = []
def ck(c, w):
    if not c: fails.append(w); print('FAIL', w)
lines = [l.rstrip('\n') for l in open(os.path.join(HERE, 'fixtures/kd_gsres_hit.txt')) if l.strip()]
kd, gs = lines[0], lines[1]
m = re.match(r'^\[kd\] F(\d+) pass (\d+) vs=(\S+) fs=(\S+)', kd)
frame, passc, vs, ps = m.group(1), m.group(2), m.group(3), m.group(4)
def intent(frame=frame, passc=passc, vs=vs, ps=ps, depth='0', active='inactive', prefix=''):
    return ('%s[tf-intent] frame=%s pass=%s vs=%s ps=%s gs=95bfab6122539993 final_pass_association=none '
            'interpretation=observed-replay-intent active=%s pause=unknown reason=none seq=3 events=2 copies=2 '
            'depth=%s bound0=none begin=0 end=0 draw=0' % (prefix, frame, passc, vs, ps, active, depth))
def chain():
    return tp.TfIntentChain()

# F2: production [kd] sub-lines are ignored; a real second header is still duplicate
c = chain(); c.feed(kd)
for sub in ('[kd]   attr 0 format 0x22 offset 0 stream 0', '[kd]   stream 0 stride 16 divisor 0 buffer 0x1 size 64',
            '[kd]   stream r0 addr=0x1 size=64', '[kd]     +000000 -0.9 -0.9 1 1', '[kd]   fragment uniform r0 addr=0x2 size=32'):
    ck(c.feed(sub) is None, 'sub-line ignored: ' + sub[:18])
ck(c.result is None, 'sub-lines are not headers')
ck(c.feed(gs) is None and c.feed(intent()) == 'hit (tf-intent chain)', 'chain after sub-lines')
c = chain(); c.feed(kd); ck(c.feed(kd) is None or c.result == 'invalid', 'duplicate header rejected')
ck(c.result == 'invalid', 'duplicate header terminal invalid')
c = chain(); c.feed('[kd] Fnotanumber pass 1 vs=x fs=y'); ck(c.result == 'invalid', 'malformed header invalid')

# F3: bare VS/PS accepted; suffixes limited to _b/_bf; weird suffixes rejected by the intent parser
# bare tokens are valid for the tf-intent parser; a bare *chain* is outside the gsres contract (record ps_style must be _b)
try:
    tp.parse_tf_intent(intent(vs=vs[:-2], ps=ps[:-2])); ok = True
except tp.ParseError: ok = False
ck(ok, 'bare VS/PS accepted by the tf-intent parser')
for bad in (vs + 'x', vs[:-2] + '_B', '0x' + vs[:14], vs[:-2] + '_bfx'):
    try: tp.parse_tf_intent(intent(vs=bad)); ok = False
    except tp.ParseError: ok = True
    ck(ok, 'weird vs rejected: ' + bad)
kd_bf = kd.replace(ps, ps + 'f')
c = chain(); c.feed(kd_bf); ck(c.result == 'target-not-obtained', '_bf header stays not-obtained')

# F4: i32 depth domain, u64 fields
for d, ok in (('2147483647', True), ('-2147483648', True), ('2147483648', False), ('-2147483649', False)):
    try: tp.parse_tf_intent(intent(depth=d)); got = True
    except tp.ParseError: got = False
    ck(got == ok, 'depth domain ' + d)
try:
    tp.parse_tf_intent(intent(frame='18446744073709551616')); ck(False, 'frame u64 overflow rejected')
except tp.ParseError: ck(True, 'frame u64 overflow rejected')

# log wrapper: bare and exact [dm] [nvn-mtl] prefix only
c = chain(); c.feed(kd); c.feed(gs)
ck(c.feed(intent(prefix='[dm] [nvn-mtl] ')) == 'hit (tf-intent chain)', 'prefixed intent accepted')
for bad in ('xx [tf-intent] ', ' [tf-intent] ', '[dm][nvn-mtl] [tf-intent] '):
    c = chain(); c.feed(kd); c.feed(gs); c.feed(intent(prefix=bad))
    ck(c.result == 'invalid', 'non-exact prefix rejected: ' + repr(bad))

# F1: evidence error must not skip child reclamation, and must not claim success
class FakeChild:
    def __init__(self): self.signals = []; self.waited = False; self.killed = False
    def poll(self): return None
    def send_signal(self, s): self.signals.append(s)
    def kill(self): self.killed = True
    def wait(self): self.waited = True; return 0
run = tempfile.mkdtemp()
class Sf: hdr = None; record = None; intent = None; terminal = 'hit (tf-intent chain)'; result = 'hit'; validated = True; record_obtained = True; intent_obtained = True
saved_final = sup._write_final
def boom(*a, **k): raise RuntimeError('forced evidence failure')
sup._write_final = boom
ch = FakeChild()
kind, reason, term_at, rc, gone_at = sup._finalize(run, Sf(), 'hit', 'hit (tf-intent chain)', ch, None, None, None)
sup._write_final = saved_final
ck(kind == 'supervisor-error' and 'evidence-write-failed' in reason, 'evidence error -> supervisor-error, no success')
ck(ch.waited, 'child reclamation happened despite evidence error')
stop = json.load(open(os.path.join(run, 'stop.json')))
ck(stop.get('success') is False, 'minimal stop.json does not claim success')
shutil.rmtree(run, ignore_errors=True)

# F5: run path must be on the allowed volume, resolved ancestor, not existing
ck(launcher.check_run_path('relative/run')[0] is False, 'relative rejected')
ck(launcher.check_run_path('/tmp/tf-run-xyz')[0] is False, 'other volume rejected')
scratch = os.path.join(launcher.RUN_ROOT, '.tfpath-test-%d' % os.getpid())
os.makedirs(scratch, exist_ok=True)
try:
    ck(launcher.check_run_path(scratch)[0] is False, 'existing run rejected')
    link = os.path.join(scratch, 'escape')
    try:
        os.symlink('/tmp', link)
        ck(launcher.check_run_path(os.path.join(link, 'run1'))[0] is False, 'symlink escape rejected')
    except OSError: ck(True, 'symlink unavailable (skipped)')
    ck(launcher.check_run_path(os.path.join(scratch, 'fresh-run'))[0] is True, 'fresh path under experiments accepted')
finally:
    shutil.rmtree(scratch, ignore_errors=True)

print('fails:', len(fails))
sys.exit(1 if fails else 0)
