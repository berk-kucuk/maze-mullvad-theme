#!/usr/bin/env python3
"""Mullvad tray ikonlarini uretir: siyah daire, Mullvad renklerinde kostebek,
kask lambasi baglanti durumunu gosterir.

Mullvad'in kare eslemesi (desktop/.../tray-icon-controller.ts, targetFrame):
  lock-1  = baglanti yok (unsecured)
  lock-9  = bagli (secured)
  lock-10 = baglaniyor (securing)
  lock-2..8 = lock-1'den lock-9'a giden animasyonun ara kareleri
Her kare icin 4 varyant: "", "_notification", "_white", "_white_notification".

Kullanim: generate.py [cikti klasoru]   (varsayilan: ./build)
"""
import pathlib
import subprocess
import sys

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent / "build"
SIZE = 48
# mullvad-vpn paketinin kurdugu hicolor boyutlari
APP_ICON_SIZES = (16, 32, 128, 256, 512)

# Lamba orijinalinde (rx 13.6, ry 8.1) 22 px tray boyutunda okunamayacak kadar kucuk;
# durum rengini tasidigi icin buyutuldu ve etrafina siyah bir cerceve eklendi.
LAMP_CX, LAMP_CY = 187.8, 134.4
LAMP_RX, LAMP_RY, LAMP_RING = 30, 21, 9

BG = "#0b0b0b"
FUR = "#D0933A"
HELMET = "#FFD524"
# Baglaniyor rengi sari kask uzerinde kayboldugu icin turuncu.
RED, AMBER, GREEN = "#E34039", "#FF7A00", "#44AD4D"

P_BG = "M74,200C74,269.6 130.5,326 200,326C269.5,326 326,269.6 326,200C326,130.4 269.6,74 200,74C130.4,74 74,130.4 74,200Z"
P_FUR = "M97.9,170.6L90.8,185L100.4,171.6C100.4,171.7 99.8,190.9 99.8,190.9L102.5,176.4C109.7,190.1 125.6,211.2 147.9,226.9C149.6,228.1 151.8,230.2 152.5,231C152.5,231 173.8,241.8 206.6,216.8C206.9,216.6 207.3,216.4 207.6,216.2L208.1,216.5L215.3,221.3C212.8,220.6 208,219.4 208,219.4C192.2,237.6 166.5,240.6 152.7,231.4C152.1,231 148.7,232.4 148.1,234.4C147.7,235.5 148.1,236.7 148.6,237.6C151.4,242.8 155.6,242.3 153.6,248.4C152.2,251.7 150.2,254.9 148,257.9C143.4,264.1 136.2,269.6 136.9,272.9C169.5,313.1 243,307.5 271,271.6C270.6,266.4 262.4,263.9 256.7,251.2C258.3,251.7 260.7,252.4 260.7,252.3C260.7,252.2 253.9,241.2 253.6,240.1L258,240.4C258,240.4 252.2,233.2 252,232.5L257.9,231.7C257.9,231.7 250.5,223.2 250.4,222.5L257.9,223.7L249.7,213.8L253.6,213.8L249,207.1L211.7,192.4C197.4,183.5 184.7,172.6 175.1,164.2L155.8,154.8C137.3,153.4 120,153.9 109.4,156L116.2,144.4L106.3,156.2C105.7,156 105,155.8 105,155.8L105.7,140.8L102.4,154.8L97.9,170.6Z"
P_NOSE = "M102.4,154.8C97.5,152.5 91.8,155.8 90.8,160.3C89.6,164.6 92.6,169.9 97.9,170.6C102.9,167.5 107.2,159.5 102.4,154.8Z"
P_HELMET = "M175.2,143.9C173.7,139.8 174.1,134.5 176.2,129.5C179.2,122.6 184.9,118 190.3,118C191.4,118 192.4,118.2 193.4,118.6C196.5,115.8 200.1,113.5 204.1,111.9C226.1,103.1 258.4,118.8 266.7,140.4C270.7,150.9 269.5,162.3 266.1,172.8C263.3,181.4 253.1,193.8 256.9,203.1C255.4,202.7 224.1,192.1 215.1,187.3C201,178.5 188.4,167.7 178.9,159.4L178.6,159.1L146.6,143.9C146.2,143.7 145.8,143.5 145.5,143.3C149.9,143.5 167.4,145.6 175.2,143.9"


def mix(a: str, b: str, t: float) -> str:
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def lamp_color(frame: int) -> str:
    if frame == 1:
        return RED
    if frame == 9:
        return GREEN
    if frame == 10:
        return AMBER
    return mix(RED, AMBER, (frame - 1) / 8)  # 2..8: lamba kirmizidan sariya isinir


def mono_lamp(frame: int) -> str:
    if frame == 1:
        return "#3A3A3A"
    if frame == 9:
        return "#FFFFFF"
    if frame == 10:
        return "#A8A8A8"
    return mix("#3A3A3A", "#A8A8A8", (frame - 1) / 8)


def svg(frame: int, white: bool, notification: bool, lamp: str | None = None) -> str:
    fur, helmet = ("#FFFFFF", "#FFFFFF") if white else (FUR, HELMET)
    lamp = lamp or (mono_lamp(frame) if white else lamp_color(frame))
    badge = ""
    if notification:
        # Sag ustte bildirim noktasi; siyah halka daireden ayirir.
        badge = (f'<circle cx="166" cy="34" r="34" fill="{BG}"/>'
                 f'<circle cx="166" cy="34" r="24" fill="{"#FFFFFF" if white else AMBER}"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 201 200" width="{SIZE}" height="{SIZE}">
<g transform="matrix(0.793954,0,0,0.793651,-58.752586,-58.730159)">
<path d="{P_BG}" fill="{BG}"/>
<path d="{P_FUR}" fill="{fur}"/><path d="{P_NOSE}" fill="{fur}"/>
<path d="{P_HELMET}" fill="{helmet}"/>
<g transform="matrix(0.4007,-0.9162,0.9162,0.4007,-10.6017,252.6081)"><ellipse cx="{LAMP_CX}" cy="{LAMP_CY}" rx="{LAMP_RX}" ry="{LAMP_RY}" fill="{lamp}" stroke="{BG}" stroke-width="{LAMP_RING}"/></g>
</g>{badge}</svg>'''


def main() -> None:
    svg_dir, png_dir = OUT / "svg", OUT / "icons"
    svg_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    for frame in range(1, 11):
        for white in (False, True):
            for notification in (False, True):
                name = f"lock-{frame}{'_white' if white else ''}{'_notification' if notification else ''}"
                s = svg_dir / f"{name}.svg"
                s.write_text(svg(frame, white, notification))
                subprocess.run(["rsvg-convert", "-w", str(SIZE), "-h", str(SIZE),
                                "-o", str(png_dir / f"{name}.png"), str(s)], check=True)
    print(f"{len(list(png_dir.glob('*.png')))} PNG -> {png_dir}")

    # Pencere basligi ve uygulama menusu ikonu (hicolor/<boyut>/apps/mullvad-vpn.png):
    # ayni siyah daireli logo, lamba durum gostermedigi icin beyaz.
    app_dir = OUT / "appicon"
    app_dir.mkdir(parents=True, exist_ok=True)
    app_svg = svg_dir / "mullvad-vpn.svg"
    app_svg.write_text(svg(1, False, False, lamp="#FFFFFF"))
    for size in APP_ICON_SIZES:
        subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size),
                        "-o", str(app_dir / f"{size}.png"), str(app_svg)], check=True)
    print(f"{len(APP_ICON_SIZES)} uygulama ikonu -> {app_dir}")


if __name__ == "__main__":
    main()
