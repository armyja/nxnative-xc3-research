# Round 58: A was pressed on the auto-save notice, and the shader burst followed immediately

**HEAD `7be6d27`**, no commit. One run, as authorised. No baseline change: chain `c1ba6be7ba12`, slots 2, host
`fb745c017b735b54`, 22 shader entries; language en-GB, APFS experiment save (never the player's).

## Precondition: satisfied, and checked against an image
`frame-1400` (`…/runs/A2-111935/shots/frame-1400.png`, 1920×1080) — I opened it: it is the **Auto-Saving notice**, the
same layout as before, with the `A` prompt at the lower right. So the press was attempted on the right screen, and the
earlier statement "the frame-1500 precondition is assumed" is now backed by an actual pre-press capture at 1400.

## The press executed
[Fenced excerpt omitted from the shareable research record.]
`f` is the **presented** frame (`dm_guest_frame()`), so this fired at presented frame 1500 with button mask `0x1` (A) and
a 0.20 s hold; the hold ends by releasing the button, per the same path that logs the press. No other key was scripted.

## What happened next, in order
[Fenced excerpt omitted from the shareable research record.]
Outer monotonic record (SSD, outside the supervisor): first complete pair seen at **53.21 s**, supervisor returned at
**54.85 s** → detection-to-termination ≈ **1.6 s**. Stop reason `complete dump: 109c554fde29c46a`, exit 0.

**No post-press screenshot exists.** The planned render 1530/1650/1800 shots were never reached: the run ended at
54.85 s before render 1530. So whether the screen changed after A is **unknown** — only the pre-press frame exists.

## What that does and does not mean
The burst begins ~0.7 s after the A press, which is **consistent with** A dismissing the notice and the next screen
requesting those shaders. That is an inference from ordering; there is no image of the resulting screen, so I do not
claim the press advanced the game.
The stop rule was not bent: the run ended on the first complete missing-shader pair, exactly as configured, even though
these keys were already seen in Round 56.

## Resources
`memstat.tsv` peak `phys_footprint` ≈ **929 MiB**. No crash, no FATAL, no Metal validation error.

## For the record (corrections accepted from review)
- 132 keys matched the five containers by **control**; **131** also matched on complete code. The one incomplete dump
  (`d05c91b9435d2685`, 0-byte code) can have its code recovered structurally from the sample, but that is **not** a
  runtime-dump verification.
- 41 keys had no contiguous literal match in `main.orig.bin`; that excludes that image/literal form only, not other
  modules or runtime construction.
- Zero `R` records among the 173 does not establish that any of them is unreachable or that all must execute.
- No timestamp means no claim of an exact detection/TERM latency; the only measured interval is the outer one above.

## Limits
One run, no second launch, no extra keys, no build, no extraction, no tracked edit, no commit; the 22-key library,
chain and `dmhost` untouched.
