#!/bin/bash
# Real-time Console Demo Monitor

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   🎬 VIDEO STREAMING CONSOLE DEMO MONITOR 🎬           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Starting demo video stream..."
echo ""

# Start the stream
RESPONSE=$(curl -s -X POST 'http://localhost:8000/api/v1/video-stream/' \
  -H 'Content-Type: application/json' \
  -d '{"stream_id":"console_demo","video_url":"sample/sample.mp4","device_id":1,"frame_interval":2}')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Monitor in real-time
echo "📊 Real-time Monitoring (updates every 2 seconds, Ctrl+C to stop):"
echo ""
echo "Time          | Frames | Sent | Failed | Running | Connected"
echo "──────────────┼────────┼──────┼────────┼─────────┼──────────"

COUNTER=0
while true; do
  TIMESTAMP=$(date '+%H:%M:%S')
  
  # Get status
  STATUS=$(curl -s 'http://localhost:8000/api/v1/video-stream/status/')
  
  # Parse JSON
  FRAMES=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'].get('console_demo', {}).get('frames_processed', 0))" 2>/dev/null)
  SENT=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'].get('console_demo', {}).get('frames_sent', 0))" 2>/dev/null)
  FAILED=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'].get('console_demo', {}).get('frames_failed', 0))" 2>/dev/null)
  RUNNING=$(echo "$STATUS" | python3 -c "import sys,json; print('Yes' if json.load(sys.stdin)['data'].get('console_demo', {}).get('is_running') else 'No')" 2>/dev/null)
  CONNECTED=$(echo "$STATUS" | python3 -c "import sys,json; print('Yes' if json.load(sys.stdin)['data'].get('console_demo', {}).get('connection_active') else 'No')" 2>/dev/null)
  
  printf "$TIMESTAMP    | %6s | %4s | %6s | %7s | %s\n" "$FRAMES" "$SENT" "$FAILED" "$RUNNING" "$CONNECTED"
  
  sleep 2
done
