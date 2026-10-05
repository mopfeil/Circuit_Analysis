"""Falstad examples for chapter 7: Sample and Hold.

All circuits sample at fs = 5 Hz with a 10 % duty cycle clock (track window
20 ms, hold 180 ms), as in the capstone task. The switch path has a series
resistor R_S = 1 kOhm (switch resistance of a discrete switch plus a
protective resistor for the op-amp output); the Falstad switch adds
Ron = 20 Ohm.
"""
import math

from falstad import Circuit
from _check import approx

TITLE = "Sample and Hold"

FS = 5.0          # sampling frequency
DUTY = 0.1        # track window = 20 ms
RS = 1e3          # series resistance in the switch path
RON = 20.0        # Falstad analog switch on-resistance


def _clock(c, p, up=False):
    """5 Hz, 10 % duty, 0/5 V clock rail at p."""
    return c.rail(p, 2.5, up=up, waveform="square", freq=FS, bias=2.5,
                  duty=DUTY)


def _follower(c, x, y):
    """Voltage follower; non-inverting input on the signal line y at x,
    output on the signal line y at x+96. Returns (in, out)."""
    op = c.opamp((x, y - 16), swap=False)
    # op.pin['+'] == (x, y), op.pin['-'] == (x, y-32), out == (x+64, y-16)
    j = (x + 80, y - 16)
    c.wire(op.pin["out"], j)
    c.wire(j, (x + 80, y), (x + 96, y))
    c.wire(j, (x + 80, y - 64), (x, y - 64), op.pin["-"])
    return op.pin["+"], (x + 96, y)


def _held(rec, name, t):
    """Value of a recorded signal at time t."""
    i = int(round(t / (rec["t"][1] - rec["t"][0]))) - 1
    return float(rec[name][i])


def sh_basic():
    """Unbuffered S&H: sine in, switch, hold capacitor, staircase out."""
    c = Circuit("sh_basic", "Basic sample and hold: switch and hold capacitor",
                timestep=1e-4)
    c.text((64, 48), "Sample and hold, fs = 5 Hz, track window 20 ms")
    vin = c.rail((96, 192), 1.5, waveform="ac", freq=0.5, bias=2.0)
    c.wire((96, 192), (160, 192), (192, 192))
    lin = c.label((160, 192), "Vin", d=(0, -16))
    c.res((192, 192), (288, 192), RS)
    sw = c.aswitch((288, 192), (352, 192))
    c.wire((352, 192), (448, 192))
    c.cap((448, 192), (448, 288), 1e-6)
    c.gnd((448, 288))
    lh = c.label((448, 192), "Vhold")
    c.wire(sw.pin["ctl"], (320, 240), (320, 272))
    lclk = c.label((320, 240), "CLK", d=(-16, 0))
    _clock(c, (320, 272), up=False)
    c.text((176, 160), "RS = 1k")
    c.text((272, 160), "switch")
    c.text((464, 256), "CH = 1 uF")
    c.text((96, 352), "Vin = 2 V + 1.5 V sin(2 pi 0.5 Hz t)")
    c.scope([lin, lh, lclk], speed=32, vscale=5)

    def check(s):
        r = s.run(1.0, record=["Vin", "Vhold", "CLK"])
        expect = [2.094, 2.956, 3.452, 3.394, 2.804]
        for k, e in enumerate(expect):
            vin_end = 2 + 1.5 * math.sin(2 * math.pi * 0.5 * (0.2 * k + 0.02))
            approx(vin_end, e, rel=1e-3, what="Vin at end of window %d" % k)
            # held value in the middle and at the end of the hold phase
            approx(_held(r, "Vhold", 0.2 * k + 0.10), e, rel=0.005,
                   what="held value %d (mid)" % k)
            approx(_held(r, "Vhold", 0.2 * k + 0.199), e, rel=0.005,
                   what="held value %d (end)" % k)
    return c, check


