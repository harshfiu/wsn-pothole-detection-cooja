#!/usr/bin/env python3
"""Generates Cooja .csc files for the pothole WSN.

Node IDs: 1 = sink, 2-7 = roadside gateways, 8+ = vehicles.
"""
import sys
from xml.sax.saxutils import escape

FW = "[CONTIKI_DIR]/examples/pothole-wsn"
GATEWAYS = [(35, 12), (35, -12), (70, 12), (70, -12), (105, 12), (105, -12)]

INTERFACES = """org.contikios.cooja.interfaces.Position
org.contikios.cooja.interfaces.RimeAddress
org.contikios.cooja.interfaces.IPAddress
org.contikios.cooja.interfaces.Mote2MoteRelations
org.contikios.cooja.interfaces.MoteAttributes
org.contikios.cooja.mspmote.interfaces.MspClock
org.contikios.cooja.mspmote.interfaces.MspMoteID
org.contikios.cooja.mspmote.interfaces.SkyButton
org.contikios.cooja.mspmote.interfaces.SkyFlash
org.contikios.cooja.mspmote.interfaces.SkyCoffeeFilesystem
org.contikios.cooja.mspmote.interfaces.Msp802154Radio
org.contikios.cooja.mspmote.interfaces.MspSerial
org.contikios.cooja.mspmote.interfaces.SkyLED
org.contikios.cooja.mspmote.interfaces.MspDebugOutput
org.contikios.cooja.mspmote.interfaces.SkyTemperature""".split()

SCRIPT = """/* Moves the vehicles, injects the gateway failure, records every log line. */
TIMEOUT(%(timeout)d, log.testOK());

var FAIL_AT_MS = %(fail_ms)d;  /* 0 = no failure */
var PAUSE_AT_MS = %(pause_ms)d;  /* 0 = never pause; press Start to continue */
var paused = false;
var VEHICLES = %(vehicles)d;
var FIRST = 8, ROAD = 140, SPEED = 8, PHASE = 35;
var parent = {};
var failed = false;

function move(nowMs) {
  for (var i = 0; i < VEHICLES; i++) {
    var vid = FIRST + i;
    var m = sim.getMoteWithID(vid);
    if (m == null) continue;
    var p = (nowMs / 1000.0 * SPEED + i * PHASE) %% (2 * ROAD);
    var x = p <= ROAD ? p : 2 * ROAD - p;
    m.getInterfaces().getPosition().setCoordinates(x, i %% 2 == 0 ? 2 : -2, 0);
  }
}

/* Removes whichever first-tier gateway gateway 4 is really routing through. */
function failGateway(nowMs) {
  var victim = parent[4];
  if (victim != 2 && victim != 3) victim = 2;
  log.log(nowMs * 1000 + "\\t0\\tFAIL," + victim + "\\n");
  sim.removeMote(sim.getMoteWithID(victim));
}

GENERATE_MSG(200, "tick");
while (true) {
  YIELD();
  if (msg.equals("tick")) {
    var now = sim.getSimulationTimeMillis();
    move(now);
    if (FAIL_AT_MS > 0 && !failed && now >= FAIL_AT_MS) {
      failed = true;
      failGateway(now);
    }
    if (PAUSE_AT_MS > 0 && !paused && now >= PAUSE_AT_MS) {
      paused = true;
      log.log(now * 1000 + "\\t0\\tDEMO_PAUSED\\n");
      /* From a separate thread: stopping waits for the simulation, which is waiting for this script. */
      new java.lang.Thread(function () { sim.stopSimulation(); }).start();
    }
    GENERATE_MSG(200, "tick");
    continue;
  }
  if (msg.startsWith("PARENT,")) {
    var f = msg.split(",");
    parent[parseInt(f[1])] = parseInt(f[2]);
  }
  log.log(time + "\\t" + id + "\\t" + msg + "\\n");
}
"""


def motetype(ident, name, with_source):
    src = ""
    base = f"{FW}/vehicle" if name == "vehicle" else FW
    if with_source:
        src = (f'      <source EXPORT="discard">{base}/{name}.c</source>\n'
               f'      <commands EXPORT="discard">make {name}.sky TARGET=sky</commands>\n')
    ifs = "".join(f"      <moteinterface>{i}</moteinterface>\n" for i in INTERFACES)
    return f"""    <motetype>
      org.contikios.cooja.mspmote.SkyMoteType
      <identifier>{ident}</identifier>
      <description>{name}</description>
{src}      <firmware EXPORT="copy">{base}/{name}.sky</firmware>
{ifs}    </motetype>
"""


