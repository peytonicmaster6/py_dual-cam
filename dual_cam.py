import time
import os

from picamera2 import Picamera2, MappedArray
import cv2
from libcamera import controls
import preview
import numpy as np

def main():

    Picamera2.set_logging(Picamera2.DEBUG)

    overlay = np.zeros((300, 400, 4), dtype=np.uint8)
    overlay[:150, 200:] = (255, 0, 0, 64)
    overlay[150:, :200] = (0, 255, 0, 64)
    overlay[150:, 200:] = (0, 0, 255, 64)

    egl = preview.EGL()

    if len(Picamera2.global_camera_info()) <= 1:
        print("SKIPPED (one camera)")
        quit()

    picam2a = Picamera2(0)
    picam2a.preview_configuration.main.format = "YUV420"
    picam2a.preview_configuration.main.size = (640, 480)
    picam2a.preview_configuration.controls.FrameRate = 40.0
    #picam2a.preview_configuration.buffer_count = 8
    picam2a.configure('preview')
    

    picam2b = Picamera2(1)
    picam2b.preview_configuration.main.format = "YUV420"
    picam2b.preview_configuration.main.size = (640, 480)
    picam2b.preview_configuration.controls.FrameRate = 40.0
    #picam2b.preview_configuration.buffer_count = 8
    picam2b.configure('preview')


    picam2a.start()
    picam2b.start()
    
    picam2a.set_controls({'AfMode': controls.AfModeEnum.Continuous})
    picam2b.set_controls({'AfMode': controls.AfModeEnum.Continuous})

    frame_count = 0
    lastFrames = 0

    start_time = time.time()
        
    while True:
        if len(picam2a.completed_requests) > 0 and len(picam2b.completed_requests) > 0:
           request = picam2a.completed_requests.pop(0)
           request2 = picam2b.completed_requests.pop(0)

           #with MappedArray(request, "main") as m:
              #print(m.array)
           #   cv2.putText(m.array, str(frame_count), (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2, cv2.LINE_AA)
              #(T, test) = cv2.threshold(m.array, 200, 255, cv2.THRESH_BINARY)
              #print(test.shape)
           
           egl.make_egl_buffer(request, 1)
           egl.make_egl_buffer(request2, 2)
           request.release()
           request2.release()

           egl.display_frame(overlay)

           frame_count += 1

           if frame_count % 120 == 0:
                current_time = time.time()
                elapsed_time = current_time - start_time
                frames = frame_count -lastFrames
                lastFrames = frame_count
                print(frames / elapsed_time)
                start_time = current_time
                #frame_count = 0


    picam2a.stop()
    picam2b.stop()

if __name__ == "__main__":
    main()