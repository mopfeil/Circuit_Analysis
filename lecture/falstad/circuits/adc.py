"""Falstad examples for chapter 8: Analog-to-Digital Conversion.

The flash converter is the one of the capstone task: reference ladder
8 x 1 kOhm from 4 V (taps 0.5 .. 3.5 V), comparators Ck = (Vin > k*0.5 V),
thermometer-to-binary encoder
    B2 = C4
    B1 = (C2 AND NOT C4) OR C6
    B0 = (C1 AND NOT C2) OR (C3 AND NOT C4) OR (C5 AND NOT C6) OR C7
and one LED with its own 330 Ohm resistor per output.
"""
import math

from falstad import Circuit
from _check import approx

TITLE = "Analog-to-Digital Conversion"

RLED = 330.0


def _settle(s, n=10):
    """Run a few steps so that the logic (one step delay per gate) settles."""
    for _ in range(n):
        s.step()


def _at(rec, name, t):
    i = int(round(t / (rec["t"][1] - rec["t"][0]))) - 1
    return float(rec[name][i])


def _edges(x, thr=2.5):
    b = x > thr
    return int(sum(b[1:] != b[:-1]))


# ---------------------------------------------------------------------------
def comparator_hyst():
    """Comparator without and with hysteresis, noisy input."""
    c = Circuit("comparator_hyst", "Comparator with and without hysteresis",
                timestep=1e-4)
    c.text((48, 32), "Input: 1 Hz triangle 0..4 V plus 50 Hz interference 0.2 V")
    # input: triangle in series with a 50 Hz source
    c.vsrc((64, 400), (64, 304), 2.0, waveform="triangle", freq=1.0, bias=2.0)
    c.vsrc((64, 304), (64, 208), 0.2, waveform="ac", freq=50, phase=0.5)
    c.gnd((64, 400))
    c.wire((64, 208), (64, 176), (96, 176))
    lin = c.label((96, 176), "Vin")
    # reference 2 V from 5 V
    c.rail((160, 448), 5.0)
    c.res((160, 448), (160, 528), 15e3)
    c.res((160, 528), (160, 608), 10e3)
    c.gnd((160, 608))
    c.wire((160, 528), (192, 528))
    c.label((192, 528), "Vref")
    c.text((176, 480), "15k")
    c.text((176, 560), "10k")
    # plain comparator: + = Vin (bottom), - = Vref (top)
    k1 = c.comparator((320, 144))
    c.label(k1.pin["-"], "Vref", d=(-16, 0))
    c.label(k1.pin["+"], "Vin", d=(-16, 0))
    c.wire(k1.pin["out"], (448, 144), (480, 144))
    lc = c.label((480, 144), "Vcomp")
    c.text((304, 80), "no hysteresis")
    # Schmitt trigger
    k2 = c.comparator((400, 336))
    c.label(k2.pin["-"], "Vref", d=(-16, 0))
    c.label((208, 352), "Vin", d=(-16, 0))
    c.res((208, 352), (336, 352), 10e3)
    c.wire((336, 352), (368, 352), k2.pin["+"])
    c.wire((368, 352), (368, 432))
    c.res((368, 432), (528, 432), 100e3)
    c.wire((528, 432), (528, 336))
    c.wire(k2.pin["out"], (528, 336), (560, 336))
    ls = c.label((560, 336), "Vschmitt")
    c.text((240, 320), "R1 = 10k")
    c.text((400, 464), "R2 = 100k")
    c.text((304, 272), "with hysteresis: VT%2B = 2.2 V, VT- = 1.7 V")
    c.scope([lin, lc], speed=16, vscale=5)
    c.scope([lin, ls], speed=16, vscale=5)

    def check(s):
        r = s.run(1.0, record=["Vin", "Vcomp", "Vschmitt"])
        approx(s.v("Vref"), 2.0, what="Vref")
        n_plain = _edges(r["Vcomp"])
        n_schmitt = _edges(r["Vschmitt"])
        if n_plain != 10:
            raise AssertionError("plain comparator: %d edges, expected 10" % n_plain)
        if n_schmitt != 2:
            raise AssertionError("Schmitt trigger: %d edges, expected 2" % n_schmitt)
        b = r["Vschmitt"] > 2.5
        i_up = int(next(i for i in range(1, len(b)) if b[i] and not b[i - 1]))
        i_dn = int(next(i for i in range(1, len(b)) if b[i - 1] and not b[i]))
        approx(r["Vin"][i_up], 2.2, rel=0.01, what="VT+")
        approx(r["Vin"][i_dn], 1.7, rel=0.01, what="VT-")
    return c, check


