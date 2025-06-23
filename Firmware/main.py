#!/usr/bin/env python3

import sys
import os
import time
import threading
import logging
import json
import signal
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import queue

try:
    import numpy as np
    from rtlsdr import RtlSdr
    import RPi.GPIO as GPIO
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    import alsaaudio
    from scipy import signal as scipy_signal
    from scipy.signal import butter, lfilter
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/rtl_scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """Radio service types"""
    FM_RADIO = "FM Radio"
    AVIATION = "Aviation"
    EMERGENCY = "Emergency"
    AMATEUR = "Amateur"
    POLICE = "Police"


class ScanMode(Enum):
    """Scanning modes"""
    MANUAL = "Manual"
    AUTO_SCAN = "Auto Scan"
    PRESET_SCAN = "Preset Scan"


class ModulationType(Enum):
    """Modulation types"""
    FM = "FM"
    AM = "AM"
    NFM = "NFM"  # Narrow FM


@dataclass
class RadioPreset:
    """Radio preset configuration"""
    frequency: float
    name: str
    service_type: ServiceType
    modulation: ModulationType
    step_size: int = 25000  # Hz


@dataclass
class RadioState:
    """Current radio state"""
    frequency: float = 88.0e6
    volume: int = 50
    service_type: ServiceType = ServiceType.FM_RADIO
    scan_mode: ScanMode = ScanMode.MANUAL
    preset_bank: int = 0
    current_preset: int = 0
    signal_strength: float = 0.0
    squelch_level: int = 30
    is_scanning: bool = False
    is_muted: bool = False


