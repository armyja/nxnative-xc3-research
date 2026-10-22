"""Strict parser for the production [gs-res] record emitted by dm/gfx/nvn/nvn_kd_res.h kdr_format.
No target selection, no cross-line state, no host/renderer dependency."""
import re

HEX16 = re.compile(r'^[0-9a-f]{16}$')
HEX32 = re.compile(r'^[0-9a-f]{32}$')
HEX4 = re.compile(r'^[0-9a-f]{4}$')
U64 = re.compile(r'^(?:0x[0-9a-f]+|[0-9]+)$')
I32 = re.compile(r'^-?(?:0x[0-9a-f]+|[0-9]+)$')
U32 = re.compile(r'^(?:0x[0-9a-f]+|[0-9]+)$')
DIM = re.compile(r'^([0-9]+)x([0-9]+)x([0-9]+)$')
SLOT = re.compile(r'^(tex|samp)([0-9]+)$')

class ParseError(ValueError):
    pass

def _int(s, what):
    if not isinstance(s,str) or not s: raise ParseError(f'{what}: empty')
    neg = s.startswith('-')
    t = s[1:] if neg else s
    if t.startswith('0x'):
        if not re.match(r'^0x[0-9a-f]+$', t): raise ParseError(f'{what}: bad hex {s!r}')
        v = int(t[2:],16)
    else:
        if not re.match(r'^[0-9]+$', t): raise ParseError(f'{what}: bad decimal {s!r}')
        v = int(t,10)
    return -v if neg else v

def _u64(s, what):
    v=_int(s,what)
    if v<0 or v>2**64-1: raise ParseError(f'{what}: u64 range')
    return v

def _i32(s, what):
    v=_int(s,what)
    if not -2**31 <= v <= 2**31-1: raise ParseError(f'{what}: i32 range')
    return v

def _u32(s, what, hi=2**32-1):
    v=_int(s,what)
    if not 0 <= v <= hi: raise ParseError(f'{what}: u32 range')
    return v

def _hex32(s, what):
    if not HEX32.match(s): raise ParseError(f'{what}: bad 32hex {s!r}')
    return int(s, 16)

class _Stream:
    def __init__(self, toks):
        self.t = toks; self.i = 0
    def name(self):
        if self.i >= len(self.t): raise ParseError('truncated record')
        n = self.t[self.i]; self.i += 1
        return n
    def kv(self, want):
        n = self.name()
        if '=' not in n: raise ParseError(f'expected {want}, got anonymous {n!r}')
        k, v = n.split('=', 1)
        if k != want: raise ParseError(f'expected {want}, got {k}')
        return v
    def anon(self, what):
        n = self.name()
        if '=' in n: raise ParseError(f'expected {what}, got {n!r}')
        return n
    def done(self):
        if self.i != len(self.t): raise ParseError(f'extra tokens: {" ".join(self.t[self.i:])[:80]}')


KD_RE = re.compile(r'^\[kd\] F([0-9]+) pass ([0-9]+) vs=(\S+) fs=(\S+) prim (-?[0-9]+) vertices (-?[0-9]+) instances (-?[0-9]+) '
                   r'first (-?[0-9]+) base_vertex (-?[0-9]+) base_instance (-?[0-9]+) target (\S+)$')

def parse_kd(line):
    if not isinstance(line,str): return None
    s=line.rstrip('\n\r')
    m=KD_RE.match(s)
    if not m: raise ParseError('bad [kd] header')
    if not HEX16.match(m.group(3)) and not re.match(r'^[0-9a-f]{16}(?:_[a-z0-9]+)?$',m.group(3)):
        raise ParseError('kd vs token')
    if not re.match(r'^[0-9a-f]{16}(?:_[a-z0-9]+)?$',m.group(4)) and not re.match(r'^[0-9a-f]{16}(?:_[a-z0-9]+)?$',m.group(4)):
        raise ParseError('kd ps token')
    nums=[_u64(m.group(1),'kd frame'),_u64(m.group(2),'kd pass')]
    for i in (5,6,7,8,9,10): nums.append(_i32(m.group(i),'kd int'))
    return {'frame':nums[0],'pass_counter':nums[1],'vs':m.group(3),'ps':m.group(4),'prim':nums[2],
            'vertices':nums[3],'instances':nums[4],'first':nums[5],'base_vertex':nums[6],'base_instance':nums[7],
            'target':m.group(11)}

