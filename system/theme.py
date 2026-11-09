"""Mullvad'in lacivert arayuzunu Maze siyahina (#0b0b0b) cevirir.

Mullvad'in renkleri tek bir tabloda (desktop/.../foundations/tokens/color-tokens.ts)
ve harita icin 3dmap.ts'te tanimli; derlenmis arayuz paketinde (build/assets/
index-*.js) her biri bir kez gecer. Maviler duz siyaha degil, katmanlar
ayirt edilsin diye elle secilmis grilere eslenir: arka plan #0b0b0b, kartlar
ve butonlar biraz daha acik. Yesil, kirmizi ve sari durum renklerine dokunulmaz.
"""
import re


def _gray(v: int) -> str:
    return f"rgb({v}, {v}, {v})"


# Derlenmis arayuzdeki token degerleri -> gri karsiliklari.
RENDERER = {
    "rgb(25, 46, 69)": _gray(11),            # darkBlue: sayfa arka plani
    "rgba(25, 38, 56)": _gray(16),           # darkerBlue50: kartlar
    "rgba(25, 38, 56, 0.8)": "rgba(16, 16, 16, 0.8)",
    "rgba(16, 24, 35)": _gray(6),            # darkerBlue10
    "rgba(16, 24, 35, 0.8)": "rgba(6, 6, 6, 0.8)",
    "rgba(16, 24, 35, 0.4)": "rgba(6, 6, 6, 0.4)",
    "rgba(21, 39, 58, 1)": "rgba(14, 14, 14, 1)",
    "rgb(27, 49, 74)": _gray(20),            # blue10
    "rgb(28, 52, 78)": _gray(23),            # blue20
    "rgb(31, 58, 87)": _gray(28),            # blue40
    "rgb(33, 62, 92)": _gray(32),            # blue50
    "rgb(35, 65, 97)": _gray(36),            # blue60
    "rgb(38, 71, 106)": _gray(42),           # blue80
    "rgb(41, 77, 115)": _gray(48),           # blue: butonlar
    "rgb(37, 57, 78)": _gray(30),            # whiteOnDarkBlue5
    "rgb(48, 67, 88)": _gray(42),            # whiteOnDarkBlue10
    "rgb(71, 88, 106)": _gray(64),           # whiteOnDarkBlue20
    "rgb(117, 130, 143)": _gray(116),        # whiteOnDarkBlue40
    "rgb(140, 150, 162)": _gray(140),        # whiteOnDarkBlue50
    "rgb(163, 171, 181)": _gray(164),        # whiteOnDarkBlue60
    "rgb(209, 213, 218)": _gray(210),        # whiteOnDarkBlue80
    "rgb(56, 86, 116)": _gray(60),           # whiteOnBlue5
    "rgb(62, 95, 129)": _gray(70),           # whiteOnBlue10
    "rgb(84, 113, 143)": _gray(92),          # whiteOnBlue20
    "rgb(127, 148, 171)": _gray(132),        # whiteOnBlue40
    "rgb(148, 166, 185)": _gray(152),        # whiteOnBlue50
    "rgb(169, 184, 199)": _gray(172),        # whiteOnBlue60
    "rgb(212, 219, 227)": _gray(214),        # whiteOnBlue80
    # 3dmap.ts: uzay, kara, okyanus (kenarliklar okyanus rengini kullanir)
    "[10/255,25/255,35/255,1]": "[11/255,11/255,11/255,1]",
    "[.16,.302,.45,1]": "[.14,.14,.14,1]",
    "[.098,.18,.271,1]": "[.043,.043,.043,1]",
}

# Bu ikisi bulunamazsa Mullvad renk tablosunu degistirmis demektir; tema atlanir.
RENDERER_REQUIRED = ("rgb(25, 46, 69)", "rgb(41, 77, 115)")

# Ana surec (BrowserWindow arka plani, pencere acilirken gorunen renk).
MAIN = {"#192e45": "#0b0b0b"}

# Gorsellerdeki (logo, multihop ve DAITA illustrasyonlari) lacivertler; ayni
# tonlarin arayuzdeki karsiliklariyla tutarli. Listede olmayan renklere dokunulmaz.
SVG = {
    "192E45": "0B0B0B",  # darkBlue
    "152637": "101010",  # darkerBlue50'ye yakin
    "294D73": "303030",  # blue
    "304358": "2A2A2A",  # whiteOnDarkBlue10
    "3E5F81": "464646",  # whiteOnBlue10
}


def _replace_each(text: str, table: dict) -> tuple[str, int]:
    # Tek gecis: bir degisimin ciktisi baska bir anahtarla tekrar eslesmesin.
    pattern = re.compile("|".join(re.escape(k) for k in sorted(table, key=len, reverse=True)))
    hits = 0

    def sub(m):
        nonlocal hits
        hits += 1
        return table[m.group(0)]

    return pattern.sub(sub, text), hits


def transform(path: tuple, content: bytes) -> tuple[bytes, int]:
    """Bir arsiv dosyasini temalar; (yeni icerik, degisen deger sayisi) dondurur."""
    name = "/".join(path)
    if name.startswith("build/assets/index-") and name.endswith(".js"):
        text = content.decode("utf-8")
        if not all(k in text for k in RENDERER_REQUIRED):
            return content, 0
        text, hits = _replace_each(text, RENDERER)
        return text.encode("utf-8"), hits
    if len(path) == 2 and path[0] == "build" and path[1].startswith("index-") and name.endswith(".js"):
        text, hits = _replace_each(content.decode("utf-8"), MAIN)
        return text.encode("utf-8"), hits
    if name.startswith("build/assets/images/") and name.endswith(".svg"):
        text = content.decode("utf-8")
        hits = 0

        def sub(m):
            nonlocal hits
            new = SVG.get(m.group(1).upper())
            if new is None:
                return m.group(0)
            hits += 1
            return "#" + new

        text = re.sub(r"#([0-9A-Fa-f]{6})\b", sub, text)
        return text.encode("utf-8"), hits
    return content, 0
