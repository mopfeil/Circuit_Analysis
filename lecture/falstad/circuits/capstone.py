"""Falstad examples for chapter 9: From Sensor to Digital Value (capstone).

Design (see Capstone.tex):
  sensor     Pt100, R(T) = 100 Ohm (1 + 0.00385/K T), 0..100 degC -> 100..138.5 Ohm
  bridge     fed from the 4.00 V reference (also feeds the ADC ladder:
             ratiometric), R1 = R3 = 3.9 kOhm, R4 = 100 Ohm
             -> sensor current 1.00 mA at 0 degC, bridge output 0..37.18 mV
  INA        two followers + difference amplifier, G1 = 100k/10k = 10
  gain stage non-inverting, G2 = 1 + 97.6k/10k = 10.76 -> 0..4.00 V
  low-pass   R = 6.8 kOhm, C = 10 uF, fc = 2.34 Hz, follower
  S&H        follower, analog switch (20 Ohm), C_H = 1 uF, follower;
             clock 5 Hz, 10 % duty (20 ms sampling window)
  flash ADC  8 x 1 kOhm ladder from 4.00 V, 7 comparators (0/5 V)
  encoder    B2 = C4, B1 = C2 !C4 + C6, B0 = C1 !C2 + C3 !C4 + C5 !C6 + C7
  display    10 LEDs with 330 Ohm each
"""
import math
from falstad import Circuit
from _check import approx

TITLE = "From Sensor to Digital Value"

VREF = 4.0
R0, ALPHA = 100.0, 0.00385
R1 = R3 = 3900.0
R4 = 100.0
G1 = 100e3 / 10e3
RF2, RG2 = 97.6e3, 10e3
G2 = 1 + RF2 / RG2
RLP, CLP = 6.8e3, 10e-6
CH = 1e-6
FS = 5.0
NOISE = 0.005
NOISE_PHASE = math.pi / 2       # noise maximum at the end of the sampling window
TARGETS = [0.25, 0.75, 1.75, 2.25, 3.25, 3.75]


def r_sensor(t):
    return R0 * (1 + ALPHA * t)


def v_bridge(r):
    return VREF * (r / (R1 + r) - R4 / (R3 + R4))


def v_cond(r):
    return G1 * G2 * v_bridge(r)


def r_for_vcond(v):
    """Sensor resistance that gives the conditioned voltage v (inverse)."""
    x = v / (G1 * G2 * VREF) + R4 / (R3 + R4)      # = r/(R1+r)
    return x * R1 / (1 - x)


def t_for_r(r):
    return (r / R0 - 1) / ALPHA


def code(v):
    return max(0, min(7, int(v / 0.5)))


# ---------------------------------------------------------------------------
def _follower(c, x, y, vin, vout):
    """Unity-gain buffer: + input at (x, y+16) from label vin."""
    op = c.opamp((x, y))
    o = op.pin["out"]
    c.wire(op.pin["-"], (x, y - 48), (o[0], y - 48), o)
    c.label((x - 32, y + 16), vin, d=(-16, 0))
    c.wire((x - 32, y + 16), op.pin["+"])
    c.wire(o, (o[0] + 32, y))
    c.label((o[0] + 32, y), vout)
    return op


