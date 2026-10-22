#!/bin/sh
# TF-NEXT-IMPL: independent matching host build. Reuses the archived gsres-observer-fix compile line verbatim;
# the only change is the output path. The host is compiled and linked but NEVER run from this script.
set -u
REPO=/path/to/user/projects/nxnative-xc3
OUT=/path/to/external-drive/xc3/work/experiments/tf-intent-host
cd "$REPO/dm/host" || exit 90
{
  echo "cwd=$PWD"
  echo "date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "clang=$(command -v clang) $(clang --version | head -1)"
  echo "sdk=$(xcrun --show-sdk-path 2>&1)"
  echo "env: $(env | grep -E '^(SDKROOT|MACOSX_DEPLOYMENT_TARGET|ARCH|CC|CFLAGS|LDFLAGS|DM_)=' | sort | tr '\n' ' ')"
} > "$OUT/build.env"
clang -O1 -g -Wall -Wno-unused-function -I../gfx/nvn/include -I../third_party/vulkan-headers/include \
  -I/path/to/external-drive/xc3/work/experiments/gsres-observer/gen \
  -I/path/to/external-drive/xc3/work/experiments/fout-six-lgt-correct645/profile/010074F013262000/ \
  -Igen/010074F013262000/profile -I../third_party/libvpx -I../third_party/stb_vorbis -fobjc-arc \
  -o "$OUT/dmhost-tfintent" \
  main.c loader.c hle.c host_stubs.c crash.c probe.c thread.c membudget.c membudget_vm.c memstat.m \
  ../ios/Sources/dm_touch_controls.c hle_account.c hle_audio.c hle_audren.c hle_bigstack.c hle_codec.c \
  hle_count.c hle_fdstat.c hle_friends.c hle_fs.c hle_glslc.c hle_guestthread.c hle_hid.c hle_lifecycle.c \
  hle_misc.c hle_movie.c hle_movie_avc.c hle_net.c hle_nvdrv.c hle_oe.c hle_offline.c hle_os.c hle_ro.c \
  hle_sdk16.c hle_sdkinit.c hle_svc.c hle_swkbd.c hle_table.c hle_thread.c hle_time.c hle_touch.c \
  front_mac.m entry.S dm_i18n.c ../gfx/hle_nv.c ../gfx/hle_vi.c ../gfx/nvn/hle_nvn.c ../gfx/nvn/nvn_dirty.c \
  ../gfx/nvn/nvn_entry.S ../gfx/nvn/nvn_imgdiag.c ../gfx/nvn/nvn_mtl.m ../gfx/nvn/nvn_refl.m \
  ../gfx/nvn/nvn_tex.c ../gfx/nvn/nvn_thunks.S ../gfx/tex/nvn_deswizzle.c ../gfx/tex/nvn_deswizzle_gpu.m \
  ../gfx/tex/nvn_fmt_mtl.c ../gfx/vk/hle_vk.m gen/vpx/libvpx.a \
  -framework Cocoa -framework QuartzCore -framework Metal -framework AudioToolbox -framework VideoToolbox \
  -framework CoreMedia -framework CoreVideo -framework ImageIO -framework UniformTypeIdentifiers \
  -framework GameController
rc=$?
echo "rc=$rc" >> "$OUT/build.env"
if [ $rc -eq 0 ] && [ -f "$OUT/dmhost-tfintent" ]; then
  shasum -a 256 "$OUT/dmhost-tfintent" > "$OUT/dmhost-tfintent.sha256"
  echo "product_sha=$(cat "$OUT/dmhost-tfintent.sha256")" >> "$OUT/build.env"
fi
exit $rc
