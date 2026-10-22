#!/usr/bin/env python3
"""Slice the real rec() body and the A1 TF-diag adapter block out of the repo sources, verify the opcode numbering,
and assert that rec() is byte-identical between the pre-A1 baseline and the new tree."""
import hashlib, re, sys
REPO = '/path/to/user/projects/nxnative-xc3/dm/gfx/nvn'
BASE = '/path/to/external-drive/xc3/work/experiments/tf-diag-a1/baseline'

def sha(b): return hashlib.sha256(b).hexdigest()

def slice_rec(text, where):
    i = text.index('static void *rec(NVNcommandBuffer *c, uint32_t op, size_t payload) {')
    j = text.index('#define REC(c, OP, T)', i)
    return text[i:j].rstrip() + '\n'

def slice_tf(text):
    i = text.index('// ---------- Transform-feedback diagnostic events')
    j = text.index('void dm_tf_diag_invalid(', i)
    k = text.index('\n', j) + 1
    return text[i:k]

new_c = open(REPO + '/hle_nvn.c').read()
base_c = open(BASE + '/hle_nvn.c').read()
r_new, r_base = slice_rec(new_c, 'new'), slice_rec(base_c, 'baseline')
assert r_new == r_base, 'rec() differs between baseline and new tree'
tf = slice_tf(new_c)

# opcode numbering, from the real enum
obj = open(REPO + '/nvn_obj.h').read()
m = re.search(r'enum \{(.*?)OP_COUNT_', obj, re.S)
names = [x.strip() for x in m.group(1).replace('\n', ' ').split(',') if x.strip()]
num = {n: i for i, n in enumerate(names)}
assert num['OP_TF_DIAG'] == 42, 'OP_TF_DIAG=%d (expected 42); stop, do not renumber' % num['OP_TF_DIAG']
assert len(names) == 43, 'OP_COUNT_=%d (expected 43); stop, do not renumber' % len(names)
assert num['OP_RENDER_COND'] == 41
base_obj = open(BASE + '/nvn_obj.h').read()
mb = re.search(r'enum \{(.*?)OP_COUNT_', base_obj, re.S)
base_names = [x.strip() for x in mb.group(1).replace('\n', ' ').split(',') if x.strip()]
assert base_names == names[:len(base_names)], 'existing opcode values changed'
assert names[len(base_names)] == 'OP_TF_DIAG' and len(names) == len(base_names) + 1

open('rec.inc', 'w').write(r_new)
open('tf_block.inc', 'w').write(tf)
print('rec slice: %d bytes sha256 %s' % (len(r_new), sha(r_new.encode())))
print('tf block : %d bytes sha256 %s' % (len(tf), sha(tf.encode())))
print('baseline rec == new rec: yes')
print('opcodes: OP_RENDER_COND=%d OP_TF_DIAG=%d OP_COUNT_=%d (existing names unchanged)' % (41, 42, len(names)))
print('nvn_obj.h sha256', sha(obj.encode()), ' baseline', sha(base_obj.encode()))
