# -*- coding: utf-8 -*-
"""
Created on Tue Dec  8 14:56:54 2020

@author: cjkri
"""

#from matplotlib.backends.backend_tkagg import (
#    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
#from matplotlib.backend_bases import key_press_handler

from platform import system
import matplotlib
from tkinter import Tk
if system() == 'Linux':
    matplotlib.use('tkagg')
else:
    matplotlib.use('macosx')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.figure import Figure
from frame_process import frame_rgba
import multiprocessing as mp

from os import getpgid, getpid, setpgid
from numba import njit
import numpy as np
import logging
import time
from datetime import datetime
import math
import cmath
import threading
from io_thread import io_thread_impl
from backup_thread import backup_thread_impl
from matplotlib.widgets import Button, TextBox, Slider
import rd_store
import button_press
from annotations import getAnnotations, addToAnnotations
from avro_export import avroImport, avroExport
from config import read_config, validate_config
from queue import Queue
from image import image_thread
from app_logging import app_logging
numpoints = 256
video_frames = 50
anim = None
logging.getLogger().setLevel(logging.INFO)

# business logic for what rbga frames to show
@njit
def calc_window(idx,window_size,head):
    
    if idx < window_size:
        return 0,window_size

    idx_min = int(idx - window_size / 2)
    idx_max = int(idx + window_size / 2)

    if idx_max >= head:
        return head - window_size,head + 1

    return idx_min,idx_max

def iqplot_update_test(n, img_q, image):
    if img_q.empty() == False:
        image.set_array(img_q.get())
    return [image]

#@njit("u1[:,:](u1[:],u1[:])")
#njit
def color_window(img_np,last_img,alpha):
    delta_max = 100
    # delta is absolute value of pixel by pixel difference between the images 
    diff = np.abs(np.subtract( img_np, last_img, dtype=np.int16))
    if diff.max() > 5:
        delta = np.multiply(diff, (delta_max/255))
    
        # adding delta to red, removing it from green and blue channels
        img_r = np.clip(img_np + delta, 0, 255).astype(np.uint8)
        img_gb = np.clip(img_np - delta, 0, 255).astype(np.uint8)

        # returning an rgba image
        return np.stack((img_r,img_gb,img_gb,alpha),axis=-1)
    else:
        return np.stack((img_np,img_np,img_np,alpha),axis=-1)

def iqplot_update_fig(n,  readings, reading_q, img_q, buttons, scat, phase_plot, velocity_plot, unrolled_plot, mag_plot, seqno, video, image):

    # readings are pushed to reading_q by the io_thread Process.
    # if the readings source is live,  then push the reading
    # if not (ie file load), then throw it away
    # this is easier than controlling io_thread as its a separate process

    while reading_q.empty() == False:
        reading = reading_q.get()
        if readings.source == 'live':
            readings.put(reading)
            frame_rgba(readings, readings.head, reading)
            reading['annotation'] = getAnnotations().NONE.name
            if img_q.empty() == False:
                reading['image'] = img_q.get()
                #print(f'added image: {reading["seqno"]}')
                break
            else: 
                reading['image'] = None

 
    if iqplot_update_fig.lastReading == None or iqplot_update_fig.lastReading > readings.head:
        # caused by Avro load
        idx = readings.head
    else:
        idx = buttons.indexFn(iqplot_update_fig.lastReading,readings)

    if idx == iqplot_update_fig.lastReading or idx == -1:
        # no new readings
        # TODO: don't return the entire list of artists
        iqplot_update_fig.lastReading = idx
        time.sleep(0.1)
        return scat,phase_plot,velocity_plot,unrolled_plot,mag_plot,seqno, video, image
    try:
        
        # the transparency of the current frame is 255, other frames are lower
        if iqplot_update_fig.lastReading != None:
            readings.rgba[0,iqplot_update_fig.lastReading,3] = 0
        readings.rgba[0,idx,3] = 100

        iqplot_update_fig.lastReading = idx
        reading = readings.get(iqplot_update_fig.lastReading)
        #print(f'iqplot update: seqno = {reading["seqno"]}')

        # annotation specified by radio button
        if buttons.annotation != getAnnotations().EXISTING:
            reading['annotation'] = buttons.annotation.name
            if buttons.annotation != getAnnotations().NONE:
                readings.rgba[3,idx,3] = 100
            else:
                readings.rgba[3,idx,3] = 0

        date_time = datetime.fromtimestamp(reading['timestamp'])
        seqno.set_text(f'frame: {idx}\ntime: {date_time}\nseqno: {reading["seqno"]}\nannotation: {reading["annotation"]}\nsource:{readings.source}')
        #print(f'{reading["seqno"]},{reading["count"]},{packet[0]},{packet[-1]}')

        #iq plot
        scat.set_offsets( np.column_stack((reading["data_i"],reading["data_q"])))

        # if hasattr(reading, "magnitude") == False:
        #     process_frame(readings, idx, reading)
     
        #magnitude plot
        mag_plot.set_ydata(reading['magnitude'])

        #phase plots
        phase_plot.set_ydata(reading['phase'])
        unrolled_plot.set_ydata(reading['phase_unrolled'])
        velocity_plot.set_ydata(reading['phase_velocity'])

        # setting range for video
        (idx_min,idx_max) = calc_window(idx,video_frames,readings.head)
        video.set_array(readings.rgba[:,idx_min:idx_max,:])

        #image
        img_bytes = reading['image']
        if img_bytes is not None:
            # see comment in image.py about how this has to be a native 
            # python array for Avro export

            # this block of code colors pixels that are different from the previous 
            # image
            img_np = np.reshape(np.frombuffer(img_bytes,dtype=np.uint8),newshape=(64,64))
            alpha = np.full((64,64),255,dtype = np.ubyte)
            if iqplot_update_fig.lastImage.size == 0:
                im_data = np.stack((img_np,img_np,img_np,alpha),axis=-1)
            else:
                im_data = color_window(img_np, iqplot_update_fig.lastImage,alpha)

            iqplot_update_fig.lastImage = img_np
            image.set_array(im_data)
            #image.set_array(np.reshape(np.frombuffer(img_bytes,dtype=np.uint8),newshape=(64,64)))
            #print(f'set image: {reading["seqno"]}')

        return scat,phase_plot,velocity_plot,unrolled_plot,mag_plot,seqno, video, image
    except Exception as e:
        logging.getLogger(__name__).exception('iqplot_update_fig exception')
        return []


    
