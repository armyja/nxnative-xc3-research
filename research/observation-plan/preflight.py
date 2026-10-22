#!/usr/bin/env python3
"""Read-only fixed-identity preflight for the gs-res observation. No host/child/gate/guest."""
import argparse, hashlib, json, os, sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,'/path/to/user/projects/nxnative-xc3/dm/gfx/tools')
import dmsh_refill
def sha(p):
 try:
  with open(p,'rb') as f: return hashlib.sha256(f.read()).hexdigest()
 except OSError: return None
def tree(paths):
 h=hashlib.sha256()
 for p in sorted(paths,key=lambda x:os.path.basename(x)):
  h.update(os.path.basename(p).encode()+b'\0'+(hashlib.sha256(open(p,'rb').read()).digest() if os.path.isfile(p) else b''))
 return h.hexdigest()
def rows(p):
 return sum(1 for ln in open(p) if ln.strip() and not ln.startswith('#'))
def check(idp=None):
 ident=json.load(open(idp or os.path.join(HERE,'identity.json')))
 errs=[]
 def eq(label,path,want):
  got=sha(path)
  if got!=want: errs.append(f'{label}: sha {got} != {want} ({path})')
 eq('host',ident['host'],ident['host_sha']); eq('nvn_mtl',ident['nvn_mtl'],ident['nvn_mtl_sha']); eq('nvn_kd_res',ident['nvn_kd_res'],ident['nvn_kd_res_sha'])
 eq('nvn_tf_diag',ident['nvn_tf_diag'],ident['nvn_tf_diag_sha']); eq('nvn_obj',ident['nvn_obj'],ident['nvn_obj_sha'])
 eq('parser',ident['parser'],ident['parser_sha']); eq('supervisor',ident['supervisor'],ident['supervisor_sha']); eq('launcher',ident['launcher'],ident['launcher_sha'])
 for n in ('shader_map.tsv','shader_pairs.tsv','shader_facts.tsv','game.tsv','dmsh_chain.h','c1_full.tsv'):
  if not os.path.isfile(os.path.join(ident['profile'],n)): errs.append('profile missing '+n)
 try:
  if open(os.path.join(ident['profile'],'dmsh_chain.h')).read().find(ident['chain']) < 0: errs.append('chain macro mismatch')
  if rows(os.path.join(ident['profile'],'shader_facts.tsv'))!=ident['facts_rows']: errs.append('facts rows')
  if rows(os.path.join(ident['profile'],'shader_map.tsv'))!=ident['map_rows']: errs.append('map rows')
  if rows(os.path.join(ident['profile'],'shader_pairs.tsv'))!=ident['pairs_rows']: errs.append('pairs rows')
  eq('map',os.path.join(ident['profile'],'shader_map.tsv'),ident['map_sha']); eq('pairs',os.path.join(ident['profile'],'shader_pairs.tsv'),ident['pairs_sha'])
  eq('facts',os.path.join(ident['profile'],'shader_facts.tsv'),ident['facts_sha']); eq('game',os.path.join(ident['profile'],'game.tsv'),ident['game_sha'])
  eq('chain',os.path.join(ident['profile'],'dmsh_chain.h'),ident['chain_sha']); eq('c1',os.path.join(ident['profile'],'c1_full.tsv'),ident['c1_sha'])
 except OSError as e: errs.append(str(e))
 # production validators
 try:
  keys,probs=dmsh_refill.validate_map(os.path.join(ident['profile'],'shader_map.tsv'),ident['pkg_dir'])
  errs += ['map: '+p for p in probs]
  errs += ['pairs: '+p for p in dmsh_refill.validate_pairs(os.path.join(ident['profile'],'shader_pairs.tsv'),keys)]
  pkgs=sorted(os.path.join(ident['pkg_dir'],n) for n in os.listdir(ident['pkg_dir']))
  if len(pkgs)!=645: errs.append('pkg count %d != 645'%len(pkgs))
  if tree(pkgs)!=ident['pkg_tree_sha']: errs.append('pkg tree sha')
  lib=ident['out_dir']
  jf=sorted(os.path.join(lib,n) for n in os.listdir(lib) if n.endswith('.json'))
  if tree(jf)!=ident['json_tree_sha']: errs.append('json tree sha')
  for k in sorted(keys):
   for suf in ('_b.json','_b.metal','_b.metallib'):
    if not os.path.isfile(os.path.join(lib,k+suf)): errs.append('key artifact missing '+k+suf)
   jp=os.path.join(lib,k+'_b.json')
   try:
    jj=json.load(open(jp))
    if jj.get('chain')!=ident['chain'] or not str(jj.get('key','')).startswith(k): errs.append('json key/chain '+k)
   except Exception as e: errs.append('json parse '+k+': '+str(e))
 except Exception as e: errs.append('validator: %s'%e)
 # package output list
 try:
  out=ident['out_dir']; names=os.listdir(out)
  metal=sorted(os.path.join(out,n) for n in names if n.endswith('.metallib'))
  bf=sorted(os.path.join(out,n) for n in names if n.endswith('_bf.metallib'))
  if len(metal)!=ident['metal_count']: errs.append('metal count %d'%len(metal))
  if len(bf)!=72: errs.append('bf count %d'%len(bf))
  if tree(metal)!=ident['metal_tree_sha']: errs.append('metal tree sha')
  if tree(bf)!=ident['bf_tree_sha']: errs.append('bf tree sha')
 except OSError as e: errs.append('out: '+str(e))
 # patched baseline
 if not os.path.isdir(ident['patched_dir']): errs.append('patched is not a directory')
 for n,w in ident['patched'].items(): eq('patched/'+n,os.path.join(ident['patched_dir'],n),w)
 # real exemptions (read-only)
 try:
  exf=ident['exempt_file']
  if sha(exf)!=ident['exempt_file_sha']: errs.append('runtime exempt file sha')
  ex=json.load(open(exf))
  if ex!=ident['exempt']: errs.append('runtime exempt values')
  if set(ex)!=set(ident['exempt']): errs.append('exempt key set')
  for k,v in ident['exempt'].items():
   b=ident['exempt_path']; ctl=open(os.path.join(b,k+'.ctl'),'rb').read(); code=open(os.path.join(b,k+'.code'),'rb').read()
   if len(ctl)!=v['ctl'] or len(code)!=v['code'] or hashlib.sha256(ctl).hexdigest()!=v['ctl_sha'] or hashlib.sha256(code).hexdigest()!=v['code_sha']:
    errs.append('exempt mismatch '+k)
 except Exception as e: errs.append('exempt: %s'%e)
 return ident,errs
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--identity'); a=ap.parse_args()
 ident,errs=check(a.identity)
 print('preflight-only identity=%s'%json.dumps({k:ident[k] for k in ('host_sha','nvn_mtl_sha','nvn_kd_res_sha','parser_sha','supervisor_sha','chain')}))
 if errs:
  for e in errs: print('PREFLIGHT-FAIL',e)
  return 2
 print('PREFLIGHT-OK host=%s profile=%s chain=%s exemptions=2 map=645 pairs=90'%(ident['host'],ident['profile'],ident['chain']))
 return 0
if __name__=='__main__': sys.exit(main())
