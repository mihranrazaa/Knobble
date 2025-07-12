# rtl_sdr_radio_scanner/sdr.py

from rtlsdr import RtlSdr
import numpy as np

class SDRController:
    def __init__(self):
        self.sdr = RtlSdr()
        self.sample_rate = 2.4e6  # Default
        self.gain = 'auto'
        self.freq = 100e6
        self.mode = "FM"

        self.sdr.sample_rate = self.sample_rate
        self.sdr.gain = self.gain

    def tune(self, freq_hz, mode):
        self.freq = freq_hz
        self.mode = mode
        self.sdr.center_freq = freq_hz

    def get_samples(self, num_samples=256*1024):
        return self.sdr.read_samples(num_samples)

    def get_signal_strength(self):
        samples = self.sdr.read_samples(1024)
        power = 10 * np.log10(np.mean(np.abs(samples)**2))
        return round(power, 1)

    def close(self):
        self.sdr.close()

