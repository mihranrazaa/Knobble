#!/bin/bash
# RTL-SDR Scanner Installation Script for Raspberry Pi Zero 2W

echo "Installing RTL-SDR Scanner..."

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
echo "Installing system dependencies..."
sudo apt install -y python3-pip python3-dev python3-numpy \
    rtl-sdr rtl-sdr-dev librtlsdr-dev \
    alsa-utils pulseaudio pulseaudio-utils \
    i2c-tools python3-pil python3-pil.imagetk \
    git cmake build-essential

# Enable I2C
echo "Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# Install Python packages
echo "Installing Python packages..."
pip3 install --user RPi.GPIO luma.oled numpy pyrtlsdr

# Create RTL-SDR udev rules
echo "Setting up RTL-SDR permissions..."
sudo tee /etc/udev/rules.d/20-rtlsdr.rules > /dev/null <<EOF
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="adm", MODE="0666", SYMLINK+="rtl_sdr"
EOF

# Add user to audio group
echo "Adding user to audio group..."
sudo usermod -a -G audio $USER

# Create scanner directory
echo "Creating scanner directory..."
mkdir -p ~/rtl_scanner
cd ~/rtl_scanner

# Copy main script (assumes rtl_scanner.py is in current directory)
if [ -f "rtl_scanner.py" ]; then
    echo "RTL Scanner script found"
else
    echo "ERROR: rtl_scanner.py not found!"
    echo "Please copy the main scanner script to rtl_scanner.py"
    exit 1
fi

# Make script executable
chmod +x rtl_scanner.py

# Create systemd service for auto-start
echo "Creating systemd service..."
sudo tee /etc/systemd/system/rtl-scanner.service > /dev/null <<EOF
[Unit]
Description=RTL-SDR Scanner
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/rtl_scanner
ExecStart=/usr/bin/python3 /home/$USER/rtl_scanner/rtl_scanner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable auto-start service
echo "Enabling auto-start service..."
sudo systemctl daemon-reload
sudo systemctl enable rtl-scanner.service

# Configure audio for headphones
echo "Configuring audio..."
sudo tee -a /boot/config.txt > /dev/null <<EOF

# RTL Scanner Audio Configuration
dtparam=audio=on
audio_pwm_mode=2
dtoverlay=hifiberry-dac
EOF

# Create test script
echo "Creating test script..."
tee ~/rtl_scanner/test_hardware.py > /dev/null <<EOF
#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas

# Test GPIO
print("Testing GPIO...")
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)
print(f"Encoder button state: {GPIO.input(17)}")

# Test display
print("Testing display...")
try:
    serial = i2c(port=1, address=0x3C)
    display = ssd1306(serial, width=128, height=64)
    with canvas(display) as draw:
        draw.text((0, 0), "RTL Scanner", fill="white")
        draw.text((0, 16), "Hardware Test", fill="white")
        draw.text((0, 32), "Display OK", fill="white")
    print("Display test successful")
except Exception as e:
    print(f"Display test failed: {e}")

# Test RTL-SDR
print("Testing RTL-SDR...")
try:
    from rtlsdr import RtlSdr
    sdr = RtlSdr()
    print(f"SDR found: {sdr}")
    sdr.close()
    print("RTL-SDR test successful")
except Exception as e:
    print(f"RTL-SDR test failed: {e}")

GPIO.cleanup()
print("Hardware test complete")
EOF

chmod +x ~/rtl_scanner/test_hardware.py

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Reboot the Pi: sudo reboot"
echo "2. Test hardware: cd ~/rtl_scanner && python3 test_hardware.py"
echo "3. Run scanner: cd ~/rtl_scanner && python3 rtl_scanner.py"
echo "4. Check service: sudo systemctl status rtl-scanner"
echo ""
echo "Hardware connections:"
echo "- Encoder: CLK=22, DT=27, SW=17"
echo "- Switches: SW1=23, SW2=24, SW3=25"
echo "- Display: SDA=2, SCL=3"
echo "- All devices need 3.3V and GND connections"
echo ""
echo "Controls:"
echo "- Encoder: Volume control (normal), Frequency tuning (when pressed)"
echo "- Switch 1: Band selection (FM/Aviation/Emergency)"
echo "- Switch 2: Scanning on/off"
echo "- Switch 3: Preset selection"