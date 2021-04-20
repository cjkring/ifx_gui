from logging import getLogger
import numpy as np
import bottleneck as bn
from annotations import getAnnotations
from math import atan2
from numba import njit

# this is the entry point
def process_frame(reading):

    # average all frame values to eliminate bias that affects phase
    reading['data_i'] -= int(np.mean(reading['data_i']))
    reading['data_q'] -= int(np.mean(reading['data_q']))

    reading['packet'] = reading["data_i"] + reading["data_q"] * 1j
    reading['magnitude'] = np.absolute(reading['packet'])
    reading['phase'] = np.angle(reading['packet'])
    frame_unroll_phase(reading)
    frame_phase_velocity(reading)
    #frame_rgba(readings, idx, reading)
    #reading['phase'] = bn.move_mean( reading['phase'], window=5, min_count=1 )

@njit
def handle_rollover(velocity):
    for k in range(len(velocity)):
        if velocity[k] < -np.pi:
            velocity[k] += 2 * np.pi
        elif velocity[k] > np.pi:
                velocity[k] -= 2 * np.pi
   

def frame_phase_velocity(reading):
    try:
        data_i = reading['data_i'][1:] - reading['data_i'][0:-1]
        data_q = reading['data_q'][1:] - reading['data_q'][0:-1]
        tmp = data_i + data_q * 1j
        velocity = np.angle(tmp) - reading['phase'][1:]
        # handle rollover
        handle_rollover(velocity)
        #reading['phase_velocity'] = bn.move_mean( velocity, window=5, min_count=1 )
        reading['phase_velocity'] = velocity 
        
    # old
        # last_i = reading['data_i'][0]
        # last_q = reading['data_q'][0]
        # velocity = np.zeros(reading['data_i'].shape, dtype=np.float)
        # reading['phase_velocity'] = velocity
        # velocity[0] = 0
        # for k in range(1,len(reading['data_i'])):
        #     i = reading['data_i'][k]
        #     q = reading['data_q'][k]
        #     velocity[k] = atan2(q - last_q,i - last_i)
        #     last_i = i
        #     last_q = q
    # really old
    #     tmp1 = reading['phase'][:-1]O
    #     tmp2 = reading['phase'][1:]
    #     velocity = np.subtract(tmp2,tmp1)
    #     pi_2 = np.pi / 2
    #     #velocity = np.subtract(phase[:-1], phase[1:])
    #     with np.nditer(velocity, op_flags=['readwrite']) as it:
    #         for v in it:
    #             if v < -pi_2:
    #                 tmp = v + np.pi
    #                 while tmp < -pi_2:
    #                     tmp += np.pi
    #                 v[...] = tmp
    #             elif v > pi_2:
    #                 tmp = v - np.pi
    #                 while tmp > pi_2:
    #                     tmp -= np.pi
    #                 v[...] = tmp
    #     reading['phase_velocity'] = bn.move_mean( velocity, window=5, min_count=1 )
    #     #reading['phase_velocity'] = velocity
    except Exception as e:
        getLogger(__name__).exception('Caught exception: phase velocity:')
        # dont die but create a noticable result
        reading['phase_velocity'] = reading['phase']

@njit
def do_unroll(unroll):
    # range is -pi to pi
    threshold = np.pi * 1.6
    offset = 0
    count = 0
    last_v = unroll[0]
    for i in range(1,len(unroll)):
        v = unroll[i]
        tmp = last_v - v
        if tmp < -threshold:
            # negative rollover
            offset -= np.pi * 2
            count -= 1
        elif tmp > threshold:
            # positive rollover
            offset += np.pi * 2
            count += 1
        last_v = v
        unroll[i] = v + offset
    return count


def frame_unroll_phase(reading):
    try:
        unroll = np.copy(reading['phase'])
        count = do_unroll(unroll)
        reading['phase_unrolled'] = unroll
        reading.rollover_count = count
    except Exception as e:
        getLogger(__name__).exception('Caught exception in unroll_phase:')
        # dont die but create a noticable result
        reading['phase_unrolled'] = reading['phase']
        reading.rollover_count = 0

def clip(i):
    if i < 0: return 0
    if i > 255: return 255
    return i

# return a (4) array of R,G,B, A values
def frame_rgba(readings,idx, reading):

    # rgba is a (4,4) array of bytes.  The last column are RBGA values used in the 'video' imshow
    # rgba[0] is the curser -- the dot that shows the current iqplot idx
    # rgba[1] is red / green and visualized whether movement to do or from the radar
    # rgba[2] is magnitude
    # rgba[3] is activity -- used to clip readings during avroExport
    rgba = readings.rgba[:,idx]
    if rgba[1,3] == 0:
        # dont repeat the work
        rgba[1,2] = 0
        rgba[1,3] = 255
        # avro export didn't add rollover count
        if hasattr(reading,'rollover_count') == False:
            reading.rollover_count = (reading['phase_unrolled'][-1] - reading['phase_unrolled'][0] ) / ( 2 * np.pi)
        if reading.rollover_count >= 0:
            rgba[1,1] = clip( 255 - reading.rollover_count * 20 )
            rgba[1,0] = 255
        else:
            rgba[1,1] = 255
            rgba[1,0] = clip( 255 + reading.rollover_count * 20 )

        mag = clip( 255 - int( np.mean(reading['magnitude']) / 2))
        rgba[2,0:2] = mag
        rgba[2,3] = 150
        # marker
        rgba[0,0:2] = 0
        rgba[0,0:0] = 0

        if reading['annotation'] != getAnnotations().NONE.name:
            readings.rgba[3,idx,3] = 100
        else:
            readings.rgba[3,idx,3] = 0