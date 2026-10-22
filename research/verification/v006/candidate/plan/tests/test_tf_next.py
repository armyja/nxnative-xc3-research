#!/usr/bin/env python3
"""Basic checks for the dedicated tf-intent chain and the preflight-only launcher. Basic smoke, not independent acceptance."""
import io, json, os, re, subprocess, sys, tempfile, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import tfintent_parser as tp

fails = []
def ck(cond, what):
    if not cond: fails.append(what); print('FAIL', what)

lines = [l.rstrip('\n') for l in open(os.path.join(HERE, 'fixtures/kd_gsres_hit.txt')) if l.strip()]
kd, gs = lines[0], lines[1]
m = re.match(r'^\[kd\] F(\d+) pass (\d+) vs=(\S+) fs=(\S+)', kd)
frame, passc, vs, ps = m.group(1), m.group(2), m.group(3), m.group(4)
A = ('[tf-intent] frame=%s pass=%s vs=%s ps=%s gs=95bfab6122539993 final_pass_association=none '
     'interpretation=observed-replay-intent active=inactive pause=unknown reason=none seq=3 events=2 copies=2 '
     'depth=0 bound0=none begin=0x10 end=0x10 draw=0' % (frame, passc, vs, ps))
def chain():
    c = tp.TfIntentChain(); return c

# 1: header + gs-res hit alone is NOT terminal
c = chain(); ck(c.feed(kd) is None, 'kd not terminal'); ck(c.feed(gs) is None, 'gs-res hit not terminal')
ck(c.result is None, 'gs-res hit does not end the chain')
# 2: matching intent completes
ck(c.feed(A) == 'hit (tf-intent chain)', 'complete chain terminal'); ck(c.intent is not None, 'intent stored')
# 3: wrong frame
c = chain(); c.feed(kd); c.feed(gs)
c.feed(A.replace('frame=%s' % frame, 'frame=9999', 1)); ck(c.result == 'invalid', 'frame mismatch invalid')
# 4: intent before hit
c = chain(); c.feed(kd); c.feed(A); ck(c.result == 'invalid', 'intent before gs-res invalid')
# 5: bad active / reason / copies
for bad, why in ((A.replace('active=inactive', 'active=weird'), 'active domain'),
                 (A.replace('reason=none', 'reason=bogus'), 'reason domain'),
                 (A.replace('events=2 copies=2', 'events=1 copies=2'), 'copies>events')):
    c = chain(); c.feed(kd); c.feed(gs); c.feed(bad); ck(c.result == 'invalid', why)
# 6: diagnostic-error intent
c = chain(); c.feed(kd); c.feed(gs)
c.feed('[tf-intent] diagnostic-error'); ck(c.result == 'diagnostic-error', 'diagnostic-error terminal')
# 7: duplicate/terminal idempotent
c = chain(); c.feed(kd); c.feed(gs); t1 = c.feed(A); t2 = c.feed(A)
ck(t1 == t2, 'terminal idempotent (supervisor stops on first)')
# 8: GS mismatch
c = chain(); c.feed(kd); c.feed(gs)
c.feed(A.replace('gs=95bfab6122539993', 'gs=0000000000000000')); ck(c.result == 'invalid', 'gs mismatch')
# 9: truncated line is a parse error, not a hit
c = chain(); c.feed(kd); c.feed(gs)
c.feed(A.rsplit(' ', 1)[0]); ck(c.result == 'invalid', 'truncated intent invalid')
# 10: unknown/inactive/active all complete
for v in ('unknown', 'inactive', 'active'):
    c = chain(); c.feed(kd); c.feed(gs)
    ck(c.feed(A.replace('active=inactive', 'active=' + v)) == 'hit (tf-intent chain)', 'any active completes: ' + v)

# launcher: default is preflight-only, no child, no real sysctl/vm_stat/ps
import launcher
def boom(*a, **k): raise AssertionError('real process/sampler call attempted: %r' % (a[:1],))
saved = (subprocess.Popen, subprocess.run, os.popen, os.system)
subprocess.Popen = subprocess.run = boom; os.popen = boom; os.system = boom
try:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = launcher.main() if False else None
    # launcher.main() parses sys.argv; call it explicitly with an empty argument list
    old = sys.argv; sys.argv = ['launcher.py']
    try:
        with contextlib.redirect_stdout(out):
            rc = launcher.main()
    finally:
        sys.argv = old
    txt = out.getvalue()
    ck(rc == 0, 'preflight-only rc 0')
    ck('launch=not-requested' in txt and 'NOT_CREATED' in txt, 'no run/child')
    ck('DM_NVN_TF_DIAG=1' in txt, 'TF diag env in child config')
    ck('"2800"' in txt and '"10"' in txt and '"180"' in txt, 'thresholds unchanged')
    ck(sys.executable in txt, 'argv uses sys.executable')
    # --launch refusals do not create directories
    sys.argv = ['launcher.py', '--launch', '--run', 'relative/path']
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc2 = launcher.main()
    sys.argv = ['launcher.py']
    ck(rc2 == 3, 'relative run refused')
    tmp = tempfile.mkdtemp()
    sys.argv = ['launcher.py', '--launch', '--run', tmp]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc3 = launcher.main()
    sys.argv = ['launcher.py']
    ck(rc3 == 3, 'existing run refused')
finally:
    subprocess.Popen, subprocess.run, os.popen, os.system = saved

print('fails:', len(fails))
sys.exit(1 if fails else 0)
