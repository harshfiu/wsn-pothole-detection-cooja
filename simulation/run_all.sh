#!/bin/bash
# Full experiment: 2/4/6/8 vehicles, with and without a gateway failure at
# t=300 s, 5 random seeds each, 600 simulated seconds per run.
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../results/raw"
mkdir -p "$OUT"
for veh in 2 4 6 8; do
  for fail in 0 300; do
    for seed in 1 2 3 4 5; do
      echo "v${veh}_f${fail}_s${seed} $veh $fail $seed 600"
    done
  done
done | xargs -P 6 -L 1 bash "$HERE/run_one.sh"
for d in "$HOME"/runs/v*_f*_s*; do
  cp "$d/COOJA.testlog" "$OUT/$(basename "$d").log"
done
echo ALL_DONE
