import queue
import threading
from picamera2 import Picamera2, MappedArray
import preview
import numpy as np
import time
import cv2

def cam_thread(num, picam):
    while True:
        queues[num].put(picam.capture_request())
        event.set()

def start_picam2(num):
    picam = Picamera2(num)
    config = picam.create_preview_configuration({'size': (1920, 1080), 'format': 'YUV420'},
                                                controls={'FrameRate': 30})
    picam.start(config)
    return picam

def main_thread():
    egl = preview.EGL()
    overlay = np.zeros((960, 1080, 4), dtype=np.uint8)

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
                # if cam == 0:
                #     timestamp = (request.get_metadata()['SensorTimestamp'])
                #     timestamp, last_timestamp = timestamp - last_timestamp, timestamp
                #     print(cam, round(timestamp / 1000000, 2))

                if cam == 1:
                #     timestamp = (request.get_metadata()['SensorTimestamp'])
                #     timestamp, last_timestamp2 = timestamp - last_timestamp2, timestamp
                #     print(cam, round(timestamp / 1000000, 2))

                    with MappedArray(request, "main") as m:
                    #print(m.array)
                        cv2.putText(m.array, str(frame_count), (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2, cv2.LINE_AA)
                
                egl.make_egl_buffer(request, cam)
                request.release()
            
            #start_time = time.time()
       
            egl.display_frame(overlay)
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
queues = [queue.Queue() for _ in picams]
event = threading.Event()
threads = [threading.Thread(target=cam_thread, args=args) for args in enumerate(picams)]
for thread in threads:
    thread.start()

main_thread()