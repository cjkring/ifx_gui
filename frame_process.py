from logging import getLogger
import numpy as np
import bottleneck as bn
from annotations import getAnnotations

# this is the entry point
def process_frame(reading):

    reading['packet'] = reading["data_i"] + reading["data_q"] * 1j
    reading['magnitude'] = np.absolute(reading['packet'])
    reading['phase'] = np.angle(reading['packet'])
    frame_unroll_phase(reading)
    frame_phase_velocity(reading)
    #frame_rgba(readings, idx, reading)
    reading['phase'] = bn.move_mean( reading['phase'], window=5, min_count=1 )

def frame_phase_velocity(reading):
    try:
        tmp1 = reading['phase'][:-1]
        tmp2 = reading['phase'][1:]
        velocity = np.subtract(tmp2,tmp1)
        pi_2 = np.pi / 2
        #velocity = np.subtract(phase[:-1], phase[1:])
        with np.nditer(velocity, op_flags=['readwrite']) as it:
            for v in it:
                if v < -pi_2:
                    tmp = v + np.pi
                    while tmp < -pi_2:
                        tmp += np.pi
                    v[...] = tmp
                elif v > pi_2:
                    tmp = v - np.pi
                    while tmp > pi_2:
                        tmp -= np.pi
                    v[...] = tmp
        reading['phase_velocity'] = bn.move_mean( velocity, window=5, min_count=1 )
        #reading['phase_velocity'] = velocity
    except Exception as e:
        getLogger(__name__).exception('Caught exception: phase velocity:')
        # dont die but create a noticable result
        reading['phase_velocity'] = reading['phase']

def frame_unroll_phase(reading):
    try:
        count = 0
        unroll = np.copy(reading['phase'])
        offset = 0
        last_v = 0
        threshold = np.pi * 0.8
        for i in range(len(unroll)):
            v = unroll[i]
            if v > threshold and last_v < -threshold:
                # negative rollover
                offset -= np.pi * 2
                count -= 1
            elif v < -threshold and last_v > threshold:
                # negative rollover
                offset += np.pi * 2
                count += 1
            last_v = v
            unroll[i] = v + offset
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
            rgba[1,1] = clip( 255 - reading.rollover_count * 15 )
            rgba[1,0] = 255
        else:
            rgba[1,1] = 255
            rgba[1,0] = clip( 255 + reading.rollover_count * 15 )

        mag = clip( 255 - int( np.mean(reading['magnitude']) / 5))
        rgba[2,0:2] = mag
        rgba[2,3] = 150
        # marker
        rgba[0,0:2] = 0
        rgba[0,0:0] = 0

        if reading['annotation'] != getAnnotations().NONE.name:
            readings.rgba[3,idx,3] = 100
        else:
            readings.rgba[3,idx,3] = 0