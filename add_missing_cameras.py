#!/usr/bin/env python3
"""
Add Missing Cameras Script

This script reads a CSV file created by nvr-scanner.py, compares it with the existing
config.yaml file, and adds any missing cameras to the configuration.

Usage:
    python3 add_missing_cameras.py --csv <csv_file> --config <config_file> [--network-interface <interface>]

Example:
    python3 add_missing_cameras.py --csv tools/nvr_192.168.6.219/192.168.6.219.csv --config config.yaml --network-interface enp6s0
"""

import argparse
import csv
import os
import re
import sys
import yaml


def parse_csv_file(csv_file):
    """Parse the CSV file created by nvr-scanner.py and extract camera information."""
    cameras = []
    
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip cameras that are not working
                if row['Status'] != "✅ Working":
                    continue
                
                # Extract camera information
                channel = row['Channel']
                rtsp_url = row['RTSP URL']
                overlay_text = row['Overlay Text']
                resolution = row['Resolution']
                codec = row['Codec']
                fps = row['FPS']
                
                # Parse resolution
                width, height = resolution.split('x')
                
                # Create camera name by replacing spaces with hyphens
                camera_name = overlay_text.strip().replace(' ', '-')
                
                # Parse RTSP URL more robustly
                # Format: rtsp://[username:password@]hostname:port/path
                
                # First, find the last @ symbol (in case password contains @)
                parts = rtsp_url.split('://', 1)[1]
                last_at_index = parts.rfind('@')
                
                if last_at_index != -1:
                    # URL has credentials
                    host_port_path = parts[last_at_index + 1:]
                else:
                    # URL has no credentials
                    host_port_path = parts
                
                # Now extract hostname and path
                host_port, path = host_port_path.split('/', 1)
                hostname, port = host_port.split(':')
                rtsp_path = '/' + path
                
                # Validate the extracted hostname and path
                if not hostname or not rtsp_path:
                    print(f"Warning: Could not extract hostname or path from URL: {rtsp_url}")
                    print(f"Extracted hostname: {hostname}, path: {rtsp_path}")
                    continue
                
                # Create camera configuration
                camera = {
                    'name': camera_name,
                    'channel': channel,
                    'hostname': hostname,
                    'rtsp_path': rtsp_path,
                    'width': int(width),
                    'height': int(height),
                    'framerate': float(fps) if fps != "N/A" else 30,
                    'codec': codec if codec != "N/A" else "h264"
                }
                
                cameras.append(camera)
        
        return cameras
    
    except Exception as e:
        print(f"Error parsing CSV file: {e}")
        sys.exit(1)


def parse_config_file(config_file):
    """Parse the existing config.yaml file."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)


def find_missing_cameras(csv_cameras, config):
    """Find cameras that are in the CSV file but not in the config file."""
    missing_cameras = []
    
    # Get existing camera names from config
    existing_camera_names = []
    existing_camera_channels = []
    
    if 'onvif' in config and isinstance(config['onvif'], list):
        for camera in config['onvif']:
            if 'name' in camera:
                existing_camera_names.append(camera['name'])
            
            # Extract channel number from RTSP path
            if 'highQuality' in camera and 'rtsp' in camera['highQuality']:
                rtsp_path = camera['highQuality']['rtsp']
                channel_match = re.search(r'channel=(\d+)', rtsp_path)
                if channel_match:
                    existing_camera_channels.append(channel_match.group(1))
    
    # Find missing cameras
    for camera in csv_cameras:
        if camera['name'] not in existing_camera_names and camera['channel'] not in existing_camera_channels:
            missing_cameras.append(camera)
    
    return missing_cameras


def add_cameras_to_config(missing_cameras, config, network_interface):
    """Add missing cameras to the config file."""
    if 'onvif' not in config:
        config['onvif'] = []
    
    # Find the highest port numbers currently in use
    highest_server_port = 8081
    highest_rtsp_port = 8554
    highest_snapshot_port = 8080
    
    for camera in config['onvif']:
        if 'ports' in camera:
            if 'server' in camera['ports'] and camera['ports']['server'] > highest_server_port:
                highest_server_port = camera['ports']['server']
            if 'rtsp' in camera['ports'] and camera['ports']['rtsp'] > highest_rtsp_port:
                highest_rtsp_port = camera['ports']['rtsp']
            if 'snapshot' in camera['ports'] and camera['ports']['snapshot'] > highest_snapshot_port:
                highest_snapshot_port = camera['ports']['snapshot']
    
    # Add missing cameras
    for camera in missing_cameras:
        # Increment port numbers for each new camera
        highest_server_port += 1000
        highest_rtsp_port += 1000
        highest_snapshot_port += 1000
        
        # Create camera configuration
        camera_config = {
            'name': camera['name'],
            'dev': network_interface,
            'target': {
                'hostname': camera['hostname'],
                'ports': {
                    'rtsp': 554,
                    'snapshot': 80
                }
            },
            'highQuality': {
                'rtsp': camera['rtsp_path'],
                'snapshot': '/onvif-http/snapshot',
                'width': camera['width'],
                'height': camera['height'],
                'framerate': camera['framerate'],
                'bitrate': 2048,
                'quality': 4
            },
            'ports': {
                'server': highest_server_port,
                'rtsp': highest_rtsp_port,
                'snapshot': highest_snapshot_port
            }
        }
        
        config['onvif'].append(camera_config)
    
    return config


def save_config_file(config, config_file):
    """Save the updated config to the config file."""
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"Updated config file saved to {config_file}")
    except Exception as e:
        print(f"Error saving config file: {e}")
        sys.exit(1)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Add missing cameras to config.yaml')
    parser.add_argument('--csv', required=True, help='Path to the CSV file created by nvr-scanner.py')
    parser.add_argument('--config', required=True, help='Path to the config.yaml file')
    parser.add_argument('--network-interface', default='enp6s0', help='Network interface to use (default: enp6s0)')
    args = parser.parse_args()
    
    # Check if files exist
    if not os.path.exists(args.csv):
        print(f"Error: CSV file {args.csv} does not exist")
        sys.exit(1)
    
    if not os.path.exists(args.config):
        print(f"Error: Config file {args.config} does not exist")
        sys.exit(1)
    
    # Parse CSV file
    print(f"Parsing CSV file: {args.csv}")
    csv_cameras = parse_csv_file(args.csv)
    print(f"Found {len(csv_cameras)} working cameras in CSV file")
    
    # Parse config file
    print(f"Parsing config file: {args.config}")
    config = parse_config_file(args.config)
    
    # Find missing cameras
    print("Finding missing cameras...")
    missing_cameras = find_missing_cameras(csv_cameras, config)
    print(f"Found {len(missing_cameras)} missing cameras")
    
    if not missing_cameras:
        print("No missing cameras found. Config file is up to date.")
        return
    
    # Print missing cameras
    print("\nMissing cameras:")
    for camera in missing_cameras:
        print(f"  - Channel {camera['channel']}: {camera['name']} ({camera['width']}x{camera['height']})")
    
    # Add missing cameras to config
    print("\nAdding missing cameras to config...")
    updated_config = add_cameras_to_config(missing_cameras, config, args.network_interface)
    
    # Save updated config
    print("\nSaving updated config...")
    save_config_file(updated_config, args.config)
    
    print("\nDone! Please restart the Docker container to apply the changes:")
    print("  sudo docker compose down && sudo docker compose up -d")


if __name__ == "__main__":
    main()