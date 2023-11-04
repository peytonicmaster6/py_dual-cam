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

face_detector = cv2.CascadeClassifier("/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml")
class FaceClass():
    def __init__(self):
        self.faces = []
        self.faces2 = []
        self.facebuffer = []
        self.facebuffer2 = []
        self.lastfacebuffer = []
        self.lastfacebuffer2 = []
        self.first = True

def draw_faces(request):
    with MappedArray(request, "main") as m:
        #print('drawing faces in 0')
        for f in fc.faces:
            (x,y,w,h) = [c * n // d for c, n, d in zip(f, (w0, h0) * 2, (w1, h1) * 2)]
            cv2.rectangle(m.array, (x,y), (x+w, y+h), (0, 255,0))

def draw_faces2(request):
    with MappedArray(request, "main") as m:
        #print('drawing faces in 1')
        for f in fc.faces2:
            (x,y,w,h) = [c *n // d for c, n, d in zip(f, (w0, h0) * 2, (w1, h1) * 2)]
            cv2.rectangle(m.array, (x,y), (x+w, y+h), (0, 255,0))
        #img = m.array
        #img[img < 120] = 0
        #img = []
        #buffer = []

def face_thread():
    while True:
        #buffer = picams[0].capture_buffer("lores")
        #buffer2 = picams[1].capture_buffer("lores")
        buffer = fc.facebuffer
        if len(buffer) > 1:
          if not np.array_equal(buffer, fc.lastfacebuffer):
            grey = buffer[:s1 * h1].reshape((h1, s1))
            fc.faces = face_detector.detectMultiScale(grey, 1.1, 3)
            fc.lastfacebuffer = grey

        buffer2 = fc.facebuffer2
        if len(buffer2) > 1:
          if not np.array_equal(buffer2, fc.lastfacebuffer2):
            grey = buffer2[:s1 * h1].reshape((h1, s1))
            fc.faces2 = face_detector.detectMultiScale(grey, 1.1, 3)
            fc.lastfacebuffer2 = grey
    
def cam_thread(num, picam):
    while True:
        queues[num].put(picam.capture_request())
        event.set()

def start_picam2(num):
    picam = Picamera2(num)
    config = picam.create_preview_configuration(main={'size': (1920, 1080)},
                                                lores={"size": (320, 240), "format": "YUV420"},
                                                controls={'FrameRate': 56})

    if num == 0:
        picam.post_callback = draw_faces
    else:
        picam.post_callback = draw_faces2

    picam.start(config)
    # (w0, h0) = picam.stream_configuration("main")["size"]
    # (w1, h1) = picam.stream_configuration("lores")["size"]
    # s1 = picam.stream_configuration("lores")["stride"]

    # print(w0, h0, w1, h1, s1)

    picam.set_controls({'AfMode': controls.AfModeEnum.Continuous})
    return picam

def main_thread():
    # set width and height of preview using width=, height =
    drm = drm_preview.DrmPreview()

    face_detect_thread = threading.Thread(target=face_thread)
    face_detect_thread.start()

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
            #print(len(requests))
            #time.sleep(0.005)
            for cam, request in enumerate(requests):
                #print(request.get_metadata())
                if cam == 0:
                    #timestamp = (request.get_metadata()['SensorTimestamp'])
                    #timestamp, last_timestamp = timestamp - last_timestamp, timestamp
                    #print(cam, round(timestamp / 1000000, 2))
                    fc.facebuffer = request.make_buffer("lores")
                    if fc.first:
                        fc.lastfacebuffer = fc.facebuffer

                else:
                    #timestamp = (request.get_metadata()['SensorTimestamp'])
                    #timestamp, last_timestamp2 = timestamp - last_timestamp2, timestamp
                    fc.facebuffer2 = request.make_buffer("lores")
                    if fc.first:
                        fc.lastfacebuffer2 = fc.facebuffer2
                        fc.first = False
                    #print(cam, round(timestamp / 1000000, 2))
                #request.make_buffer('main')[request.make_buffer('main') < 255] = 0
                #img2 = img < 10
                #img[img2] = 0

                # timestamp_str = str(cam) + ": " + str(round(timestamp / 1000000, 2))
                # with MappedArray(request, "main") as m:
                #      cv2.putText(m.array, str(timestamp_str), (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2, cv2.LINE_AA)
                #      #m.array[m.array < 120] = 0
                
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
                #print('making buffer for ', cam)
                drm.make_buffer(request, cam)
                #drm.render_drm(request)
                request.release()
            
            #start_time = time.time()
       
            #egl.display_frame(overlay)
            #print('displaying frame')
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
(w0,h0) = (1920,1080)
(w1,h1) = (320,240)
s1 = 320
#faces = []
fc = FaceClass()

queues = [queue.Queue() for _ in picams]
face_queues = [queue.Queue() for _ in picams]
event = threading.Event()
threads = [threading.Thread(target=cam_thread, args=args) for args in enumerate(picams)]
# face_detect_thread = threading.Thread(target=face_thread)
for thread in threads:
    thread.start()

# face_detect_thread.start()
main_thread()

