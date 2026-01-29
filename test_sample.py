import requests
import json
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
DETECTION_API_URL = "http://localhost:5000/api/detect"  # Your detection API endpoint
SAMPLE_VIDEO = Path("sample/sample.mp4")

def test_video_streaming():
    """Test video streaming with sample.mp4"""
    
    if not SAMPLE_VIDEO.exists():
        print(f"❌ Error: {SAMPLE_VIDEO} not found!")
        print(f"   Current working directory: {Path.cwd()}")
        print(f"   Available files: {list(Path('.')).glob('*')}")
        return
    
    print(f"✓ Found sample video: {SAMPLE_VIDEO}")
    print(f"  File size: {SAMPLE_VIDEO.stat().st_size / (1024*1024):.2f} MB")
    
    # Test 1: Start video stream without user_id and device_id (both null)
    print("\n" + "="*60)
    print("TEST 1: Starting video stream (user_id=null, device_id=null)...")
    print("="*60)
    
    stream_data = {
        "stream_id": "test_stream_1",
        "video_url": str(SAMPLE_VIDEO.resolve()),
        "detection_api_url": DETECTION_API_URL,
        "frame_interval": 5,  # Send frame every 5 seconds for testing
        "user_id": None,
        "device_id": None
    }
    
    response = requests.post(
        f"{BASE_URL}/video-stream/",
        json=stream_data,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code != 200:
        print("❌ Failed to start stream!")
        return
    
    print("✓ Stream started successfully")
    stream_id = stream_data["stream_id"]
    
    # Test 2: Check stream status multiple times
    print("\n" + "="*60)
    print("TEST 2: Monitoring stream status...")
    print("="*60)
    
    for i in range(6):
        time.sleep(2)  # Wait 2 seconds between checks
        
        response = requests.get(
            f"{BASE_URL}/video-stream/status/",
            params={"stream_id": stream_id},
            timeout=10
        )
        
        if response.status_code == 200:
            status = response.json().get('data', {})
            print(f"[{i+1}] Frames processed: {status.get('frame_count', 'N/A')}, "
                  f"Running: {status.get('is_running', 'N/A')}, "
                  f"User ID: {status.get('user_id', 'null')}, "
                  f"Device ID: {status.get('device_id', 'null')}")
        else:
            print(f"[{i+1}] Status check failed: {response.status_code}")
    
    # Test 3: Stop the stream
    print("\n" + "="*60)
    print("TEST 3: Stopping video stream...")
    print("="*60)
    
    response = requests.delete(
        f"{BASE_URL}/video-stream/{stream_id}/",
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("✓ Stream stopped successfully")
    else:
        print("❌ Failed to stop stream!")
    
    # Test 4: Start stream WITH user_id and device_id
    print("\n" + "="*60)
    print("TEST 4: Starting stream with user_id=1, device_id=42...")
    print("="*60)
    
    stream_data_with_ids = {
        "stream_id": "test_stream_2",
        "video_url": str(SAMPLE_VIDEO.resolve()),
        "detection_api_url": DETECTION_API_URL,
        "frame_interval": 5,
        "user_id": 1,
        "device_id": 42
    }
    
    response = requests.post(
        f"{BASE_URL}/video-stream/",
        json=stream_data_with_ids,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Stream with IDs started successfully")
        print(json.dumps(response.json(), indent=2))
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    print("Pothole Detection - Video Stream Test")
    print("Testing with sample.mp4...\n")
    
    try:
        test_video_streaming()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to backend server")
        print("   Make sure Django server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")