# ---------------------------------------------------------------------------
def _ladder_and_comparators(c, n, x0=96, y_top=112, dy=80, vref=4.0,
                            r=1e3, xc=272):
    """Reference ladder of n resistors from vref (top) to ground and
    n-1 comparators Ck = (Vin > k*vref/n). Labels C1..C(n-1)."""
    ybot = y_top + n * dy
    c.rail((x0, y_top), vref)
    for i in range(n):
        c.res((x0, y_top + i * dy), (x0, y_top + (i + 1) * dy), r)
    c.gnd((x0, ybot))
    c.text((x0 - 80, y_top - 48), "Vref = %g V" % vref)
    outs = {}
    for k in range(1, n):
        y = ybot - k * dy                # tap k: k*vref/n
        comp = c.comparator((xc, y + 16))
        c.wire((x0, y), comp.pin["-"])
        c.label(comp.pin["+"], "Vin", d=(-16, 0))
        o = (xc + 96, y + 16)
        c.wire(comp.pin["out"], o)
        outs[k] = c.label(o, "C%d" % k, d=(0, -16))
        c.text((x0 + 24, y - 8), "%g V" % (k * vref / n))
    return outs


def _led(c, p, name, length=96):
    """Label name -> 330 Ohm -> LED -> ground, horizontal at p."""
    x, y = p
    c.label(p, name, d=(-16, 0))
    rr = c.res((x, y), (x + length, y), RLED)
    c.led((x + length, y), (x + length + 64, y))
    c.gnd((x + length + 64, y))
    return rr


def _encoder3(c, x, y):
    """Thermometer-to-binary encoder of the capstone (labels in/out)."""
    # inverters
    for i, k in enumerate((2, 4, 6)):
        yy = y + 48 * i
        inv = c.inverter((x, yy))
        c.label(inv.pin["in"], "C%d" % k, d=(-16, 0))
        c.label(inv.pin["out"], "nC%d" % k)
    # AND gates
    ands = [("C2", "nC4", "a24"), ("C1", "nC2", "a12"),
            ("C3", "nC4", "a34"), ("C5", "nC6", "a56")]
    for i, (p, q, o) in enumerate(ands):
        yy = y + 64 * i
        g = c.gate("and", (x + 144, yy))
        c.label(g.pin["in"][1], p, d=(-16, 0))   # upper input
        c.label(g.pin["in"][0], q, d=(-16, 0))   # lower input
        c.label(g.pin["out"], o)
    # OR gates
    g = c.gate("or", (x + 304, y))
    c.label(g.pin["in"][1], "a24", d=(-16, 0))
    c.label(g.pin["in"][0], "C6", d=(-16, 0))
    c.label(g.pin["out"], "B1")
    g = c.gate("or", (x + 304, y + 144), n=4)
    for pin, nm in zip(g.pin["in"][::-1], ("a12", "a34", "a56", "C7")):
        c.label(pin, nm, d=(-16, 0))
    c.label(g.pin["out"], "B0")
    # B2 = C4 (a wire between two labels)
    c.label((x + 304, y + 272), "C4", d=(-16, 0))
    c.wire((x + 304, y + 272), (x + 368, y + 272))
    c.label((x + 368, y + 272), "B2")
    c.text((x, y - 64), "Thermometer-to-binary encoder")


