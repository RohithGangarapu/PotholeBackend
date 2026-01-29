#!/bin/bash
# Quick Demo Video Streaming

echo "🎬 Starting Demo Video Stream..."
echo ""

# Start a demo stream with sample video
curl -X POST http://localhost:8000/api/v1/video-stream/ \
  -H "Content-Type: application/json" \
  -d '{
    "stream_id": "demo_video",
    "video_url": "sample/sample.mp4",
    "device_id": 1,
    "frame_interval": 2
  }' 2>/dev/null | python3 -m json.tool

echo ""
echo "✅ Stream started!"
echo ""
echo "📊 Monitoring in real-time (press Ctrl+C to stop):"
echo ""

# Monitor in real-time
while true; do
  curl -s http://localhost:8000/api/v1/video-stream/status/?stream_id=demo_video | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
print(f'  🎥 Processed: {data[\"frames_processed\"]} | ✅ Sent: {data[\"frames_sent\"]} | ❌ Failed: {data[\"frames_failed\"]} | Running: {\"Yes\" if data[\"is_running\"] else \"No\"}', end='\r')
" 2>/dev/null
  sleep 1
done
