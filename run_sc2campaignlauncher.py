#!/usr/bin/env python3.12

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path


APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DATA_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
RECOVERED_DIR = DATA_ROOT / "recovered_launcher"
PYC_PATH = RECOVERED_DIR / "SC2CampaignLauncher.pyc"
STEAM_DIR = Path.home() / ".local" / "share" / "Steam"
DEFAULT_COMPAT_APPID = "2924749016"


def find_proton() -> Path | None:
    override = os.environ.get("SC2_PROTON")
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return candidate

    for candidate in (
        STEAM_DIR / "compatibilitytools.d" / "UMU-Proton-9.0-3.2" / "proton",
        STEAM_DIR / "steamapps" / "common" / "Proton 9.0 (Beta)" / "proton",
        STEAM_DIR / "steamapps" / "common" / "Proton - Experimental" / "proton",
        STEAM_DIR / "steamapps" / "common" / "Proton Hotfix" / "proton",
    ):
        if candidate.is_file():
            return candidate

    return None


def find_sc2_root() -> Path | None:
    override = os.environ.get("SC2_ROOT")
    if override:
        candidate = Path(override).expanduser()
        if (candidate / "Support64" / "SC2Switcher_x64.exe").is_file():
            return candidate

    direct = (
        STEAM_DIR
        / "steamapps"
        / "compatdata"
        / DEFAULT_COMPAT_APPID
        / "pfx"
        / "drive_c"
        / "Program Files (x86)"
        / "StarCraft II"
    )
    if (direct / "Support64" / "SC2Switcher_x64.exe").is_file():
        return direct

    compatdata = STEAM_DIR / "steamapps" / "compatdata"
    if compatdata.is_dir():
        for switcher in compatdata.glob("*/pfx/drive_c/**/Support64/SC2Switcher_x64.exe"):
            return switcher.parent.parent

    return None


def infer_prefix(sc2_root: Path | None) -> tuple[Path | None, str | None]:
    if not sc2_root:
        return None, None

    parts = sc2_root.parts
    if "compatdata" in parts and "pfx" in parts:
        compat_index = parts.index("compatdata")
        appid = parts[compat_index + 1]
        prefix_index = parts.index("pfx")
        prefix = Path(*parts[: prefix_index + 1])
        return prefix, appid

    pfx = sc2_root
    while pfx != pfx.parent:
        if pfx.name == "pfx" and (pfx / "drive_c").is_dir():
            return pfx, os.environ.get("SC2_STEAM_APPID")
        pfx = pfx.parent

    return None, os.environ.get("SC2_STEAM_APPID")


def proton_appdata(prefix: Path | None) -> Path:
    fallback = APP_ROOT / ".launcher_appdata"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def wrapper_config_path() -> Path:
    cfg_dir = proton_appdata(None) / "SC2CampaignLauncher"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "wrapper_config.json"


def load_wrapper_config() -> dict:
    path = wrapper_config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_wrapper_config(data: dict) -> None:
    wrapper_config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_config(appdata: Path, sc2_root: Path | None) -> Path:
    cfg_dir = appdata / "SC2CampaignLauncher"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.json"
    if sc2_root:
        cfg_path.write_text(json.dumps({"sc2_root": str(sc2_root)}, indent=2), encoding="utf-8")
    return cfg_path


def host_to_windows_path(path: Path, prefix: Path | None) -> str:
    resolved = path.resolve()
    if prefix:
        drive_c = (prefix / "drive_c").resolve()
        try:
            rel = resolved.relative_to(drive_c)
            return "C:\\" + "\\".join(rel.parts)
        except ValueError:
            pass

    return "Z:\\" + "\\".join(part for part in resolved.parts if part != "/")


