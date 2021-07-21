#!/usr/bin/env bash
# Go to project root
cd "$(cd -P -- "$(dirname -- "$0")" && pwd -P)" || exit
cd ..

# Install realsense
function install_package() { # usage: install_package package_name
    if ! dpkg-query -W -f='${Status}' $1  | grep "ok installed"; then
      echo -e "Could not find '$1' on your system."
        sudo apt update
        sudo apt install $1 && return 0
        echo -e "Could not install '$1'"
        return 1
    fi
    return 0
}

install_package "librealsense2-dkms" > /dev/null
if [ $? -ne 0 ]; then
  echo "Error installing packages please follow instructions on https://github.com/IntelRealSense/librealsense"
  exit
fi

install_package "librealsense2-utils" > /dev/null
if [ $? -ne 0 ]; then
  echo "Error installing packages please follow instructions on https://github.com/IntelRealSense/librealsense"
  exit
fi

# Install > python3.7 (if you don't have it)
install_package python3.7 > /dev/null
install_package python3.7-dev > /dev/null
install_package python3.7-venv > /dev/null

# Create virtual environment
rm -rf venv || true
python3.7 -m venv venv --clear
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
