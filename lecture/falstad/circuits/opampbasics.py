"""Falstad examples for chapter 2: Op-Amp Basics."""
import math

import numpy as np

from falstad import Circuit
from _check import approx
from opamps import follower

TITLE = "Op-Amp Basics"

F_C = 1 / (2 * math.pi * 10e3 * 100e-9)      # 159.2 Hz


def amplitude(rec, name):
    return float((np.max(rec[name]) - np.min(rec[name])) / 2)


# ---------------------------------------------------------------------------
# 1. two RC low-passes in cascade, directly and with a buffer in between
# ---------------------------------------------------------------------------
def buffer_rc_cascade():
    """Two RC low-passes 10k / 100 nF at fc = 159 Hz: direct and buffered."""
    c = Circuit("buffer_rc_cascade",
                "Two RC low-passes in cascade at fc: directly and with a buffer")
    # top: second stage loads the first one
    c.text((64, 48), "R = 10k, C = 100 nF, fc = 159 Hz. Directly connected: |H| = 1/3 at fc")
    c.vsrc((96, 208), (96, 112), 1.0, waveform="ac", freq=F_C)
    c.wire((96, 112), (128, 112))
    c.res((128, 112), (224, 112), 10e3)
    c.wire((224, 112), (256, 112))
    c.cap((256, 112), (256, 208), 100e-9)
    c.res((256, 112), (352, 112), 10e3)
    c.wire((352, 112), (384, 112))
    c.cap((384, 112), (384, 208), 100e-9)
    c.wire((96, 208), (256, 208), (384, 208))
    c.gnd((256, 208))
    c.label((256, 112), "V1_direct", d=(0, -16))
    lo_d = c.label((384, 112), "Vout_direct", d=(16, 0))
    # bottom: a voltage follower separates the stages
    c.text((64, 272), "With a voltage follower in between: |H| = 1/2 at fc")
    c.vsrc((96, 432), (96, 336), 1.0, waveform="ac", freq=F_C)
    c.wire((96, 336), (128, 336))
    c.res((128, 336), (224, 336), 10e3)
    c.wire((224, 336), (256, 336))
    c.cap((256, 336), (256, 432), 100e-9)
    c.wire((96, 432), (256, 432))
    c.gnd((256, 432))
    c.label((256, 336), "V1_buffered", d=(0, -16))
    follower(c, 320, 352)                 # input wire starts at (256, 336)
    c.res((448, 352), (544, 352), 10e3)
    c.wire((544, 352), (576, 352))
    c.cap((576, 352), (576, 448), 100e-9)
    c.gnd((576, 448))
    lo_b = c.label((576, 352), "Vout_buffered", d=(16, 0))
    c.scope([lo_d, lo_b], speed=4, vscale=1)

    def check(s):
        s.run(0.030)
        rec = s.run(0.030 + 2 / F_C, record=["V1_direct", "Vout_direct",
                                             "V1_buffered", "Vout_buffered"])
        approx(amplitude(rec, "Vout_direct"), 1 / 3, rel=0.01, what="direct")
        approx(amplitude(rec, "V1_direct"), math.sqrt(2) / 3, rel=0.01,
               what="V1 direct")
        approx(amplitude(rec, "Vout_buffered"), 0.500, rel=0.01, what="buffered")
        approx(amplitude(rec, "V1_buffered"), 1 / math.sqrt(2), rel=0.01,
               what="V1 buffered")
    return c, check


# ---------------------------------------------------------------------------
# 2. potentiometer (10k, middle position) with a 1k load
# ---------------------------------------------------------------------------
def buffer_pot():
    """10k potentiometer at 5 V, middle position, 1k load: direct and buffered."""
    c = Circuit("buffer_pot", "Potentiometer 10k at 5 V with a 1k load: directly and buffered")
    # direct load
    c.text((64, 48), "1k directly at the wiper")
    c.rail((96, 112), 5)
    c.res((96, 112), (96, 208), 5e3)
    c.res((96, 208), (96, 304), 5e3)
    c.gnd((96, 304))
    c.wire((96, 208), (208, 208))
    rl = c.res((208, 208), (208, 304), 1e3)
    c.gnd((208, 304))
    c.label((208, 208), "V_direct", d=(16, -16))
    # buffered load: rail-to-rail op-amp at 0 .. 5 V
    c.text((352, 48), "1k behind a voltage follower (op-amp at 5 V)")
    c.rail((368, 112), 5)
    c.res((368, 112), (368, 208), 5e3)
    c.res((368, 208), (368, 304), 5e3)
    c.gnd((368, 304))
    c.label((368, 208), "V_wiper", d=(-16, -16))
    c.wire((368, 208), (416, 208))
    op = c.opamp((480, 224), swap=True, vmax=5, vmin=0)
    c.wire((416, 208), op.pin["+"])
    c.wire(op.pin["-"], (480, 272), (576, 272), (576, 224))
    c.wire(op.pin["out"], (576, 224), (608, 224))
    rlb = c.res((608, 224), (608, 304), 1e3)
    c.gnd((608, 304))
    c.label((608, 224), "V_buffered", d=(16, -16))
    c.text((112, 144), "5k")
    c.text((112, 256), "5k")
    c.text((224, 256), "RL")
    c.slider(rl, 100, 100e3, "RL direct")

    def check(s):
        s.dc()
        approx(s.v("V_direct"), 2.5 * 1e3 / 3.5e3, rel=0.002, what="direct")  # 0.714 V
        approx(s.v("V_wiper"), 2.500, rel=0.001, what="wiper")
        approx(s.v("V_buffered"), 2.500, rel=0.001, what="buffered")
        approx(s.i_res(rlb), 2.50e-3, rel=0.002, what="op-amp output current")
    return c, check


CIRCUITS = [buffer_rc_cascade, buffer_pot]