def load_launcher_module():
    if not PYC_PATH.is_file():
        raise FileNotFoundError(f"Recovered launcher not found: {PYC_PATH}")

    spec = importlib.util.spec_from_file_location("sc2campaignlauncher_native", PYC_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {PYC_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def show_env_confirmation_dialog() -> int:
    from PyQt5.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    app = QApplication(sys.argv)
    dialog = QDialog()
    dialog.setWindowTitle("Confirm SC2 Environment")
    dialog.resize(760, 240)

    intro = QLabel(
        "Review the discovered paths before starting the launcher. "
        "Adjust them if auto-discovery picked the wrong install."
    )
    intro.setWordWrap(True)

    sc2_root_edit = QLineEdit(os.environ.get("SC2_DISCOVERED_ROOT", ""))
    appid_edit = QLineEdit(os.environ.get("SC2_DISCOVERED_APPID", ""))
    proton_edit = QLineEdit(os.environ.get("SC2_DISCOVERED_PROTON", ""))
    skip_checkbox = QCheckBox("Skip this confirmation window on future startups")
    skip_checkbox.setChecked(load_wrapper_config().get("skip_env_confirmation", False))

    def path_row(edit: QLineEdit, title: str, folder: bool) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit)
        button = QPushButton("Browse…")

        def choose() -> None:
            start = edit.text().strip() or str(Path.home())
            if folder:
                chosen = QFileDialog.getExistingDirectory(dialog, title, start)
            else:
                chosen, _ = QFileDialog.getOpenFileName(dialog, title, start)
            if chosen:
                edit.setText(chosen)

        button.clicked.connect(choose)
        layout.addWidget(button)
        return row

    form = QFormLayout()
    form.addRow("SC2_ROOT", path_row(sc2_root_edit, "Select StarCraft II folder", True))
    form.addRow("SC2_STEAM_APPID", appid_edit)
    form.addRow("SC2_PROTON", path_row(proton_edit, "Select Proton executable", False))

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

    def accept() -> None:
        sc2_root = sc2_root_edit.text().strip()
        proton = proton_edit.text().strip()
        if sc2_root and not (Path(sc2_root) / "Support64" / "SC2Switcher_x64.exe").is_file():
            QMessageBox.warning(
                dialog,
                "Invalid SC2_ROOT",
                "SC2_ROOT must point to the StarCraft II folder containing Support64/SC2Switcher_x64.exe.",
            )
            return
        if proton and not Path(proton).is_file():
            QMessageBox.warning(dialog, "Invalid SC2_PROTON", "SC2_PROTON must point to a Proton 'proton' file.")
            return
        print(
            json.dumps(
                {
                    "sc2_root": sc2_root,
                    "appid": appid_edit.text().strip(),
                    "proton": proton,
                    "skip_env_confirmation": skip_checkbox.isChecked(),
                }
            )
        )
        dialog.accept()

    buttons.accepted.connect(accept)
    buttons.rejected.connect(dialog.reject)

    layout = QVBoxLayout(dialog)
    layout.addWidget(intro)
    layout.addLayout(form)
    layout.addWidget(skip_checkbox)
    layout.addWidget(buttons)

    code = dialog.exec_()
    return 0 if code == QDialog.Accepted else 1


def confirm_env_settings(sc2_root: Path | None, appid: str | None, proton: Path | None) -> tuple[Path | None, str | None, Path | None]:
    if os.environ.get("SC2_LAUNCHER_AUTO_CONFIRM") == "1":
        return sc2_root, appid, proton
    if load_wrapper_config().get("skip_env_confirmation", False):
        return sc2_root, appid, proton

    env = os.environ.copy()
    env["SC2_DISCOVERED_ROOT"] = str(sc2_root or "")
    env["SC2_DISCOVERED_APPID"] = appid or ""
    env["SC2_DISCOVERED_PROTON"] = str(proton or "")

    cmd = [sys.executable, "--confirm-env"] if getattr(sys, "frozen", False) else [sys.executable, __file__, "--confirm-env"]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.returncode)

    payload = json.loads(result.stdout.strip())
    save_wrapper_config({"skip_env_confirmation": bool(payload.get("skip_env_confirmation"))})
    confirmed_root = Path(payload["sc2_root"]).expanduser() if payload.get("sc2_root") else None
    confirmed_appid = payload.get("appid") or None
    confirmed_proton = Path(payload["proton"]).expanduser() if payload.get("proton") else None
    return confirmed_root, confirmed_appid, confirmed_proton


def launch_command(sc2_exe: Path, launcher_file: Path, prefix: Path | None, appid: str | None) -> tuple[list[str], dict[str, str]]:
    env = os.environ.copy()
    env.setdefault("STEAM_DIR", str(STEAM_DIR))

    protontricks = shutil.which("protontricks-launch")
    if protontricks and appid:
        cmd = [protontricks, "--appid", appid, str(sc2_exe), "-run", str(launcher_file)]
        return cmd, env

    proton = find_proton()

    if proton and prefix and appid:
        env["STEAM_COMPAT_DATA_PATH"] = str(prefix.parent)
        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(STEAM_DIR)
        cmd = [str(proton), "run", str(sc2_exe), "-run", str(launcher_file)]
        return cmd, env

    wine = shutil.which("wine")
    if wine and prefix:
        env["WINEPREFIX"] = str(prefix)
        cmd = [wine, str(sc2_exe), "-run", str(launcher_file)]
        return cmd, env

    raise RuntimeError(
        "No usable launch backend found. Install protontricks or set SC2_PROTON to a Proton 'proton' script."
    )