def build(name, title, with_filter=True):
    c = Circuit(name, title, timestep=1e-4, speed=40, voltage_range=5)

    # ------------------------------------------------------------ stage 1
    c.box((32, 32), (1088, 512))
    c.text((48, 56), "1  Conditioning: Pt100 bridge, INA (G=10), gain stage (G=10.76)")
    # reference (also used by the ADC ladder)
    c.rail((96, 112), VREF, up=True)
    c.label((96, 112), "VREF", d=(0, 16))
    c.wire((96, 112), (160, 112), (288, 112))
    # left arm: R1, sensor (slider), 50 Hz noise in series
    c.res((160, 112), (160, 240), R1)
    sensor = c.res((160, 240), (160, 336), r_sensor(0))
    c.vsrc((160, 432), (160, 336), NOISE, waveform="ac", freq=50,
           phase=NOISE_PHASE)
    c.gnd((160, 432))
    c.text((176, 300), "Pt100")
    c.text((176, 400), "50 Hz, 5 mV")
    c.label((160, 240), "VS", d=(-32, 0))
    # right arm: R3, R4
    c.res((288, 112), (288, 240), R3)
    c.res((288, 240), (288, 432), R4)
    c.gnd((288, 432))
    c.label((288, 240), "VR", d=(32, 0))
    # instrumentation amplifier: buffers + difference amplifier
    _follower(c, 432, 192, "VS", "VSB")
    _follower(c, 432, 368, "VR", "VRB")
    da = c.opamp((704, 288))
    m, p, o = da.pin["-"], da.pin["+"], da.pin["out"]
    c.label((560, 272), "VRB", d=(-16, 0))
    c.res((560, 272), m, 10e3)
    c.wire(m, (640, 272))
    c.wire((640, 272), (640, 208))
    c.res((640, 208), (768, 208), 100e3)
    c.wire((768, 208), o)
    c.label((560, 304), "VSB", d=(-16, 0))
    c.res((560, 304), p, 10e3)
    c.wire(p, (656, 304))
    c.res((656, 304), (656, 432), 100e3)
    c.gnd((656, 432))
    c.wire(o, (800, 288))
    c.label((800, 288), "VDIFF", d=(0, -16))
    # gain stage (non-inverting), trimmed with RF
    gs = c.opamp((880, 304), swap=True)            # + on top
    c.wire((800, 288), gs.pin["+"])
    c.wire(gs.pin["-"], (880, 368))
    c.res((880, 368), (880, 464), RG2)
    c.gnd((880, 464))
    c.wire((880, 368), (944, 368))
    c.res((944, 368), (1008, 368), RF2)
    c.wire((1008, 368), (1008, 304))
    c.wire(gs.pin["out"], (1008, 304))
    c.wire((1008, 304), (1040, 304))
    c.label((1040, 304), "VCOND")
    c.slider(sensor, 100, 138.5, "Sensor R (Pt100, 0..100 C)")

    # ------------------------------------------------------------ stage 2
    c.box((1120, 32), (1504, 512))
    c.text((1136, 56), "2  Anti-aliasing low-pass, fc = 2.34 Hz")
    c.label((1168, 240), "VCOND", d=(-16, 0))
    c.res((1168, 240), (1264, 240), RLP)
    c.wire((1264, 240), (1264, 256))
    c.cap((1264, 256), (1264, 352), CLP)
    c.gnd((1264, 352))
    c.wire((1264, 240), (1296, 240))
    c.label((1296, 240), "VF")
    _follower(c, 1360, 224, "VF", "VAA")
    if not with_filter:
        c.text((1136, 448), "NOT USED: S&H takes VCOND directly")

    # ------------------------------------------------------------ stage 3
    c.box((1536, 32), (2080, 512))
    c.text((1552, 56), "3  Sample and hold, fs = 5 Hz (20 ms window)")
    sh_in = "VAA" if with_filter else "VCOND"
    _follower(c, 1632, 224, sh_in, "VSH")
    sw = c.aswitch((1760, 240), (1824, 240))
    c.label((1760, 240), "VSH", d=(-16, 0))
    c.wire((1824, 240), (1856, 240))
    c.cap((1856, 240), (1856, 336), CH)
    c.gnd((1856, 336))
    c.wire((1856, 240), (1888, 240))
    c.label((1888, 240), "VC")
    c.rail(sw.pin["ctl"], 2.5, up=False, waveform="square", freq=FS,
           bias=2.5, duty=0.1)
    c.text((1680, 384), "clock 0/5 V, 5 Hz, 10 %")
    _follower(c, 1952, 224, "VC", "VHOLD")

    # ------------------------------------------------------------ stage 4
    c.box((32, 544), (1088, 1120))
    c.text((48, 568), "4  Flash ADC: 8 x 1k ladder from 4.00 V, 7 comparators")
    c.label((96, 608), "VREF", d=(0, -16))
    taps = []
    y = 608
    for k in range(8, 0, -1):          # resistor between tap k and k-1
        c.res((96, y), (96, y + 64), 1e3)
        y += 64
        if k - 1 >= 1:
            taps.append((k - 1, (96, y)))
    c.gnd((96, y))
    for k, (x0, y0) in taps:
        c.wire((x0, y0), (128, y0))
        c.label((128, y0), "T%d" % k)
    for i, k in enumerate(range(1, 8)):  # C1 at the bottom
        x = 352
        y = 1072 - 64 * i
        cp = c.comparator((x, y), swap=True)       # + on top
        c.label((x - 32, y - 16), "VHOLD", d=(-16, 0))
        c.wire((x - 32, y - 16), cp.pin["+"])
        c.label((x - 32, y + 16), "T%d" % k, d=(-16, 0))
        c.wire((x - 32, y + 16), cp.pin["-"])
        c.wire(cp.pin["out"], (x + 96, y))
        c.label((x + 96, y), "C%d" % k)
    c.text((592, 640), "Ck = 1 if VHOLD > k x 0.5 V")
    c.text((592, 672), "thermometer code C1..C7, LSB = 0.5 V")

    # ------------------------------------------------------------ stage 5
    c.box((1120, 544), (2080, 1120))
    c.text((1136, 568), "5  Encoder and display")
    # inverters for C2, C4, C6
    for j, k in enumerate((2, 4, 6)):
        y = 640 + 48 * j
        c.label((1168, y), "C%d" % k, d=(-16, 0))
        inv = c.inverter((1168, y))
        c.label(inv.pin["out"], "N%d" % k)
    # AND gates: C1 !C2, C3 !C4, C5 !C6, C2 !C4
    ands = [("C1", "N2", "A0"), ("C3", "N4", "A1"), ("C5", "N6", "A2"),
            ("C2", "N4", "A3")]
    for j, (a, b, out) in enumerate(ands):
        y = 832 + 64 * j
        g = c.gate("and", (1184, y))
        c.label(g.pin["in"][1], a, d=(-16, 0))      # upper input
        c.label(g.pin["in"][0], b, d=(-16, 0))      # lower input
        c.label(g.pin["out"], out)
    # OR gates
    g = c.gate("or", (1392, 672), n=4)
    for lab, pin in zip(("A0", "A1", "A2", "C7"), g.pin["in"]):
        c.label(pin, lab, d=(-16, 0))
    c.label(g.pin["out"], "B0")
    g = c.gate("or", (1392, 848))
    c.label(g.pin["in"][1], "A3", d=(-16, 0))
    c.label(g.pin["in"][0], "C6", d=(-16, 0))
    c.label(g.pin["out"], "B1")
    c.text((1312, 960), "B2 = C4")
    c.text((1312, 992), "B1 = C2 !C4 %2B C6")
    c.text((1312, 1024), "B0 = C1 !C2 %2B C3 !C4 %2B C5 !C6 %2B C7")
    # LEDs: bar graph C1..C7 and binary B2 B1 B0, each with 330 Ohm
    leds = ["C%d" % k for k in range(1, 8)] + ["B0", "B1", "B2"]
    for j, lab in enumerate(leds):
        x = 1600 + 32 * j + (32 if j >= 7 else 0)
        c.label((x, 640), lab, d=(0, -16))
        c.res((x, 640), (x, 736), 330)
        color = (1, 0, 0) if j < 7 else (0, 1, 0)
        c.led((x, 736), (x, 816), color)
        c.gnd((x, 816))
    c.text((1600, 880), "bar graph C1..C7 (red)")
    c.text((1600, 912), "binary B0 B1 B2 (green)")
    c.text((1600, 944), "each LED with 330 Ohm")
    c.text((1600, 1008), "B2 = C4 (wire)")
    c.label((1600, 1056), "C4", d=(-16, 0))
    c.wire((1600, 1056), (1664, 1056))
    c.label((1664, 1056), "B2")

    # scopes: input and held output, digital outputs
    lab = {e.params[0]: e for e in c.elms if e.kind == "207"}
    c.scope([lab["VCOND"], lab["VHOLD"]] if not with_filter
            else [lab["VAA"], lab["VHOLD"]], speed=64, vscale=5)
    c.scope([lab["VHOLD"], lab["VCOND"]], speed=64, vscale=5)
    c.sensor = sensor
    return c


