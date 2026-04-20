# pibooth-share

Plugin for [pibooth](https://github.com/pibooth/pibooth) to share photos via a local web server with QR code.

## Features

- Local web server serving a mobile-friendly photo gallery
- QR code displayed on screen after each capture for direct photo download
- Automatic thumbnail generation for fast gallery loading
- No internet required - works via WiFi hotspot

## Install

```bash
pip install pibooth-share
```

## Configuration

```ini
[SHARE]
# Enable photo sharing via web server
share_enabled = True

# Web server port
share_port = 8080

# Gallery page title
share_title = Photobooth

# QR code size on screen (pixels)
share_qrcode_size = 150

# Show QR code of last photo on screen
share_show_qrcode = True
```

## Usage

1. Print a QR code pointing to `http://<pi-ip>:8080/` and stick it on your photobooth
2. Guests scan the QR code to access the gallery on their phone
3. After each capture, a QR code for that specific photo appears on screen
