#!/bin/bash
export DISPLAY=":0.0"
PID=/tmp/ifx_gui.gid
if [ -e $PID ]; then
     GID=`cat $PID`
     kill -HUP -$GID
     rm $PID
else
     (cd /opt/ifx_gui; python3 iqplot.py > /tmp/ifx_gui.out 2 >&1 & )
fi
