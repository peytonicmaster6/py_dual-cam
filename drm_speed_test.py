#!/usr/bin/python3

# For use from the login console, when not running X Windows.

import time

from picamera2 import Picamera2, Preview, MappedArray
from libcamera import controls
import cv2
import queue
import threading
import numpy as np
#import drm_preview_test as drm_preview
import drm_preview3 as drm_preview

# face_detector = cv2.CascadeClassifier("/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml")

# def draw_faces(request):
#     with MappedArray(request, "main") as m:
#         for f in faces:
#             print('here')
#             (x,y,w,h) = [c *n // d for c, n, d in zip(f, (w0, h0) * 2, (w1, h1) * 2)]
#             cv2.rectangle(m.array, (x,y), (x+w, y+h), (0, 255,0))
# #         img = m.array
# #         img[img < 120] = 0
# #         img = []

def cam_thread(num, picam):
    while True:
        queues[num].put(picam.capture_request())
        event.set()

def start_picam2(num):
    picam = Picamera2(num)
    config = picam.create_preview_configuration({'size': (1920, 1080), 'format': 'YUV420'},
                                                controls={'FrameRate': 60})
    #picam.post_callback = draw_faces
    picam.start(config)
    return picam

def main_thread():
    drm = drm_preview.DrmPreview()
    #overlay = np.zeros((960, 1080, 4), dtype=np.uint8)

    frame_count = 0
    lastFrames = 0
    last_timestamp = 0
    last_timestamp2 = 0
    start_time = time.time()

    while True:
        event.wait()
        event.clear()
        
        while all(not queue.empty() for queue in queues):
            requests = [queue.get() for queue in queues]
            for cam, request in enumerate(requests):
                #print(request.get_metadata())
                if cam == 0:
                    timestamp = (request.get_metadata()['SensorTimestamp'])
                    timestamp, last_timestamp = timestamp - last_timestamp, timestamp
                    #print(cam, round(timestamp / 1000000, 2))

                if cam == 1:
                    timestamp = (request.get_metadata()['SensorTimestamp'])
                    timestamp, last_timestamp2 = timestamp - last_timestamp2, timestamp
                    #print(cam, round(timestamp / 1000000, 2))
                #request.make_buffer('main')[request.make_buffer('main') < 255] = 0
                #img2 = img < 10
                #img[img2] = 0

                timestamp_str = str(cam) + ": " + str(round(timestamp / 1000000, 2))
                with MappedArray(request, "main") as m:
                     cv2.putText(m.array, str(timestamp_str), (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2, cv2.LINE_AA)
                
                # with MappedArray(request, "main") as m:
                #     #print(id(m.array))
                #     img = m.array
                #     #print(id(img))
                # #    cv2.putText(m.array, str(frame_count), (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2, cv2.LINE_AA)
                #     #cv2.rectangle(m.array, (frame_count, frame_count), (frame_count+frame_count, frame_count+frame_count), (255, 255, 0))
                #     #img[img < 120] = 0

                #     _, img = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY_INV)
                #     #img = _
                #     #print(id(_))
                #     img = []
                
                #egl.make_egl_buffer(request, cam)
                drm.make_buffer(request, cam)
                #drm.render_drm(request)
                request.release()
            
            #start_time = time.time()
       
            #egl.display_frame(overlay)
            drm.render_drm()
            #print((time.time() - start_time) *1000)
            frame_count += 1

            if frame_count % 120 == 0:
                current_time = time.time()
                elapsed_time = current_time - start_time
                frames = frame_count -lastFrames
                lastFrames = frame_count
                print(frames / elapsed_time)
                start_time = current_time

        for queue in queues:
            while queue.qsize() > 1:
                queue.get().release()

picams = [start_picam2(i) for i in range(2)]
# (w0,h0) = (1920,1080)
# (w1,h1) = (1920,1080)
# faces = []

queues = [queue.Queue() for _ in picams]
event = threading.Event()
threads = [threading.Thread(target=cam_thread, args=args) for args in enumerate(picams)]
for thread in threads:
    thread.start()

main_thread()

