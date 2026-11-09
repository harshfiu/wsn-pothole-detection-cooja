#!/bin/bash
# Runs Cooja on a virtual display and serves it to the browser at
# http://localhost:6080/vnc.html  Usage: demo_vnc.sh [failure|baseline]
SIM=${1:-failure}
DISP=:77
# WSLg sets these; x11vnc refuses to start while it thinks it is on Wayland.
unset WAYLAND_DISPLAY XDG_SESSION_TYPE
pkill -x java; pkill -x x11vnc; pkill -x openbox; pkill -x Xvfb; pkill -f websockify
sleep 1
rm -f /tmp/.X77-lock /tmp/.X11-unix/X77

Xvfb $DISP -screen 0 1600x900x24 >/dev/null 2>&1 &
sleep 2
export DISPLAY=$DISP
openbox >/dev/null 2>&1 &
x11vnc -display $DISP -localhost -nopw -forever -shared -rfbport 5977 -quiet -bg >/dev/null 2>&1
websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5977 >/tmp/websockify.log 2>&1 &

cd "$HOME/contiki/tools/cooja" || exit 1
java -Xmx1g -jar dist/cooja.jar -quickstart="$HOME/contiki/examples/pothole-wsn/pothole-demo-$SIM.csc" \
     -contiki="$HOME/contiki" >/tmp/cooja-demo.log 2>&1 &
J=$!

# Fill the virtual screen once Cooja's window is up.
for i in $(seq 1 60); do
  W=$(xdotool search --name "Cooja: The Contiki" 2>/dev/null | head -1)
  [ -n "$W" ] && break
  sleep 1
done
sleep 3
xdotool windowmove "$W" 0 0 windowsize "$W" 1600 880

wait $J
pkill -x x11vnc; pkill -x openbox; pkill -x Xvfb; pkill -f websockify
