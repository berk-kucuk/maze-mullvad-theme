#!/usr/bin/env bash
# README gorsellerini generate.py ciktisindan yeniden uretir.
# Gerekenler: rsvg-convert (librsvg), magick (imagemagick).
# Kullanim: docs/make-images.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMG="$ROOT/docs/images"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$ROOT/generate.py" "$TMP" >/dev/null
mkdir -p "$IMG"
I="$TMP/icons"

# Bir panel seridi: <arka plan> <yazi rengi> <cikti> <ikon...>
strip() {
    local bg="$1" fg="$2" out="$3"; shift 3
    local tiles=() name label
    for name in "$@"; do
        case "$name" in
            lock-10|lock-10_*) label="Connecting" ;;
            lock-1|lock-1_*)   label="Not connected" ;;
            lock-9|lock-9_*)   label="Connected" ;;
        esac
        magick "$I/$name.png" -background "$bg" -gravity center -extent 150x64 \
            \( -size 150x26 -background "$bg" -fill "$fg" -font DejaVu-Sans -pointsize 14 \
               -gravity center label:"$label" \) -append "$TMP/tile-$name-$bg.png"
        tiles+=("$TMP/tile-$name-$bg.png")
    done
    magick "${tiles[@]}" +append -bordercolor "$bg" -border 12 "$out"
}

strip '#2a2e32' '#c8ccd0' "$TMP/dark.png"  lock-1 lock-10 lock-9
strip '#eff0f1' '#31363b' "$TMP/light.png" lock-1 lock-10 lock-9
magick "$TMP/dark.png" "$TMP/light.png" -append "$IMG/tray-states.png"

strip '#2a2e32' '#c8ccd0' "$IMG/tray-monochrome.png" lock-1_white lock-10_white lock-9_white

# Bildirim noktasi ve animasyon kareleri (lock-1 -> lock-9 arasi lamba isinir)
frames=()
for f in 1 2 3 4 5 6 7 8 9 10; do frames+=("$I/lock-$f.png"); done
magick "${frames[@]}" "$I/lock-9_notification.png" -background '#2a2e32' \
    -gravity center -extent 60x60 +append -bordercolor '#2a2e32' -border 10 "$IMG/tray-frames.png"

cp "$TMP/appicon/256.png" "$IMG/app-icon.png"
echo "Gorseller: $IMG"
ls -1 "$IMG"
