# rtl_sdr_radio_scanner/audio.py

import alsaaudio
import threading
import numpy as np
import os
import wave
from scipy.signal import decimate, hilbert

class AudioOutput:
    def __init__(self):
        self.volume = 50
        self.pcm = alsaaudio.PCM()
        self.pcm.setchannels(1)
        self.pcm.setrate(44100)
        self.pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self.pcm.setperiodsize(1024)

        self.source = None
        self.playing = False
        self.recording = False
        self.record_file = None

        self.thread = threading.Thread(target=self._play_loop)
        self.thread.daemon = True
        self.thread.start()

    def set_volume(self, vol):
        self.volume = vol

    def set_source(self, sdr):
        self.source = sdr
        self.playing = True

    def toggle_recording(self, freq, mode):
        if self.recording:
            self.record_file.close()
            self.recording = False
        else:
            filename = f"recordings/{freq}_{mode}.wav"
            os.makedirs("recordings", exist_ok=True)
            self.record_file = wave.open(filename, 'wb')
            self.record_file.setnchannels(1)
            self.record_file.setsampwidth(2)
            self.record_file.setframerate(44100)
            self.recording = True

    def _demodulate(self, samples, mode):
        if mode == "FM":
            angle = np.unwrap(np.angle(samples))
            audio = np.diff(angle)
        elif mode in ["AM", "NFM"]:
            audio = np.abs(hilbert(samples))
        else:
            audio = samples

        audio = decimate(audio, int(len(audio) / 44100))
        audio *= self.volume / 100.0
        audio = np.clip(audio, -1, 1)
        return (audio * 32767).astype(np.int16).tobytes()

    def _play_loop(self):
        while True:
            if self.playing and self.source:
                samples = self.source.get_samples(256*1024)
                data = self._demodulate(samples, self.source.mode)
                self.pcm.write(data)

                if self.recording:
                    self.record_file.writeframes(data)
            else:
                time.sleep(0.1)

