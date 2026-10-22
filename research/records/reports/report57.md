# Round 57: the 173-key burst, checked offline (no guest run)

**HEAD `7be6d27`**, no commit. All evidence under
`/path/to/external-drive/xc3/work/experiments/boot22/` (manifest) and the run's own directory.

## 1. The 173-key manifest
Built from the run's own `shdump/` (input pinned: `main.orig.bin` sha256 `d6488ee7da0a04cd…`, build
`82d187fe9ef9be921b8e1b1cddf7bd28`):

| check | result |
|---|---|
| keys dumped | **173** |
| control magic `34127698` | 173 / 173 |
| `+0x704` equals `.code` length | **172 / 173** |
| key recomputed from ctl+code | **172 / 173** |
| byte-exact in the five sample containers | **132** (ctl 132, code 131) |
| GS entries | **2** |
| compute (non-zero thread group) | **7** |

**One dump is incomplete**: `d05c91b9435d2685` has a full 2176-byte control and a **0-byte code**, so it cannot be
hashed and it is also the single sample match whose code bytes did not compare equal. The other 132 sample matches are
byte-identical (control 0x880 and code).

The two GS entries are both in `shd_post`, and both programs are **`vs` → `gs` → `ps`** chains:
[Fenced excerpt omitted from the shareable research record.]
They stay refused as GS; they are not reclassified.

The 41 keys not in the five containers are only that: **not in these five samples**. Nothing here says where they come
from, and I did not infer `wismt` or `main`.

## 2. When the burst happens, and what it is attached to
Order in the log:
[Fenced excerpt omitted from the shareable research record.]
So the screenshot was taken **before** the burst began; the burst started immediately after the Auto-Saving frame.

`pso.tsv` gives the association: **22 `S` (library) records and 13 `R` (pipeline) records — exactly our 22-key library
— and the intersection with the 173 dumped keys is 0.** The 173 were therefore requested at program-translation time
(the `[RED] shader … is not in the shader map` message is emitted from the program lookup that a pipeline build
performs), and none of them produced a pipeline record. **Keys with an actual PSO among the 173: 0; the rest are
unknown beyond "requested".**

This is consistent with a **bulk preload** right after the auto-save notice (many keys in one frame interval), but the
logs alone do not prove a preload versus many skipped draws — that stays an inference.

## 3. Are the 41 in `main.orig.bin`? No
Exact full-code byte search of all 41 in the pinned image: **0 matches** (searching the complete `.code` bytes, not
lengths or magic). So these shaders are not embedded in the main module as literal code; they must come from the
archive side, which our five sampled containers do not cover. I did not search any other input and did not extend this
into a broader binary search.

## 4. Supervisor timing evidence
`sup.txt` records `reason=complete dump: a7fe954c9b04785e` and `exit=0`, but my supervisor does **not timestamp** the
moment of detection, so I cannot give a detection→TERM interval from the script. What the host's own log shows at the
end is:
[Fenced excerpt omitted from the shareable research record.]
i.e. TERM was received and the host did not finish its graceful exit within 1.5 s, then exited by itself; the
supervisor's `wait` collected exit 0. The 173 dumps were produced within one polling interval (0.2 s), which is why so
many exist at once — the rule stopped at the first complete pair it observed, and it did stop the run (frames 1752, no
further dumps after that point).

## 5. Decision input for the next A experiment
The burst shows **173 shaders genuinely requested** at that point, not 173 proven draws. Of those:
- **130 non-GS keys can be built offline** from the five containers we have;
- **2 are GS** and stay refused;
- **41 are not in our samples and not in `main`**, so they need inputs we do not currently have.

So the next A experiment should **not** assume "build all 173": without the 41 (and with 2 GS refused) a run would still
hit missing shaders at the same boundary. The realistic options are (a) build the 130 in-sample non-GS keys and accept
that the 43 remain a wall, or (b) obtain the containers that hold the 41 before re-attempting. That decision is the
supervisor's.

## Limits
No guest run, no input, no build, no extraction, no scanner change, no tracked edit, no commit; the 22-key chain
`c1ba6be7ba12` and its library are untouched.
