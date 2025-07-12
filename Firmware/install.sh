#!/bin/bash

set -e

# System dependencies
sudo apt update && sudo apt install -y \
  python3 python3-pip \
  python3-numpy \
  python3-scipy \
  python3-pil \
  libatlas-base-dev \
  rtl-sdr \
  i2c-tools \
  libjpeg-dev zlib1g-dev \
  python3-setuptools \
  python3-dev \
  build-essential \
  libasound2-dev \
  fonts-dejavu-core

# Python packages
pip3 install --upgrade pip
pip3 install \
  pyrtlsdr \
  luma.oled \
  RPi.GPIO \
  pyalsaaudio \
  numpy \
  scipy

# Enable I2C
sudo raspi-config nonint do_i2c 0

# Create systemd service
SERVICE_FILE="/etc/systemd/system/radio-scanner.service"
echo "[Unit]
Description=RTL-SDR Radio Scanner
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/rtl_sdr_radio_scanner/main.py
WorkingDirectory=/home/pi/rtl_sdr_radio_scanner
Restart=on-failure

[Install]
WantedBy=multi-user.target" | sudo tee $SERVICE_FILE

# Enable service
sudo systemctl daemon-reexec
sudo systemctl enable radio-scanner.service

echo "Installation complete. Reboot to start the scanner automatically."

