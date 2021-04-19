
import numpy as np
from time import time
from annotations import getAnnotations
from logging import getLogger
from frame_process import frame_rgba, process_frame
class Reading(dict):

    def __init__(self, seqno, count, data_i, data_q):
        global Annotations
        self['timestamp'] = time()
        self['seqno'] = seqno
        self['count'] = count
        self['data_i'] = np.asarray(data_i)
        self['data_q'] = np.asarray(data_q)
        #self['annotation'] = getAnnotations()['NONE']
        self['annotation'] = None

class Readings:
    def __init__(self):
        self.head = -1
        self.size = 20000
        self.readings = np.empty(self.size, dtype=Reading)
        self.rgba = np.zeros((4,self.size,4),dtype=np.ubyte)
        self.pause = 0
        # changes to file name if file is imported
        self.source = 'live'
    
    def __iter__(self):
        return iter(self.readings[:self.head + 1])

    def put(self,reading):
        while self.pause == 1:
            time.sleep(0.01)
        self.head += 1
        self.readings[self.head] = reading

    def get(self, index):
        if index > self.head:
            return self.readings[self.head]
        if index < 0:
            return self.readings[0]
        return self.readings[index]
    
    def backup(self):
        self.pause = 1
        backup = Readings()
        tmp = self.readings
        self.readings = backup.readings
        backup.readings = tmp
        backup.head = self.head
        self.head = -1
        self.pause = 0
        return backup
    
    # removes all unannotated readings except readings adjacent to an annotated reading
    # the remaining unannotated readings act as a marker

    # helper only used in prune, moves readings[i] to readings[idx]
    def update_readings(self, i, idx):
        if i == idx:
            return
        self.readings[idx] = self.readings[i]
        self.rgba[:,idx] = self.rgba[:,i]

    def prune(self):
        if self.head == -1: 
            return
        prev = round( time(), 3 )
        self.pause = True
        readings = self.readings
        #self.readings = np.empty(self.size, dtype=Reading)
        idx = 0
        prev_active = False
        annotation = readings[0]['annotation']
        cur_active = ( annotation != getAnnotations().NONE.name )
        for i in range(self.head):
            annotation = readings[i+1]['annotation']
            next_active = ( annotation != getAnnotations().NONE.name )
            if prev_active == True or cur_active == True or next_active == True:
                self.update_readings(i, idx)
                idx += 1
            prev_active = cur_active
            cur_active = next_active
        # take care of readings.head
        if prev_active == True or cur_active == True:
            self.update_readings(self.head, idx)
        self.head = idx
        self.pause = False
        now = round( time(), 3 )
        getLogger(__name__).info(f'{idx} readings retained in {now-prev} seconds')
        

    # unused
    # sets annotation to ACTIVE based upon the following
    # - significant pixel differences between 
    def autoAnnotate(self):
        if self.head == -1: 
            return
        return
    
    # reprocesses all frames in readings. Used to reprocess old data files
    def recalc(self):
        print('start')
        for i in range(self.head + 1):
            if i == 19:
                print('here')
            process_frame(self.readings[i])
            frame_rgba(self, i, self.readings[i])
        print('done')

            
        
    


            


