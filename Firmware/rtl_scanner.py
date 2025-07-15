#!/usr/bin/env python3
"""
RTL-SDR Radio Scanner for Raspberry Pi Zero 2W
Simple, working implementation with basic features
"""

import time
import threading
import subprocess
import os
import json
from datetime import datetime

# GPIO and Hardware imports
try:
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    import numpy as np
    from rtlsdr import RtlSdr
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip3 install RPi.GPIO luma.oled numpy pyrtlsdr")
    exit(1)

# Hardware Configuration
ENCODER_CLK = 22
ENCODER_DT = 27
ENCODER_SW = 17
SWITCH_1 = 23
SWITCH_2 = 24
SWITCH_3 = 25

# Frequency presets (India-specific)
PRESETS = {
    'FM': [
        {'name': 'All India Radio', 'freq': 101.3e6},
        {'name': 'Radio Mirchi', 'freq': 98.3e6},
        {'name': 'Red FM', 'freq': 93.5e6},
        {'name': 'FM Gold', 'freq': 100.1e6},
        {'name': 'Big FM', 'freq': 92.7e6},
    ],
    'Aviation': [
        {'name': 'Delhi Tower', 'freq': 119.1e6},
        {'name': 'Mumbai Tower', 'freq': 119.9e6},
        {'name': 'Bangalore Tower', 'freq': 124.5e6},
        {'name': 'Chennai Tower', 'freq': 122.7e6},
    ],
    'Emergency': [
        {'name': 'Police Band', 'freq': 162.5e6},
        {'name': 'Fire Service', 'freq': 165.0e6},
        {'name': 'Ambulance', 'freq': 163.0e6},
    ]
}

