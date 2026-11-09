#!/usr/bin/env bash
# =============================================================================
#  Maze Mullvad Theme — local Arch package builder
#
#  Builds maze-mullvad-theme-<version>-<rel>-any.pkg.tar.zst straight from the
#  current working tree (uncommitted changes included), using packaging/PKGBUILD.
#  The version is read from ./VERSION. The icons are rendered here (needs
#  rsvg-convert from librsvg), so the package itself has no build step.
#
#  Building needs no privileges and this script asks for none: it runs makepkg
#  and stops. Installing is a separate, explicit step you run yourself — the
#  command is printed at the end.
#
#  Usage:
#    ./build-pkg.sh              build the package into ./dist-pkg/
#    ./build-pkg.sh --clean      remove ./dist-pkg/ and exit
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG_SRC="$ROOT/packaging"
OUT="$ROOT/dist-pkg"

if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; RESET='\033[0m'
else
  GREEN=''; BLUE=''; RED=''; RESET=''
fi
info() { echo -e "${BLUE}[*]${RESET} $*"; }
ok()   { echo -e "${GREEN}[✓]${RESET} $*"; }
die()  { echo -e "${RED}[✗]${RESET} $*" >&2; exit 1; }

for arg in "$@"; do
  case "$arg" in
    --clean)   rm -rf "$OUT"; ok "Removed $OUT"; exit 0 ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^#\s\?//'; exit 0 ;;
    *)         die "Unknown option: $arg" ;;
  esac
done

command -v makepkg >/dev/null 2>&1 || die "makepkg not found — run this on Arch (pacman)."
command -v rsvg-convert >/dev/null 2>&1 || die "rsvg-convert not found — install librsvg."
[[ -f "$PKG_SRC/PKGBUILD" ]] || die "Missing $PKG_SRC/PKGBUILD"

VER="$(tr -d '[:space:]' < "$ROOT/VERSION")"
[[ -n "$VER" ]] || die "Could not read the version from VERSION"
info "Building maze-mullvad-theme ${VER} from working tree"

# ── Tests first ───────────────────────────────────────────────────────────────
info "Running tests ..."
LOG="$(mktemp -t maze-mullvad-theme-tests.XXXXXX.log)"
if python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v >"$LOG" 2>&1; then
  ok "$(grep -c '\.\.\. ok' "$LOG") tests passed"
  rm -f "$LOG"
else
  tail -30 "$LOG"
  die "Tests failed — see $LOG"
fi

# ── Stage the source tree, with the icons rendered ────────────────────────────
BUILD="$OUT/build"
STAGE="$OUT/stage/maze-mullvad-theme-${VER}"
rm -rf "$BUILD" "$OUT/stage"
mkdir -p "$BUILD" "$STAGE"

info "Rendering icons"
python3 "$ROOT/generate.py" "$OUT/stage/render" >/dev/null
cp -r "$OUT/stage/render/icons" "$STAGE/icons"
cp -r "$OUT/stage/render/appicon" "$STAGE/appicon"
cp -r "$ROOT/system" "$STAGE/system"
find "$STAGE/system" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "$ROOT/README.md" "$ROOT/LICENSE" "$ROOT/VERSION" "$ROOT/generate.py" "$STAGE/"
mkdir -p "$STAGE/docs" && cp -r "$ROOT/docs/images" "$STAGE/docs/images"

info "Creating source tarball"
tar czf "$BUILD/maze-mullvad-theme-${VER}.tar.gz" -C "$OUT/stage" "maze-mullvad-theme-${VER}"
rm -rf "$OUT/stage"

# ── Assemble the makepkg working dir ──────────────────────────────────────────
cp "$PKG_SRC/PKGBUILD" "$PKG_SRC/maze-mullvad-theme.install" "$BUILD/"
# Pin pkgver to the version we just built (leaves packaging/PKGBUILD untouched).
sed -i "s/^pkgver=.*/pkgver=${VER}/" "$BUILD/PKGBUILD"

info "Running makepkg ..."
( cd "$BUILD" && makepkg -f --noconfirm --nodeps )

PKG="$(find "$BUILD" -maxdepth 1 -name '*.pkg.tar.zst' -print -quit)"
[[ -n "$PKG" ]] || die "makepkg finished but produced no .pkg.tar.zst"
mv -f "$PKG" "$OUT/"
FINAL="$OUT/$(basename "$PKG")"
mv -f "$BUILD/maze-mullvad-theme-${VER}.tar.gz" "$OUT/"
rm -rf "$BUILD"

ok "Package ready: $FINAL"
echo "    Source:  $OUT/maze-mullvad-theme-${VER}.tar.gz"
echo
echo "  To install (this script does not do it for you):"
echo "    sudo pacman -U \"$FINAL\""
echo
