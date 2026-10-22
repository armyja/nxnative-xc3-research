# Round 53: 30 s of the loading screen, three frames captured, I/O stalls at ~21 s, eight new shader keys

**HEAD `7be6d27`**, no commit. One 30 s headless run, no production change.

## Process disclosure first
My supervisor did **not** implement the "stop at the first complete CTL/code dump" rule. Dumps began early (first
missing-shader line at boot.log:251) and the run continued to the 30 s limit. That is a supervision gap on my side, not
a decision to ignore the stop condition; the dumps themselves are intact.

## Run facts
[Fenced excerpt omitted from the shareable research record.]

## The three captures (all absolute paths)
[Fenced excerpt omitted from the shareable research record.]
I opened all three. Every one is still the **loading screen**: black field, emblem at lower right, `Loading` text whose
dot count cycles (one, three, one). The emblem's colour has changed from **blue** at frames 45/60 (Round 52) to
**green** at 120/300/600 — so the screen is animating through states, not frozen. **The game did not leave Loading
within 30 s / 624 rendered frames.**

## Is it progressing, and where does it stall?
- Frames keep advancing the whole time (frame 624 at 22.6 s), submission and GPU times stay small (submit 0.2 ms,
  GPU 0.6 ms in the last longframe), so it is not a crashed or spinning render loop.
- **File I/O effectively stops at ~21 s**: 5,951 reads in the first 5 s, then ~400 per 5 s, and only 9 in the
  20–25 s window with the last read at 20.83 s.
- So: rendering continues, loading I/O has finished (or stalled), and the title remains on the loading screen. This is
  **not** called a deadlock — frames still advance — but it is also not a completed load.

## Eight new missing shader keys, and where they belong
[Fenced excerpt omitted from the shareable research record.]
All eight are present in the already-extracted five-`.wishp` sample set (checked by recomputing `skey` over every
stage of those containers), so none requires new extraction. Their complete `<key>.ctl` / `<key>.code` pairs were saved
to the run's `shdump/` (e.g. `0afb759d75151a28.ctl` 2176 B + `.code` 768 B).

The most likely reason the title stays on the loading screen is that these eight have no library entry: the draws that
would advance past loading cannot be built. That is a hypothesis consistent with the missing-key lines and the stalled
I/O, not a proven cause.

## Unchanged known issues (listed as-is, not attributed)
- `nvnTextureWriteTexelsStrided` unimplemented.
- Save transaction falls back to a read-only committed directory (`errno=45`).
- `c1_full.tsv` stale/missing, `pso_manifest.tsv` missing.
None of these is claimed to cause the loading screen or the dark-blue region around the emblem noted in review.

## Limits
One run; no second launch; no CPU probes or full PASSDUMP; no settings changed to make frames appear; no tracked edit,
no commit, no push/PR, no install, no new asset extraction, no shader build; shared `dmhost` untouched.
