#!/bin/bash
# run_one.sh NAME VEHICLES FAIL_S SEED DURATION_S
# Runs one headless Cooja simulation and stores its log in ~/runs/NAME/.
NAME=$1; VEH=$2; FAIL=$3; SEED=$4; DUR=$5
HERE="$(cd "$(dirname "$0")" && pwd)"
RUN="$HOME/runs/$NAME"
rm -rf "$RUN"; mkdir -p "$RUN"; cd "$RUN" || exit 1
python3 "$HERE/make_csc.py" sim.csc "$VEH" "$FAIL" "$SEED" "$DUR" 0 "$NAME"
java -Xmx700m -Djava.awt.headless=true -jar "$HOME/contiki/tools/cooja/dist/cooja.jar" \
  -nogui=sim.csc -contiki="$HOME/contiki" > cooja.out 2>&1
echo "$NAME exit=$? lines=$(wc -l < COOJA.testlog 2>/dev/null)"
