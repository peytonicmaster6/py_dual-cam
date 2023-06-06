import time
import os

from picamera2 import Picamera2
import cv2
from libcamera import controls
import preview



def main():

    egl = preview.EGL()

    if len(Picamera2.global_camera_info()) <= 1:
        print("SKIPPED (one camera)")
        quit()

    picam2a = Picamera2(0)
    picam2a.preview_configuration.main.format = "YUV420"
    picam2a.preview_configuration.main.size = (1920, 1080)
    picam2a.preview_configuration.controls.FrameRate = 30
    picam2a.configure('preview')
    

    picam2b = Picamera2(1)
    picam2b.preview_configuration.main.format = "YUV420"
    picam2b.preview_configuration.main.size = (1920, 1080)
    picam2b.preview_configuration.controls.FrameRate = 30
    picam2b.configure('preview')


    picam2a.start()
    picam2b.start()
    
    picam2a.set_controls({'AfMode': controls.AfModeEnum.Continuous})
    picam2b.set_controls({'AfMode': controls.AfModeEnum.Continuous})
        
    while True:
        if len(picam2a.completed_requests) > 0 and len(picam2b.completed_requests) > 0:
           request = picam2a.completed_requests.pop(0)
           request2 = picam2b.completed_requests.pop(0)
           
           egl.make_egl_buffer(request, 1)
           egl.make_egl_buffer(request2, 2)
           request.release()
           request2.release()

           egl.display_frame()


    picam2a.stop()
    picam2b.stop()

if __name__ == "__main__":
    main()