def sh_acquisition():
    """Charging of the hold capacitor in the track window."""
    c = Circuit("sh_acquisition", "Acquisition: charging CH through RS + Ron",
                timestep=1e-5)
    c.text((64, 48), "Acquisition time: tau = (RS %2B Ron) CH = 1.02 ms")
    c.rail((96, 192), 4.0)
    c.wire((96, 192), (192, 192))
    c.res((192, 192), (288, 192), RS)
    sw = c.aswitch((288, 192), (352, 192))
    c.wire((352, 192), (448, 192))
    c.cap((448, 192), (448, 288), 1e-6)
    c.gnd((448, 288))
    lh = c.label((448, 192), "Vhold")
    c.wire(sw.pin["ctl"], (320, 240), (320, 272))
    lclk = c.label((320, 240), "CLK", d=(-16, 0))
    _clock(c, (320, 272), up=False)
    c.text((176, 160), "RS = 1k")
    c.text((464, 256), "CH = 1 uF")
    c.text((64, 352), "after 2.77 tau = 2.83 ms: within 1/2 LSB (3 bit, 4 V)")
    c.scope([lh, lclk], speed=1, vscale=5)

    def check(s):
        tau = (RS + RON) * 1e-6
        r = s.run(0.025, record=["Vhold"])
        approx(tau, 1.02e-3, what="tau")
        approx(_held(r, "Vhold", tau), 2.528, rel=0.01, what="V(1 tau)")
        t_half = tau * math.log(16)
        approx(t_half, 2.83e-3, rel=0.005, what="t settle")
        approx(_held(r, "Vhold", t_half), 3.75, rel=0.01, what="V(2.77 tau)")
        approx(_held(r, "Vhold", 0.0199), 4.0, rel=0.001, what="V(20 ms)")
        approx(_held(r, "Vhold", 0.025), 4.0, rel=0.001, what="held")
    return c, check


def sh_buffered():
    """Unbuffered vs. buffered S&H, real source (10k) and load (100k)."""
    c = Circuit("sh_buffered", "Why both buffers: unbuffered vs buffered S&H",
                timestep=1e-4)
    c.text((48, 32), "Source with Ri = 10k, load (ADC input) 100k, Vin = 3 V")
    # common source and clock
    src = c.rail((64, 336), 3.0)
    c.slider(src, 0, 4, "Vin")
    c.wire((64, 336), (96, 336))
    lin = c.label((96, 336), "Vin")
    _clock(c, (64, 480), up=False)
    c.wire((64, 480), (96, 480))
    c.label((96, 480), "CLK")
    # --- top: unbuffered
    y = 144
    c.text((176, 80), "unbuffered")
    c.label((176, y), "Vin", d=(-16, 0))
    c.res((176, y), (272, y), 10e3)
    c.wire((272, y), (304, y))
    sw = c.aswitch((304, y), (368, y))
    c.label(sw.pin["ctl"], "CLK", d=(0, 16))
    c.wire((368, y), (464, y), (560, y))
    c.cap((464, y), (464, y + 96), 1e-6)
    c.gnd((464, y + 96))
    c.res((560, y), (560, y + 96), 100e3)
    c.gnd((560, y + 96))
    lu = c.label((560, y), "Vout_unbuf")
    c.text((192, y - 32), "Ri = 10k")
    c.text((576, y + 64), "100k")
    # --- bottom: buffered
    y = 368
    c.text((176, 272), "buffered")
    c.label((176, y), "Vin", d=(-16, 0))
    c.res((176, y), (272, y), 10e3)
    c.wire((272, y), (304, y))
    _i, o = _follower(c, 304, y)
    c.res(o, (496, y), RS)
    sw = c.aswitch((496, y), (560, y))
    c.label(sw.pin["ctl"], "CLK", d=(0, 16))
    c.wire((560, y), (608, y), (640, y))
    c.cap((608, y), (608, y + 96), 1e-6)
    c.gnd((608, y + 96))
    lh = c.label((608, y), "Vhold", d=(0, 16))
    _i, o2 = _follower(c, 640, y)
    c.wire(o2, (800, y))
    c.res((800, y), (800, y + 96), 100e3)
    c.gnd((800, y + 96))
    lb = c.label((800, y), "Vout_buf")
    c.text((688, y + 112), "CH = 1 uF, RS = 1k")
    c.scope([lu, lb], speed=32, vscale=5)

    def check(s):
        r = s.run(0.4, record=["Vout_unbuf", "Vout_buf", "Vhold"])
        tau_t = (10e3 * 100e3 / 110e3) * 1e-6
        v1 = 3 * 100 / 110 * (1 - math.exp(-0.02 / tau_t))
        approx(v1, 2.425, rel=0.002, what="unbuffered after window (calc)")
        approx(_held(r, "Vout_unbuf", 0.02), 2.425, rel=0.01,
               what="unbuffered after window")
        approx(_held(r, "Vout_unbuf", 0.1999), 0.401, rel=0.02,
               what="unbuffered end of hold")
        approx(_held(r, "Vout_buf", 0.02), 3.0, rel=0.001, what="buffered")
        approx(_held(r, "Vout_buf", 0.1999), 3.0, rel=0.001,
               what="buffered end of hold")
    return c, check