def _codes(s):
    return (int(s.v("B2") > 2.5), int(s.v("B1") > 2.5), int(s.v("B0") > 2.5))


def _hold_value(s, settle):
    """Run until `settle` seconds later, then to just before the next sample."""
    t = s.t + settle
    period = 1 / FS
    t_end = (math.floor(t / period) + 1) * period - 0.005
    s.run(t_end)
    return s.v("VHOLD")


def capstone():
    c = build("capstone", "Capstone: sensor to 3-bit code (complete solution)")
    rows = []

    def check(s):
        s.dt = 2e-4
        s.c.sensor.params[0] = r_for_vcond(0.0)
        _hold_value(s, 0.6)
        for v in TARGETS:
            r = r_for_vcond(v)
            s.c.sensor.params[0] = r
            vh = _hold_value(s, 0.6)
            b = _codes(s)
            rows.append((t_for_r(r), r, s.v("VAA"), vh, b))
            approx(vh, v, absol=0.03, rel=0, what="held voltage for %.2f V" % v)
            lvl = code(v)
            exp = ((lvl >> 2) & 1, (lvl >> 1) & 1, lvl & 1)
            assert b == exp, "code for %.2f V: %s, expected %s" % (v, b, exp)
            therm = [int(s.v("C%d" % k) > 2.5) for k in range(1, 8)]
            assert sum(therm) == lvl and therm == sorted(therm, reverse=True)
        for row in rows:
            print("    T=%5.1f C  R=%7.3f Ohm  Vaa=%.3f V  Vhold=%.3f V  code=%s" % row)
    return c, check