def flash2():
    """2-bit flash converter."""
    c = Circuit("flash2", "2-bit flash converter")
    c.text((48, 32), "2-bit flash ADC: Vref = 4 V, LSB = 1 V")
    src = c.rail((176, 96), 2.5)
    c.slider(src, 0, 4, "Vin")
    c.wire((176, 96), (208, 96))
    c.label((208, 96), "Vin")
    _ladder_and_comparators(c, 4, y_top=128)
    # encoder: B1 = C2, B0 = (C1 AND NOT C2) OR C3
    x, y = 496, 192
    inv = c.inverter((x, y))
    c.label(inv.pin["in"], "C2", d=(-16, 0))
    c.label(inv.pin["out"], "nC2")
    g = c.gate("and", (x, y + 96))
    c.label(g.pin["in"][1], "C1", d=(-16, 0))
    c.label(g.pin["in"][0], "nC2", d=(-16, 0))
    c.label(g.pin["out"], "a12")
    g = c.gate("or", (x + 160, y + 96))
    c.label(g.pin["in"][1], "a12", d=(-16, 0))
    c.label(g.pin["in"][0], "C3", d=(-16, 0))
    c.label(g.pin["out"], "B0")
    c.label((x + 160, y + 192), "C2", d=(-16, 0))
    c.wire((x + 160, y + 192), (x + 224, y + 192))
    c.label((x + 224, y + 192), "B1")
    c.text((x, y - 64), "B1 = C2, B0 = C1 nC2 %2B C3")

    def check(s):
        src_ = src
        expect = {0.5: (0, 0), 1.5: (0, 1), 2.5: (1, 0), 3.5: (1, 1)}
        for v, (b1, b0) in expect.items():
            src_.params[2] = v
            _settle(s)
            got = (int(s.v("B1") > 2.5), int(s.v("B0") > 2.5))
            if got != (b1, b0):
                raise AssertionError("Vin=%g: code %s, expected %s" % (v, got, (b1, b0)))
        approx(s.v("C3"), 5.0, what="C3 at 3.5 V")
    return c, check


def _flash3_circuit(name, title, input_kind="slider"):
    c = Circuit(name, title, timestep=1e-3 if input_kind == "slider" else 1e-3)
    c.text((48, 24), "3-bit flash ADC: 8 x 1k from 4 V, LSB = 0.5 V, LEDs with 330 Ohm")
    if input_kind == "slider":
        src = c.rail((176, 80), 2.6)
        c.slider(src, 0, 4, "Vin")
    else:
        src = c.rail((176, 80), 2.0, waveform="triangle", freq=0.25, bias=2.0)
    c.wire((176, 80), (208, 80))
    lin = c.label((208, 80), "Vin")
    outs = _ladder_and_comparators(c, 8, y_top=128)
    return c, src, outs, lin


def flash3():
    """3-bit flash converter with encoder, LED bar graph and binary LEDs."""
    c, src, outs, _lin = _flash3_circuit("flash3", "3-bit flash converter with encoder and LEDs")
    # LED bar graph C7 (top) .. C1 (bottom)
    leds = {}
    for k in range(1, 8):
        y = 128 + (8 - k) * 80 + 16
        leds["C%d" % k] = _led(c, (448, y), "C%d" % k)
    c.text((448, 96), "bar graph")
    _encoder3(c, 800, 192)
    for i, b in enumerate(("B2", "B1", "B0")):
        leds[b] = _led(c, (848, 560 + 64 * i), b)
    c.text((848, 528), "binary output B2 B1 B0")

    def check(s):
        for code in range(8):
            v = 0.25 + 0.5 * code
            src.params[2] = v
            _settle(s)
            therm = [int(s.v("C%d" % k) > 2.5) for k in range(1, 8)]
            if therm != [1] * code + [0] * (7 - code):
                raise AssertionError("Vin=%g: thermometer %s" % (v, therm))
            got = 4 * (s.v("B2") > 2.5) + 2 * (s.v("B1") > 2.5) + (s.v("B0") > 2.5)
            if got != code:
                raise AssertionError("Vin=%g: code %d, expected %d" % (v, got, code))
        # tap voltages of the ladder (x0 = 96, ybot = 768, dy = 80)
        for k in range(1, 8):
            approx(s.v((96, 768 - 80 * k)), 0.5 * k, what="tap %d" % k)
        approx(s.i_res([e for e in c.elms if e.kind == "r"][0]), 0.5e-3,
               what="ladder current")
        # LED current with 330 Ohm (Vin = 3.75 V: all on)
        i_led = s.i_res(leds["C1"])
        approx(i_led, 9.8e-3, rel=0.01, what="LED current")
        approx(5.0 - i_led * RLED, 1.77, rel=0.01, what="LED forward voltage")
        src.params[2] = 2.6
        _settle(s)
        approx(s.v("B2") + s.v("B0") - s.v("B1"), 10.0, what="code 101 at 2.6 V")
    return c, check