def sh_capsize():
    """Hold capacitor too small (droop), right, too large (no charge)."""
    c = Circuit("sh_capsize", "Hold capacitor: too small, right, too large",
                timestep=1e-4)
    c.text((48, 32), "Leakage 50 nA (exaggerated), RS = 1k, Vin = 3 V, fs = 5 Hz")
    src = c.rail((64, 224), 3.0)
    c.wire((64, 224), (96, 224))
    _i, o = _follower(c, 96, 224)
    c.wire(o, (224, 224))
    c.label((224, 224), "Vbuf")
    _clock(c, (64, 384), up=False)
    c.wire((64, 384), (96, 384))
    c.label((96, 384), "CLK")
    elms = []
    for k, (cv, name, txt) in enumerate([(10e-9, "V_10n", "CH = 10 nF"),
                                         (1e-6, "V_1u", "CH = 1 uF"),
                                         (100e-6, "V_100u", "CH = 100 uF")]):
        x = 320 + 224 * k
        y = 128
        c.label((x, y), "Vbuf", d=(-16, 0))
        c.res((x, y), (x + 64, y), RS)
        sw = c.aswitch((x + 64, y), (x + 128, y))
        c.label(sw.pin["ctl"], "CLK", d=(0, 16))
        c.wire((x + 128, y), (x + 160, y), (x + 192, y))
        c.cap((x + 160, y), (x + 160, y + 128), cv)
        c.wire((x + 192, y), (x + 192, y + 32))
        c.isrc((x + 192, y + 32), (x + 192, y + 128), 50e-9)
        c.wire((x + 160, y + 128), (x + 192, y + 128))
        c.gnd((x + 160, y + 128))
        elms.append(c.label((x + 160, y), name, d=(0, -16)))
        c.text((x, y + 160), txt)
    c.text((320, 336), "droop 0.9 V")
    c.text((544, 336), "droop 9 mV")
    c.text((768, 336), "18 % per sample")
    del src
    c.scope(elms, speed=32, vscale=5)

    def check(s):
        r = s.run(1.0, record=["V_10n", "V_1u", "V_100u"])
        approx(50e-9 / 10e-9 * 0.18, 0.9, what="droop 10n (calc)")
        approx(_held(r, "V_10n", 0.02), 3.0, rel=0.002, what="10n after window")
        approx(_held(r, "V_10n", 0.1999), 2.1, rel=0.01, what="10n end of hold")
        approx(_held(r, "V_1u", 0.02) - _held(r, "V_1u", 0.1999), 0.009,
               rel=0.05, what="droop 1u")
        a = 1 - math.exp(-0.02 / ((RS + RON) * 100e-6))
        approx(a, 0.178, rel=0.01, what="fraction per sample")
        approx(_held(r, "V_100u", 0.1), 0.534, rel=0.02, what="100u sample 1")
        approx(_held(r, "V_100u", 0.9), 1.876, rel=0.02, what="100u sample 5")
    return c, check


