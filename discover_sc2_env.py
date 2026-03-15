#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_COMPAT_APPID = "2924749016"
SC2_SWITCHER = Path("Support64") / "SC2Switcher_x64.exe"


def dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in paths:
        try:
            normalized = path.expanduser().resolve()
        except Exception:
            normalized = path.expanduser()
        if normalized in seen or not normalized.exists():
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def parse_libraryfolders_vdf(vdf_path: Path) -> list[Path]:
    libraries: list[Path] = []
    try:
        for raw_line in vdf_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or '"path"' not in line:
                continue
            parts = [part for part in line.split('"') if part]
            if len(parts) < 2:
                continue
            candidate = Path(parts[-1].replace("\\\\", "\\"))
            libraries.append(candidate)
    except Exception:
        return []
    return libraries


def candidate_steam_library_dirs() -> list[Path]:
    libraries: list[Path] = []
    for steam_dir in candidate_steam_dirs():
        libraries.append(steam_dir)
        libraries.extend(parse_libraryfolders_vdf(steam_dir / "steamapps" / "libraryfolders.vdf"))
        libraries.extend(parse_libraryfolders_vdf(steam_dir / "libraryfolder.vdf"))
    return dedupe_paths(libraries)


def candidate_steam_dirs() -> list[Path]:
    candidates = []
    env_value = os.environ.get("STEAM_DIR")
    if env_value:
        candidates.append(Path(env_value))

    home = Path.home()
    for value in (
        os.environ.get("STEAM_DIR"),
        home / ".local" / "share" / "Steam",
        home / ".steam" / "steam",
        home / ".steam" / "root",
        home / ".steam" / "debian-installation",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam",
        home / "snap" / "steam" / "common" / ".steam" / "steam",
        home / "snap" / "steam" / "common" / ".local" / "share" / "Steam",
    ):
        if value:
            candidates.append(Path(value))
    return [path for path in dedupe_paths(candidates) if path.is_dir()]


def steam_compatdata_dirs(steam_library: Path) -> list[Path]:
    compatdata = steam_library / "steamapps" / "compatdata"
    return [compatdata] if compatdata.is_dir() else []


def is_sc2_root(path: Path) -> bool:
    return (path / SC2_SWITCHER).is_file()


def discover_sc2_root_from_steam(steam_library: Path) -> tuple[Path | None, str | None]:
    compatdata_dirs = steam_compatdata_dirs(steam_library)
    if not compatdata_dirs:
        return None, None

    matches: list[tuple[str | None, Path]] = []
    direct = (
        compatdata_dirs[0]
        / DEFAULT_COMPAT_APPID
        / "pfx"
        / "drive_c"
        / "Program Files (x86)"
        / "StarCraft II"
    )
    if is_sc2_root(direct):
        return direct, DEFAULT_COMPAT_APPID

    for compatdata in compatdata_dirs:
        for switcher in compatdata.glob("*/pfx/drive_c/**/Support64/SC2Switcher_x64.exe"):
            try:
                appid = switcher.relative_to(compatdata).parts[0]
            except Exception:
                appid = None
            matches.append((appid, switcher.parent.parent))

    if not matches:
        return None, None

    for appid, root in matches:
        if appid == DEFAULT_COMPAT_APPID:
            return root, appid

    matches.sort(key=lambda item: (item[0] is None, item[0] or "", str(item[1])))
    return matches[0][1], matches[0][0]


def candidate_prefix_dirs() -> list[Path]:
    home = Path.home()
    prefixes: list[Path] = []
    env_prefixes = os.environ.get("WINEPREFIX")
    if env_prefixes:
        prefixes.append(Path(env_prefixes))

    prefixes.extend(
        [
            home / ".wine",
            home / ".local" / "share" / "lutris",
            home / "Games",
        ]
    )

    for root in (home / ".local" / "share" / "lutris", home / "Games"):
        if not root.is_dir():
            continue
        for candidate in root.iterdir():
            prefixes.append(candidate)
            prefixes.append(candidate / "pfx")
    return [path for path in dedupe_paths(prefixes) if path.is_dir()]


def discover_sc2_root_from_prefix(prefix: Path) -> Path | None:
    roots = [
        prefix / "drive_c" / "Program Files (x86)" / "StarCraft II",
        prefix / "pfx" / "drive_c" / "Program Files (x86)" / "StarCraft II",
        prefix / "drive_c" / "Program Files" / "StarCraft II",
        prefix / "pfx" / "drive_c" / "Program Files" / "StarCraft II",
    ]
    for root in roots:
        if is_sc2_root(root):
            return root

    for drive_c in (prefix / "drive_c", prefix / "pfx" / "drive_c"):
        if not drive_c.is_dir():
            continue
        for switcher in drive_c.glob("**/Support64/SC2Switcher_x64.exe"):
            return switcher.parent.parent
    return None


def discover_sc2_root() -> tuple[Path | None, str | None, Path | None]:
    for steam_library in candidate_steam_library_dirs():
        sc2_root, appid = discover_sc2_root_from_steam(steam_library)
        if sc2_root:
            return sc2_root, appid, steam_library

    for prefix in candidate_prefix_dirs():
        sc2_root = discover_sc2_root_from_prefix(prefix)
        if sc2_root:
            return sc2_root, os.environ.get("SC2_STEAM_APPID"), None

    return None, None, None


def discover_proton(steam_library: Path) -> Path | None:
    candidates = [
        steam_library / "compatibilitytools.d" / "UMU-Proton-9.0-3.2" / "proton",
        steam_library / "steamapps" / "common" / "Proton 9.0 (Beta)" / "proton",
        steam_library / "steamapps" / "common" / "Proton - Experimental" / "proton",
        steam_library / "steamapps" / "common" / "Proton Hotfix" / "proton",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    dynamic = sorted(steam_library.glob("compatibilitytools.d/*/proton"))
    if dynamic:
        return dynamic[0]

    dynamic = sorted((steam_library / "steamapps" / "common").glob("*/proton"))
    if dynamic:
        return dynamic[0]

    return None


def discover_any_proton() -> tuple[Path | None, Path | None]:
    for steam_library in candidate_steam_library_dirs():
        proton = discover_proton(steam_library)
        if proton:
            return proton, steam_library
    return None, None


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main() -> int:
    sc2_root, appid, sc2_steam_library = discover_sc2_root()
    proton, proton_steam_library = discover_any_proton()

    if not sc2_root and not proton:
        print("# No Steam install, Proton binary, or SC2 prefix could be discovered.", file=sys.stderr)
        return 1

    steam_library = sc2_steam_library or proton_steam_library
    if steam_library:
        print(f"# Steam library: {steam_library}")

    if sc2_root:
        print(f"export SC2_ROOT={shell_quote(str(sc2_root))}")
    else:
        print("# SC2_ROOT not found")

    if appid:
        print(f"export SC2_STEAM_APPID={shell_quote(appid)}")
    else:
        print("# SC2_STEAM_APPID not found")

    if proton:
        print(f"export SC2_PROTON={shell_quote(str(proton))}")
    else:
        print("# SC2_PROTON not found")

    launcher = shutil_which("protontricks-launch")
    if launcher:
        print(f"# protontricks-launch: {launcher}")

    return 0


def shutil_which(name: str) -> str | None:
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for entry in paths:
        candidate = Path(entry) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
