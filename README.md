# Realsense Example 

This file will save and visualise data from an Intel Realsense camera. Tested with python>=3.7.

## Installation

### Ubuntu (debian)

First install [librealsense](https://github.com/IntelRealSense/librealsense) on your system. 
Instructions below accurate on 1st of April 2021.

```bash
# Install librealsense (up to date instructions here https://github.com/IntelRealSense/librealsense)
sudo apt-key adv --keyserver keys.gnupg.net --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE || sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE

# Ubuntu 16 run this
sudo add-apt-repository "deb http://realsense-hw-public.s3.amazonaws.com/Debian/apt-repo xenial main" -u
# Ubuntu 18 run this
sudo add-apt-repository "deb http://realsense-hw-public.s3.amazonaws.com/Debian/apt-repo bionic main" -u

# Install libraries 
sudo apt update
sudo apt install librealsense2-dkms
sudo apt install librealsense2-utils
```

Then install this repository.

```bash
# Clone the repo
git clone https://github.com/RaymondKirk/realsense_save_example
cd realsense_save_example

# Install > python3.7 (if you don't have it) 
sudo apt install python3.7-*

# Create virtual environment
python3.7 -m venv venv --clear
source venv/bin/activate
pip install --upgrade pip setuptools wheel                                                                                                                                       main!?
pip install -e .

# Run the code
python main.py --visualise
```

## Examples

Capture every frame.

```bash
python main.py --save --interval 0
```

Capture every 5.3 seconds.

```bash
python main.py --save --interval 5.3
```

Show the camera.

```bash
python main.py --visualise
```

Capture when space is pressed (GUI required).

```bash
python main.py --save --visualise
```

Utilise more threads to save to disk faster.

```bash
python main.py --save --interval 0 --threads 8
```

Capture every 5 seconds or when space is pressed, show a GUI and load custom camera config.

```bash
python main.py --save --interval 5 --visualise --config configs/default.yaml
```