def sh_staircase():
    """Buffered S&H sampling a ramp (triangle): staircase output."""
    c = Circuit("sh_staircase", "Buffered sample and hold with a ramp input",
                timestep=1e-4)
    c.text((48, 32), "Buffered S&H: follower - RS - switch - CH - follower")
    vin = c.rail((64, 208), 2.0, waveform="triangle", freq=0.5, bias=2.0)
    c.wire((64, 208), (96, 208), (128, 208))
    lin = c.label((96, 208), "Vin", d=(0, 16))
    _i, o = _follower(c, 128, 208)
    c.res(o, (320, 208), RS)
    sw = c.aswitch((320, 208), (384, 208))
    c.wire((384, 208), (432, 208), (480, 208))
    c.cap((432, 208), (432, 304), 1e-6)
    c.gnd((432, 304))
    c.wire(sw.pin["ctl"], (352, 256), (352, 288))
    lclk = c.label((352, 256), "CLK", d=(-16, 0))
    _clock(c, (352, 288), up=False)
    _i, o2 = _follower(c, 480, 208)
    c.wire(o2, (640, 208))
    lo = c.label((640, 208), "Vout")
    c.text((64, 352), "ramp 4 V/s: steps of 0.8 V every 200 ms")
    c.text((400, 336), "CH = 1 uF")
    del vin
    c.scope([lin, lo, lclk], speed=32, vscale=5)

    def check(s):
        r = s.run(1.0, record=["Vin", "Vout"])
        for k in range(5):
            e = 0.08 + 0.8 * k
            approx(_held(r, "Vout", 0.2 * k + 0.1), e, absol=0.01, rel=0,
                   what="step %d" % k)
    return c, check


def sh_pedestal():
    """Charge injection through the gate-drain capacitance of the switch."""
    c = Circuit("sh_pedestal", "Pedestal error by charge injection",
                timestep=1e-5)
    c.text((48, 32), "Charge injection: Cgd = 10 pF couples the clock edge into CH")
    c.rail((64, 208), 2.0)
    c.wire((64, 208), (96, 208))
    c.label((96, 208), "Vin")
    _clock(c, (64, 400), up=False)
    c.wire((64, 400), (96, 400))
    c.label((96, 400), "CLK")
    elms = []
    for k, (ch, name, txt) in enumerate([(1e-9, "Vhold_1n", "CH = 1 nF: -49.5 mV"),
                                         (100e-9, "Vhold_100n", "CH = 100 nF: -0.5 mV")]):
        x = 224 + 320 * k
        y = 160
        c.label((x, y), "Vin", d=(-16, 0))
        c.res((x, y), (x + 64, y), RS)
        sw = c.aswitch((x + 64, y), (x + 128, y))
        c.wire(sw.pin["ctl"], (x + 96, y + 64))
        c.label((x + 96, y + 64), "CLK", d=(0, 16))
        c.wire((x + 128, y), (x + 160, y), (x + 192, y))
        c.cap((x + 96, y + 64), (x + 160, y + 64), 10e-12)
        c.wire((x + 160, y + 64), (x + 160, y))
        c.cap((x + 192, y), (x + 192, y + 128), ch)
        c.gnd((x + 192, y + 128))
        elms.append(c.label((x + 192, y), name, d=(0, -16)))
        c.text((x, y + 176), txt)
        c.text((x + 112, y + 96), "Cgd")
    c.scope(elms, speed=8, vscale=2)

    def check(s):
        r = s.run(0.03, record=["Vhold_1n", "Vhold_100n"])
        approx(_held(r, "Vhold_1n", 0.0195), 2.0, rel=1e-3, what="tracking")
        ped = -5.0 * 10e-12 / (10e-12 + 1e-9)
        approx(ped, -0.0495, rel=0.01, what="pedestal (calc)")
        approx(_held(r, "Vhold_1n", 0.025) - 2.0, -0.0495, rel=0.03,
               what="pedestal 1n")
        approx(_held(r, "Vhold_100n", 0.025) - 2.0, -0.0005, rel=0.05,
               what="pedestal 100n")
    return c, check


CIRCUITS = [sh_basic, sh_acquisition, sh_buffered, sh_capsize, sh_staircase,
            sh_pedestal]
