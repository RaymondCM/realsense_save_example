# Realsense Example 

This file will save and visualise data from an Intel Realsense camera. Tested with python>=3.7.

```bash
# Install librealsense
sudo apt-key adv --keyserver keys.gnupg.net --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE || sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE

# Ubuntu 16 run this
sudo add-apt-repository "deb http://realsense-hw-public.s3.amazonaws.com/Debian/apt-repo xenial main" -u
# Ubuntu 18 run this
sudo add-apt-repository "deb http://realsense-hw-public.s3.amazonaws.com/Debian/apt-repo bionic main" -u

# Install libraries 
sudo apt-get install librealsense2-dkms
sudo apt-get install librealsense2-utils

# Clone the repo
git clone https://github.com/RaymondKirk/realsense_save_example
cd realsense_save_example

# Install python wrapper
pip install pyrealsense2 opencv-python numpy

# Run the code
python main.py --visualise
```