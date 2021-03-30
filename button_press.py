#import easygui

from annotations import getAnnotations, addToAnnotations
from tkinter.filedialog import askopenfilename, asksaveasfilename
from avro_export import avroExport, avroImport
from io_thread import io_thread_lock
from time import time_ns
import matplotlib.pyplot as plt
from iqplot import createRadioButton
from aws_connector import awsExport
from logging import getLogger

class ButtonPress(object):
    def __init__(self):
        global Annotations
        self.indexFn = self.last_impl
        self.intervalMillis = 200
        self.frame_incr = 1
        self.last_update = 0
        self.annotation = getAnnotations().NONE
        self.annotateButton = None

# to change label
# button.label.set_text('new label')
    
    #def get.intervalMillis(self):
    #    return self.intervalMillis

    # annotation radio button
    def annotate(self, event):
        self.annotation = getAnnotations()[event]
        getLogger(__name__).info(f'setting annotation to {self.annotation}')

    # frame slider
    def frame(self, event):
        self.intervalMillis = 200

    # frame press event handlers

    def ff_prev(self, event):
        self.setAnnotationsExisting()
        self.intervalMillis = 100
        self.set_or_increment_speed(self.ff_prev_impl, -10, -10)

    def prev(self, event):
        self.frame_incr = -1
        self.set_or_decrement_refresh(self.prev_impl, 500, 200)

    def stop(self, event):
        self.intervalMillis = 500
        self.indexFn = self.stop_impl

    def next(self, event):
        self.frame_incr = 1
        self.set_or_decrement_refresh(self.next_impl, 500, 200)

    def ff_next(self, event):
        self.setAnnotationsExisting()
        self.intervalMillis = 100
        self.set_or_increment_speed(self.ff_next_impl, 10, 10)

    def last(self, event):
        self.setAnnotationsExisting()
        self.intervalMillis = 100
        self.indexFn = self.last_impl

    # turns annotations back to existing when a speed button is pressed
    def setAnnotationsExisting(self):
        self.annotation = getAnnotations().EXISTING
        self.annotateButton.set_active(0)

    def addAnnotation(self, event):
        addToAnnotations([event])
        ax = self.annotateButton.ax
        self.anno_textbox.set_val('')
        ax.clear()
        createRadioButton(ax, self)


    # when you click on a ff button start at 10 frame increment and increase every click
    def set_or_increment_speed(self, indexFn, init, increment):
        if self.indexFn != indexFn:
            self.indexFn = indexFn
            self.frame_incr = init
        else:
            self.frame_incr += increment

    # when you click on a next/prev button it starts at 500 millis then decrease every click
    def set_or_decrement_refresh(self, indexFn, init, increment):
        if self.indexFn != indexFn:
            self.indexFn = indexFn
            self.intervalMillis = init
        else:
            self.intervalMillis -= increment

    def stop_impl(self,frame_idx,readings):
        return frame_idx

    def ff_prev_impl(self,frame_idx,readings):
        return self.update_idx(frame_idx,readings)

    def prev_impl(self,frame_idx,readings):
        return self.update_idx(frame_idx,readings)

    def next_impl(self,frame_idx,readings):
        return self.update_idx(frame_idx,readings)
        
    def ff_next_impl(self,frame_idx,readings):
        return self.update_idx(frame_idx,readings)

    def update_idx(self,frame_idx,readings):
        now = time_ns()
        if self.last_update + self.intervalMillis * 1000000 > now:
            return frame_idx
        self.last_update = now
        next_idx = frame_idx + self.frame_incr

        if next_idx < 0:
            return 0
        if next_idx > readings.head:
            return readings.head
        return next_idx

    def last_impl(self,frame_idx,readings):
        return readings.head

    def save(self,config,readings):
        datadir = config['app']['data']
        if readings.source != 'live':
            filename = asksaveasfilename(initialdir=datadir, initialfile=readings.source, filetypes = (("avro files","*.avro"),("all files","*.*")))
        else:
            filename = asksaveasfilename(initialdir=datadir,filetypes = (("avro files","*.avro"),("all files","*.*")))
        getLogger(__name__).info(f'save: {filename}')
        avroExport(filename, readings)
        io_thread_lock(False)
        self.indexFn = self.last_impl

    def load(self,config,readings):
        datadir = config['app']['data']
        filename = askopenfilename(initialdir=datadir,filetypes = (("avro files","*.avro"),("all files","*.*")))
        if filename != '':
            getLogger(__name__).info(f'load: {filename}')
            io_thread_lock(True)
            self.indexFn = self.stop_impl
            avroImport(filename, readings)
            self.intervalMillis = 10000000
            self.frame_incr = 1
            self.indexFn = self.next_impl

    def prune(self, readings):
        readings.prune()

    def autoAnnotate(self, readings):
        readings.autoAnnotate()


    def export(self,config,readings):
        datadir = config['app']['data']
        filename = askopenfilename(initialdir=datadir,filetypes = (("avro files","*.avro"),("all files","*.*")))
        if filename != '':
            getLogger(__name__).info(f'export: {filename}')
            awsExport(config, filename)