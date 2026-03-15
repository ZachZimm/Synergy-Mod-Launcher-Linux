# SC2CampaignLauncher Linux Compatibility Bundle

This folder packages the changes needed to run the Warcraft III: Azeroth Reborn launcher on Linux without relying on the original Windows PyInstaller bootstrap.

## Quick start

1. Be sure python version 3.12 or newer is installed.
2. Run the all-in-one setup script:

```bash
./setup.sh
```

That script will create `./venv`, install `requirements.txt`, run `discover_sc2_env.py`, export any discovered values, and then start the launcher. It can be re-run in order to start the launcher again later.

or

1. Create a Python 3.12 virtualenv.
2. Install `requirements.txt`.
3. Make sure SC2 already works in Proton.
4. Set `SC2_ROOT`, `SC2_STEAM_APPID`, or `SC2_PROTON` only if auto-detection fails.
5. Run `./run_sc2campaignlauncher.sh`.

## What this bundle contains

- `run_sc2campaignlauncher.py`
  - Native Python bootstrap for Linux.
  - Loads the recovered launcher bytecode from `recovered_launcher/SC2CampaignLauncher.pyc`.
  - Auto-detects a StarCraft II install inside a Steam Proton prefix when possible.
  - Disables the launcher's Windows self-update path.
  - Patches the `Play` action to launch SC2 through Proton instead of trying to start a Windows `.exe` directly from Linux.
- `run_sc2campaignlauncher.sh`
  - Convenience wrapper that runs the bootstrap script.
- `recovered_launcher/`
  - Recovered launcher payload and bundled assets extracted from the original Windows executable.
- `SC2CampaignLauncher.exe`
  - Original launcher executable kept here for reference/provenance.
- `requirements.txt`
  - Python packages needed by the Linux bootstrap.
- `discover_sc2_env.py`
  - Helper script that discovers likely values for `SC2_ROOT`, `SC2_STEAM_APPID`, and `SC2_PROTON`.
- `setup.sh`
  - Creates a local Python 3.12 virtualenv, installs dependencies, runs discovery, and launches the wrapper.

## Some more details if you're interested
## What was changed

The original `SC2CampaignLauncher.exe` is a PyInstaller one-file Windows build. Under Proton it failed very early while trying to initialize its embedded Python runtime:

- `Failed to load Python DLL ... python312.dll`

To bypass that failure, the launcher payload was extracted and is now run directly under a normal Python 3.12 environment on Linux.

The Linux bootstrap also changes behavior in a few places:

- Uses Python 3.12 directly instead of the Windows PyInstaller stub.
- Uses a local writable appdata directory instead of assuming a writable Windows `%APPDATA%`.
- Detects the SC2 install in a Proton prefix.
- Converts the launcher map path to Windows form before passing it to `SC2Switcher_x64.exe`.
- Launches through `protontricks-launch` when available.
- Disables the original Windows self-update flow.

## Expected layout

Keep these files together:

- `run_sc2campaignlauncher.py`
- `run_sc2campaignlauncher.sh`
- `recovered_launcher/`

The script expects `recovered_launcher/SC2CampaignLauncher.pyc` and `recovered_launcher/assets/` to exist relative to the wrapper script.

## Python setup

This bundle assumes Python 3.12.

Example:

```bash
python3.12 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

Then run:

```bash
./venv/bin/python ./run_sc2campaignlauncher.py
```

or:

```bash
./run_sc2campaignlauncher.sh
```

If you use `run_sc2campaignlauncher.sh`, adjust it if your venv is not at `./venv`.

## Install assumptions

The script currently prefers Steam installed at:

```text
~/.local/share/Steam
```

It also assumes StarCraft II is inside a Steam Proton prefix and tries this app id first:

```text
2924749016
```

On the machine where this was tested, SC2 was found at:

```text
~/.local/share/Steam/steamapps/compatdata/2924749016/pfx/drive_c/Program Files (x86)/StarCraft II
```

## Things you may need to tailor

### 1. Different StarCraft II location

If SC2 is not auto-detected, set:

```bash
export SC2_ROOT="/path/to/StarCraft II"
```

This path should be the directory that contains:

```text
Support64/SC2Switcher_x64.exe
Maps/
Mods/
```

### 2. Different Steam app id / Proton prefix

If the SC2 install lives in a different compatdata prefix, set:

```bash
export SC2_STEAM_APPID="your_appid"
```

This matters mainly for `protontricks-launch --appid ...`.

### 3. Different Proton executable

If `protontricks-launch` is not available or you want to force a specific Proton build, set:

```bash
export SC2_PROTON="/full/path/to/proton"
```

Example:

```bash
export SC2_PROTON="$HOME/.local/share/Steam/steamapps/common/Proton 9.0 (Beta)/proton"
```

### 4. Different Steam directory

The script currently assumes:

```text
~/.local/share/Steam
```

If Steam lives somewhere else, the script itself will need to be edited. The relevant constant is near the top of `run_sc2campaignlauncher.py`:

```python
STEAM_DIR = Path.home() / ".local" / "share" / "Steam"
```

### 5. Different Python environment path

`run_sc2campaignlauncher.sh` currently runs:

```bash
./venv/bin/python ./run_sc2campaignlauncher.py
```

If your virtualenv is elsewhere, change that line.

## Runtime data

The Linux bootstrap writes launcher config/cache/log data to:

```text
./.launcher_appdata/SC2CampaignLauncher
```

That is intentional. It avoids write-permission problems inside Steam compatdata directories.

Useful files:

- `./.launcher_appdata/SC2CampaignLauncher/config.json`
- `./.launcher_appdata/SC2CampaignLauncher/launcher.log`
- `./.launcher_appdata/SC2CampaignLauncher/manifest.json`

## Launch behavior

When `Play` is clicked, the wrapper launches:

- `SC2Switcher_x64.exe`
- with `-run`
- and a Windows-style path to the launcher map, for example:

```text
C:\Program Files (x86)\StarCraft II\Maps\azerothreborn\ARLauncher.SC2Map
```

That Windows path conversion is necessary. Passing the Linux host path caused SC2 to report `Unable to open map`.

## Known limitations

- The original Windows self-update flow is intentionally disabled.
- This bundle is tied to the recovered payload from the included launcher build.
- If the upstream launcher changes significantly, the wrapper may need to be updated.
- If the mod author distributes source or an official Linux launcher, that is the better long-term solution.

## Discovery helper

This bundle also includes:

```bash
./discover_sc2_env.py
```

It prints shell-ready `export` lines for:

- `SC2_ROOT`
- `SC2_STEAM_APPID`
- `SC2_PROTON`

Example:

```bash
eval "$(./discover_sc2_env.py)"
```

Then launch the wrapper as usual.