def parse_gs_res(line):
    """Return dict or None when the line is not a gs-res record. Raises ParseError when a gs-res line is malformed."""
    if not isinstance(line, str): return None
    s = line.rstrip('\n\r')
    # Host logging may prefix [dm] [nvn-mtl] ; kdr_format itself starts [gs-res].
    if s.startswith('[dm] [nvn-mtl] '): s = s[len('[dm] [nvn-mtl] '):]
    if not s.startswith('[gs-res] '): return None
    toks = s.split()
    if not toks or toks[0] != '[gs-res]':
        raise ParseError('bad gs-res marker')
    st = _Stream(toks[1:])
    r = {'raw': line.rstrip('\n\r')}
    r['result'] = st.kv('result')
    if r['result'] not in ('hit','target-not-obtained','identity-unavailable','no-geometry-source','gs-key-mismatch','diagnostic-error','invalid-config'):
        raise ParseError('bad result')
    r['vs'] = st.kv('vs'); r['ps'] = st.kv('ps'); r['ps_style'] = st.kv('ps_style')
    def keyform(tok, what, allow_dash=False):
        if allow_dash and tok=='-': return {'base':None,'suffix':'absent','form':'absent'}
        m=re.match(r'^([0-9a-f]{16})(?:_([a-z0-9]+))?$',tok)
        if not m: raise ParseError(f'{what}: bad key token {tok!r}')
        suf=m.group(2) or ''
        form=suf if suf in ('','b','bf') else 'other'
        return {'base':m.group(1),'suffix':suf,'form':form}
    r['vs_form']=keyform(r['vs'],'vs',True); r['ps_form']=keyform(r['ps'],'ps')
    exp=r['ps_form']['form']
    if r['ps_style'] not in ('bare','_b','_bf','other'): raise ParseError('ps_style')
    if r['ps_form']['suffix']=='' and r['ps_style']!='bare': raise ParseError('ps_style suffix')
    if r['ps_form']['suffix']=='b' and r['ps_style']!='_b': raise ParseError('ps_style suffix')
    if r['ps_form']['suffix']=='bf' and r['ps_style']!='_bf': raise ParseError('ps_style suffix')
    if r['ps_form']['form']=='other' and r['ps_style']!='other': raise ParseError('ps_style suffix')
    r['frame'] = _u64(st.kv('frame'),'frame'); r['pass_counter'] = _u64(st.kv('pass_counter'),'pass_counter')
    if st.kv('final_pass_association') != 'none': raise ParseError('final_pass_association')
    r['drawkind'] = st.kv('drawkind')
    if r['drawkind'] not in ('direct','indexed'): raise ParseError('drawkind')
    r['prim'] = _i32(st.kv('prim'),'prim')
    c=st.kv('count'); ins=st.kv('instances'); bi=st.kv('base_instance')
    r['indirect'] = _u32(st.kv('indirect'),'indirect',1)
    if r['indirect']:
        if (c,ins,bi) != ('unavailable','unavailable','unavailable'):
            raise ParseError('indirect counts')
        r['count']=r['instances']=r['base_instance']=None
    else:
        if c=='unavailable' or ins=='unavailable' or bi=='unavailable': raise ParseError('direct unavailable counts')
        r['count']=_i32(c,'count'); r['instances']=_i32(ins,'instances'); r['base_instance']=_i32(bi,'base_instance')
    r['gs_present']=_u32(st.kv('gs_present'),'gs_present',1)
    r['nstage']=_u32(st.kv('nstage'),'nstage')
    r['gs_query_calls']=_u32(st.kv('gs_query_calls'),'gs_query_calls')
    if r['nstage'] <= 6:
        if r['gs_query_calls'] != r['nstage']: raise ParseError('query/nstage mismatch')
    else:
        if r['gs_query_calls'] != 0: raise ParseError('query/nstage mismatch (>6)')
    keysv=st.kv('keys')
    r['keys']=keysv.split(',') if keysv else []
    wantkeys = r['nstage'] if r['nstage'] <= 6 else 6
    if len(r['keys']) != wantkeys: raise ParseError('keys length != nstage/capacity')
    for k in r['keys']:
        if k!='unknown' and not HEX16.match(k): raise ParseError('key entry')
    r['ubo_avail']=_u32(st.kv('ubo_avail'),'ubo_avail',1)
    um=st.kv('ubo_mask')
    if not HEX4.match(um): raise ParseError('ubo_mask')
    r['ubo_mask']=int(um,16)
    r['ubo0']=st.kv('ubo0')
    if r['ubo0'] not in ('present','unavailable'): raise ParseError('ubo0')
    r['ubo0_addr']=_u64(st.kv('addr'),'ubo addr'); r['ubo0_size']=_u64(st.kv('size'),'ubo size')
    if st.kv('contents')!='unavailable': raise ParseError('contents')
    # textures
    r['tex_avail']=_u32(st.kv('tex_avail'),'tex_avail',1)
    tm=st.kv('tex_mask'); r['tex_mask']=_hex32(tm,'tex_mask')
    r['tex_n']=_u32(st.kv('tex_n'),'tex_n'); r['tex_omitted']=_u32(st.kv('tex_omitted'),'tex_omitted')
    r['tex_slots']=[]
    if r['tex_avail']==0 and (r['tex_n']!=0 or r['tex_mask']!=0 or r['tex_omitted']!=0): raise ParseError('tex unavailable nonempty')
    for _ in range(r['tex_n']):
        n=st.name()
        if '=' not in n: raise ParseError(f'expected tex slot, got {n!r}')
        key,val=n.split('=',1); m=SLOT.match(key)
        if not m or m.group(1)!='tex': raise ParseError(f'expected tex slot, got {n!r}')
        idx=int(m.group(2)); r['tex_slots'].append((idx,_u64(val,'tex slot')))
    # samplers
    r['samp_avail']=_u32(st.kv('samp_avail'),'samp_avail',1)
    sm=st.kv('samp_mask'); r['samp_mask']=_hex32(sm,'samp_mask')
    r['samp_n']=_u32(st.kv('samp_n'),'samp_n'); r['samp_omitted']=_u32(st.kv('samp_omitted'),'samp_omitted')
    r['samp_slots']=[]
    if r['samp_avail']==0 and (r['samp_n']!=0 or r['samp_mask']!=0 or r['samp_omitted']!=0): raise ParseError('samp unavailable nonempty')
    for _ in range(r['samp_n']):
        n=st.name()
        if '=' not in n: raise ParseError(f'expected samp slot, got {n!r}')
        key,val=n.split('=',1); m=SLOT.match(key)
        if not m or m.group(1)!='samp': raise ParseError(f'expected samp slot, got {n!r}')
        idx=int(m.group(2)); r['samp_slots'].append((idx,_u64(val,'samp slot')))
    for pref,slots,mask,n,om in (('tex',r['tex_slots'],r['tex_mask'],r['tex_n'],r['tex_omitted']),
                                  ('samp',r['samp_slots'],r['samp_mask'],r['samp_n'],r['samp_omitted'])):
        avail=(r['tex_avail'] if pref=='tex' else r['samp_avail'])
        if avail==0:
            if slots or n!=0 or mask!=0 or om!=0: raise ParseError(pref+' unavailable slots')
        else:
            if not slots or slots[0][0]!=0: raise ParseError(pref+' slot0')
            if len(slots)>9: raise ParseError(pref+' too many slots')
            if len({i for i,_ in slots})!=len(slots): raise ParseError(pref+' duplicate slot')
            if any(slots[i][0]>=slots[i+1][0] for i in range(len(slots)-1)): raise ParseError(pref+' slot order')
            if any(i<0 or i>127 for i,_ in slots): raise ParseError(pref+' slot range')
            nz=sum(1 for _,v in slots if v!=0); pop=bin(mask).count('1')
            if nz>pop: raise ParseError(pref+' mask/listed')
            if any(v!=0 and not (mask>>i)&1 for i,v in slots): raise ParseError(pref+' mask missing')
            if any(v==0 and (mask>>i)&1 for i,v in slots): raise ParseError(pref+' zero/mask')
            if n!=len(slots): raise ParseError(pref+' n')
            if om!=pop-nz: raise ParseError(pref+' omitted')
    # tex candidate
    r['tex_candidate']=_u32(st.kv('tex_candidate'),'tex_candidate',1)
    r['tex_raw']=_u64(st.kv('raw'),'tex raw')
    r['tex_hint']=st.kv('hint'); r['tex_hint_ser']=_u64(st.kv('hint_ser'),'hint_ser')
    r['tex_registry_checked']=_u32(st.kv('registry_checked'),'tex registry_checked',1)
    r['tex_registered']=_u32(st.kv('registered'),'tex registered',1)
    r['tex_desc']=st.kv('desc')
    r['tex_target']=_i32(st.kv('target'),'tex target'); r['tex_format']=_i32(st.kv('format'),'tex format')
    dim=st.anon('tex dimensions'); m=DIM.match(dim)
    if not m: raise ParseError('tex dimensions')
    r['tex_w'],r['tex_h'],r['tex_d']=[_u32(x,'tex dim') for x in m.groups()]
    r['tex_samples']=_u32(st.kv('samples'),'tex samples')
    r['tex_reg_serial']=_u64(st.kv('reg_serial'),'tex reg_serial')
    if r['tex_candidate']==0:
        if r['tex_raw']!=0 or r['tex_hint']!='unavailable' or r['tex_hint_ser']!=0 or r['tex_registry_checked']!=0 or r['tex_registered']!=0 or r['tex_desc']!='unavailable': raise ParseError('tex candidate0 contract')
    else:
        if r['tex_raw']==0: raise ParseError('tex candidate raw0')
        if r['tex_avail']==0 or not r['tex_slots'] or r['tex_slots'][0][1]!=r['tex_raw']: raise ParseError('tex raw != tex0')
        if r['tex_hint'] not in ('present','unavailable'): raise ParseError('tex hint')
        if r['tex_desc'] not in ('present','unavailable'): raise ParseError('tex desc')
        if r['tex_registered'] and r['tex_desc']!='present': raise ParseError('tex registered/desc')
    # sampler candidate
    r['samp_candidate']=_u32(st.kv('samp_candidate'),'samp_candidate',1)
    r['samp_raw']=_u64(st.kv('raw'),'samp raw')
    r['samp_sid64']=_u64(st.kv('sid_u64'),'sid_u64')
    r['samp_registry_checked']=_u32(st.kv('registry_checked'),'samp registry_checked',1)
    r['samp_registered']=_u32(st.kv('registered'),'samp registered',1)
    r['samp_desc']=st.kv('desc')
    for k in ('minf','magf'): r['samp_'+k]=_u32(st.kv(k),k)
    wrap=st.kv('wrap').split(',')
    if len(wrap)!=3: raise ParseError('wrap')
    r['samp_ws'],r['samp_wt'],r['samp_wr']=[_u32(x,'wrap') for x in wrap]
    cmp=st.kv('cmp').split('/')
    if len(cmp)!=2: raise ParseError('cmp')
    r['samp_cmp_mode'],r['samp_cmp_func']=[_u32(x,'cmp') for x in cmp]
    lod=st.kv('lod_bits').split(',')
    if len(lod)!=3: raise ParseError('lod_bits')
    if any(not re.match(r'^[0-9a-f]{8}$',x) for x in lod): raise ParseError('lod_bits format')
    r['samp_lod_bits']=[int(x,16) for x in lod]
    an=st.kv('aniso_bits')
    if not re.match(r'^[0-9a-f]{8}$',an): raise ParseError('aniso_bits format')
    r['samp_aniso_bits']=int(an,16)
    bor=st.kv('border_bits').split(',')
    if len(bor)!=4 or any(not re.match(r'^[0-9a-f]{8}$',x) for x in bor): raise ParseError('border_bits')
    r['samp_border_bits']=[int(x,16) for x in bor]
    if st.kv('reg_serial')!='unavailable': raise ParseError('sampler reg_serial')
    if r['samp_candidate']==0:
        if r['samp_raw']!=0 or r['samp_desc']!='unavailable' or r['samp_registry_checked']!=0 or r['samp_registered']!=0: raise ParseError('samp candidate0 contract')
    else:
        if r['samp_raw']==0: raise ParseError('samp candidate raw0')
        if r['samp_sid64'] != (r['samp_raw']>>20): raise ParseError('sid != raw>>20')
        if r['samp_desc'] not in ('present','unavailable'): raise ParseError('samp desc')
        if r['samp_registered'] and r['samp_desc']!='present': raise ParseError('samp registered/desc')
    if r['tex_candidate'] and r['samp_candidate'] and r['samp_raw'] != r['tex_raw']:
        raise ParseError('sampler raw != combined tex raw')
    if st.kv('tf')!='unknown': raise ParseError('tf')
    if st.kv('bind_source')!='current_S_state': raise ParseError('bind_source')
    st.done()
    return r

