from django.shortcuts import render
import numpy as np
from django.http import StreamingHttpResponse
import cv2

# Create your views here.

from django.shortcuts import render

def index(request):
    return render(request, 'index.html')


from django.http import JsonResponse


# Store last detected status
last_status = {"message": "Checking roti shape...", "alert": False}

def roti_status(request):
    """
    Send live roti shape status to frontend.
    """
    return JsonResponse(last_status)



import cv2
import numpy as np

# Store last detected status
last_status = {"message": "Checking roti shape...", "alert": False}

def detect_roti(frame):
    """
    Detect if the roti is circular and highlight incorrect areas.
    Uses contours to identify deviations from a perfect circle.
    """
    global last_status
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # Edge detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest_contour = max(contours, key=cv2.contourArea)  # Find the largest contour
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)  # Get the minimum enclosing circle
        center = (int(x), int(y))
        radius = int(radius)
        
        # Compute aspect ratio and circularity to check if it's a perfect circle
        area = cv2.contourArea(largest_contour)
        perimeter = cv2.arcLength(largest_contour, True)
        circularity = (4 * np.pi * area) / (perimeter ** 2) if perimeter > 0 else 0

        # Define a threshold for a perfect circle (higher circularity is better)
        if 0.8 <= circularity <= 1.2:
            cv2.circle(frame, center, radius, (0, 255, 0), 2)  # Draw green circle
            cv2.putText(frame, "Perfect Circle!", (center[0] - 50, center[1] - 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            last_status = {"message": "Perfect Circle!", "alert": False}
        else:
            cv2.drawContours(frame, [largest_contour], -1, (0, 0, 255), 2)  # Draw red contour
            cv2.putText(frame, "Adjust Shape!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            last_status = {"message": "Adjust Shape!", "alert": True}
            
            # Detect incorrect areas by comparing the contour to the enclosing circle
            for point in largest_contour:
                px, py = point[0]
                distance = np.sqrt((px - center[0]) ** 2 + (py - center[1]) ** 2)
                if abs(distance - radius) > 10:  # Threshold for deviation
                    cv2.circle(frame, (px, py), 5, (255, 0, 0), -1)  # Mark incorrect points

    else:
        cv2.putText(frame, "No Shape Detected!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        last_status = {"message": "No Roti Detected!", "alert": True}

    return frame


def video_stream():
    """
    Capture live video from webcam, process it, and send back to frontend.
    """
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = detect_roti(frame)

        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()

def video_feed(request):
    """
    Return a real-time video response to the frontend.
    """
    return StreamingHttpResponse(video_stream(), content_type='multipart/x-mixed-replace; boundary=frame')

