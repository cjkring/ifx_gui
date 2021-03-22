#!/bin/bash
export DISPLAY=":0.0"
if [ ! -e /tmp/ifx_gui.gid ]; then
     (cd /opt/ifx_gui; python3 iqplot.py > /tmp/ifx_gui.out 2 >&1 & )
fi