# def createRadioButton(ax,buttons):
#     labels = [anno.name for anno in getAnnotations()]
#     bannotate = RadioButtons(ax,labels, active=None)
#     bannotate.on_clicked(buttons.annotate)
#     bannotate.set_active(0)
#     buttons.annotateButton = bannotate

def iqplot_thread_impl(readings,config,reading_q, img_q):

    # this produces a dangling root window but is needed for the filesaveas dialogs to work
    Tk()  
    logging.getLogger(__name__).warning("IQ Plot Thread started")
    fig = plt.figure()
    fig.tight_layout(pad=0.05)
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
    # font = {'family': 'monospace',
    #         'weight': 'normal',
    #         'size':8}
    # matplotlib.rc('font', **font)
            
    fig.set_size_inches(12,8)
    plt.rcParams.update({'font.size':8})
    gridsize = (30,40)

    buttons = button_press.ButtonPress()
    offsets = np.zeros(numpoints)
    
    colors = np.array(range(0,numpoints))

    # I/Q readings
    ax = plt.subplot2grid(gridsize,(0,0),rowspan=9,colspan=10)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_xlim(-3000,3000)
    ax.set_ylim(-3000,3000)
    scat = ax.scatter(offsets, offsets, c=colors, cmap='plasma', alpha=0.75)
    #ax.set_title('I/Q Readings')

    # phase
    ax = plt.subplot2grid(gridsize,(10,10),rowspan=9,colspan=10)
    #ax.set_yticks([])
    #ax.set_xticks([])
    ax.set_ylim(-np.pi,np.pi)
    ax.set_xlim(0,255)
    ax.axhline(0,color='grey')
    phase, = ax.plot(offsets)
    #ax.set_title('phase')

    # phase velocity
    ax = plt.subplot2grid(gridsize,(10,0),rowspan=9,colspan=10)
    #ax.set_yticks([])
    #ax.set_xticks([])
    ax.set_ylim(-np.pi,np.pi)
    ax.set_xlim(0,255)
    ax.axhline(0,color='grey')
    velocity, = ax.plot(offsets[:-1])
    #ax.set_title('phase velocity')

    # phase unrolled
    ax = plt.subplot2grid(gridsize,(10,20),rowspan=9,colspan=10)
    #ax.set_yticks([])
    #ax.set_xticks([])
    ax.set_ylim(-np.pi * 10 ,np.pi * 10 )
    ax.set_xlim(0,256)
    ax.axhline(0,color='grey')
    unrolled, = ax.plot(offsets)
    #ax.set_title('phase no rollover')

    # magnitude
    ax = plt.subplot2grid(gridsize,(0,10),rowspan=9,colspan=10)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_ylim(0 ,2000 )
    ax.set_xlim(0,252)
    #ax.set_title('magnitude')
    ax.axhline(0,color='grey')
    magnitude, = ax.plot(offsets)

    # image 
    ax = plt.subplot2grid(gridsize,(0,20),rowspan=9,colspan=10)
    ax.axis('off')
    #ax.set_title('image')
    #tmp = np.reshape(np.frombuffer(tbwbwest_bytes,dtype=np.uint8),newshape=(64,64))
    tmp = np.random.randint(230,255,(64,64),dtype = np.ubyte)
    tmp_alpha = np.full((64,64),255,dtype = np.ubyte)
    im_data = np.stack((tmp,tmp,tmp,tmp_alpha),axis=-1)
    #im_data = np.random.randint(230,255,(60,60),dtype=np.ubyte)
    image = ax.imshow(im_data, vmin=0, vmax=255)

    # annotations buttons
    ax = plt.subplot2grid(gridsize,(0,30),rowspan=18,colspan=10)
    #ax.set_title('annotations')
    buttons.createRadioButton(ax)

    ax = plt.subplot2grid(gridsize,(18,30),rowspan=1,colspan=10)
    text_box = TextBox(ax,None)
    text_box.on_submit(buttons.addAnnotation)
    buttons.anno_textbox = text_box


    # rgb hostory
    ax = plt.subplot2grid(gridsize,(20,0),rowspan=3,colspan=40)
    ax.axis('off')
    tmp = readings.rgba[:,0:video_frames,:]
    video = ax.imshow(tmp, vmin=0, vmax=255, aspect='auto')

    # info text
    ax = plt.subplot2grid(gridsize,(24,0),rowspan=5,colspan=15)
    ax.axis('off')
    seqno = ax.text(0, 0, "frame:\ntime:\nseqno:\nannotation:\nsource:",fontsize=8)

    # control buttons
    bff_prev = Button( plt.subplot2grid(gridsize,(24,16),rowspan=2,colspan=3), '<<')
    bff_prev.on_clicked(buttons.ff_prev)

    bprev =  Button( plt.subplot2grid(gridsize,(24,20),rowspan=2,colspan=3), '<')
    bprev.on_clicked(buttons.prev)
    
    bstop =  Button( plt.subplot2grid(gridsize,(24,24),rowspan=2,colspan=3), '||')
    bstop.on_clicked(buttons.stop)
    
    bnext = Button( plt.subplot2grid(gridsize,(24,28),rowspan=2,colspan=3), '>')
    bnext.on_clicked(buttons.next)
    
    bff_next = Button( plt.subplot2grid(gridsize,(24,32),rowspan=2,colspan=3), '>>')
    bff_next.on_clicked(buttons.ff_next)
    
    # seek fast forwards 20 frame at a time, then stops when the next 10 frames have 
    # significant activity
    bseek = Button( plt.subplot2grid(gridsize,(24,36),rowspan=2,colspan=3), 'seek')
    bseek.on_clicked(buttons.seek)

    bload = Button( plt.subplot2grid(gridsize,(27,18),rowspan=2,colspan=3), 'load')
    bload.on_clicked(lambda x: buttons.load(config,readings))
    buttons.importbutton = bload

    bsave = Button( plt.subplot2grid(gridsize,(27,22),rowspan=2,colspan=3), 'save')
    bsave.on_clicked(lambda x: buttons.save(config,readings))
    buttons.savebutton = bsave

    bexport = Button( plt.subplot2grid(gridsize,(27,26),rowspan=2,colspan=3), 'export')
    bexport.on_clicked(lambda x: buttons.export(config,readings))
    buttons.exportbutton = bexport

    bprune = Button( plt.subplot2grid(gridsize,(27,30),rowspan=2,colspan=3), 'prune')
    bprune.on_clicked(lambda x: buttons.prune(readings))

    bcalc = Button( plt.subplot2grid(gridsize,(27,34),rowspan=2,colspan=3), 'recalc')
    bcalc.on_clicked(lambda x: buttons.recalc(readings))


    global anim
    #anim = animation.FuncAnimation(fig,iqplot_update_fig,fargs=(readings,reading_q, img_q, buttons,scat,phase,velocity,unrolled,magnitude,seqno,video,image),interval=100, blit=False)
    anim = animation.FuncAnimation(fig,iqplot_update_fig,fargs=(readings,reading_q, img_q, buttons,scat,phase,velocity,unrolled,magnitude,seqno,video,image),interval=100, blit=True)
    figManager = plt.get_current_fig_manager()
    figManager.full_screen_toggle()
    plt.show()

iqplot_update_fig.lastReading = None
iqplot_update_fig.lastImage = np.array([])

# This is the main entry point to the ifx_gui app

if  __name__ == "__main__":

    # This is used to implement start/stop from a button
    # It writes a group id to the PID file that the button
    # hander uses to stop a running instance
    setpgid(0,0)
    with open('/tmp/ifx_gui.gid', 'w') as pid:
        pid.write(f"{getpgid(getpid())}")

    config = read_config()
    validate_config(config)
    app_logging(logging.getLogger(__name__),config,logging.DEBUG,"iqplot.log")
    addToAnnotations(config['app']['annotations'])
    readings = rd_store.Readings()

    img_q = mp.Queue(maxsize=2);
    reading_q = mp.Queue(maxsize=5);

    image_t = mp.Process(target=image_thread,args=(config,img_q))
    image_t.start()

    io = mp.Process(target=io_thread_impl, args=(reading_q,))
    io.start()

    # this has to be a thread because it relies on readings
    backup = threading.Thread(target=backup_thread_impl, args=(readings,config))
    backup.start()
    iqplot_thread_impl(readings,config,reading_q, img_q)



