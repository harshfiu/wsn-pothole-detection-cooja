#!/bin/bash
# Mirrors the project into the Contiki tree (Contiki cannot build from paths with spaces)
# and builds all firmware.
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/contiki/examples/pothole-wsn"
mkdir -p "$DST/vehicle"
rm -f "$DST"/vehicle.c "$DST"/vehicle.sky
cp "$SRC"/firmware/Makefile "$SRC"/firmware/*.c "$SRC"/firmware/*.h "$DST"/
cp "$SRC"/firmware/vehicle/* "$DST"/vehicle/
cp "$SRC"/simulation/*.csc "$DST"/ 2>/dev/null
find "$DST" -maxdepth 2 -type f \( -name Makefile -o -name '*.c' -o -name '*.h' \) -exec sed -i 's/\r$//' {} +
cd "$DST" && make TARGET=sky sink.sky gateway.sky 2>&1 | grep -E "error|Error|overflow"
cd "$DST/vehicle" && make TARGET=sky vehicle.sky 2>&1 | grep -E "error|Error|overflow"
msp430-size "$DST"/*.sky "$DST"/vehicle/*.sky
