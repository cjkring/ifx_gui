import numpy as np
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import math
import logging
from app_logging import app_logging


# NOTE:  The image is captured and manipulated as an np array, then converted to native
# bytes because this is what works for avro import / export.   If has to be converted back 
# to a np array for imshow
enableCamera = True
try:
    import picamera
except ImportError as e:
    enableCamera = False

def image_thread(config,img_q):
    logger = logging.getLogger(__name__)
    app_logging(logger, config, logging.INFO, "image.log")
    if enableCamera == False:
        logger.warning('PiCamera not installed -- images disabled')
        return
    (h,w) = config['app']['image_size'].split('x')
    h = 64
    w = 64
    camera = picamera.PiCamera()
    camera.resolution = (w,h)
    camera.framerate = 1
    camera.exposure_mode = 'night'
    # black and white
    camera.color_effects = (128,128)
    while True:
        frame = np.empty((h*w*2),dtype=np.ubyte)
        camera.capture(frame,'yuv')
        img = np.rot90(np.resize(frame,(h,w)))
        img_q.put(img.tobytes())
        now = time.time()
        #print(f'new image = {now}')
        # wake up at top of the current second
        #time.sleep(math.ceil(now) - now)

if  __name__ == "__main__":
    #import threading
    import multiprocessing as mp
    import config

    def image_update_fig(n,img_q,im):
        if img_q.empty() == False:
            tmp = np.frombuffer(img_q.get(),dtype=np.uint8)
            im_data = np.reshape(tmp, newshape=(64,64))
            #im_data = np.reshape(np.frombuffer(img_q.get()),newshape=(64,64))
            im.set_array(im_data)
        return im

    conf = config.read_config()
    config.validate_config(conf)

    img_q = mp.Queue(maxsize=2);

    image_t = mp.Process(target=image_thread,args=(conf,img_q))
    image_t.start()

    fig = plt.figure()
    fig.set_size_inches(5,5)
    im_data = np.zeros((32,32),dtype=np.ubyte)
    im = plt.imshow(im_data, vmin=0, vmax=255, cmap='gray')

    anim = animation.FuncAnimation(fig,image_update_fig,fargs=(img_q,im),interval=100, blit=False)

    plt.show()
    #image_t.join()