def capstone_nofilter():
    c = build("capstone_nofilter",
              "Capstone without anti-aliasing filter (aliasing experiment)",
              with_filter=False)

    def check(s):
        s.dt = 2e-4
        for v, wrong in ((1.75, 4), (0.25, 1)):
            s.c.sensor.params[0] = r_for_vcond(v)
            vh = _hold_value(s, 0.4)
            b = _codes(s)
            lvl = b[0] * 4 + b[1] * 2 + b[2]
            print("    no filter: Vcond=%.2f V -> Vhold=%.3f V, code %d (correct %d)"
                  % (v, vh, lvl, code(v)))
            approx(vh - v, 0.525, rel=0.08, what="alias offset at %.2f V" % v)
            assert lvl == wrong
    return c, check


CIRCUITS = [capstone, capstone_nofilter]


if __name__ == "__main__":
    print("G1 = %.2f, G2 = %.4f, G = %.2f" % (G1, G2, G1 * G2))
    print("Vbridge(100C) = %.4f mV, Vcond(100C) = %.4f V" %
          (1e3 * v_bridge(r_sensor(100)), v_cond(r_sensor(100))))
    print("sensor current 0 C: %.4f mA, 100 C: %.4f mA" %
          (1e3 * VREF / (R1 + r_sensor(0)), 1e3 * VREF / (R1 + r_sensor(100))))
    print("fc = %.3f Hz, |H(50 Hz)| = %.4f" %
          (1 / (2 * math.pi * RLP * CLP),
           1 / math.sqrt(1 + (50 * 2 * math.pi * RLP * CLP) ** 2)))
    for v in TARGETS:
        r = r_for_vcond(v)
        print("V=%.2f V: R=%.3f Ohm, T=%.2f C (linear %.1f C)" % (v, r, t_for_r(r), v * 25))
