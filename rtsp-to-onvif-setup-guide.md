# RTSP to ONVIF Setup Guide

## Overview
This document summarizes the setup process for adding an RTSP stream to Unifi Protect using the rtsp-to-onvif Docker container. This container creates a virtual ONVIF proxy that allows Unifi Protect to adopt any RTSP stream.

## RTSP Stream Details
We probed the following RTSP stream:
```
rtsp://admin:Nespnp@123@192.168.6.219:554/cam/realmonitor?channel=1&subtype=0
```

### Stream Specifications
- **Video Codec**: HEVC (H.265)
- **Resolution**: 960x1080
- **Frame Rate**: 100 fps
- **Color Format**: yuv420p

### Audio Specifications
- **Audio Codec**: PCM A-law
- **Sample Rate**: 8000 Hz
- **Channels**: Mono
- **Bitrate**: 64 kb/s

## Configuration
We've configured the `config.yaml` file with the following settings:

```yaml
onvif:
  - name: IPCamera                                # Camera name in Unifi Protect
    dev: eth0                                     # Network interface
    target:
      hostname: 192.168.6.219                     # Camera IP address
      ports:
        rtsp: 554                                 # Camera RTSP port
        snapshot: 80                              # Camera HTTP port for snapshots
    highQuality:
      rtsp: /cam/realmonitor?channel=1&subtype=0  # RTSP path
      snapshot: /onvif-http/snapshot              # Snapshot path (may need adjustment)
      width: 960                                  # Video width
      height: 1080                                # Video height
      framerate: 100                              # Video framerate
      bitrate: 2048                               # Estimated bitrate
      quality: 4                                  # Quality setting
    ports:                                        # Virtual server ports
      server: 8081
      rtsp: 8554
      snapshot: 8080
    # mac - automatically added here and IP comes from DHCP
    # uuid - ONVIF ID - automatically added here
```

## Docker Compose Configuration
The `compose.yaml` file is configured as follows:

```yaml
services:
  rtsp-to-onvif:
    image: kulasolutions/rtsp-to-onvif:latest
    hostname: rtsp-to-onvif
    #restart: unless-stopped
    volumes:
      - ./config.yaml:/onvif.yaml
    network_mode: "host"   
    cap_add:
      - NET_ADMIN
    environment: # uncomment this to get more debug info during setup
      DEBUG: 1
```

## Installation Issue
When attempting to run the container on an ARM64 device (Raspberry Pi), we encountered the following error:
```
no matching manifest for linux/arm64/v8 in the manifest list entries
```

This indicates that the Docker image `kulasolutions/rtsp-to-onvif:latest` does not support ARM64 architecture.

## Next Steps for Standard PC Installation

1. **Prepare the Environment**
   - Create a directory for the project: `mkdir rtsp-to-onvif && cd rtsp-to-onvif`
   - Ensure Docker and Docker Compose are installed on your PC

2. **Copy Configuration Files**
   - Copy the `config.yaml` and `compose.yaml` files to your PC
   - Verify the network interface in `config.yaml` matches your PC's interface (use `ip addr` to check)

3. **Run the Container**
   ```bash
   sudo docker compose up
   ```

4. **Verify in Unifi Protect**
   - Check if the camera appears in Unifi Protect
   - During adoption, provide the username and password:
     - Username: admin
     - Password: Nespnp@123

5. **Run in Detached Mode**
   Once everything is working correctly:
   ```bash
   sudo docker compose up -d
   ```

## Important Notes

1. **H.265/HEVC Support**: The camera uses H.265/HEVC codec, which may have varying support in Unifi Protect according to the documentation.

2. **Snapshot Path**: The snapshot path may need adjustment based on your specific camera model.

3. **Network Interface**: Make sure to update the `dev` field in `config.yaml` to match your PC's network interface.

4. **Credentials**: The username and password are not included in the config file but will be needed during adoption in Unifi Protect.

## Troubleshooting

If you encounter issues:

1. Check the Docker logs: `docker logs rtsp-to-onvif`
2. Verify network connectivity between your PC and the camera
3. Ensure the RTSP stream is accessible directly (test with VLC or ffmpeg)
4. Check if your firewall is blocking the required ports