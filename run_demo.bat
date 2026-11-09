@echo off
rem Opens the Cooja demo in a browser tab. Keep this black window open during the demo.
rem Usage: run_demo.bat            (gateway failure at 300 s)
rem        run_demo.bat baseline   (no failure)
set SIM=failure
if /I "%1"=="baseline" set SIM=baseline
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep 25; Start-Process 'http://localhost:6080/vnc.html?autoconnect=1&resize=scale'"
wsl -d Ubuntu-20.04 -u wsn --cd "%~dp0." -- bash demo_vnc.sh %SIM%
