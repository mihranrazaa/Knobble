# config.py

import json
import os

CONFIG_DIR = os.path.expanduser("~/.rtl_sdr_scanner")
PRESET_FILE = os.path.join(CONFIG_DIR, "presets.json")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")

DEFAULT_PRESETS = [
    {"name": "FM Radio", "frequency": 98300000, "mode": "FM"},
    {"name": "AIR Band", "frequency": 125000000, "mode": "AM"},
    {"name": "VHF Emergency", "frequency": 154600000, "mode": "NFM"},
    {"name": "Ham 2m", "frequency": 145500000, "mode": "NFM"},
    {"name": "UHF Band", "frequency": 435000000, "mode": "NFM"},
]

def load_presets():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(PRESET_FILE):
        with open(PRESET_FILE, "w") as f:
            json.dump(DEFAULT_PRESETS, f, indent=2)
    with open(PRESET_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

