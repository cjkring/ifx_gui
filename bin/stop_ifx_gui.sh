#/bin/sh
GID=`cat /tmp/ifx_gui.gid`
kill -9 -$GID
rm /tmp/ifx_gui.gid