class RTLSDRScanner:
    """Main RTL-SDR Scanner class"""

    def __init__(self, config_file: str = '/etc/rtl_scanner/config.json'):
        self.config_file = config_file
        self.state = RadioState()
        self.presets: Dict[int, List[RadioPreset]] = {}
        self.sdr: Optional[RtlSdr] = None
        self.display = None
        self.audio_queue = queue.Queue(maxsize=1024)
        self.running = False

        # GPIO pins
        self.ENCODER_CLK = 22
        self.ENCODER_DT = 27
        self.ENCODER_SW = 17
        self.SWITCH_1 = 23  # Preset bank
        self.SWITCH_2 = 24  # Scan mode
        self.SWITCH_3 = 25  # Service type

        # Audio settings
        self.SAMPLE_RATE = 2048000  # RTL-SDR sample rate
        self.AUDIO_RATE = 48000  # Audio output rate
        self.CHUNK_SIZE = 1024

        self.SERVICE_RANGES = {
            ServiceType.FM_RADIO: (88.0e6, 108.0e6, 100000, ModulationType.FM),
            ServiceType.AVIATION: (118.0e6, 137.0e6, 25000, ModulationType.AM),
            ServiceType.EMERGENCY: (146.0e6, 174.0e6, 12500, ModulationType.NFM),
            ServiceType.AMATEUR: (144.0e6, 148.0e6, 25000, ModulationType.FM),
            ServiceType.POLICE: (400.0e6, 470.0e6, 12500, ModulationType.NFM)
        }

        # Initialize components
        self._setup_gpio()
        self._setup_display()
        self._load_config()
        self._setup_audio()

        self.audio_thread = None
        self.scan_thread = None
        self.display_thread = None

        logger.info("RTL-SDR Scanner initialized successfully")

    def _setup_gpio(self):
        """Initialize GPIO pins"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Rotary encoder
            GPIO.setup(self.ENCODER_CLK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.ENCODER_DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.ENCODER_SW, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Switches
            GPIO.setup(self.SWITCH_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.SWITCH_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.SWITCH_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Add event detection
            GPIO.add_event_detect(self.ENCODER_CLK, GPIO.FALLING,
                                  callback=self._encoder_callback, bouncetime=5)
            GPIO.add_event_detect(self.ENCODER_SW, GPIO.FALLING,
                                  callback=self._encoder_button_callback, bouncetime=200)
            GPIO.add_event_detect(self.SWITCH_1, GPIO.FALLING,
                                  callback=self._switch1_callback, bouncetime=200)
            GPIO.add_event_detect(self.SWITCH_2, GPIO.FALLING,
                                  callback=self._switch2_callback, bouncetime=200)
            GPIO.add_event_detect(self.SWITCH_3, GPIO.FALLING,
                                  callback=self._switch3_callback, bouncetime=200)

            logger.info("GPIO setup completed")

        except Exception as e:
            logger.error(f"GPIO setup failed: {e}")
            raise

    def _setup_display(self):
        """Initialize OLED display"""
        try:
            serial = i2c(port=1, address=0x3c)
            self.display = sh1106(serial, width=128, height=64)
            self.display.clear()

            with canvas(self.display) as draw:
                draw.text((10, 20), "RTL-SDR Scanner", fill="white")
                draw.text((10, 35), "Initializing...", fill="white")

            logger.info("Display setup completed")

        except Exception as e:
            logger.error(f"Display setup failed: {e}")
            raise

    def _setup_audio(self):
        """Initialize audio output"""
        try:
            # Find available audio devices
            devices = alsaaudio.pcms(alsaaudio.PCM_PLAYBACK)
            logger.info(f"Available audio devices: {devices}")

            device = 'default'
            for dev in devices:
                if 'pcm5102' in dev.lower() or 'dac' in dev.lower():
                    device = dev
                    break

            self.audio_device = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, device=device)
            self.audio_device.setchannels(1)
            self.audio_device.setrate(self.AUDIO_RATE)
            self.audio_device.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            self.audio_device.setperiodsize(self.CHUNK_SIZE)

            logger.info(f"Audio setup completed with device: {device}")

        except Exception as e:
            logger.error(f"Audio setup failed: {e}")
            raise

    def _load_config(self):
        """Load configuration and presets"""
        try:

            if not os.path.exists(self.config_file):
                self._create_default_config()

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            # Load presets
            for bank_id, presets_data in config.get('presets', {}).items():
                self.presets[int(bank_id)] = []
                for preset_data in presets_data:
                    preset = RadioPreset(
                        frequency=preset_data['frequency'],
                        name=preset_data['name'],
                        service_type=ServiceType(preset_data['service_type']),
                        modulation=ModulationType(preset_data['modulation']),
                        step_size=preset_data.get('step_size', 25000)
                    )
                    self.presets[int(bank_id)].append(preset)

            # Load last state
            if 'last_state' in config:
                state_data = config['last_state']
                self.state.frequency = state_data.get('frequency', 88.0e6)
                self.state.volume = state_data.get('volume', 50)
                self.state.service_type = ServiceType(state_data.get('service_type', 'FM Radio'))
                self.state.preset_bank = state_data.get('preset_bank', 0)
                self.state.squelch_level = state_data.get('squelch_level', 30)

            logger.info("Configuration loaded successfully")

        except Exception as e:
            logger.error(f"Config loading failed: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration file"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

        default_presets = {
            0: [  # FM Radio Bank
                {'frequency': 93.5e6, 'name': 'FM Rainbow', 'service_type': 'FM Radio', 'modulation': 'FM'},
                {'frequency': 98.3e6, 'name': 'Radio Mirchi', 'service_type': 'FM Radio', 'modulation': 'FM'},
                {'frequency': 104.0e6, 'name': 'Red FM', 'service_type': 'FM Radio', 'modulation': 'FM'},
            ],
            1: [  # Aviation Bank
                {'frequency': 121.5e6, 'name': 'Emergency', 'service_type': 'Aviation', 'modulation': 'AM'},
                {'frequency': 118.1e6, 'name': 'Tower', 'service_type': 'Aviation', 'modulation': 'AM'},
                {'frequency': 119.1e6, 'name': 'Ground', 'service_type': 'Aviation', 'modulation': 'AM'},
            ],
            2: [  # Emergency Bank
                {'frequency': 146.52e6, 'name': 'Repeater', 'service_type': 'Emergency', 'modulation': 'NFM'},
                {'frequency': 156.8e6, 'name': 'Marine VHF', 'service_type': 'Emergency', 'modulation': 'NFM'},
            ]
        }

        config = {
            'presets': default_presets,
            'last_state': {
                'frequency': 88.0e6,
                'volume': 50,
                'service_type': 'FM Radio',
                'preset_bank': 0,
                'squelch_level': 30
            }
        }

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info("Default configuration created")

    def _save_state(self):
        """Save current state to config file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            config['last_state'] = {
                'frequency': self.state.frequency,
                'volume': self.state.volume,
                'service_type': self.state.service_type.value,
                'preset_bank': self.state.preset_bank,
                'squelch_level': self.state.squelch_level
            }

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _setup_sdr(self):
        """Initialize RTL-SDR"""
        try:
            if self.sdr:
                self.sdr.close()

            self.sdr = RtlSdr()
            self.sdr.sample_rate = self.SAMPLE_RATE
            self.sdr.center_freq = self.state.frequency
            self.sdr.gain = 'auto'

            # Set appropriate bandwidth based on service type
            if self.state.service_type == ServiceType.FM_RADIO:
                self.sdr.bandwidth = 200000
            elif self.state.service_type == ServiceType.AVIATION:
                self.sdr.bandwidth = 25000
            else:
                self.sdr.bandwidth = 12500

            logger.info(f"SDR setup completed - Freq: {self.state.frequency / 1e6:.3f} MHz")

        except Exception as e:
            logger.error(f"SDR setup failed: {e}")
            raise

    def _encoder_callback(self, channel):
        """Handle rotary encoder rotation"""
        try:
            clk_state = GPIO.input(self.ENCODER_CLK)
            dt_state = GPIO.input(self.ENCODER_DT)

            if clk_state == 0:
                if dt_state == 1:
                    # Clockwise rotation
                    if GPIO.input(self.ENCODER_SW) == 0:  # Button pressed
                        self._tune_frequency(1)
                    else:
                        self._adjust_volume(1)
                else:
                    # Counter-clockwise rotation
                    if GPIO.input(self.ENCODER_SW) == 0:  # Button pressed
                        self._tune_frequency(-1)
                    else:
                        self._adjust_volume(-1)

        except Exception as e:
            logger.error(f"Encoder callback error: {e}")

    def _encoder_button_callback(self, channel):
        """Handle encoder button press"""
        try:
            # Debounce
            time.sleep(0.01)
            if GPIO.input(self.ENCODER_SW) == 0:
                # Check for long press
                start_time = time.time()
                while GPIO.input(self.ENCODER_SW) == 0:
                    if time.time() - start_time > 1.0:  # Long press
                        self._toggle_mute()
                        return
                    time.sleep(0.01)

                # Short press - toggle scan mode
                self._toggle_scan()

        except Exception as e:
            logger.error(f"Encoder button callback error: {e}")

    def _switch1_callback(self, channel):
        """Handle switch 1 - Preset bank selection"""
        try:
            time.sleep(0.01)  # Debounce
            if GPIO.input(self.SWITCH_1) == 0:
                self.state.preset_bank = (self.state.preset_bank + 1) % len(self.presets)
                self.state.current_preset = 0
                logger.info(f"Switched to preset bank {self.state.preset_bank}")

        except Exception as e:
            logger.error(f"Switch 1 callback error: {e}")

    def _switch2_callback(self, channel):
        """Handle switch 2 - Scan mode toggle"""
        try:
            time.sleep(0.01)  # Debounce
            if GPIO.input(self.SWITCH_2) == 0:
                self._toggle_scan_mode()

        except Exception as e:
            logger.error(f"Switch 2 callback error: {e}")

    def _switch3_callback(self, channel):
        """Handle switch 3 - Service type switching"""
        try:
            time.sleep(0.01)  # Debounce
            if GPIO.input(self.SWITCH_3) == 0:
                self._cycle_service_type()

        except Exception as e:
            logger.error(f"Switch 3 callback error: {e}")

    def _tune_frequency(self, direction: int):
        """Tune frequency up or down"""
        try:
            min_freq, max_freq, step, _ = self.SERVICE_RANGES[self.state.service_type]

            new_freq = self.state.frequency + (direction * step)
            new_freq = max(min_freq, min(max_freq, new_freq))

            if new_freq != self.state.frequency:
                self.state.frequency = new_freq
                if self.sdr:
                    self.sdr.center_freq = self.state.frequency
                logger.info(f"Tuned to {self.state.frequency / 1e6:.3f} MHz")

        except Exception as e:
            logger.error(f"Frequency tuning error: {e}")

    def _adjust_volume(self, direction: int):
        """Adjust volume up or down"""
        try:
            new_volume = self.state.volume + (direction * 5)
            self.state.volume = max(0, min(100, new_volume))
            logger.info(f"Volume: {self.state.volume}%")

        except Exception as e:
            logger.error(f"Volume adjustment error: {e}")

    def _toggle_scan(self):
        """Toggle scanning on/off"""
        try:
            self.state.is_scanning = not self.state.is_scanning
            if self.state.is_scanning:
                self._start_scan()
            else:
                self._stop_scan()

        except Exception as e:
            logger.error(f"Scan toggle error: {e}")

    def _toggle_scan_mode(self):
        """Toggle between scan modes"""
        try:
            modes = list(ScanMode)
            current_index = modes.index(self.state.scan_mode)
            self.state.scan_mode = modes[(current_index + 1) % len(modes)]
            logger.info(f"Scan mode: {self.state.scan_mode.value}")

        except Exception as e:
            logger.error(f"Scan mode toggle error: {e}")

    def _cycle_service_type(self):
        """Cycle through service types"""
        try:
            services = list(ServiceType)
            current_index = services.index(self.state.service_type)
            self.state.service_type = services[(current_index + 1) % len(services)]

            # Update frequency to first in range
            min_freq, _, _, _ = self.SERVICE_RANGES[self.state.service_type]
            self.state.frequency = min_freq

            self._setup_sdr()
            logger.info(f"Service type: {self.state.service_type.value}")

        except Exception as e:
            logger.error(f"Service type cycling error: {e}")

    def _toggle_mute(self):
        """Toggle mute on/off"""
        try:
            self.state.is_muted = not self.state.is_muted
            logger.info(f"Mute: {'ON' if self.state.is_muted else 'OFF'}")

        except Exception as e:
            logger.error(f"Mute toggle error: {e}")

    def _start_scan(self):
        """Start scanning"""
        try:
            if not self.scan_thread or not self.scan_thread.is_alive():
                self.scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
                self.scan_thread.start()
                logger.info("Scanning started")

        except Exception as e:
            logger.error(f"Failed to start scan: {e}")

    def _stop_scan(self):
        """Stop scanning"""
        try:
            self.state.is_scanning = False
            logger.info("Scanning stopped")

        except Exception as e:
            logger.error(f"Failed to stop scan: {e}")

    def _scan_worker(self):
        """Scanning worker thread"""
        try:
            while self.state.is_scanning and self.running:
                if self.state.scan_mode == ScanMode.AUTO_SCAN:
                    self._auto_scan()
                elif self.state.scan_mode == ScanMode.PRESET_SCAN:
                    self._preset_scan()
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Scan worker error: {e}")
            self.state.is_scanning = False

    def _auto_scan(self):
        """Auto scan within current service range"""
        try:
            min_freq, max_freq, step, _ = self.SERVICE_RANGES[self.state.service_type]

            # Check signal strength
            if self._get_signal_strength() > self.state.squelch_level:
                time.sleep(2)  # Pause on active signal
                return

            # Move to next frequency
            new_freq = self.state.frequency + step
            if new_freq > max_freq:
                new_freq = min_freq

            self.state.frequency = new_freq
            if self.sdr:
                self.sdr.center_freq = self.state.frequency

            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Auto scan error: {e}")

    def _preset_scan(self):
        """Scan through presets in current bank"""
        try:
            if self.state.preset_bank not in self.presets:
                return

            presets = self.presets[self.state.preset_bank]
            if not presets:
                return

            # Check signal strength
            if self._get_signal_strength() > self.state.squelch_level:
                time.sleep(2)
                return

            # Move to next preset
            self.state.current_preset = (self.state.current_preset + 1) % len(presets)
            preset = presets[self.state.current_preset]

            self.state.frequency = preset.frequency
            if self.sdr:
                self.sdr.center_freq = self.state.frequency

            time.sleep(0.5)  # Preset scan speed

        except Exception as e:
            logger.error(f"Preset scan error: {e}")

    def _get_signal_strength(self) -> float:
        """Get current signal strength"""
        try:
            if not self.sdr:
                return 0.0

            # Read samples and calculate power
            samples = self.sdr.read_samples(1024)
            power = np.mean(np.abs(samples) ** 2)

            if power > 0:
                signal_strength = 10 * np.log10(power) + 30  # Rough calibration
                self.state.signal_strength = max(0, min(100, signal_strength + 100))
            else:
                self.state.signal_strength = 0.0

            return self.state.signal_strength

        except Exception as e:
            logger.error(f"Signal strength error: {e}")
            return 0.0

    def _audio_worker(self):
        """Audio processing worker thread"""
        try:
            while self.running:
                if not self.sdr or self.state.is_muted:
                    time.sleep(0.01)
                    continue

                # Read IQ samples
                samples = self.sdr.read_samples(self.CHUNK_SIZE * 4)

                audio_data = self._demodulate(samples)

                if audio_data is not None and len(audio_data) > 0:
                    # Apply volume
                    audio_data = audio_data * (self.state.volume / 100.0)

                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    self.audio_device.write(audio_int16.tobytes())

        except Exception as e:
            logger.error(f"Audio worker error: {e}")

    def _demodulate(self, samples: np.ndarray) -> Optional[np.ndarray]:
        """Demodulate IQ samples to audio"""
        try:
            _, _, _, modulation = self.SERVICE_RANGES[self.state.service_type]

            if modulation == ModulationType.FM:
                return self._demodulate_fm(samples)
            elif modulation == ModulationType.AM:
                return self._demodulate_am(samples)
            elif modulation == ModulationType.NFM:
                return self._demodulate_nfm(samples)

            return None

        except Exception as e:
            logger.error(f"Demodulation error: {e}")
            return None

    def _demodulate_fm(self, samples: np.ndarray) -> np.ndarray:
        """FM demodulation"""
        try:

            angle = np.angle(samples)

            # Differentiate to get frequency
            fm_demod = np.diff(np.unwrap(angle))

            decimation = self.SAMPLE_RATE // self.AUDIO_RATE
            audio = scipy_signal.decimate(fm_demod, decimation)

            tau = 75e-6
            alpha = 1 - np.exp(-1 / (self.AUDIO_RATE * tau))
            deemph = lfilter([alpha], [1, alpha - 1], audio)

            return deemph.astype(np.float32)

        except Exception as e:
            logger.error(f"FM demodulation error: {e}")
            return np.array([])

    def _demodulate_am(self, samples: np.ndarray) -> np.ndarray:
        """AM demodulation"""
        try:

            am_demod = np.abs(samples)

            am_demod = am_demod - np.mean(am_demod)

            decimation = self.SAMPLE_RATE // self.AUDIO_RATE
            audio = scipy_signal.decimate(am_demod, decimation)

            return audio.astype(np.float32)

        except Exception as e:
            logger.error(f"AM demodulation error: {e}")
            return np.array([])

    def _demodulate_nfm(self, samples: np.ndarray) -> np.ndarray:
        """Narrow FM demodulation"""
        try:
            # Similar to FM but with less deviation
            angle = np.angle(samples)
            nfm_demod = np.diff(np.unwrap(angle)) * 0.5  # Reduced deviation

            decimation = self.SAMPLE_RATE // self.AUDIO_RATE
            audio = scipy_signal.decimate(nfm_demod, decimation)

            return audio.astype(np.float32)

        except Exception as e:
            logger.error(f"NFM demodulation error: {e}")
            return np.array([])

    def _display_worker(self):
        """Display update worker thread"""
        try:
            while self.running:
                self._update_display()
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Display worker error: {e}")

    def _update_display(self):
        """Update OLED display"""
        try:
            if not self.display:
                return

            with canvas(self.display) as draw:
                # Line 1: Frequency
                freq_str = f"{self.state.frequency / 1e6:.3f} MHz"
                draw.text((0, 0), freq_str, fill="white")

                # Line 2: Service type and scan mode
                service_str = self.state.service_type.value[:8]
                scan_str = "SCAN" if self.state.is_scanning else "MAN"
                draw.text((0, 12), f"{service_str} {scan_str}", fill="white")

                # Line 3: Volume and signal strength
                vol_str = f"Vol:{self.state.volume}%"
                if self.state.is_muted:
                    vol_str = "MUTED"
                sig_str = f"Sig:{int(self.state.signal_strength)}%"
                draw.text((0, 24), f"{vol_str} {sig_str}", fill="white")

                # Line 4: Preset info
                if (self.state.preset_bank in self.presets and
                        self.state.current_preset < len(self.presets[self.state.preset_bank])):
                    preset = self.presets[self.state.preset_bank][self.state.current_preset]
                    preset_str = f"P{self.state.preset_bank}:{self.state.current_preset} {preset.name[:8]}"
                    draw.text((0, 36), preset_str, fill="white")

                # Line 5: Status
                status_str = ""
                if self.state.is_scanning:
                    status_str = f"Scanning {self.state.scan_mode.value}"
                else:
                    status_str = f"Bank {self.state.preset_bank}"
                draw.text((0, 48), status_str, fill="white")

        except Exception as e:
            logger.error(f"Display update error: {e}")

    def start(self):
        """Start the radio scanner"""
        try:
            self.running = True

            # Initialize SDR
            self._setup_sdr()

            self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
            self.display_thread = threading.Thread(target=self._display_worker, daemon=True)

            self.audio_thread.start()
            self.display_thread.start()

            logger.info("RTL-SDR Scanner started successfully")

            # Main loop
            while self.running:
                try:
                    time.sleep(0.1)
                    self._get_signal_strength()  # Update signal strength
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Main loop error: {e}")
                    time.sleep(1)

        except Exception as e:
            logger.error(f"Failed to start scanner: {e}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the radio scanner"""
        try:
            logger.info("Stopping RTL-SDR Scanner...")
            self.running = False

            self.state.is_scanning = False

            self._save_state()

            # Close SDR
            if self.sdr:
                self.sdr.close()
                self.sdr = None

            # Clean up audio
            if hasattr(self, 'audio_device'):
                self.audio_device.close()

            GPIO.cleanup()

            if self.display:
                self.display.clear()

            logger.info("RTL-SDR Scanner stopped")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info(f"Received signal {signum}")
    if 'scanner' in globals():
        scanner.stop()
    sys.exit(0)


def main():
    """Main function"""
    global scanner

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Check if running as root (required for GPIO)
        if os.geteuid() != 0:
            print("This program must be run as root for GPIO access")
            print("Please run: sudo python3 rtl_scanner.py")
            sys.exit(1)

        scanner = RTLSDRScanner()

        # Start scanner
        scanner.start()

    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