def validate_record(r):
    """Production-wrapper consistency that is determined by kd_res_line; no registry capacity/enum semantics."""
    if r is None: raise ParseError('no record')
    hit = r['result']=='hit'
    if hit:
        if r['gs_present']!=1: raise ParseError('hit gs_present')
        if not (1 <= r['nstage'] <= 6): raise ParseError('hit nstage')
        if not (r['ubo_avail']==1 and r['tex_avail']==1 and r['samp_avail']==1): raise ParseError('hit resource availability')
    else:
        if any((r['ubo_avail'],r['tex_avail'],r['samp_avail'])): raise ParseError('nonhit resource availability')
        if r['ubo_mask'] or r['ubo0']!='unavailable' or r['ubo0_addr'] or r['ubo0_size']: raise ParseError('nonhit ubo placeholder')
        if r['tex_n'] or r['tex_mask'] or r['tex_omitted'] or r['tex_slots']: raise ParseError('nonhit tex placeholder')
        if r['samp_n'] or r['samp_mask'] or r['samp_omitted'] or r['samp_slots']: raise ParseError('nonhit samp placeholder')
        for k in ('tex_candidate','tex_raw','tex_hint_ser','tex_registry_checked','tex_registered','tex_target','tex_format','tex_w','tex_h','tex_d','tex_samples','tex_reg_serial','samp_candidate','samp_raw','samp_sid64','samp_registry_checked','samp_registered','samp_minf','samp_magf','samp_ws','samp_wt','samp_wr','samp_cmp_mode','samp_cmp_func','samp_aniso_bits'):
            if r[k]!=0: raise ParseError('nonhit placeholder '+k)
        if r['tex_hint']!='unavailable' or r['tex_desc']!='unavailable' or r['samp_desc']!='unavailable': raise ParseError('nonhit unavailable')
        return r
    # hit: wrapper unconditionally sets these before resources are copied
    if r['ubo0']!='present': raise ParseError('hit ubo0')
    bit0=1 if (r['ubo0_addr'] or r['ubo0_size']) else 0
    if ((r['ubo_mask']>>0)&1)!=bit0: raise ParseError('ubo mask0')
    # tex candidate is exactly raw slot0 nonzero; hint iff low20 tid nonzero
    tex0=r['tex_slots'][0][1]
    if r['tex_candidate'] != (1 if tex0 else 0): raise ParseError('tex candidate/raw')
    if r['tex_raw']!=tex0: raise ParseError('tex raw/slot0')
    tid=tex0 & 0xfffff
    if r['tex_candidate'] and tid:
        if r['tex_hint']!='present': raise ParseError('tex hint')
    else:
        if r['tex_hint']!='unavailable' or r['tex_hint_ser']!=0: raise ParseError('tex hint unavailable')
    if r['tex_registered']:
        if not r['tex_registry_checked'] or r['tex_desc']!='present': raise ParseError('tex registered/desc')
    else:
        if r['tex_desc']!='unavailable': raise ParseError('tex desc without registered')
        if any((r['tex_target'],r['tex_format'],r['tex_w'],r['tex_h'],r['tex_d'],r['tex_samples'],r['tex_reg_serial'])): raise ParseError('tex desc placeholder')
    if r['tex_candidate'] and r['tex_registry_checked'] and not r['tex_registered'] and r['tex_desc']=='present': raise ParseError('tex desc')
    # sampler is derived from the same combined tex raw, never from S.samp0
    if r['samp_candidate'] != r['tex_candidate'] or r['samp_raw'] != tex0: raise ParseError('sampler candidate/raw')
    if r['samp_registered']:
        if not r['samp_registry_checked'] or r['samp_desc']!='present': raise ParseError('samp registered/desc')
    else:
        if r['samp_desc']!='unavailable': raise ParseError('samp desc without registered')
        if any((r['samp_minf'],r['samp_magf'],r['samp_ws'],r['samp_wt'],r['samp_wr'],r['samp_cmp_mode'],r['samp_cmp_func'],r['samp_aniso_bits'])) or any(r['samp_lod_bits']) or any(r['samp_border_bits']): raise ParseError('samp desc placeholder')
    return r

