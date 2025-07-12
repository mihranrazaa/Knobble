# rtl_sdr_radio_scanner/display.py

from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont
import os

class DisplayManager:
    def __init__(self):
        serial = i2c(port=1, address=0x3C)
        self.device = sh1106(serial)

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(font_path):
            self.font = ImageFont.truetype(font_path, 12)
        else:
            self.font = None

    def update(self, frequency, volume, signal_strength, mode, scan, preset):
        with canvas(self.device) as draw:
            draw.text((0, 0), f"{preset} [{mode}]", font=self.font, fill=255)
            draw.text((0, 14), f"Freq: {frequency/1e6:.3f} MHz", font=self.font, fill=255)
            draw.text((0, 26), f"Vol: {volume}%", font=self.font, fill=255)
            draw.text((0, 38), f"RSSI: {signal_strength} dB", font=self.font, fill=255)
            draw.text((0, 50), "Scan: ON" if scan else "Scan: OFF", font=self.font, fill=255)

            # Simple waterfall bar
            bar_length = int((signal_strength + 50) * 1.2)
            bar_length = min(max(bar_length, 0), 128)
            draw.rectangle((0, 63, bar_length, 63), outline=255, fill=255)

