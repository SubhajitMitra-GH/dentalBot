#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "Installing download tools..."
# Install curl and tar/xz utils, which are needed to download and extract
yum install -y curl tar xz-utils

echo "Downloading static ffmpeg build..."
# Download a known-good static build of ffmpeg from a trusted source
curl -L -o ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

echo "Extracting ffmpeg..."
# Extract the tarball
tar -xf ffmpeg.tar.xz

# The tarball extracts to a folder like 'ffmpeg-6.0-amd64-static'
# We use a wildcard * to find the ffmpeg binary inside that folder
echo "Moving ffmpeg to /usr/local/bin..."
mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg

# Also move ffprobe, which whisper sometimes uses
mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe

echo "Cleaning up..."
# Clean up the downloaded file and extracted folder
rm -f ffmpeg.tar.xz
rm -rf ffmpeg-*-amd64-static

echo "ffmpeg and ffprobe successfully installed."
