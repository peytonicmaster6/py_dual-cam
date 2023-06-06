import os

os.environ["PYOPENGL_PLATFORM"] = "egl"
from OpenGL.EGL.EXT.image_dma_buf_import import *
from OpenGL.EGL.KHR.image import *
from OpenGL.EGL.VERSION.EGL_1_0 import *
from OpenGL.EGL.VERSION.EGL_1_2 import *
from OpenGL.EGL.VERSION.EGL_1_3 import *
from OpenGL.GL import shaders
from OpenGL.GLES2.OES.EGL_image import *
from OpenGL.GLES2.OES.EGL_image_external import *
from OpenGL.GLES2.VERSION.GLES2_2_0 import *
from OpenGL.GLES3.VERSION.GLES3_3_0 import *
from OpenGL.raw.GLES2 import _types as _cs

from ctypes import (CFUNCTYPE, POINTER, c_bool, c_char_p, c_int, c_void_p,
                    cdll, pointer, util, byref, c_ulong)
from Xlib import X, display

def str_to_fourcc(str):
        assert (len(str) == 4)
        fourcc = 0
        for i, v in enumerate([ord(c) for c in str]):
            fourcc |= v << (i * 8)

        #print(fourcc)
        return fourcc

def getglEGLImageTargetTexture2DOES():
    funcptr = eglGetProcAddress("glEGLImageTargetTexture2DOES")
    prototype = CFUNCTYPE(None, _cs.GLenum, _cs.GLeglImageOES)
    return prototype(funcptr)

glEGLImageTargetTexture2DOES = getglEGLImageTargetTexture2DOES()

