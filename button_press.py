#import easygui

from annotations import getAnnotations, addToAnnotations
from tkinter.filedialog import askopenfilename, asksaveasfilename
from matplotlib.widgets import RadioButtons
from avro_export import avroExport, avroImport
from io_thread import io_thread_lock
from time import time_ns
import matplotlib.pyplot as plt
from aws_connector import awsExport
from logging import getLogger
from numpy import mean
from numba import njit

@njit
def calcTrueSpeed(frame_idx, idx, last_update, now):
    return round(( idx - frame_idx ) * 1000000000 / (now - last_update), 1)

@njit
def update_idx(last_update, intervalMillis, frame_incr, now, frame_idx,head):
    if last_update + intervalMillis * 1000000 > now:
        return frame_idx
    next_idx = frame_idx + frame_incr

    if next_idx < 0:
        return 0
    if next_idx > head:
        return head
    return next_idx
class ButtonPress(object):
    def __init__(self):
        self.reset(10)
        self.annotateButton = None
    
    # brings the GUI to a starting state
    def reset(self,frame_incr):
        self.indexFn = self.next_impl
        self.intervalMillis = 100
        self.frame_incr = frame_incr
        self.last_update = 0
        self.annotation = getAnnotations().NONE
        # this causes the idx to go to zero after a load
        self.reset_idx = True
        #self.calcSpeed()

