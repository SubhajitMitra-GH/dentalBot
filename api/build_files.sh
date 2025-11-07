#!/bin/bash
set -e # Exit immediately if a command fails

echo "Installing xz (for extracting .tar.xz)..."
# 'xz-utils' wasn't found, try the more common package name 'xz'
yum install -y xz

echo "Downloading static ffmpeg build..."
curl -L -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

echo "Extracting ffmpeg..."
# Now that 'xz' is installed, tar's 'x' flag should work
tar -xf ffmpeg.tar.xz

echo "Moving ffmpeg to /usr/local/bin..."
# Use wildcard to find the folder
mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg
mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe

echo "Cleaning up..."
rm -f ffmpeg.tar.xz
rm -rf ffmpeg-*-amd64-static

echo "ffmpeg and ffprobe successfully installed."
