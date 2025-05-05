import cv2
import time
import numpy as np
import HandTrackingModule as htm
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

###############################
wCam, hCam = 640, 480
stable_tolerance = 3         # Allowed % fluctuation to count as stable
lock_time_required = 3       # Seconds to hold the same volume
###############################

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0

# Initialize hand detector
detector = htm.handDetector(detectionCon=0.7)

# Initialize audio controller
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
)
volume = interface.QueryInterface(IAudioEndpointVolume)
volRange = volume.GetVolumeRange()

# Variables for volume bar and percentage
volBar = 400
volPer = 0

# Auto-lock detection
lockStartTime = None
lastStableVol = None

while True:
    success, img = cap.read()
    img = detector.findHands(img)
    lmList = detector.findPosition(img, draw=False)

    if len(lmList) != 0:
        # Thumb tip = id 4, Index finger tip = id 8
        x1, y1 = lmList[4][1], lmList[4][2]
        x2, y2 = lmList[8][1], lmList[8][2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        # Draw finger circles and line
        # In OpenCV, colors are BGR, and not RGB
        cv2.circle(img, (x1, y1), 8, (255, 0, 255), cv2.FILLED)
        cv2.circle(img, (x2, y2), 8, (255, 0, 255), cv2.FILLED)
        cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 2)
        cv2.circle(img, (cx, cy), 8, (255, 0, 255), cv2.FILLED)

        # Calculate distance between fingers
        length = math.hypot(x2 - x1, y2 - y1)

        # Convert length to volume percentage
        volPer = np.interp(length, [17, 150], [0, 100])
        volBar = np.interp(length, [17, 150], [400, 150])

        # Set system volume (linear scale: 0.0 to 1.0)
        volume.SetMasterVolumeLevelScalar(volPer / 100.0, None)

        # Visual feedback when fingers are very close
        if length < 17:
            cv2.circle(img, (cx, cy), 8, (0, 255, 0), cv2.FILLED)

        # =====================
        # Auto-lock Logic
        # =====================
        if lastStableVol is None or abs(volPer - lastStableVol) > stable_tolerance:
            lastStableVol = volPer
            lockStartTime = time.time()
        else:
            elapsed = time.time() - lockStartTime
            remaining = lock_time_required - elapsed
            if remaining > 0:
                cv2.putText(img, f'Locking in: {int(remaining)}s',
                            (300, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                print(f"✅ Volume locked at {int(volPer)}%. Exiting...")
                break

    # Draw volume bar
    cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 3)
    cv2.rectangle(img, (50, int(volBar)), (85, 400), (0, 255, 0), cv2.FILLED)

    # Draw volume percentage text
    cv2.putText(img, f'Volume: {int(volPer)} %', (40, 450),
                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 2)

    # Show FPS
    cTime = time.time()
    fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
    pTime = cTime
    cv2.putText(img, f'FPS: {int(fps)}', (40, 50),
                cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 2)

    cv2.imshow("Img", img)

    # ESC to exit manually
    if cv2.waitKey(1) & 0xFF == 27:
        print("⛔ Exited manually.")
        break

cap.release()
cv2.destroyAllWindows()