# to change label
# button.label.set_text('new label')
    
    #def get.intervalMillis(self):
    #    return self.intervalMillis

    def calcSpeed(self):
        if self.intervalMillis == 0:
            return 0
        self.speed = f'{1000/self.intervalMillis * self.frame_incr} frames/second'

    def getSpeed(self): 
        return self.speed

    # annotation radio button
    def annotate(self, event):
        self.annotation = getAnnotations()[event]
        getLogger(__name__).info(f'setting annotation to {self.annotation}')

    # frame slider
    def frame(self, event):
        self.intervalMillis = 200

    # frame press event handlers

    def ff_prev(self, event):
        self.resetIf(self.frame_incr > -5)
        self.setAnnotationsExisting()
        self.intervalMillis = 100
        self.set_or_increment_speed(self.next_impl, -5, 2)
        #self.calcSpeed()

    def prev(self, event):
        self.resetIf(self.frame_incr != -1)
        self.frame_incr = -1
        self.set_or_decrement_refresh(self.next_impl, 400, 2)
        #self.calcSpeed()

    def stop(self, event=None):
        self.intervalMillis = 500
        self.indexFn = self.stop_impl
        #self.calcSpeed()

    def next(self, event=None):
        self.resetIf(self.frame_incr != 1)
        self.frame_incr = 1
        self.set_or_decrement_refresh(self.next_impl, 400, 2)
        #self.calcSpeed()

    def ff_next(self, event):
        self.resetIf(self.frame_incr < 5)
        self.setAnnotationsExisting()
        self.intervalMillis = 100
        self.set_or_increment_speed(self.next_impl, 5, 2)
        #self.calcSpeed()

    def seek(self, event=None):
        self.setAnnotationsExisting()
        self.intervalMillis = 100
        self.indexFn = self.seek_impl
        self.speed = 'seek'

    def calc(self, event):
        self.recalc = True

    # condition is true when switching speed buttons (e.g. prev to next)
    # does a virtual stop because the handlers depend on existing button state
    def resetIf(self,condition):
        if condition:
            self.intervalMillis = 500
            self.indexFn = self.stop_impl

    # turns annotations back to existing when a speed button is pressed
    def setAnnotationsExisting(self):
        self.annotation = getAnnotations().EXISTING
        self.annotateButton.set_active(0)

    def addAnnotation(self, event):
        addToAnnotations([event])
        ax = self.annotateButton.ax
        self.anno_textbox.set_val('')
        ax.clear()
        self.createRadioButton(ax)
    
    def createRadioButton(self,ax):
        labels = [anno.name for anno in getAnnotations()]
        bannotate = RadioButtons(ax,labels, active=None)
        bannotate.on_clicked(self.annotate)
        bannotate.set_active(0)
        self.annotateButton = bannotate


    # when you click on a ff button start at 10 frame increment and increase every click
    def set_or_increment_speed(self, indexFn, init, increment):
        if self.indexFn != indexFn:
            self.indexFn = indexFn
            self.frame_incr = init
        else:
            self.frame_incr *= increment

    # when you click on a next/prev button it starts at 500 millis then decrease every click
    def set_or_decrement_refresh(self, indexFn, init, increment):
        if self.indexFn != indexFn:
            self.indexFn = indexFn
            self.intervalMillis = init
        else:
            self.intervalMillis /= increment

    def stop_impl(self,frame_idx,readings):
        if self.reset_idx:
            self.reset_idx = False
            return -1
        self.speed = 0
        return frame_idx

    def next_impl(self,frame_idx,readings):
        if self.reset_idx:
            self.reset_idx = False
            return -1
        now = time_ns()
        idx = update_idx( self.last_update, self.intervalMillis, self.frame_incr, 
                          now, frame_idx, readings.head)
        self.speed = calcTrueSpeed(frame_idx, idx, self.last_update, now)
        if idx != frame_idx:
            self.last_update = now
        return idx

    def seek_impl(self,frame_idx,readings):
        for i in range(frame_idx, readings.head - 10):
            # mean of RGBA phase red / green values over 10 frames
            prev = i - 10
            if prev < 0:
                prev = 0
            mean_prev = 255 - mean(readings.rgba[1,prev:i,0:1])
            next = i + 10
            if next > readings.head:
                next = readings.head
            mean_next = 255 - mean(readings.rgba[1,i:next,0:1])
            #print(f'seek: i = {i}, mean_next={mean_next}, mean_prev={mean_prev}')
            if  mean_next > 30 and mean_next > 1.5 * mean_prev:
            #    print(f'seek: i = {i}, mean_next={mean_next}, mean_prev={mean_prev}')
                now = time_ns()
                self.speed = calcTrueSpeed(frame_idx, idx, self.last_update, now)
                self.last_update = now
                self.stop(None)
                return i
        now = time_ns()
        self.speed = calcTrueSpeed(frame_idx, idx, self.last_update, now)
        self.last_update = now
        self.next(None)
        return readings.head

    # handler to save the current readings to a file in the data directory
    def save(self,config,readings):
        datadir = config['app']['data']
        if readings.source != 'live':
            filename = asksaveasfilename(initialdir=datadir, initialfile=readings.source, filetypes = (("avro files","*.avro"),("all files","*.*")))
        else:
            filename = asksaveasfilename(initialdir=datadir,filetypes = (("avro files","*.avro"),("all files","*.*")))
        getLogger(__name__).info(f'save: {filename}')
        avroExport(filename, readings)
        io_thread_lock(False)
        self.indexFn = self.seek_impl

    # handler to load a file
    def load(self,config,readings):
        datadir = config['app']['data']
        filename = askopenfilename(initialdir=datadir,filetypes = (("avro files","*.avro"),("all files","*.*")))
        if filename != '':
            getLogger(__name__).info(f'load: {filename}')
            io_thread_lock(True)
            self.indexFn = self.stop_impl
            avroImport(filename, readings)
            # restart all GUI modes
            self.reset(1)

    # handler to remove big stretches of unannotated data
    def prune(self, readings):
        readings.prune()

    # handler to recalc readings.  This is useful when loading
    # old data that might not persisted with up to date calculations
    def recalc(self, readings):
        readings.recalc()


    # handler to export a file from the data directory to the AWS bucket
    def export(self,config,readings):
        datadir = config['app']['data']
        filename = askopenfilename(initialdir=datadir,filetypes = (("avro files","*.avro"),("all files","*.*")))
        if filename != '':
            getLogger(__name__).info(f'export: {filename}')
            awsExport(config, filename)