class RTLScanner:
    def __init__(self):
        self.sdr = None
        self.current_freq = 101.3e6  # Default FM frequency
        self.volume = 50
        self.scanning = False
        self.current_band = 'FM'
        self.preset_index = 0
        self.signal_strength = 0
        
        # Encoder state
        self.encoder_pos = 0
        self.encoder_pressed = False
        self.last_clk = GPIO.HIGH
        
        # Initialize hardware
        self.setup_gpio()
        self.setup_display()
        self.setup_sdr()
        
        # Audio process
        self.audio_process = None
        
        # Start threads
        self.running = True
        self.display_thread = threading.Thread(target=self.display_loop)
        self.control_thread = threading.Thread(target=self.control_loop)
        
        print("RTL Scanner initialized successfully")
    
    def setup_gpio(self):
        """Initialize GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Encoder pins
        GPIO.setup(ENCODER_CLK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(ENCODER_DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(ENCODER_SW, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Switch pins
        GPIO.setup(SWITCH_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(SWITCH_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(SWITCH_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Add interrupt for encoder
        GPIO.add_event_detect(ENCODER_CLK, GPIO.BOTH, callback=self.encoder_callback)
        GPIO.add_event_detect(ENCODER_SW, GPIO.FALLING, callback=self.encoder_button_callback, bouncetime=200)
        
        print("GPIO initialized")
    
    def setup_display(self):
        """Initialize OLED display"""
        try:
            serial = i2c(port=1, address=0x3C)
            self.display = ssd1306(serial, width=128, height=64)
            self.display.clear()
            print("Display initialized")
        except Exception as e:
            print(f"Display initialization failed: {e}")
            self.display = None
    
    def setup_sdr(self):
        """Initialize RTL-SDR"""
        try:
            self.sdr = RtlSdr()
            self.sdr.sample_rate = 2.048e6  # 2.048 MHz
            self.sdr.center_freq = self.current_freq
            self.sdr.freq_correction = 60   # PPM correction
            self.sdr.gain = 'auto'
            print(f"SDR initialized at {self.current_freq/1e6:.1f} MHz")
        except Exception as e:
            print(f"SDR initialization failed: {e}")
            self.sdr = None
    
    def encoder_callback(self, channel):
        """Handle encoder rotation"""
        clk_state = GPIO.input(ENCODER_CLK)
        dt_state = GPIO.input(ENCODER_DT)
        
        if clk_state != self.last_clk:
            if dt_state != clk_state:
                self.encoder_pos += 1
            else:
                self.encoder_pos -= 1
            
            # Handle encoder actions
            if self.encoder_pressed:
                # Frequency tuning when pressed
                self.tune_frequency(self.encoder_pos)
            else:
                # Volume control
                self.adjust_volume(self.encoder_pos)
            
            self.encoder_pos = 0  # Reset position
        
        self.last_clk = clk_state
    
    def encoder_button_callback(self, channel):
        """Handle encoder button press"""
        self.encoder_pressed = not self.encoder_pressed
        print(f"Encoder mode: {'Frequency' if self.encoder_pressed else 'Volume'}")
    
    def adjust_volume(self, direction):
        """Adjust volume level"""
        if direction > 0:
            self.volume = min(100, self.volume + 5)
        elif direction < 0:
            self.volume = max(0, self.volume - 5)
        
        # Apply volume through ALSA
        try:
            subprocess.run(['amixer', 'set', 'PCM', f'{self.volume}%'], 
                         capture_output=True, check=True)
        except:
            pass
    
    def tune_frequency(self, direction):
        """Tune frequency based on encoder direction"""
        if self.current_band == 'FM':
            step = 0.1e6  # 100kHz steps for FM
        else:
            step = 0.025e6  # 25kHz steps for others
        
        if direction > 0:
            self.current_freq += step
        elif direction < 0:
            self.current_freq -= step
        
        # Constrain to band limits
        if self.current_band == 'FM':
            self.current_freq = max(88e6, min(108e6, self.current_freq))
        
        self.set_frequency(self.current_freq)
    
    def set_frequency(self, freq):
        """Set SDR frequency and restart audio"""
        if self.sdr:
            try:
                self.sdr.center_freq = freq
                self.current_freq = freq
                self.restart_audio()
                print(f"Tuned to {freq/1e6:.1f} MHz")
            except Exception as e:
                print(f"Frequency setting failed: {e}")
    
    def restart_audio(self):
        """Restart audio demodulation"""
        if self.audio_process:
            self.audio_process.terminate()
            self.audio_process = None
        
        # Start rtl_fm for FM demodulation
        if self.current_band == 'FM':
            cmd = [
                'rtl_fm', '-f', str(int(self.current_freq)),
                '-M', 'fm', '-s', '200000', '-r', '48000',
                '-E', 'deemp', '-'
            ]
        else:
            cmd = [
                'rtl_fm', '-f', str(int(self.current_freq)),
                '-M', 'am', '-s', '200000', '-r', '48000', '-'
            ]
        
        try:
            # Pipe to aplay for audio output
            rtl_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            self.audio_process = subprocess.Popen(
                ['aplay', '-r', '48000', '-f', 'S16_LE'],
                stdin=rtl_proc.stdout
            )
        except Exception as e:
            print(f"Audio restart failed: {e}")
    
    def check_switches(self):
        """Check physical switches"""
        if not GPIO.input(SWITCH_1):  # Band selection
            bands = list(PRESETS.keys())
            current_idx = bands.index(self.current_band)
            self.current_band = bands[(current_idx + 1) % len(bands)]
            self.load_preset(0)
            time.sleep(0.3)  # Debounce
        
        if not GPIO.input(SWITCH_2):  # Scanning
            self.scanning = not self.scanning
            print(f"Scanning: {'ON' if self.scanning else 'OFF'}")
            time.sleep(0.3)
        
        if not GPIO.input(SWITCH_3):  # Preset selection
            presets = PRESETS[self.current_band]
            self.preset_index = (self.preset_index + 1) % len(presets)
            self.load_preset(self.preset_index)
            time.sleep(0.3)
    
    def load_preset(self, index):
        """Load preset frequency"""
        presets = PRESETS[self.current_band]
        if 0 <= index < len(presets):
            preset = presets[index]
            self.set_frequency(preset['freq'])
            print(f"Loaded preset: {preset['name']}")
    
    def get_signal_strength(self):
        """Get signal strength (simplified)"""
        if self.sdr:
            try:
                samples = self.sdr.read_samples(1024)
                self.signal_strength = int(np.mean(np.abs(samples)) * 100)
                return min(100, self.signal_strength)
            except:
                return 0
        return 0
    
    def scan_frequencies(self):
        """Simple frequency scanning"""
        if not self.scanning:
            return
        
        presets = PRESETS[self.current_band]
        if presets:
            self.preset_index = (self.preset_index + 1) % len(presets)
            self.load_preset(self.preset_index)
            time.sleep(2)  # Stay on frequency for 2 seconds
    
    def update_display(self):
        """Update OLED display"""
        if not self.display:
            return
        
        try:
            with canvas(self.display) as draw:
                # Frequency display
                freq_str = f"{self.current_freq/1e6:.1f} MHz"
                draw.text((0, 0), freq_str, fill="white")
                
                # Band and preset info
                presets = PRESETS[self.current_band]
                if presets and self.preset_index < len(presets):
                    preset_name = presets[self.preset_index]['name']
                    draw.text((0, 12), f"{self.current_band}: {preset_name}", fill="white")
                
                # Volume
                draw.text((0, 24), f"Vol: {self.volume}%", fill="white")
                
                # Signal strength
                signal = self.get_signal_strength()
                draw.text((0, 36), f"Signal: {signal}%", fill="white")
                
                # Status indicators
                status = []
                if self.scanning:
                    status.append("SCAN")
                if self.encoder_pressed:
                    status.append("FREQ")
                else:
                    status.append("VOL")
                
                draw.text((0, 48), " ".join(status), fill="white")
                
                # Time
                draw.text((0, 56), datetime.now().strftime("%H:%M"), fill="white")
        
        except Exception as e:
            print(f"Display update failed: {e}")
    
    def control_loop(self):
        """Main control loop"""
        while self.running:
            try:
                self.check_switches()
                self.scan_frequencies()
                time.sleep(0.1)
            except Exception as e:
                print(f"Control loop error: {e}")
                time.sleep(1)
    
    def display_loop(self):
        """Display update loop"""
        while self.running:
            try:
                self.update_display()
                time.sleep(0.2)
            except Exception as e:
                print(f"Display loop error: {e}")
                time.sleep(1)
    
    def run(self):
        """Start the scanner"""
        print("Starting RTL Scanner...")
        
        # Load initial preset
        self.load_preset(0)
        
        # Start threads
        self.display_thread.start()
        self.control_thread.start()
        
        try:
            # Main loop
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        if self.audio_process:
            self.audio_process.terminate()
        
        if self.sdr:
            self.sdr.close()
        
        if self.display:
            self.display.clear()
        
        GPIO.cleanup()
        print("Cleanup complete")

def main():
    """Main function"""
    try:
        scanner = RTLScanner()
        scanner.run()
    except Exception as e:
        print(f"Scanner failed: {e}")
        GPIO.cleanup()

if __name__ == "__main__":
    main()