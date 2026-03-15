#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path


def candidate_steam_dirs() -> list[Path]:
    seen: list[Path] = []
    for value in (
        os.environ.get("STEAM_DIR"),
        str(Path.home() / ".local" / "share" / "Steam"),
        str(Path.home() / ".steam" / "steam"),
        str(Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"),
    ):
        if not value:
            continue
        path = Path(value).expanduser()
        if path not in seen and path.is_dir():
            seen.append(path)
    return seen


def discover_sc2_root(steam_dir: Path) -> tuple[Path | None, str | None]:
    compatdata = steam_dir / "steamapps" / "compatdata"
    if not compatdata.is_dir():
        return None, None

    matches: list[tuple[str, Path]] = []
    for switcher in compatdata.glob("*/pfx/drive_c/**/Support64/SC2Switcher_x64.exe"):
        try:
            appid = switcher.relative_to(compatdata).parts[0]
        except Exception:
            continue
        matches.append((appid, switcher.parent.parent))

    if not matches:
        return None, None

    for appid, root in matches:
        if appid == "2924749016":
            return root, appid

    matches.sort(key=lambda item: item[0])
    return matches[0][1], matches[0][0]


def discover_proton(steam_dir: Path) -> Path | None:
    candidates = [
        steam_dir / "compatibilitytools.d" / "UMU-Proton-9.0-3.2" / "proton",
        steam_dir / "steamapps" / "common" / "Proton 9.0 (Beta)" / "proton",
        steam_dir / "steamapps" / "common" / "Proton - Experimental" / "proton",
        steam_dir / "steamapps" / "common" / "Proton Hotfix" / "proton",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    dynamic = sorted(steam_dir.glob("compatibilitytools.d/*/proton"))
    if dynamic:
        return dynamic[0]

    dynamic = sorted((steam_dir / "steamapps" / "common").glob("*/proton"))
    if dynamic:
        return dynamic[0]

    return None


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main() -> int:
    for steam_dir in candidate_steam_dirs():
        sc2_root, appid = discover_sc2_root(steam_dir)
        proton = discover_proton(steam_dir)
        if not sc2_root and not proton:
            continue

        print(f"# Steam dir: {steam_dir}")
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

    print("# No Steam install or SC2 Proton prefix could be discovered.", file=sys.stderr)
    return 1


def shutil_which(name: str) -> str | None:
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for entry in paths:
        candidate = Path(entry) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
