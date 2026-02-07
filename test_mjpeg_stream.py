#!/usr/bin/env python3
"""
Test MJPEG Stream Capture Script
Verifies that the backend can correctly capture frames from an MJPEG stream.
"""

import requests
import time
import argparse
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

def start_stream(stream_id, video_url, frame_interval=5, device_id=1, user_id=1):
    print(f"\n🚀 Starting MJPEG Stream: {stream_id}")
    print(f"🔗 URL: {video_url}")
    
    payload = {
        "stream_id": stream_id,
        "video_url": video_url,
        "frame_interval": frame_interval,
        "device_id": device_id,
        "user_id": user_id
    }
    
    try:
        response = requests.post(f"{BASE_URL}/video-stream/", json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Success: {response.json()['message']}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Connection Error: {str(e)}")
        return False

def monitor_status(stream_id, duration=20):
    print(f"\n📊 Monitoring status for {duration} seconds...")
    start_time = time.time()
    
    while time.time() - start_time < duration:
        try:
            resp = requests.get(f"{BASE_URL}/video-stream/status/?stream_id={stream_id}")
            if resp.status_code == 200:
                data = resp.json()['data']
                print(f"\r⏱️  {int(time.time() - start_time)}s | 🎥 Frames: {data['frames_processed']} | ✅ Sent: {data['frames_sent']} | ❌ Fail: {data['frames_failed']} | 🔗 Active: {data['connection_active']}", end="", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"\n⚠️  Error: {str(e)}")
            break
    print("\n\n✅ Monitoring complete.")

def stop_stream(stream_id):
    print(f"\n🛑 Stopping Stream: {stream_id}")
    try:
        resp = requests.delete(f"{BASE_URL}/video-stream/{stream_id}/")
        if resp.status_code == 200:
            print("✅ Stream stopped.")
        else:
            print(f"⚠️  Status: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_telemetry(device_id):
    print(f"\n📡 Testing Telemetry (GPS Update) for Device {device_id}...")
    payload = {
        "lat": 17.3850,
        "lng": 78.4867,
        "ip": "10.64.6.250"
    }
    try:
        resp = requests.post(f"{BASE_URL}/devices/{device_id}/gps/", json=payload, timeout=5)
        if resp.status_code == 200:
            print(f"✅ GPS Updated: {resp.json().get('message')}")
        else:
            print(f"❌ GPS Error {resp.status_code}: {resp.json()}")
    except Exception as e:
        print(f"❌ GPS Connection Error: {str(e)}")

def test_controls(device_id):
    print(f"\n🎮 Testing Commands for Device {device_id}...")
    commands = ["forward", "stop"]
    for cmd in commands:
        try:
            print(f"   Sending '{cmd}'...", end="", flush=True)
            # Note: This will likely fail in test if the actual ESP is not reachable
            resp = requests.post(f"{BASE_URL}/devices/{device_id}/control/{cmd}/", timeout=5)
            if resp.status_code in [200, 502]: 
                status_icon = "✅" if resp.status_code == 200 else "⚠️ (Proxy OK, Device Offline)"
                print(f" {status_icon}")
            else:
                print(f" ❌ Error {resp.status_code}")
        except Exception as e:
            print(f" ❌ Error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Test MJPEG Stream Capture")
    parser.add_argument("--url", default="http://10.64.6.250/stream", help="Stream URL")
    parser.add_argument("--id", default="test_esp32_cam", help="Stream ID")
    parser.add_argument("--interval", type=int, default=5, help="Frame interval in seconds")
    parser.add_argument("--device", type=int, default=1, help="Device ID")
    parser.add_argument("--user", type=int, default=1, help="User ID")
    
    args = parser.parse_args()
    
    if start_stream(args.id, args.url, args.interval, args.device, args.user):
        time.sleep(2)
        monitor_status(args.id)
        stop_stream(args.id)
        
        # Test the new integration endpoints
        test_telemetry(args.device)
        test_controls(args.device)

if __name__ == "__main__":
    main()
