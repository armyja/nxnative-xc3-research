#!/usr/bin/env python3
"""A2a: slice the real replay consumer, the real OP_END/OP_BEGIN/OP_CALL/OP_DRAW/OP_DRAW_IDX case bodies and the real
OP_TF_DIAG case out of nvn_mtl.m; emit mutated copies (consumer/helper and case-label level) for the mutation tests."""
import hashlib
MTL = '/path/to/user/projects/nxnative-xc3/dm/gfx/nvn/nvn_mtl.m'
s = open(MTL).read()
def sha(t): return hashlib.sha256(t.encode()).hexdigest()
def between(a, b, start=0):
    i = s.index(a, start); j = s.index(b, i)
    return s[i:j]

mtl = s.index('void mtl_exec(const uint8_t *p) {')
consumer = between('// ---- TF-DIAG-A2A-BEGIN ----', '// ---- TF-DIAG-A2A-END ----', 0) + '// ---- TF-DIAG-A2A-END ----\n'
end_begin = between('case OP_END: g_exec_cur = NULL;', 'case OP_JUMP:', mtl)
call = between('case OP_CALL: {', 'case OP_SIGNAL_EVENT:', mtl)
case_tf = '            case OP_TF_DIAG: tf_diag_case(h.size, a); break;   // A2a: one consumer call, no GPU work\n'
assert case_tf in s, 'OP_TF_DIAG case text not found'
lines = s.split('\n')
di = next(i for i, l in enumerate(lines) if l.strip().startswith('case OP_DRAW: if (g_rc_skip)'))
draw = []
for l in lines[di:]:
    draw.append(l)
    if len(draw) >= 2 and l.strip().startswith('case OP_') and len(draw) > 2:
        draw.pop()          # stop before the third case
        break
draw = '\n'.join(draw) + '\n'
assert 'case OP_DRAW: ' in draw and 'case OP_DRAW_IDX: ' in draw and 'g_rc_skip' in draw, 'draw slice'
assert len(draw) < 1200, 'draw slice too large'
i_tf = s.index('case OP_TF_DIAG:')
assert s.index('case OP_RENDER_COND:') < i_tf < s.index('default: break;', i_tf), 'case order'
assert s.count('case OP_TF_DIAG:') == 1, 'exactly one OP_TF_DIAG case'

mut1 = consumer.replace('    tf_diag_apply(&g_tf_diag, &e);\n', '    /* mutation: apply removed */\n', 1)
assert mut1 != consumer
val = '''    if (hsize != (uint32_t)(sizeof(op_hdr) + TF_DIAG_PAYLOAD) || (((uintptr_t)a) & 7u) != 0) {
        tf_diag_mark_unknown(&g_tf_diag, TF_DIAG_REASON_BAD_RECORD);   // bad size/alignment: never touch the payload
        tf_diag_tick(&g_tf_diag);
        return;
    }
'''
assert val in consumer
mut2 = consumer.replace(val, '', 1).replace('    tf_diag_apply(&g_tf_diag, &e);', val + '    tf_diag_apply(&g_tf_diag, &e);', 1)
mut3 = case_tf.replace('tf_diag_case(h.size, a); ', '')
mut4 = case_tf.replace('case OP_TF_DIAG:', 'case 200:')

for n, t in [('a2_consumer.inc', consumer), ('a2_consumer_mut_noapply.inc', mut1), ('a2_consumer_mut_applyfirst.inc', mut2),
             ('a2_cases_end_begin.inc', end_begin), ('a2_cases_call.inc', call), ('a2_cases_draw.inc', draw),
             ('a2_case_tf.inc', case_tf), ('a2_case_tf_mut_nocall.inc', mut3), ('a2_case_tf_mut_relabel.inc', mut4)]:
    open(n, 'w').write(t)
    print('%-34s %4d bytes sha256 %s' % (n, len(t), sha(t)))
print('case placement: OP_RENDER_COND < OP_TF_DIAG < default, exactly one OP_TF_DIAG case')
print('nvn_mtl.m sha256', sha(s))
