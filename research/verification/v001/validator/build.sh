#!/bin/sh
# Build the independent CPU verifier. Usage: ./build.sh [outdir]
set -eu
ROOT=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$ROOT/build}
CC=${CC:-cc}
python3 "$ROOT/src/gen.py" >"$ROOT/logs/gen.log" 2>&1
INC="-I$ROOT/build/include"
CFLAGS="-std=c11 -O1 -g -Wall -Wextra -Werror $INC"
mkdir -p "$OUT"
$CC $CFLAGS "$ROOT/tests/tfv_tests.c" -o "$OUT/tfv_tests"
$CC $CFLAGS -fsanitize=address,undefined -fno-omit-frame-pointer \
    "$ROOT/tests/tfv_tests.c" -o "$OUT/tfv_tests_asan"
echo "built: $OUT/tfv_tests $OUT/tfv_tests_asan"
