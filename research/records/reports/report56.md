# Round 56: the authorized A press did not execute — a 173-key shader burst stopped the run first

**HEAD `7be6d27`**, no commit. One run, as authorised. Baseline unchanged: chain `c1ba6be7ba12`, slots 2, fresh CAS,
host `fb745c017b735b54`, `DM_LANG=en-GB`, APFS save directory (never the player's).

## The run
`boot22/runs/A-111345`, 90 s wall clock, stop rule as tested:
[Fenced excerpt omitted from the shareable research record.]

## Why the press did not happen
`frame-1750` (I opened it) is **still the Auto-Saving screen**, identical layout with the `A` prompt. At that moment the
renderer began requesting a **large batch of new shaders**: 173 distinct keys were dumped before the first complete
pair triggered the stop. So the precondition for the A press — "at frame 1800 the Auto-Saving screen is up" — was not
reached in this run; per instruction I did not press, retry, or extend.

This is a valid stop rather than a failed experiment: the shader burst is itself the finding.

## The 173-key burst
[Fenced excerpt omitted from the shareable research record.]
- 132 could be built offline from the containers we already have — except the **2 GS stages**, which `dmsh_build`
  refuses by design (and which stay refused).
- 41 would need extraction from containers outside the current five-file sample; I did not extract anything.

The burst happens right after the auto-save notice, which is consistent with the title preloading the next scene's
shaders before leaving that screen. That is an inference from timing, not proof.

## Other facts
- No crash, no FATAL, no Metal validation error; exit 0 after the stop.
- Known warnings unchanged (c1_full stale, pso_manifest missing, `nvnTextureWriteTexelsStrided` stub).
- The Auto-Saving text appearing does not prove the save succeeded; no save error was logged in this run (the save
  directory is writable APFS, so the clone step succeeded).

## What this establishes for the next round
Proceeding past the auto-save screen requires a **much larger shader set**: at minimum the 132 in-sample keys (130
non-GS), and 41 more that are not in the sample containers. The current 22-key baseline is not sufficient past this
point; the A-press experiment must be re-authorised after the burst is covered, or run with the stop rule allowing the
burst.

## Limits
No production/tracked change, no commit, no install, no asset extraction, no change to memory/scheduling/language/GS/
resource facts; shared `dmhost` untouched; one run only.