def mote(ident, nid, x, y):
    return f"""    <mote>
      <breakpoints />
      <interface_config>
        org.contikios.cooja.interfaces.Position
        <x>{x}</x>
        <y>{y}</y>
        <z>0.0</z>
      </interface_config>
      <interface_config>
        org.contikios.cooja.mspmote.interfaces.MspMoteID
        <id>{nid}</id>
      </interface_config>
      <motetype_identifier>{ident}</motetype_identifier>
    </mote>
"""


def plugin(cls, x, y, w, h, z, inner=""):
    return f"""  <plugin>
    {cls}
{inner}    <width>{w}</width>
    <z>{z}</z>
    <height>{h}</height>
    <location_x>{x}</location_x>
    <location_y>{y}</location_y>
  </plugin>
"""


def build(vehicles, fail_s, seed, dur_s, gui, title):
    script = SCRIPT % {"timeout": dur_s * 1000 + 1000, "fail_ms": fail_s * 1000,
                       "pause_ms": 390000 if gui else 0,
                       "vehicles": vehicles}
    motes = mote("sink", 1, 0.0, 0.0)
    for i, (x, y) in enumerate(GATEWAYS):
        motes += mote("gateway", i + 2, float(x), float(y))
    for i in range(vehicles):
        motes += mote("vehicle", 8 + i, float(i * 35 % 140), 2.0 if i % 2 == 0 else -2.0)

    plugins = plugin("org.contikios.cooja.plugins.ScriptRunner", 900, 420, 600, 400, 5,
                     f"    <plugin_config>\n      <script>{escape(script)}</script>\n"
                     "      <active>true</active>\n    </plugin_config>\n")
    if gui:
        viz = ("    <plugin_config>\n      <moterelations>true</moterelations>\n"
               "      <skin>org.contikios.cooja.plugins.skins.IDVisualizerSkin</skin>\n"
               "      <skin>org.contikios.cooja.plugins.skins.UDGMVisualizerSkin</skin>\n"
               "      <skin>org.contikios.cooja.plugins.skins.GridVisualizerSkin</skin>\n"
               "      <skin>org.contikios.cooja.plugins.skins.TrafficVisualizerSkin</skin>\n"
               "      <viewport>4.0 0.0 0.0 4.0 40.0 220.0</viewport>\n    </plugin_config>\n")
        plugins += plugin("org.contikios.cooja.plugins.Visualizer", 0, 0, 600, 470, 0, viz)
        plugins += plugin("org.contikios.cooja.plugins.SimControl", 640, 0, 260, 180, 4)
        plugins += plugin("org.contikios.cooja.plugins.LogListener", 0, 500, 900, 300, 1,
                          "    <plugin_config>\n      <filter />\n      <formatted_time />\n"
                          "      <coloring />\n    </plugin_config>\n")
        plugins += plugin("org.contikios.cooja.plugins.RadioLogger", 900, 0, 600, 420, 2,
                          "    <plugin_config>\n      <split>150</split>\n"
                          "      <formatted_time />\n      <showdups>false</showdups>\n"
                          "      <hidenodests>false</hidenodests>\n    </plugin_config>\n")
        plugins += plugin("PowerTracker", 640, 180, 260, 320, 3)

    types = (motetype("sink", "sink", gui) + motetype("gateway", "gateway", gui)
             + motetype("vehicle", "vehicle", gui))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<simconf>
  <project EXPORT="discard">[APPS_DIR]/mrm</project>
  <project EXPORT="discard">[APPS_DIR]/mspsim</project>
  <project EXPORT="discard">[APPS_DIR]/avrora</project>
  <project EXPORT="discard">[APPS_DIR]/powertracker</project>
  <simulation>
    <title>{escape(title)}</title>
    <speedlimit>1.0</speedlimit>
    <randomseed>{seed}</randomseed>
    <motedelay_us>1000000</motedelay_us>
    <radiomedium>
      org.contikios.cooja.radiomediums.UDGM
      <transmitting_range>50.0</transmitting_range>
      <interference_range>100.0</interference_range>
      <success_ratio_tx>1.0</success_ratio_tx>
      <success_ratio_rx>0.9</success_ratio_rx>
    </radiomedium>
    <events>
      <logoutput>100000</logoutput>
    </events>
{types}{motes}  </simulation>
{plugins}</simconf>
"""


if __name__ == "__main__":
    # make_csc.py OUT VEHICLES FAIL_S SEED DURATION_S GUI(0/1) TITLE
    out, veh, fail, seed, dur, gui, title = sys.argv[1:8]
    with open(out, "w", newline="\n") as fh:
        fh.write(build(int(veh), int(fail), int(seed), int(dur), gui == "1", title))