# ---------------------------------------------------------------------------
def _r2r(c, x, y, bits, r=10e3, load=None):
    """3-bit R-2R ladder; bits = label names (LSB first). Output node at
    (x + 3*128 - 128, y) labelled 'Vdac'. Bit inputs come from below."""
    # termination 2R to ground at the left end
    nodes = [(x + 128 * i, y) for i in range(3)]
    c.wire((x - 64, y), nodes[0])
    c.res((x - 64, y), (x - 64, y + 96), 2 * r)
    c.gnd((x - 64, y + 96))
    for i in range(2):
        c.res(nodes[i], nodes[i + 1], r)
    for n, b in zip(nodes, bits):
        c.res(n, (n[0], n[1] + 96), 2 * r)
        c.label((n[0], n[1] + 96), b, d=(0, 16))
    out = nodes[-1]
    c.wire(out, (out[0] + 64, out[1]))
    o = (out[0] + 64, out[1])
    if load:
        c.wire(o, (o[0] + 32, o[1]))
        o2 = (o[0] + 32, o[1])
        c.res(o2, (o2[0], o2[1] + 96), load)
        c.gnd((o2[0], o2[1] + 96))
        return o2
    return o


def r2r_dac():
    """3-bit R-2R DAC driven by a binary counter (square wave sources)."""
    c = Circuit("r2r_dac", "3-bit R-2R DAC driven by logic levels", timestep=1e-3)
    c.text((48, 32), "R-2R DAC, R = 10k: Vout = 5 V * code / 8")
    for i, f in enumerate((1.0, 0.5, 0.25)):
        p = (96, 128 + 64 * i)
        c.rail(p, 2.5, waveform="square", freq=f, bias=2.5, phase=math.pi,
               label_dir=(-32, 0))
        c.wire(p, (128, p[1]))
        c.label((128, p[1]), "B%d" % i)
        c.text((p[0] - 80, p[1] - 24), "B%d %g Hz" % (i, f))
    o = _r2r(c, 256, 160, ["B0", "B1", "B2"])
    c.wire(o, (576, 160), (608, 160))
    c.label((576, 160), "Vdac", d=(0, -16))
    c.text((304, 128), "R")
    c.text((432, 128), "R")
    c.text((176, 208), "2R")
    # follower
    op = c.opamp((608, 176), swap=True)    # + on top at (608,160)
    j = (688, 176)
    c.wire(op.pin["out"], j, (720, 176))
    c.wire(j, (688, 240), (608, 240), op.pin["-"])
    lo = c.label((720, 176), "Vout")
    c.scope([lo], speed=16, vscale=5)

    def check(s):
        r = s.run(4.0, record=["Vout", "B0", "B1", "B2"])
        for code in range(8):
            t = 0.25 + 0.5 * code
            approx(_at(r, "Vout", t), 0.625 * code, absol=1e-3, rel=1e-3,
                   what="Vout code %d" % code)
    return c, check


