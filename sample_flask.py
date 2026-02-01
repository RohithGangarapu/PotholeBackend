from flask import Flask, Response, render_template_string
import cv2
import time

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MJPEG Test Stream</title>
</head>
<body>
    <h2>MJPEG Test Camera</h2>
    <img src="/stream" width="640">
</body>
</html>
"""

camera = cv2.VideoCapture(0)  # use webcam

def generate():
    while True:
        success, frame = camera.read()
        if not success:
            break

        _, jpeg = cv2.imencode('.jpg', frame)

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               jpeg.tobytes() + b'\r\n')

        time.sleep(0.05)  # ~20 FPS

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/stream')
def stream():
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, threaded=True)
