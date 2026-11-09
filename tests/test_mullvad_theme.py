"""maze-mullvad-theme tests. No root, no Mullvad install needed.

The archive patcher is tested against a small asar built here, the apply and
restore scripts against that archive in a temp dir (their paths are taken from
MMT_* environment variables), and the generator renders the real icon set.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "system"
sys.path.insert(0, str(SYSTEM))

import patch_asar
import theme

ICON_DIR = "build/assets/images/menubar-icons/linux"
# What Mullvad loads on Linux (tray-icon-controller.ts): lock-1..10 with "",
# "_notification", "_white" and "_white_notification".
EXPECTED_ICONS = sorted(
    f"lock-{frame}{white}{note}.png"
    for frame in range(1, 11)
    for white in ("", "_white")
    for note in ("", "_notification")
)


def make_asar(path: pathlib.Path, files: dict[str, bytes]) -> None:
    """Writes an asar holding `files` (path -> content), with integrity like Electron's."""
    header: dict = {"files": {}}
    body = b""
    for name, content in files.items():
        node = header
        *dirs, leaf = name.split("/")
        for d in dirs:
            node = node["files"].setdefault(d, {"files": {}})
        node["files"][leaf] = {
            "size": len(content),
            "offset": str(len(body)),
            "integrity": patch_asar.integrity(content, 4 * 1024 * 1024),
        }
        body += content
    path.write_bytes(patch_asar.pack_header(header) + body)


def read_files(path: pathlib.Path) -> dict[str, bytes]:
    header, data, base = patch_asar.read_asar(path)
    out = {}
    for parts, entry in patch_asar.files_in_order(header):
        off = base + int(entry["offset"])
        content = data[off:off + entry["size"]]
        assert hashlib.sha256(content).hexdigest() == entry["integrity"]["hash"], parts
        out["/".join(parts)] = content
    return out


class PatchAsarTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.files = {
            "package.json": b'{"name":"mullvad-vpn"}',
            f"{ICON_DIR}/lock-1.png": b"old-red",
            f"{ICON_DIR}/lock-9.png": b"old-green",
            f"{ICON_DIR}/lock-placeholder.png": b"placeholder",
            "build/main.js": b"console.log('main')" * 50,
        }
        make_asar(self.tmp / "in.asar", self.files)
        self.icons = self.tmp / "icons"
        self.icons.mkdir()

    def patch(self):
        return subprocess.run([sys.executable, str(SYSTEM / "patch_asar.py"),
                               str(self.tmp / "in.asar"), str(self.icons), str(self.tmp / "out.asar")],
                              check=False, capture_output=True, text=True)

    def test_replaces_icons_and_keeps_everything_else(self):
        (self.icons / "lock-1.png").write_bytes(b"new red icon, longer than before")
        (self.icons / "lock-9.png").write_bytes(b"g")
        self.assertEqual(self.patch().returncode, 0)
        out = read_files(self.tmp / "out.asar")  # also checks every integrity hash
        self.assertEqual(out[f"{ICON_DIR}/lock-1.png"], b"new red icon, longer than before")
        self.assertEqual(out[f"{ICON_DIR}/lock-9.png"], b"g")
        for name in ("package.json", "build/main.js", f"{ICON_DIR}/lock-placeholder.png"):
            self.assertEqual(out[name], self.files[name])

    def test_unknown_icon_leaves_no_output(self):
        """If Mullvad renames its icons, nothing is written: apply keeps the original."""
        (self.icons / "lock-99.png").write_bytes(b"x")
        r = self.patch()
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.tmp / "out.asar").exists())


RENDERER_JS = b"const c={darkBlue:'rgb(25, 46, 69)',blue:'rgb(41, 77, 115)',green:'rgb(68, 173, 77)'};"


