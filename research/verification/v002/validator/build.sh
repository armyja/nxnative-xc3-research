#!/bin/sh
set -eu
ROOT=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$ROOT/build}
CC=${CC:-cc}
python3 "$ROOT/src/gen2.py" >"$ROOT/logs/gen.log" 2>&1
CFLAGS="-std=c11 -O1 -g -Wall -Wextra -Werror -I$ROOT/build/include"
mkdir -p "$OUT"
$CC $CFLAGS "$ROOT/tests/v002_tests.c" -o "$OUT/v002_tests"
$CC $CFLAGS -fsanitize=address,undefined -fno-omit-frame-pointer "$ROOT/tests/v002_tests.c" -o "$OUT/v002_tests_asan"
echo "built"
