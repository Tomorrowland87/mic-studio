import subprocess
import json
import os
import shutil
import time
import signal
from pathlib import Path

EE_CONFIG_DIR = Path.home() / ".config" / "easyeffects" / "db"
EE_PRESETS_DIR = Path.home() / ".local" / "share" / "easyeffects" / "input"
EE_AUTOLOAD_DIR = Path.home() / ".local" / "share" / "easyeffects" / "autoload" / "input"
EE_CONFIG_FILE = EE_CONFIG_DIR / "easyeffectsrc"

MIC_DEVICE_NAME = "alsa_card.usb-3142_fifine_Microphone-00"
MIC_SOURCE_NAME = "alsa_input.usb-3142_fifine_Microphone-00.analog-stereo"
AUTOLOAD_FILE = EE_AUTOLOAD_DIR / f"{MIC_DEVICE_NAME}:analog-stereo.json"


class Engine:
    def __init__(self):
        self._presets = {}

    def load_presets(self, preset_dir):
        preset_dir = Path(preset_dir)
        for f in sorted(preset_dir.glob("*.json")):
            name = f.stem.replace("_", " ").title()
            self._presets[name] = f

    def get_preset_names(self):
        return list(self._presets.keys())

    def apply_preset(self, name):
        if name not in self._presets:
            return False

        src = self._presets[name]
        dest = EE_PRESETS_DIR / src.name

        os.makedirs(EE_PRESETS_DIR, exist_ok=True)
        os.makedirs(EE_AUTOLOAD_DIR, exist_ok=True)

        shutil.copy2(src, dest)

        autoload = {
            "device": MIC_DEVICE_NAME,
            "device-description": "fifine Microphone",
            "device-profile": "analog-stereo",
            "preset-name": name
        }
        with open(AUTOLOAD_FILE, "w") as f:
            json.dump(autoload, f, indent=4)

        self._update_config(name)

        self._restart_ee()

        return True

    def _update_config(self, preset_name):
        os.makedirs(EE_CONFIG_DIR, exist_ok=True)
        config = {}
        if EE_CONFIG_FILE.exists():
            with open(EE_CONFIG_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("["):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        config[k.strip()] = v.strip()

        with open(EE_CONFIG_FILE, "w") as f:
            f.write("[Main]\n")
            f.write(f"lastLoadedInputPreset={preset_name}\n")
            f.write("\n")
            f.write("[StreamInputs]\n")
            f.write(f"inputDevice={MIC_SOURCE_NAME}\n")
            f.write("plugins=gate#0,compressor#0,limiter#0\n")
            f.write("visiblePage=pluginsPage\n")
            f.write("\n")
            f.write("[StreamOutputs]\n")
            f.write(f"outputDevice={MIC_SOURCE_NAME}\n")
            f.write("\n")
            f.write("[Window]\n")
            f.write("visiblePage=inputPage\n")

    def _restart_ee(self):
        self._stop_ee()
        time.sleep(0.5)
        subprocess.Popen(
            ["easyeffects", "--hide-window"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.5)

    def _stop_ee(self):
        subprocess.run(["easyeffects", "-q"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        for _ in range(10):
            r = subprocess.run(["pgrep", "easyeffects"],
                               capture_output=True, text=True)
            if not r.stdout.strip():
                return
            time.sleep(0.3)

        r = subprocess.run(["pgrep", "easyeffects"],
                           capture_output=True, text=True)
        for pid in r.stdout.strip().split():
            if pid:
                os.kill(int(pid), signal.SIGKILL)

    def get_bypass_state(self):
        r = subprocess.run(
            ["easyeffects", "--bypass", "3"],
            capture_output=True, text=True
        )
        return "1" in r.stdout

    def toggle_bypass(self):
        subprocess.run(["easyeffects", "--bypass-toggle"],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    def is_running(self):
        r = subprocess.run(["pgrep", "easyeffects"],
                           capture_output=True, text=True)
        return bool(r.stdout.strip())
