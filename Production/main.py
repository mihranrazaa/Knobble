# rtl_sdr_radio_scanner/main.py

import time
from hardware import HardwareController
from sdr import SDRController
from audio import AudioOutput
from display import DisplayManager
from config import load_presets, save_state, load_state

class RadioScanner:
    def __init__(self):
        self.hardware = HardwareController()
        self.sdr = SDRController()
        self.audio = AudioOutput()
        self.display = DisplayManager()
        self.presets = load_presets()

        last_state = load_state()
        if last_state:
            self.current_freq = last_state.get("frequency", self.presets[0]["frequency"])
            self.volume = last_state.get("volume", 50)
            self.mode = last_state.get("mode", "FM")
            self.preset_index = last_state.get("preset_index", 0)
        else:
            self.current_freq = self.presets[0]["frequency"]
            self.volume = 50
            self.mode = "FM"
            self.preset_index = 0

        self.scan_mode = False

    def update_display(self):
        signal_strength = self.sdr.get_signal_strength()
        self.display.update(
            frequency=self.current_freq,
            volume=self.volume,
            signal_strength=signal_strength,
            mode=self.mode,
            scan=self.scan_mode,
            preset=self.presets[self.preset_index]["name"]
        )

    def handle_input(self):
        enc_event = self.hardware.get_encoder_event()
        if enc_event == "ROTATE":
            self.volume = max(0, min(100, self.volume + self.hardware.encoder_delta))
            self.audio.set_volume(self.volume)
        elif enc_event == "PRESS_ROTATE":
            self.current_freq += self.hardware.encoder_delta * 25_000
            self.tune()
        elif enc_event == "PRESS":
            self.audio.toggle_recording(self.current_freq, self.mode)
        elif enc_event == "LONG_PRESS":
            self.scan_mode = not self.scan_mode

        if self.hardware.switch1_pressed():
            self.preset_index = (self.preset_index + 1) % len(self.presets)
            self.current_freq = self.presets[self.preset_index]["frequency"]
            self.mode = self.presets[self.preset_index]["mode"]
            self.tune()

        if self.hardware.switch2_pressed():
            self.scan_mode = not self.scan_mode

        if self.hardware.switch3_pressed():
            # Cycle modes: FM -> AM -> NFM
            modes = ["FM", "AM", "NFM"]
            idx = (modes.index(self.mode) + 1) % len(modes)
            self.mode = modes[idx]
            self.tune()

    def tune(self):
        self.sdr.tune(self.current_freq, self.mode)
        self.audio.set_source(self.sdr)

    def scan(self):
        self.current_freq += 25_000
        if self.current_freq > 470_000_000:
            self.current_freq = 88_000_000
        self.tune()

    def run(self):
        self.tune()
        self.audio.set_volume(self.volume)

        try:
            while True:
                self.handle_input()
                self.update_display()

                if self.scan_mode:
                    self.scan()
                    time.sleep(0.5)
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            save_state({
                "frequency": self.current_freq,
                "volume": self.volume,
                "mode": self.mode,
                "preset_index": self.preset_index
            })
            print("Exiting safely.")

if __name__ == "__main__":
    app = RadioScanner()
    app.run()

