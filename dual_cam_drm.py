#!/usr/bin/python3

# For use from the login console, when not running X Windows.

import time

from picamera2 import Picamera2, Preview, MappedArray
from libcamera import controls
import cv2
import drm_preview

class frame_rate:
    frame_count = 0
    start = time.time()

drm = drm_preview.DrmPreview()

picam2a = Picamera2(0)
picam2b = Picamera2(1)
#picam2a.start_preview(Preview.DRM, x=0, y=0, width=960, height=1080)
#picam2b.start_preview(Preview.DRM, x=960, y=0, width=960, height=1080)

picam2a.preview_configuration.main.size=(1920,1080)
picam2a.preview_configuration.controls.FrameRate = 60.0
picam2a.configure('preview')

picam2a.set_controls({'AfMode': controls.AfModeEnum.Continuous})

picam2b.preview_configuration.main.size=(1920,1080)
picam2b.preview_configuration.controls.FrameRate = 60.0
picam2b.configure('preview')

picam2a.start()
picam2b.start()

# colour = (0, 255, 0)
# origin = (0, 30)
# font = cv2.FONT_HERSHEY_SIMPLEX
# scale = 1
# thickness = 2

# #frame_count = 0
# fr = frame_rate()

# def apply_timestamp(request):
#   with MappedArray(request, "main") as m:
#     cv2.putText(m.array, str(fr.frame_count), origin, font, scale, colour, thickness)

#   fr.frame_count += 1

# picam2a.pre_callback = apply_timestamp

# #picam2b.start()
# time.sleep(10)
# end_time = time.time()
# elapsed_time = end_time - fr.start

# print(fr.frame_count / elapsed_time)
frame_count = 0
lastFrames = 0

start_time = time.time()
last_timestamp = 0

while True:
    if len(picam2a.completed_requests) > 0 and len(picam2b.completed_requests) > 0:
        req = picam2a.completed_requests.pop(0)
        req2 = picam2b.completed_requests.pop(0)
        drm.render_drm(picam2a, picam2b, req, req2)
        req.release()
        req2.release()

        frame_count += 1

        if frame_count % 120 == 0:
            current_time = time.time()
            elapsed_time = current_time - start_time
            frames = frame_count -lastFrames
            lastFrames = frame_count
            print(frames / elapsed_time)
            start_time = current_time