class GsResStateMachine:
    """Pure [kd] -> [gs-res] matcher. Constructor targets are GS/PS base keys; no XC3 constants in the parser."""
    _CTRL = {
        '[gs-res] invalid DM_NVN_GSRES; observer closed': ('invalid-config','invalid DM_NVN_GSRES switch'),
        '[gs-res] diagnostic-error: identity copy overflow; observer closed': ('diagnostic-error','identity copy diagnostic'),
        '[gs-res] diagnostic-error: record formatting overflow; observer closed': ('diagnostic-error','record formatting diagnostic'),
    }
    def __init__(self, target_gs, target_ps):
        if not HEX16.match(target_gs) or not HEX16.match(target_ps): raise ValueError('bad target')
        self.target_gs=target_gs; self.target_ps=target_ps
        self.hdr=None; self.terminal=None; self.result=None; self.raw=[]; self.record=None
    def _term(self, result, why):
        if self.terminal is None:
            self.terminal=why; self.result=result
        return self.terminal
    @staticmethod
    def _identity(r, target_gs):
        """Return the wrapper-reachable result or raise ParseError for field contradictions."""
        if r['gs_present']==0:
            if r['nstage']!=0 or r['gs_query_calls']!=0 or r['keys']: raise ParseError('present0 fields')
            return 'no-geometry-source'
        if r['nstage']==0 or r['nstage']>6:
            if r['gs_query_calls']!=0: raise ParseError('capacity query nonzero')
            want=0 if r['nstage']==0 else 6
            if len(r['keys'])!=want or any(k!='unknown' for k in r['keys']): raise ParseError('capacity known keys')
            return 'identity-unavailable'
        if r['gs_query_calls']!=r['nstage']: raise ParseError('query/nstage')
        known=[k for k in r['keys'] if k!='unknown']
        if target_gs in known: return 'hit'
        if len(known)!=len(r['keys']): return 'identity-unavailable'
        return 'gs-key-mismatch'
    def feed(self, line):
        if self.terminal is not None: return self.terminal
        s=line.rstrip('\n\r')
        if s.startswith('[kd]'):
            if self.hdr is not None: return self._term('invalid','duplicate [kd] header')
            try: h=parse_kd(s)
            except ParseError as e: return self._term('invalid',str(e))
            self.raw.append(s)
            ps=h['ps']; m=re.match(r'^([0-9a-f]{16})(?:_([a-z0-9]+))?$',ps)
            if not m: return self._term('invalid','bad header PS token')
            base=m.group(1); suf=m.group(2) or ''
            if base != self.target_ps or suf not in ('','b'):
                return self._term('target-not-obtained','first complete [kd] PS/suffix is not normal target')
            self.hdr=h
            return None
        if s.startswith('[gs-res]') or s.startswith('[dm] [nvn-mtl] [gs-res]'):
            body = s[len('[dm] [nvn-mtl] '):] if s.startswith('[dm] [nvn-mtl] ') else s
            if body in self._CTRL:
                res,why=self._CTRL[body]; return self._term(res,why)
            if self.hdr is None: return self._term('invalid','gs-res before [kd] header')
            self.raw.append(s)
            try:
                r=parse_gs_res(body)
                validate_record(r)
            except ParseError as e:
                return self._term('invalid','gs-res parse/validate: %s'%e)
            self.record=r
            if r['vs']!=self.hdr['vs'] or r['ps']!=self.hdr['ps']: return self._term('invalid','record VS/PS differs from header')
            if r['frame']!=self.hdr['frame'] or r['pass_counter']!=self.hdr['pass_counter']: return self._term('invalid','record frame/pass differs')
            if r['prim']!=self.hdr['prim']: return self._term('invalid','record prim differs')
            if not r['indirect']:
                if (r['count'],r['instances'],r['base_instance'])!=(self.hdr['vertices'],self.hdr['instances'],self.hdr['base_instance']):
                    return self._term('invalid','record command counts differ')
            try: expected=self._identity(r,self.target_gs)
            except ParseError as e: return self._term('invalid','identity fields: %s'%e)
            if r['result']!=expected: return self._term('invalid','claimed result %s != expected %s'%(r['result'],expected))
            return self._term(expected,'%s (header-associated)'%expected)
        return None
    def snapshot(self):
        return {'terminal':self.terminal,'result':self.result,'raw':list(self.raw),'record':self.record,'header':self.hdr}

