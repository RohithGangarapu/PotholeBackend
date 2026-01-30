#!/usr/bin/env python3
"""
Demo Video Streaming Script
Automatically starts video streaming with a demo video and monitors progress
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parent

# Demo video sources (local file path or public URLs)
DEMO_VIDEOS = {
    "local_sample": str(PROJECT_ROOT / "sample" / "sample.mp4"),
    "sample_video": "https://commondatastorage.googleapis.com/gtv-videos-library/sample/BigBuckBunny.mp4",
    "test_video": "https://www.w3schools.com/html/mov_bbb.mp4",
    "nature": "https://commondatastorage.googleapis.com/gtv-videos-library/sample/ForBiggerBlazes.mp4",
}

def start_demo_stream(stream_id, video_url, frame_interval=10, device_id=1):
    """Start a demo video stream"""
    print(f"\n{'='*60}")
    print(f"🎬 Starting Demo Video Stream")
    print(f"{'='*60}")
    print(f"Stream ID: {stream_id}")
    print(f"Video URL: {video_url}")
    print(f"Frame Interval: {frame_interval}s")
    
    payload = {
        "stream_id": stream_id,
        "video_url": video_url,
        "frame_interval": frame_interval,
        "device_id": device_id,
    }
    
    try:
        response = requests.post(f"{BASE_URL}/video-stream/", json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success: {result['message']}")
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.json())
            return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def monitor_stream(stream_id, duration=30):
    """Monitor stream progress in real-time"""
    print(f"\n{'='*60}")
    print(f"📊 Monitoring Stream (for {duration} seconds)")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    last_frames_processed = 0
    
    while time.time() - start_time < duration:
        try:
            # Get stream status
            response = requests.get(
                f"{BASE_URL}/video-stream/status/?stream_id={stream_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()['data']
                
                # Get queue stats
                queue_response = requests.get(f"{BASE_URL}/frame-processing/", timeout=5)
                queue_data = queue_response.json()['data']
                
                elapsed = int(time.time() - start_time)
                frames = data['frames_processed']
                frames_delta = frames - last_frames_processed
                
                conn = data.get('connection_active')
                last_error = data.get('last_error')
                
                print(f"\r⏱️  [{elapsed}s]", end="")
                print(f" 🎥 {frames} frames processed", end="")
                print(f" ✅ {data['frames_sent']} sent", end="")
                print(f" ❌ {data['frames_failed']} failed", end="")
                print(f" 🔌 {'OK' if conn else 'DOWN'}", end="")
                print(f" ⚙️  {queue_data['active_workers']} workers", end="")
                print(f" 📦 Q:{queue_data['queue_size']}", end="", flush=True)

                if last_error and not conn:
                    # Print the error on a new line so it doesn't get overwritten by the status line.
                    print(f"\n   ⚠️  last_error: {last_error}")
                
                last_frames_processed = frames
                
            time.sleep(1)
            
        except requests.exceptions.ConnectionError:
            print(f"\n⚠️  Connection error - retrying...", end="", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"\n⚠️  Error: {str(e)}", end="", flush=True)
            time.sleep(2)
    
    print("\n")

def get_results(stream_id):
    """Get detected potholes"""
    print(f"{'='*60}")
    print(f"📋 Detection Results")
    print(f"{'='*60}\n")
    
    try:
        # Get final stats
        response = requests.get(
            f"{BASE_URL}/video-stream/status/?stream_id={stream_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()['data']
            print(f"✅ Streaming Statistics:")
            print(f"   Total Frames Processed: {data['frames_processed']}")
            print(f"   Frames Sent to Detection: {data['frames_sent']}")
            print(f"   Failed Frames: {data['frames_failed']}")
            print(f"   Success Rate: {(data['frames_sent']/max(1,data['frames_processed'])*100):.1f}%")
        
        # Get detected potholes
        print(f"\n🕳️  Detected Potholes:")
        potholes_response = requests.get(f"{BASE_URL}/potholes/", timeout=5)
        
        if potholes_response.status_code == 200:
            potholes = potholes_response.json()['data']
            if potholes:
                print(f"   Found {len(potholes)} pothole(s):\n")
                for pothole in potholes[:5]:  # Show first 5
                    print(f"   • ID: {pothole['id']}")
                    print(f"     Severity: {pothole['severity']}")
                    print(f"     Depth: {pothole['depth']}cm")
                    print(f"     Status: {pothole['status']}\n")
            else:
                print(f"   No potholes detected in this demo")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def stop_stream(stream_id):
    """Stop the demo stream"""
    print(f"{'='*60}")
    print(f"🛑 Stopping Stream")
    print(f"{'='*60}\n")
    
    try:
        response = requests.delete(
            f"{BASE_URL}/video-stream/{stream_id}/",
            timeout=5
        )
        if response.status_code == 200:
            print(f"✅ Stream stopped successfully")
        else:
            print(f"⚠️  Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def main():
    """Run the demo"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "🎬 VIDEO STREAMING DEMO 🎬".center(38) + " "*10 + "║")
    print("╚" + "="*58 + "╝")
    
    # Choose video
    print("\n📹 Available Demo Videos:")
    for i, (name, url) in enumerate(DEMO_VIDEOS.items(), 1):
        print(f"   {i}. {name}")
    
    choice = input(f"\nSelect video (1-{len(DEMO_VIDEOS)}) or paste custom URL [1]: ").strip() or "1"
    
    if choice.isdigit() and 1 <= int(choice) <= len(DEMO_VIDEOS):
        video_name = list(DEMO_VIDEOS.keys())[int(choice) - 1]
        video_url = DEMO_VIDEOS[video_name]
        stream_id = f"demo_{video_name}"
    else:
        video_url = choice
        stream_id = f"demo_{int(time.time())}"
    
    print(f"\n✨ Using: {video_url}\n")
    
    # Start stream
    if not start_demo_stream(stream_id, video_url, frame_interval=10):
        print("❌ Failed to start stream")
        return
    
    # Wait a moment for stream to initialize
    time.sleep(2)
    
    # Monitor for 30 seconds
    monitor_stream(stream_id, duration=30)
    
    # Show results
    get_results(stream_id)
    
    # Stop stream
    stop_stream(stream_id)
    
    print(f"\n{'='*60}")
    print(f"✅ Demo Complete!")
    print(f"{'='*60}")
    print(f"\n📊 View more details at:")
    print(f"   • http://localhost:8000/api/v1/docs/")
    print(f"   • http://localhost:8000/api/v1/potholes/\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
