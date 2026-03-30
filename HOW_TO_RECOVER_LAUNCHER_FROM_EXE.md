# How To Recover `recovered_launcher` From A Fresh `SC2CampaignLauncher.exe`

This file documents how to rebuild the `recovered_launcher/` directory from a newly downloaded `SC2CampaignLauncher.exe`.

The goal is to extract:

- the embedded launcher bytecode
- the bundled image assets the launcher expects at runtime

This process does not require the original launcher source code.

## What `recovered_launcher` needs to contain

At minimum:

- `recovered_launcher/SC2CampaignLauncher.pyc`
- `recovered_launcher/assets/app.ico`
- `recovered_launcher/assets/discord.png`
- `recovered_launcher/assets/info.png`
- `recovered_launcher/assets/logo.png`
- `recovered_launcher/assets/patreon.png`
- `recovered_launcher/assets/settings.png`

These come from the PyInstaller archive embedded in `SC2CampaignLauncher.exe`.

## Prerequisites

Use Python 3.12 if possible, because the launcher bundle here targets Python 3.12.

Install PyInstaller into a venv:

```bash
python3.12 -m venv venv
./venv/bin/python -m pip install pyinstaller
```

## Step 1. Confirm the EXE is a PyInstaller bundle

You can inspect it with:

```bash
./venv/bin/pyi-archive_viewer ./SC2CampaignLauncher.exe
```

You should see entries such as:

- `SC2CampaignLauncher`
- `pyiboot01_bootstrap`
- `pyi_rth_pyqt5`
- `assets\\app.ico`
- `assets\\logo.png`
- `python312.dll`

That confirms the EXE contains an embedded PyInstaller archive.

## Step 2. Create the output directory

```bash
mkdir -p recovered_launcher/assets
```

## Step 3. Extract the launcher bytecode and assets

Run this from the directory containing `SC2CampaignLauncher.exe`:

```bash
./venv/bin/python - <<'PY'
from importlib.util import MAGIC_NUMBER
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

exe = Path("SC2CampaignLauncher.exe")
out = Path("recovered_launcher")
out.mkdir(exist_ok=True)
(out / "assets").mkdir(parents=True, exist_ok=True)

arc = CArchiveReader(str(exe))

# Extract the main launcher module as a normal .pyc file.
launcher_data = arc.extract("SC2CampaignLauncher")
pyc = MAGIC_NUMBER + (0).to_bytes(4, "little") + (0).to_bytes(8, "little") + launcher_data
(out / "SC2CampaignLauncher.pyc").write_bytes(pyc)

# Extract bundled assets used by the launcher UI.
for name in arc.toc:
    if name.startswith("assets\\\\"):
        rel = Path(name.replace("\\\\", "/"))
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(arc.extract(name))
        print(f"wrote {dst}")

print("wrote", out / "SC2CampaignLauncher.pyc")
PY
```

## Step 4. Verify the recovered files

Check the output:

```bash
find recovered_launcher -maxdepth 2 -type f | sort
```

You should see:

```text
recovered_launcher/SC2CampaignLauncher.pyc
recovered_launcher/assets/app.ico
recovered_launcher/assets/discord.png
recovered_launcher/assets/info.png
recovered_launcher/assets/logo.png
recovered_launcher/assets/patreon.png
recovered_launcher/assets/settings.png
```

## Step 5. Test that the recovered launcher payload is readable

This only verifies that Python can load the bytecode file, not that the full launcher UI will run:

```bash
./venv/bin/python - <<'PY'
import importlib.util
from pathlib import Path

path = Path("recovered_launcher/SC2CampaignLauncher.pyc")
spec = importlib.util.spec_from_file_location("sc2campaignlauncher_test", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print("loaded", module.__name__)
PY
```

If that succeeds, the recovered payload is usable by the Linux wrapper.

## Notes

- `SC2CampaignLauncher.pyc` is the launcher's embedded Python bytecode module.
- The wrapper scripts in this repository load that bytecode directly instead of running the original Windows PyInstaller bootstrap.
- If a future launcher release changes bundled asset names or adds more required assets, update the extraction script accordingly.
- If the upstream EXE stops being a PyInstaller bundle, this procedure will need to change.