def quant_error():
    """3-bit flash + R-2R DAC: quantized ramp and quantization error."""
    c, src, outs, lin = _flash3_circuit("quant_error",
                                        "Quantization: flash ADC and R-2R DAC",
                                        input_kind="ramp")
    _encoder3(c, 512, 192)
    c.text((864, 432), "R-2R DAC with 4R load: 0.5 V per code")
    o = _r2r(c, 864, 512, ["B0", "B1", "B2"], load=40e3)
    c.wire(o, (o[0] + 64, o[1]))
    lq = c.label((o[0] + 64, o[1]), "Vq")
    c.scope([lin, lq], speed=16, vscale=5)

    def check(s):
        r = s.run(2.0, record=["Vin", "Vq"])
        err = r["Vin"] - r["Vq"]
        # ignore the steps where the code just changed (one step logic delay)
        ok = (err > -0.01) & (err < 0.51)
        if ok.mean() < 0.98:
            raise AssertionError("quantization error outside 0..1 LSB")
        approx(_at(r, "Vq", 0.9), 1.5, absol=0.01, what="Vq at Vin = 1.8 V")
        approx(_at(r, "Vq", 1.99), 3.5, absol=0.01, what="Vq at Vin = 3.98 V")
    return c, check


# ---------------------------------------------------------------------------
def alias50():
    """Sampling 50 Hz interference at 5 Hz and at 4.9 Hz."""
    c = Circuit("alias50", "Aliasing: 50 Hz sampled at 5 Hz and at 4.9 Hz",
                timestep=2e-5, speed=50)
    c.text((48, 32), "Signal 2 V DC %2B 0.5 V 50 Hz hum, track window 1 ms")
    c.rail((64, 224), 0.5, waveform="ac", freq=50, bias=2.0)
    c.wire((64, 224), (96, 224))
    lin = c.label((96, 224), "Vin")
    elms = []
    for k, (fs, name) in enumerate([(5.0, "Vs_5Hz"), (4.9, "Vs_4.9Hz")]):
        x = 224
        y = 160 + 192 * k
        c.label((x, y), "Vin", d=(-16, 0))
        c.res((x, y), (x + 96, y), 1e3)
        sw = c.aswitch((x + 96, y), (x + 160, y))
        c.wire(sw.pin["ctl"], (sw.pin["ctl"][0], y + 64))
        c.rail((sw.pin["ctl"][0], y + 64), 2.5, up=False, waveform="square",
               freq=fs, bias=2.5, duty=0.005)
        c.wire((x + 160, y), (x + 224, y), (x + 256, y))
        c.cap((x + 224, y), (x + 224, y + 96), 100e-9)
        c.gnd((x + 224, y + 96))
        elms.append(c.label((x + 256, y), name))
        c.text((x + 288, y + 48), "fs = %g Hz" % fs)
    c.text((48, 576), "5 Hz: alias at 0 Hz (constant offset); 4.9 Hz: alias at 1 Hz")
    c.scope([lin] + elms, speed=256, vscale=5)

    def check(s):
        r = s.run(0.75, record=["Vs_5Hz", "Vs_4.9Hz"])
        lag = math.atan(2 * math.pi * 50 * 1e-4)

        def expect(t_end):
            return 2 + 0.5 * math.sin(2 * math.pi * 50 * t_end - lag)
        approx(expect(0.001), 2.140, rel=0.002, what="expected 5 Hz value")
        for k in range(4):
            approx(_at(r, "Vs_5Hz", 0.2 * k + 0.1), 2.140, rel=0.005,
                   what="5 Hz sample %d" % k)
        vals = []
        for k in range(4):
            te = k / 4.9 + 0.005 / 4.9
            v = _at(r, "Vs_4.9Hz", k / 4.9 + 0.1)
            approx(v, expect(te), rel=0.01, what="4.9 Hz sample %d" % k)
            vals.append(v)
        approx(vals[1], 2.500, rel=0.01, what="4.9 Hz sample 1")
    return c, check


CIRCUITS = [comparator_hyst, flash2, flash3, alias50, r2r_dac, quant_error]