class EGL:
    def __init__(self):
        self.create_display()
        self.choose_config()
        self.create_window()
        self.create_context()
        self.create_surface()
        
        eglMakeCurrent(self.display, EGL_NO_SURFACE, EGL_NO_SURFACE, self.context)
        n = GLint()
        glGetIntegerv(GL_MAX_TEXTURE_SIZE, n)
        self.max_texture_size = n.value

        eglMakeCurrent(self.display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.overlay_texture = glGenTextures(1)

        self.FMT_MAP = {
                "XRGB8888": "XR24",
                "XBGR8888": "XB24",
                "YUYV": "YUYV",
                # doesn't work "YVYU": "YVYU",
                "UYVY": "UYVY",
                # doesn't work "VYUY": "VYUY",
                "YUV420": "YU12",
                "YVU420": "YV12",
            }
        
        self.first_time = True

    def init_gl(self):
        vertShaderSrc_image = f"""
            attribute vec2 aPosition;
            varying vec2 texcoord;

            void main()
            {{
                gl_Position = vec4(aPosition * 2.0 - 1.0, 0.0, 1.0);
                texcoord.x = {''}aPosition.x;
                texcoord.y = {'1.0 - '}aPosition.y;
            }}
        """
        fragShaderSrc_image = """
            #extension GL_OES_EGL_image_external : enable
            precision mediump float;
            varying vec2 texcoord;
            uniform samplerExternalOES texture;

            void main()
            {
                gl_FragColor = texture2D(texture, texcoord);
            }
        """
        vertShaderSrc_overlay = """
            attribute vec2 aPosition;
            varying vec2 texcoord;

            void main()
            {
                gl_Position = vec4(aPosition * 2.0 - 1.0, 0.0, 1.0);
                texcoord.x = aPosition.x;
                texcoord.y = 1.0 - aPosition.y;
            }
        """
        fragShaderSrc_overlay = """
            precision mediump float;
            varying vec2 texcoord;
            uniform sampler2D overlay;

            void main()
            {
                gl_FragColor = texture2D(overlay, texcoord);
            }
        """

        self.program_image = shaders.compileProgram(
            shaders.compileShader(vertShaderSrc_image, GL_VERTEX_SHADER),
            shaders.compileShader(fragShaderSrc_image, GL_FRAGMENT_SHADER)
        )
        self.program_overlay = shaders.compileProgram(
            shaders.compileShader(vertShaderSrc_overlay, GL_VERTEX_SHADER),
            shaders.compileShader(fragShaderSrc_overlay, GL_FRAGMENT_SHADER)
        )

        vertPositions = [
            0.0, 0.0,
            1.0, 0.0,
            1.0, 1.0,
            0.0, 1.0
        ]

        inputAttrib = glGetAttribLocation(self.program_image, "aPosition")
        glVertexAttribPointer(inputAttrib, 2, GL_FLOAT, GL_FALSE, 0, vertPositions)
        glEnableVertexAttribArray(inputAttrib)

        inputAttrib = glGetAttribLocation(self.program_overlay, "aPosition")
        glVertexAttribPointer(inputAttrib, 2, GL_FLOAT, GL_FALSE, 0, vertPositions)
        glEnableVertexAttribArray(inputAttrib)

        glUseProgram(self.program_overlay)
        glUniform1i(glGetUniformLocation(self.program_overlay, "overlay"), 0)

        self.buffer_texture = glGenTextures(1)
        self.buffer_texture2 = glGenTextures(1)



    def create_window(self):
        pd = display.Display()
        pw = pd.screen().root.create_window(0,0,1920,1080,0,pd.screen().root_depth,X.InputOutput, X.CopyFromParent)
        pw.map()
        pd.sync()
        self.winId = pw.__resource__()

    def create_display(self):
        _x11lib = cdll.LoadLibrary(util.find_library("X11"))
        XOpenDisplay = _x11lib.XOpenDisplay
        XOpenDisplay.argtypes = [c_char_p]
        XOpenDisplay.restype = POINTER(EGLNativeDisplayType)
        xdisplay = XOpenDisplay(None)
        self.display = eglGetDisplay(xdisplay)
        
        major, minor = EGLint(), EGLint()

        eglInitialize(self.display, major, minor)

    def choose_config(self):

        extensions = eglQueryString(self.display, EGL_EXTENSIONS).decode().split(" ")

        config_attribs = [
                EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
                EGL_RED_SIZE, 8,
                EGL_GREEN_SIZE, 8,
                EGL_BLUE_SIZE, 8,
                EGL_ALPHA_SIZE, 0,
                EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
                EGL_NONE,
        ]

        n = EGLint()
        configs = (EGLConfig * 1)()
        eglChooseConfig(self.display, config_attribs, configs, 1, n)
        self.config = configs[0]

        egl_vid = EGLint()
        eglGetConfigAttrib(self.display, self.config, EGL_NATIVE_VISUAL_ID, egl_vid)

    def create_context(self):
        context_attribs = [
                EGL_CONTEXT_CLIENT_VERSION, 2,
                EGL_NONE,
        ]

        eglBindAPI(EGL_OPENGL_ES_API)

        self.context = eglCreateContext(self.display, self.config, EGL_NO_CONTEXT, context_attribs)


    def create_surface(self):
        self.surface = eglCreateWindowSurface(self.display, self.config, self.winId, None) 


    def make_egl_buffer(self, completed_request, cam_num):

        if self.first_time:
            eglMakeCurrent(self.display, self.surface, self.surface, self.context)
            self.init_gl()
            self.first_time = False

        picam2 = completed_request.picam2
        stream = picam2.stream_map[picam2.display_stream_name]
        fb = completed_request.request.buffers[stream]
        cfg = stream.configuration
        pixel_format = str(cfg.pixel_format)

        fmt = str_to_fourcc(self.FMT_MAP[pixel_format])
        w, h = (cfg.size.width, cfg.size.height)

        h2 = h // 2
        stride2 = cfg.stride // 2
        attribs = [
            EGL_WIDTH, w,
            EGL_HEIGHT, h,
            EGL_LINUX_DRM_FOURCC_EXT, fmt,
            EGL_DMA_BUF_PLANE0_FD_EXT, fb.planes[0].fd,
            EGL_DMA_BUF_PLANE0_OFFSET_EXT, 0,
            EGL_DMA_BUF_PLANE0_PITCH_EXT, cfg.stride,
            EGL_DMA_BUF_PLANE1_FD_EXT, fb.planes[0].fd,
            EGL_DMA_BUF_PLANE1_OFFSET_EXT, h * cfg.stride,
            EGL_DMA_BUF_PLANE1_PITCH_EXT, stride2,
            EGL_DMA_BUF_PLANE2_FD_EXT, fb.planes[0].fd,
            EGL_DMA_BUF_PLANE2_OFFSET_EXT, h * cfg.stride + h2 * stride2,
            EGL_DMA_BUF_PLANE2_PITCH_EXT, stride2,
            EGL_NONE,
        ]

        # attribs = [
        #      EGL_WIDTH, w,
        #      EGL_HEIGHT, h,
        #      EGL_LINUX_DRM_FOURCC_EXT, fmt,
        #      EGL_DMA_BUF_PLANE0_FD_EXT, fb.planes[0].fd,
        #      EGL_DMA_BUF_PLANE0_OFFSET_EXT, 0,
        #      EGL_DMA_BUF_PLANE0_PITCH_EXT, cfg.stride,
        #      EGL_NONE,
        # ]

        #print(self.display)

        image = eglCreateImageKHR(self.display,
                                EGL_NO_CONTEXT,
                                EGL_LINUX_DMA_BUF_EXT,
                                None,
                                attribs)

        if cam_num == 1:
            glBindTexture(GL_TEXTURE_EXTERNAL_OES, self.buffer_texture)
        elif cam_num == 2:
            glBindTexture(GL_TEXTURE_EXTERNAL_OES, self.buffer_texture2)

        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glEGLImageTargetTexture2DOES(GL_TEXTURE_EXTERNAL_OES, image)

        eglDestroyImageKHR(self.display, image)

    def display_frame(self):
        glClearColor(0, 0, 0, 0)
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(self.program_image)
        glBindTexture(GL_TEXTURE_EXTERNAL_OES, self.buffer_texture)
        glViewport(0,0,960,1080)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

        glBindTexture(GL_TEXTURE_EXTERNAL_OES, self.buffer_texture2)
        glViewport(960,0,960,1080)
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

        eglSwapBuffers(self.display, self.surface)