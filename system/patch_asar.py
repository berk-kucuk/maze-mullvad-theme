#!/usr/bin/env python3
"""Mullvad app.asar icindeki Linux tray ikonlarini degistirir ve arayuzu
Maze siyahina cevirir (bkz. theme.py).

Kullanim: patch_asar.py <girdi app.asar> <ikon klasoru> <cikti app.asar> [--no-theme]

Arsiv yeniden yazilir: degisen dosyalarin boyutu, ofseti ve integrity
(sha256 + blok hash'leri) guncellenir, diger dosyalar bayt bayt aynen kalir.
Ikonlardan sadece ikon klasorunde ayni adla bulunanlar degistirilir.
"""
import hashlib
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import theme

ICON_DIR_IN_ASAR = ("build", "assets", "images", "menubar-icons", "linux")


def read_asar(path: pathlib.Path):
    data = path.read_bytes()
    header_pickle_size = struct.unpack_from("<I", data, 4)[0]
    json_len = struct.unpack_from("<I", data, 12)[0]
    header = json.loads(data[16:16 + json_len])
    return header, data, 8 + header_pickle_size


def files_in_order(node, prefix=()):
    for name, entry in node.get("files", {}).items():
        if "files" in entry:
            yield from files_in_order(entry, prefix + (name,))
        else:
            yield prefix + (name,), entry


def integrity(content: bytes, block_size: int) -> dict:
    return {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(content).hexdigest(),
        "blockSize": block_size,
        "blocks": [hashlib.sha256(content[i:i + block_size]).hexdigest()
                   for i in range(0, max(len(content), 1), block_size)],
    }


def pack_header(header: dict) -> bytes:
    raw = json.dumps(header, separators=(",", ":")).encode()
    padded = raw + b"\0" * (-len(raw) % 4)
    string_pickle = struct.pack("<II", 4 + len(padded), len(raw)) + padded
    return struct.pack("<II", 4, len(string_pickle)) + string_pickle


def main() -> None:
    src, icons, dst = (pathlib.Path(a) for a in sys.argv[1:4])
    use_theme = "--no-theme" not in sys.argv[4:]
    header, data, base = read_asar(src)
    replacements = {p.name: p.read_bytes() for p in icons.glob("*.png")}

    body = bytearray()
    replaced = []
    themed = {}
    for path, entry in files_in_order(header):
        if entry.get("unpacked") or "link" in entry or "offset" not in entry:
            continue
        old = data[base + int(entry["offset"]): base + int(entry["offset"]) + entry["size"]]
        new = old
        if path[:-1] == ICON_DIR_IN_ASAR and path[-1] in replacements:
            new = replacements[path[-1]]
            replaced.append(path[-1])
        elif use_theme:
            new, hits = theme.transform(path, old)
            if hits:
                themed["/".join(path)] = hits
        if new != old and "integrity" in entry:
            entry["integrity"] = integrity(new, entry["integrity"].get("blockSize", 4 * 1024 * 1024))
        entry["offset"] = str(len(body))
        entry["size"] = len(new)
        body += new

    missing = sorted(set(replacements) - set(replaced))
    if missing:
        sys.exit(f"Arsivde bulunamayan ikonlar: {missing}")
    dst.write_bytes(pack_header(header) + body)
    print(f"{len(replaced)} ikon degistirildi -> {dst}")
    if use_theme:
        renderer = sum(v for k, v in themed.items() if k.startswith("build/assets/index-"))
        print(f"tema: {sum(themed.values())} renk, {len(themed)} dosya (arayuz: {renderer})")


if __name__ == "__main__":
    main()
