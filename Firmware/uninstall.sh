#!/bin/bash

set -e

echo "Starting uninstallation..."

# Remove Python packages
pip3 uninstall -y \
  pyrtlsdr \
  luma.oled \
  RPi.GPIO \
  pyalsaaudio \
  numpy \
  scipy

# Remove system packages
sudo apt remove --purge -y \
  python3-pip \
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

# Clean up unused dependencies
sudo apt autoremove -y
sudo apt clean

# Disable and remove systemd service
sudo systemctl disable radio-scanner.service || true
sudo systemctl stop radio-scanner.service || true
sudo rm -f /etc/systemd/system/radio-scanner.service
sudo systemctl daemon-reexec
sudo systemctl daemon-reload

# (Optional) Remove project directory
PROJECT_DIR="/home/pi/rtl_sdr_radio_scanner"
if [ -d "$PROJECT_DIR" ]; then
  read -p "Do you want to delete the project directory at $PROJECT_DIR? [y/N]: " confirm
  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    sudo rm -rf "$PROJECT_DIR"
    echo "Deleted $PROJECT_DIR."
  else
    echo "Skipped deleting project directory."
  fi
fi

echo "Uninstallation complete."
