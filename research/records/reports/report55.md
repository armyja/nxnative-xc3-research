# Round 55 (self-directed, per instruction): the title leaves Loading — it reaches its own Auto-Saving screen

**HEAD `7be6d27`**, tag `xc3-loading-ui`, no new commit. Baseline kept: 22-key library, chain `c1ba6be7ba12`,
`nvn_tex_base 0x20 / slots 2`, fresh CAS (the old-CAS silent-reuse caveat stays on record).

## The run
Host `boot22/dmhost` `fb745c017b735b54`, chain `c1ba6be7ba12`, `DM_LANG=en-GB`, 45 s wall clock under the verified
supervisor (complete-dump stop + RSS/free/dump/log thresholds), save directory on APFS:
[Fenced excerpt omitted from the shareable research record.]

## What the two frames show (I opened both)
- **frame-600** (`…/runs/base22-110930/shots/frame-600.png`): still the loading screen, blue emblem, `Loading…`.
- **frame-1200** (`…/runs/base22-110930/shots/frame-1200.png`): a **different, real screen**:
  > “This game saves your progress automatically. Do not close the game or turn off the console while the icon below
  > is shown on screen.” — with a spinner and **`Auto-Saving…`**, plus an `A` button icon.
That is the title's auto-save notice: the game **left the loading screen between frames 600 and 1200** and advanced to
its next startup stage. Text, spinner, button glyph and background are all rendered by the translated shaders.

## Answer to the open question
**Loading was not caused by missing shaders.** With the 22-key library there were zero missing-shader lines over 1202
frames, and the game still sat on the loading screen for ~600 frames before moving on. The loading screen is simply a
long, animated transition in this configuration (the earlier 30 s windows saw only its first part); the "stall" reading
from Rounds 53–54 is withdrawn.

## What this establishes
- The 22-key set is sufficient for startup through the auto-save stage — no shader is missing for the path up to here.
- The derived texture mapping (`0x20 / 2 slots`) does not break this path.
- The pipeline end-to-end (host → NVN → Metal → presented frames) works for real UI screens, not just the loader.

## Still open
- What comes after Auto-Saving (title screen / menu) — a longer run would tell.
- The other known warnings are unchanged and still unattributed: `nvnTextureWriteTexelsStrided` stub, `c1_full.tsv`
  stale, `pso_manifest.tsv` missing; the save clone only works on APFS (ExFAT fails with ENOTSUP and the host falls back
  to read-only).
- Runtime-measured resource facts remain limited to the one pixel stage in Round 51.

## Next step I would take
One longer supervised run (60–90 s) with frames sampled at the far end (e.g. 1800) to see whether the auto-save leads
into a title screen; same baseline, same stop rules.

## Follow-up: 90 s run — the Auto-Saving screen persists and shows an A prompt
Run `boot22/runs/title-111050`, 90 s wall clock, frames to 2395 (81.9 s), **0 missing-shader lines**.
`frame-1800` (~65 s) is **still the Auto-Saving screen**, identical in layout to frame-1200, with the **`A` button icon**
at the lower right. So after leaving the loader the title parks on this screen, which displays an input prompt; our runs
are input-free by design, which is the natural explanation for it not advancing further.
Only one of the three intended shots was reached (1800); 2700/3600 are beyond the 90 s window at this frame rate.

Next step, if desired: a supervised run that presses `A` once at this screen (`DM_KEYS`) to see whether it advances to
the title/menu. That is player input and should be an explicit decision, so I stopped here.
