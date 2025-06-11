#!/bin/bash

# Upgrade pip (good practice)
python3 -m pip install --upgrade pip

# Install TA-Lib (corrected)
wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.3/ta-lib-0.6.3-src.tar.gz
tar -xzf ta-lib-0.6.3-src.tar.gz
cd ta-lib-0.6.3
./configure --prefix=/usr/local
make
sudo make install