class ThemeTestCase(unittest.TestCase):
    def test_renderer_blues_turn_gray_and_status_colors_stay(self):
        out, hits = theme.transform(("build", "assets", "index-abc.js"), RENDERER_JS)
        self.assertEqual(hits, 2)
        self.assertIn(b"rgb(11, 11, 11)", out)
        self.assertIn(b"rgb(48, 48, 48)", out)
        self.assertIn(b"rgb(68, 173, 77)", out)

    def test_renderer_without_known_tokens_is_left_alone(self):
        """A Mullvad release with a new palette: no half-themed interface."""
        js = b"const c={darkBlue:'rgb(1, 2, 3)',blue:'rgb(41, 77, 115)'};"
        self.assertEqual(theme.transform(("build", "assets", "index-abc.js"), js), (js, 0))

    def test_main_process_window_background(self):
        out, hits = theme.transform(("build", "index-xyz.js"), b"backgroundColor:'#192e45'")
        self.assertEqual((out, hits), (b"backgroundColor:'#0b0b0b'", 1))

    def test_svg_only_known_navy_shades_change(self):
        svg = b'<svg><path fill="#192E45"/><path fill="#294d73"/><path fill="#1D4ED8"/></svg>'
        out, hits = theme.transform(("build", "assets", "images", "logo-icon.svg"), svg)
        self.assertEqual(hits, 2)
        self.assertEqual(out, b'<svg><path fill="#0B0B0B"/><path fill="#303030"/><path fill="#1D4ED8"/></svg>')

    def test_no_replacement_feeds_another(self):
        """darkBlue becomes rgb(11, 11, 11); nothing may then match that again."""
        self.assertFalse(set(theme.RENDERER.values()) & set(theme.RENDERER))


class ApplyRestoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.asar = self.tmp / "app.asar"
        make_asar(self.asar, {f"{ICON_DIR}/lock-1.png": b"mullvad", "main.js": b"code",
                              "build/assets/index-abc.js": RENDERER_JS})
        self.original = self.asar.read_bytes()
        icons = self.tmp / "icons"
        icons.mkdir()
        (icons / "lock-1.png").write_bytes(b"maze")
        share = self.tmp / "share"
        (share / "appicon").mkdir(parents=True)
        (share / "appicon" / "32.png").write_bytes(b"maze app icon")
        self.app_icon = self.tmp / "hicolor" / "32x32" / "apps" / "mullvad-vpn.png"
        self.app_icon.parent.mkdir(parents=True)
        self.app_icon.write_bytes(b"mullvad app icon")
        self.env = dict(os.environ, MMT_LIB=str(SYSTEM), MMT_ICONS=str(icons), MMT_SHARE=str(share),
                        MMT_STATE=str(self.tmp / "state"), MMT_ASAR=str(self.asar),
                        MMT_HICOLOR=str(self.tmp / "hicolor"), MMT_CONF=str(self.tmp / "conf"))

    def run_script(self, name):
        r = subprocess.run(["bash", str(SYSTEM / name)], env=self.env, check=False, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_apply_twice_then_restore_gives_back_mullvads_archive(self):
        self.run_script("apply")
        self.assertEqual(read_files(self.asar)[f"{ICON_DIR}/lock-1.png"], b"maze")
        # A second apply (package reinstall) must not back up the patched archive.
        self.run_script("apply")
        self.run_script("restore")
        self.assertEqual(self.asar.read_bytes(), self.original)

    def test_mullvad_upgrade_is_backed_up_fresh(self):
        self.run_script("apply")
        make_asar(self.asar, {f"{ICON_DIR}/lock-1.png": b"mullvad v2", "main.js": b"new code"})
        upgraded = self.asar.read_bytes()
        self.run_script("apply")  # what the pacman hook does after the upgrade
        self.assertEqual(read_files(self.asar)["main.js"], b"new code")
        self.run_script("restore")
        self.assertEqual(self.asar.read_bytes(), upgraded)

    def test_restore_leaves_an_unpatched_archive_alone(self):
        self.run_script("apply")
        make_asar(self.asar, {f"{ICON_DIR}/lock-1.png": b"mullvad v3", "main.js": b"x"})
        upgraded = self.asar.read_bytes()
        self.run_script("restore")
        self.assertEqual(self.asar.read_bytes(), upgraded)

    def test_theme_and_app_icon_are_applied_and_restored(self):
        self.run_script("apply")
        self.assertIn(b"rgb(11, 11, 11)", read_files(self.asar)["build/assets/index-abc.js"])
        self.assertEqual(self.app_icon.read_bytes(), b"maze app icon")
        self.run_script("apply")
        self.run_script("restore")
        self.assertEqual(self.asar.read_bytes(), self.original)
        self.assertEqual(self.app_icon.read_bytes(), b"mullvad app icon")

    def test_theme_can_be_turned_off(self):
        (self.tmp / "conf").write_text("THEME=0\n")
        self.run_script("apply")
        files = read_files(self.asar)
        self.assertEqual(files[f"{ICON_DIR}/lock-1.png"], b"maze")
        self.assertEqual(files["build/assets/index-abc.js"], RENDERER_JS)

    def test_failed_patch_keeps_mullvads_archive(self):
        (pathlib.Path(self.env["MMT_ICONS"]) / "lock-99.png").write_bytes(b"x")
        self.run_script("apply")
        self.assertEqual(self.asar.read_bytes(), self.original)


# Mullvad's own archive: once this package is installed the one in /usr/lib is
# already patched, so prefer the clean copy apply keeps.
# The second path is where this package kept it under its old name, maze-mullvad-tray.
MULLVAD_ASAR = next((p for p in (pathlib.Path("/var/lib/maze-mullvad-theme/app.asar.orig"),
                                 pathlib.Path("/var/lib/maze-mullvad-tray/app.asar.orig"),
                                 pathlib.Path("/usr/lib/mullvad-vpn/app.asar")) if p.is_file()), None)


@unittest.skipUnless(shutil.which("rsvg-convert"), "rsvg-convert (librsvg) missing")
class GenerateTestCase(unittest.TestCase):
    def test_renders_every_icon_mullvad_loads(self):
        with tempfile.TemporaryDirectory() as out:
            subprocess.run([sys.executable, str(ROOT / "generate.py"), out],
                           check=True, capture_output=True)
            pngs = sorted(p.name for p in pathlib.Path(out, "icons").glob("*.png"))
            self.assertEqual(pngs, EXPECTED_ICONS)
            for name in pngs:
                head = pathlib.Path(out, "icons", name).read_bytes()[:24]
                self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
                width, height = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
                self.assertEqual((width, height), (48, 48), name)

    @unittest.skipUnless(MULLVAD_ASAR, "mullvad-vpn not installed")
    def test_fits_the_installed_mullvad(self):
        """Catches a Mullvad release that renames or moves its tray icons."""
        with tempfile.TemporaryDirectory() as out:
            subprocess.run([sys.executable, str(ROOT / "generate.py"), out],
                           check=True, capture_output=True)
            r = subprocess.run([sys.executable, str(SYSTEM / "patch_asar.py"),
                                str(MULLVAD_ASAR), str(pathlib.Path(out, "icons")),
                                str(pathlib.Path(out, "app.asar"))], check=False, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(f"{len(EXPECTED_ICONS)} ikon", r.stdout)
            # Every colour in the theme table is still in this Mullvad's interface.
            self.assertIn(f"arayuz: {len(theme.RENDERER)})", r.stdout)

    def test_renders_the_app_icon_sizes(self):
        with tempfile.TemporaryDirectory() as out:
            subprocess.run([sys.executable, str(ROOT / "generate.py"), out],
                           check=True, capture_output=True)
            names = sorted(p.name for p in pathlib.Path(out, "appicon").glob("*.png"))
            self.assertEqual(names, sorted(f"{n}.png" for n in (16, 32, 128, 256, 512)))


if __name__ == "__main__":
    unittest.main()
