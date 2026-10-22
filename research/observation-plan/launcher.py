#!/usr/bin/env python3
"""Default preflight-only launcher. Contract mirrors run-kdgeom.sh; --test-supervisor is test-only."""
import argparse, hashlib, json, os, subprocess, sys
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import preflight
SYS={'PATH','HOME','TMPDIR','LANG','LC_ALL','TZ'}
RUN_ROOT='/path/to/external-drive/xc3/work/experiments'   # run paths must live on this volume
FORBIDDEN=('IMGSUP_TEST_','DM_NVN_IMGBIND','DM_NVN_PSOFAIL_RT','DM_NVN_SSBO_OBS','DM_NVN_BINDAUDIT','DM_NVN_SKIP','DM_NVN_OVERRIDE')
def sha(p):
 try: return hashlib.sha256(open(p,'rb').read()).hexdigest()
 except OSError: return None
def check_run_path(run):
    """Return (ok, why). Enforced before any directory creation or child start: absolute, not existing, inside
    RUN_ROOT after resolving the nearest existing ancestor, and that ancestor must be on the same device (st_dev).
    This is a mount-path/volume identity check; it does not prove anything about the physical drive."""
    if not run or not os.path.isabs(run):
        return False, 'run path must be an absolute path'
    if os.path.exists(run):
        return False, 'run path already exists'
    root = os.path.realpath(RUN_ROOT)
    try:
        root_dev = os.stat(root).st_dev
    except OSError as x:
        return False, 'run root unavailable: %s' % x
    anc = os.path.dirname(os.path.realpath(run))
    while anc and not os.path.exists(anc):
        nxt = os.path.dirname(anc)
        if nxt == anc: break
        anc = nxt
    if not anc or not os.path.isdir(anc):
        return False, 'no existing ancestor for run path'
    # The canonical ancestor must sit under the canonical root, and live on the root's device (no symlink escape, no other volume).
    if anc != root and not anc.startswith(root + os.sep):
        return False, 'run path escapes %s (resolved ancestor %s)' % (root, anc)
    try:
        if os.stat(anc).st_dev != root_dev:
            return False, 'run path is on a different volume'
    except OSError as x:
        return False, 'cannot stat ancestor: %s' % x
    return True, 'ok'

def config(ident, run):
 c=ident
 cfg={
  'DM_ROMFS':'/path/to/external-drive/xc3/build/RomFS',
  'DM_SAVE':os.path.join(run,'save') if run else '',
  'DM_TEMP':os.path.join(run,'temp') if run else '',
  'DM_MSL_DIR':c['msl_dir'],
  'DM_NVN_SHMAP':os.path.join(c['profile'],'shader_map.tsv'),
  'DM_NVN_SHDUMP':os.path.join(run,'shdump') if run else '',
  'DM_PSO_RECORD':os.path.join(run,'pso_user.tsv') if run else '',
  'DM_MEMSTAT':os.path.join(run,'memstat.tsv') if run else '',
  'DM_KEYS':'f1500:A~0.2,f2100:Plus~0.2,f2700:A~0.2,f3200:A~0.2,f3700:A~0.2,f4200:A~0.2',
  'DM_LANG':'en-GB','DM_AUDIO':'0',
  'DM_NVN_KEYDUMP':'2e16c536b845ea0e:1','DM_NVN_GSRES':'95bfab6122539993:2e16c536b845ea0e',
  'DM_NVN_TF_DIAG':'1',
 }
 return cfg
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--launch',action='store_true'); ap.add_argument('--run')
 ap.add_argument('--test-supervisor'); a=ap.parse_args()
 ident,errs=preflight.check()
 if errs:
  for e in errs: print('PREFLIGHT-FAIL',e)
  return 4
 # production identity binding: supervisor/host/patched are not overridable
 sup=ident['supervisor']
 if a.test_supervisor:
  sup=a.test_supervisor
 elif sha(sup)!=ident['supervisor_sha']:
  print('PREFLIGHT-FAIL supervisor sha',file=sys.stderr); return 4
 print('preflight-only: host=%s sha=%s supervisor=%s sha=%s chain=%s patched_dir=%s'%(ident['host'],ident['host_sha'],sup,sha(sup),ident['chain'],ident['patched_dir']))
 cfg=config(ident,a.run if a.launch else None)
 print('child DM configuration:'); [print('  %s=%s'%(k,v)) for k,v in cfg.items()]
 if not a.launch:
  av=[sys.executable,sup,'--host',ident['host'],'--patched',ident['patched_dir'],'--run','<RUN>','--secs','180','--gate-secs','10','--gate-mib','2800','--exempt-json',ident['exempt_file']]
  print('launch-route argv='+json.dumps(av))
  print('launch=not-requested run_dir=NOT_CREATED child=NOT_STARTED'); return 0
 ok, why = check_run_path(a.run or '')
 if not ok:
  print('LAUNCH-REFUSED %s' % why,file=sys.stderr); return 3
 bad=[k for k in os.environ if any(k.startswith(p) or k==p for p in FORBIDDEN)]
 if bad: print('LAUNCH-REFUSED forbidden inherited env: %s'%bad,file=sys.stderr); return 3
 for sub in ('save','temp','shdump'): os.makedirs(os.path.join(a.run,sub))
 env={k:v for k,v in os.environ.items() if k in SYS}
 env.update(cfg)
 if sha(sup)!=ident['supervisor_sha'] and not a.test_supervisor:
  print('LAUNCH-REFUSED supervisor changed',file=sys.stderr); return 3
 cmd=[sys.executable,sup,'--host',ident['host'],'--patched',ident['patched_dir'],'--run',a.run,'--secs','180','--gate-secs','10','--gate-mib','2800','--exempt-json',ident['exempt_file']]
 print('launch-route argv='+json.dumps(cmd)); r=subprocess.run(cmd,env=env); return r.returncode
if __name__=='__main__': sys.exit(main())
