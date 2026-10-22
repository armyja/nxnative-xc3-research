# Round 48: en-GB selects an existing font, and the old fault is gone

**HEAD `7be6d27`**, no commit. One A/B run. No production change.

## 1. The archive member the game asked for does not exist
From the existing listing `proto/out/manifest.tsv` (4,445,663 bytes, 76,445 entries, paths with ard offsets):
[Fenced excerpt omitted from the shareable research record.]
`grep -c 'bf3_us.wisty' manifest.tsv` → **0**. So `menu/font/bf3_us.wisty`, the path the title requested under
`en-US`, **is not in the archive**; the English members that exist are `bf3.wisty` (default) and `bf3_gb.wisty`.
That corrects the earlier "the target is inside the archive" phrasing: the *requested name* is not.

## 2. The A/B run (only `DM_LANG` changed)
Same host `dmhost-oe`, same integrated profile, patches, two-key library and supervisor; the only difference is the
non-sensitive environment value `DM_LANG=en-GB`, recorded in `env.txt` before exec:
[Fenced excerpt omitted from the shareable research record.]
Result:
[Fenced excerpt omitted from the shareable research record.]
So under `en-GB` the title asks for a font that exists, the load completes, the type-2 record reaches `state 4`,
`owner+0x100` is written, and the type-8 handler no longer dereferences null. **The old `main+0x10141ac` fault is
crossed.**

No new blocker appeared in the 5 s: the only `[RED]`/`UNIMPL` lines are the known ones — missing shader library and
`c1_full`, missing `pso_manifest`, `nvnDeviceRegisterFastClearDepth`, `nvnTextureWriteTexelsStrided`, the save-clone
fallback — none of which is a new crash.

## 3. What this does and does not prove
Proved: with `DM_LANG=en-GB`, the guest's language→font mapping selects `bf3_gb.wisty`, which exists; the request
succeeds; the previously crashing consumer runs normally; the process survives the full 5 s.
Not proved: that `en-GB` is the correct **title-level** default. The title's own language table decides which suffix
each system language maps to, and `en-US` apparently maps to a suffix (`us`) that this build does not ship. Whether the
right fix is a different reported language, a title-level compatibility input, or something in the game's mapping must
come from NACP/game evidence, not from this A/B. I did not change any language default, and I did not try other
languages.

## 4. Next step (bounded)
Read the title's language→file mapping (the code path that built `bf3_` + suffix from the `oe::GetDesiredLanguage`
value) and the NACP supported-language field properly; that decides whether `en-US` should fall back to `bf3.wisty`
(the default member) rather than `us`. That is a configuration/mapping question, not an archive or HLE feature gap.

## Limits
One run; no second launch. No overlay, no file rename, no archive provider, no shader translation, no HLE/rewriter/
memory/scheduler change, no tracked edit, no commit. Artifacts: `runs/20261021-103603/` (`boot.log`, `env.txt`),
`probe_plan.json`.