def patch_launcher(module, sc2_root: Path | None, prefix: Path | None, appid: str | None) -> None:
    guesses = []
    if sc2_root:
        guesses.append(sc2_root)

    compatdata = STEAM_DIR / "steamapps" / "compatdata"
    if compatdata.is_dir():
        for switcher in compatdata.glob("*/pfx/drive_c/**/Support64/SC2Switcher_x64.exe"):
            candidate = switcher.parent.parent
            if candidate not in guesses:
                guesses.append(candidate)

    def common_guesses():
        return guesses

    def pick_sc2_root(parent=None):
        start_dir = str(sc2_root or Path.home())
        chosen = module.QFileDialog.getExistingDirectory(
            parent,
            "Select your StarCraft II installation folder",
            start_dir,
            module.QFileDialog.ShowDirsOnly | module.QFileDialog.DontResolveSymlinks,
        )
        return Path(chosen) if chosen else None

    def no_self_update():
        return False, {}

    def disable_self_update(self, meta):
        self._self_meta = {}
        self.self_upd_btn.hide()

    def linux_play(self):
        try:
            launcher = self.SC2_BASE_DIR / self.folder / self.launcher
            if not launcher.exists():
                self.installed = False
                self.download_campaign()
                return

            self.sc2_started.emit()
            windows_launcher = host_to_windows_path(launcher, prefix)
            cmd, env = launch_command(Path(self.SC2_EXE), Path(windows_launcher), prefix, appid)
            subprocess.Popen(cmd, cwd=str(Path(self.SC2_BASE_DIR).parent), env=env, start_new_session=True)
            self.window().start_sc2_watchdog()
        except Exception as exc:
            details = "\n".join(
                [
                    f"SC2_ROOT: {self.SC2_BASE_DIR.parent}",
                    f"SC2_EXE: {self.SC2_EXE}",
                    f"Launcher map: {self.SC2_BASE_DIR / self.folder / self.launcher}",
                    f"SC2_STEAM_APPID: {appid or ''}",
                    f"SC2_PROTON: {os.environ.get('SC2_PROTON', '')}",
                    "",
                    traceback.format_exc(),
                ]
            )
            try:
                module.logger.exception("Failed to launch SC2")
            except Exception:
                pass
            module.QMessageBox.critical(
                self.window(),
                "Launch Failed",
                f"Failed to launch StarCraft II.\n\n{exc}\n\nSee details for more information.",
                module.QMessageBox.Ok,
            )
            try:
                box = module.QMessageBox(self.window())
                box.setIcon(module.QMessageBox.Critical)
                box.setWindowTitle("Launch Failed Details")
                box.setText("The launcher could not start StarCraft II.")
                box.setDetailedText(details)
                box.setStandardButtons(module.QMessageBox.Ok)
                box.exec_()
            except Exception:
                pass

    module._common_guesses = common_guesses
    module._pick_sc2_root = pick_sc2_root
    module.check_self_update = no_self_update
    module.Launcher._init_self_update = disable_self_update
    module.Tile.play = linux_play


def main() -> int:
    if "--confirm-env" in sys.argv:
        return show_env_confirmation_dialog()

    sc2_root = find_sc2_root()
    prefix, appid = infer_prefix(sc2_root)
    proton = find_proton()
    sc2_root, confirmed_appid, proton = confirm_env_settings(sc2_root, appid, proton)
    if sc2_root:
        os.environ["SC2_ROOT"] = str(sc2_root)
    elif "SC2_ROOT" in os.environ:
        del os.environ["SC2_ROOT"]
    if proton:
        os.environ["SC2_PROTON"] = str(proton)
    elif "SC2_PROTON" in os.environ:
        del os.environ["SC2_PROTON"]
    if confirmed_appid:
        os.environ["SC2_STEAM_APPID"] = confirmed_appid
    elif "SC2_STEAM_APPID" in os.environ:
        del os.environ["SC2_STEAM_APPID"]
    prefix, inferred_appid = infer_prefix(sc2_root)
    appid = confirmed_appid or inferred_appid
    os.environ["APPDATA"] = str(proton_appdata(prefix))
    write_config(Path(os.environ["APPDATA"]), sc2_root)

    module = load_launcher_module()
    patch_launcher(module, sc2_root, prefix, appid)
    module.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
