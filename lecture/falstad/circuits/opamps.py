"""Falstad examples for chapter 5: Operational Amplifiers."""
import numpy as np

from falstad import Circuit, Sim
from _check import approx

TITLE = "Operational Amplifiers"

A_OL = 1e5          # Falstad default open-loop gain


def closed_loop(g, a=A_OL):
    """Exact closed-loop gain of a stage with ideal gain g (noise gain g)."""
    return g / (1 + g / a)


# ---------------------------------------------------------------------------
# drawing helpers (op-amp input side at p=(x, y), output at (x+64, y))
# ---------------------------------------------------------------------------
def noninv(c, x, y, r1, r2, inp=None, out=None, vmax=15, vmin=-15,
           r2b=None):
    """Non-inverting amplifier, + input on top at (x, y-16).
    R1 from the - node to ground, R2 (and optionally R2b in series) from the
    - node to the output. Returns (opamp, input point, output point, R2 elm,
    R2b elm)."""
    op = c.opamp((x, y), swap=True, vmax=vmax, vmin=vmin)
    pin = (x - 64, y - 16)
    c.wire(pin, (x, y - 16))
    c.wire((x, y + 16), (x - 32, y + 16), (x - 32, y + 64))
    c.res((x - 32, y + 64), (x - 32, y + 128), r1)
    c.gnd((x - 32, y + 128))
    if r2b is None:
        e2 = c.res((x - 32, y + 64), (x + 96, y + 64), r2)
        e2b = None
    else:
        e2 = c.res((x - 32, y + 64), (x + 48, y + 64), r2)
        e2b = c.res((x + 48, y + 64), (x + 96, y + 64), r2b)
    c.wire((x + 96, y + 64), (x + 96, y))
    pout = (x + 128, y)
    c.wire((x + 64, y), (x + 96, y), pout)
    if inp:
        c.label(pin, inp, d=(-16, 0))
    if out:
        c.label(pout, out)
    return op, pin, pout, e2, e2b


def follower(c, x, y, inp=None, out=None):
    """Voltage follower, + input on top at (x, y-16)."""
    op = c.opamp((x, y), swap=True)
    pin = (x - 64, y - 16)
    c.wire(pin, (x, y - 16))
    c.wire((x, y + 16), (x, y + 48), (x + 96, y + 48), (x + 96, y))
    pout = (x + 128, y)
    c.wire((x + 64, y), (x + 96, y), pout)
    if inp:
        c.label(pin, inp, d=(-16, 0))
    if out:
        c.label(pout, out)
    return op, pin, pout


def inverting(c, x, y, r1, r2, inp=None, out=None, cpar=None):
    """Inverting amplifier, - input on top at (x, y-16), + grounded.
    R1 from (x-128, y-16); R2 (and C parallel) above the op-amp."""
    op = c.opamp((x, y))
    pin = (x - 128, y - 16)
    c.res(pin, (x - 32, y - 16), r1)
    c.wire((x - 32, y - 16), (x, y - 16))
    c.wire((x, y + 16), (x, y + 32))
    c.gnd((x, y + 32))
    c.wire((x - 32, y - 16), (x - 32, y - 64))
    c.res((x - 32, y - 64), (x + 96, y - 64), r2)
    c.wire((x + 96, y - 64), (x + 96, y))
    if cpar is not None:
        c.wire((x - 32, y - 64), (x - 32, y - 112))
        c.cap((x - 32, y - 112), (x + 96, y - 112), cpar)
        c.wire((x + 96, y - 112), (x + 96, y - 64))
    pout = (x + 128, y)
    c.wire((x + 64, y), (x + 96, y), pout)
    if inp:
        c.label(pin, inp, d=(-16, 0))
    if out:
        c.label(pout, out)
    return op, pin, pout


def labels(c):
    """First label element of each name (for scopes)."""
    out = {}
    for e in c.elms:
        if e.kind == "207":
            out.setdefault(e.params[0], e)
    return out


def peak(s, t_end, names, t_from=0.0):
    """Run to t_end and return max and min of each label after t_from."""
    rec = s.run(t_end, record=names)
    m = rec["t"] >= t_from
    return {n: (float(np.max(rec[n][m])), float(np.min(rec[n][m]))) for n in names}


# ---------------------------------------------------------------------------
# 1. voltage follower
# ---------------------------------------------------------------------------
def opamp_follower():
    """High-impedance divider 100k/100k loaded with 10k, direct and buffered."""
    c = Circuit("opamp_follower", "Voltage follower: loading a 100k/100k divider with 10k")
    # direct load
    c.rail((96, 112), 10)
    c.res((96, 112), (96, 208), 100e3)
    c.res((96, 208), (96, 304), 100e3)
    c.gnd((96, 304))
    c.wire((96, 208), (208, 208))
    c.res((208, 208), (208, 304), 10e3)
    c.gnd((208, 304))
    c.label((208, 208), "V_direct", d=(16, -16))
    c.text((64, 48), "RL directly at the tap")
    # buffered load
    c.rail((368, 112), 10)
    c.res((368, 112), (368, 208), 100e3)
    c.res((368, 208), (368, 304), 100e3)
    c.gnd((368, 304))
    c.label((368, 208), "V_tap", d=(-16, -16))
    c.wire((368, 208), (416, 208))
    follower(c, 480, 224)
    # follower() starts its input wire at (416, 208): connected above
    c.res((608, 224), (608, 304), 10e3)
    c.gnd((608, 304))
    c.label((608, 224), "V_buffered", d=(16, -16))
    c.text((352, 48), "RL behind a voltage follower")

    def check(s):
        s.dc()
        rp = 100e3 * 10e3 / 110e3
        approx(s.v("V_direct"), 10 * rp / (100e3 + rp), what="direct")   # 0.833 V
        approx(s.v("V_direct"), 0.833, rel=0.002, what="direct")
        approx(s.v("V_buffered"), 5.00, rel=0.001, what="buffered")
        approx(s.v("V_tap"), 5.00, rel=0.001, what="tap")
    return c, check


# ---------------------------------------------------------------------------
# 2. non-inverting and inverting amplifier
# ---------------------------------------------------------------------------
def opamp_noninv_inv():
    """Non-inverting G=3 and inverting G=-2 with a 0.5 V, 1 kHz sine."""
    c = Circuit("opamp_noninv_inv",
                "Non-inverting (G = 3) and inverting (G = -2) amplifier",
                timestep=5e-6)
    c.rail((96, 272), 0.5, waveform="ac", freq=1000, label_dir=(-32, 0))
    c.wire((96, 272), (160, 272))
    c.label((160, 272), "Vin", d=(0, -16))
    # non-inverting, R1 = 10k, R2 = 20k
    noninv(c, 336, 160, 10e3, 20e3, inp="Vin", out="Vout_ni")
    c.text((240, 64), "non-inverting: G = 1 + 20k/10k = 3")
    # inverting, R1 = 10k, R2 = 20k
    inverting(c, 368, 448, 10e3, 20e3, inp="Vin", out="Vout_inv")
    c.text((240, 336), "inverting: G = -20k/10k = -2")
    lab = labels(c)
    c.scope([lab["Vin"], lab["Vout_ni"], lab["Vout_inv"]], speed=2, vscale=2)

    def check(s):
        p = peak(s, 2e-3, ["Vin", "Vout_ni", "Vout_inv"])
        approx(p["Vin"][0], 0.5, what="Vin peak")
        approx(p["Vout_ni"][0], 1.5, what="noninv peak")       # 1.50 V
        approx(p["Vout_ni"][1], -1.5, what="noninv min")
        approx(p["Vout_inv"][0], 1.0, what="inv peak")         # 1.00 V
        approx(p["Vout_inv"][1], -1.0, what="inv min")
    return c, check


# ---------------------------------------------------------------------------
# 3. summing amplifier
# ---------------------------------------------------------------------------
def opamp_summing():
    """Inverting summer: V1 = 1 V (10k), V2 = 2 V (20k), V3 = -0.5 V (10k), Rf = 10k."""
    c = Circuit("opamp_summing", "Inverting summing amplifier")
    for y, v, r, name in ((144, 1.0, 10e3, "V1"), (208, 2.0, 20e3, "V2"),
                          (272, -0.5, 10e3, "V3")):
        c.rail((160, y), v, label_dir=(-32, 0))
        c.label((160, y), name, d=(0, -16))
        c.res((160, y), (352, y), r)
    c.wire((352, 96), (352, 144), (352, 208), (352, 272))
    c.wire((352, 208), (400, 208))
    c.opamp((400, 224))
    c.wire((400, 240), (400, 288))
    c.gnd((400, 288))
    c.res((352, 96), (496, 96), 10e3)
    c.wire((496, 96), (496, 224))
    c.wire((464, 224), (496, 224), (560, 224))
    c.label((560, 224), "Vout")
    c.label((352, 272), "V_sum_node", d=(-16, 16))
    c.text((96, 48), "Vout = -Rf (V1/R1 + V2/R2 + V3/R3)")
    c.text((256, 80), "Rf = 10k")
    c.text((224, 128), "R1 = 10k")
    c.text((224, 192), "R2 = 20k")
    c.text((224, 256), "R3 = 10k")

    def check(s):
        s.dc()
        approx(s.v("Vout"), -1.5, what="Vout")                  # -1.50 V
        approx(s.v("V_sum_node"), 0.0, absol=1e-4, what="virtual ground")
    return c, check


# ---------------------------------------------------------------------------
# 4. difference amplifier, matched and mismatched
# ---------------------------------------------------------------------------
def diffamp(c, x, y, r1, r2, r3, r4, inm, inp, out):
    """Difference amplifier; - side R1/R2, + side R3/R4. Inputs at x-128."""
    c.opamp((x, y))
    c.res((x - 128, y - 16), (x - 32, y - 16), r1)
    c.wire((x - 32, y - 16), (x, y - 16))
    c.wire((x - 32, y - 16), (x - 32, y - 64))
    e2 = c.res((x - 32, y - 64), (x + 96, y - 64), r2)
    c.wire((x + 96, y - 64), (x + 96, y))
    c.wire((x + 64, y), (x + 96, y), (x + 128, y))
    c.res((x - 128, y + 16), (x - 32, y + 16), r3)
    c.wire((x - 32, y + 16), (x, y + 16))
    e4 = c.res((x - 32, y + 16), (x - 32, y + 96), r4)
    c.gnd((x - 32, y + 96))
    if inm:
        c.label((x - 128, y - 16), inm, d=(-16, 0))
    if inp:
        c.label((x - 128, y + 16), inp, d=(-16, 0))
    if out:
        c.label((x + 128, y), out)
    return e2, e4


def opamp_diffamp():
    """Difference amplifier G = 10 with 2.505 V / 2.500 V inputs:
    matched resistors and one resistor 1 % high."""
    c = Circuit("opamp_diffamp", "Difference amplifier: matched and 1 % mismatched resistors")
    c.rail((96, 144), 2.505, label_dir=(-32, 0))
    c.label((96, 144), "V1", d=(0, -16))
    c.rail((96, 272), 2.500, label_dir=(-32, 0))
    c.label((96, 272), "V2", d=(0, -16))
    c.text((32, 64), "V1 = 2.505 V, V2 = 2.500 V")
    c.text((32, 88), "difference 5 mV, common mode 2.5 V")
    diffamp(c, 400, 176, 10e3, 100e3, 10e3, 100e3, "V2", "V1", "Vout_matched")
    c.text((304, 64), "matched: R2/R1 = R4/R3 = 10")
    diffamp(c, 400, 432, 10e3, 100e3, 10e3, 101e3, "V2", "V1", "Vout_mismatch")
    c.text((304, 320), "R4 = 101k (1 % high)")

    def check(s):
        s.dc()
        g = closed_loop(11) / 11
        approx(s.v("Vout_matched"), 0.050, rel=0.003, what="matched")    # 50.0 mV
        vp = 2.505 * 101 / 111
        vo = (vp * 11 - 2.5 * 10) * g
        approx(s.v("Vout_mismatch"), vo, rel=0.003, what="mismatch")
        approx(s.v("Vout_mismatch"), 0.0726, rel=0.002, what="mismatch")  # 72.6 mV
    return c, check


# ---------------------------------------------------------------------------
# 5. instrumentation amplifier for the capstone
# ---------------------------------------------------------------------------
# capstone values (see Capstone.tex): Pt100 bridge from the 4.00 V reference
VREF_B = 4.0
R1_B = R3_B = 3900.0
R4_B = 100.0
RS_BOTTOM, RS_TOP = 100.0, 138.5          # Pt100 at 0 and 100 degC
RF_FIX, R_TRIM, RG2 = 91e3, 6.6e3, 10e3   # 91k + 6.6k = 97.6k -> G2 = 10.76


def bridge_v(rs):
    """Bridge output V_S - V_R of the capstone bridge."""
    return VREF_B * (rs / (R1_B + rs) - R4_B / (R3_B + R4_B))


def opamp_ina():
    """Pt100 bridge (4.00 V, 3.9k/3.9k/100 Ohm) -> two buffers ->
    difference amplifier G1 = 10 -> non-inverting stage
    G2 = 1 + (91k + 6.6k trimmer)/10k = 10.76."""
    c = Circuit("opamp_ina", "Instrumentation amplifier for the capstone: 0 .. 4.00 V")
    # bridge: left arm R1 / Pt100 (V_S), right arm R3 / R4 (V_R)
    c.wire((64, 112), (128, 112), (192, 112))
    c.rail((128, 112), VREF_B)
    c.res((64, 112), (64, 224), R1_B)
    rs = c.res((64, 224), (64, 336), RS_TOP)
    c.res((192, 112), (192, 224), R3_B)
    c.res((192, 224), (192, 336), R4_B)
    c.wire((64, 336), (128, 336), (192, 336))
    c.gnd((128, 336))
    c.label((64, 224), "VB_plus", d=(-16, 16))
    c.label((192, 224), "VB_minus", d=(16, 16))
    c.text((16, 400), "R1 = R3 = 3.9k, R4 = 100, Pt100 100 .. 138.5 Ohm")
    # buffers
    follower(c, 320, 176, inp="VB_minus")
    follower(c, 320, 368, inp="VB_plus")
    # difference amplifier G = 10
    c.wire((448, 176), (448, 240))
    c.wire((448, 368), (448, 272))
    diffamp(c, 576, 256, 10e3, 100e3, 10e3, 100e3, None, None, None)
    c.label((704, 256), "V_diff", d=(0, -16))
    # second stage G = 1 + (91k + Rtrim)/10k
    c.wire((704, 256), (768, 256))
    _, _, _, _, trim = noninv(c, 832, 272, RG2, RF_FIX, out="Vout", r2b=R_TRIM)
    c.text((256, 48), "buffers")
    c.text((480, 48), "difference amp G = 10")
    c.text((768, 48), "gain stage G = 1 + (91k + Rtrim)/10k")
    c.slider(rs, 100, 138.5, "Sensor R (Pt100, 0..100 C)")
    c.slider(trim, 0, 10000, "Gain trim Rtrim")

    def check(s):
        s.dc()
        vd = bridge_v(RS_TOP)
        approx(vd, 0.03718, rel=0.001, what="bridge top")       # 37.18 mV
        approx(s.v("VB_minus"), 0.100, rel=0.001, what="V_R")   # 0.100 V
        approx(s.v("VB_plus") - s.v("VB_minus"), vd, what="bridge")
        approx(s.v("V_diff"), 0.3718, rel=0.002, what="V_diff")   # 372 mV
        approx(s.v("Vout"), 4.00, rel=0.001, what="Vout top")     # 4.00 V
        rs.params[0] = RS_BOTTOM
        s2 = Sim(c).dc()
        rs.params[0] = RS_TOP
        approx(s2.v("Vout"), 0.0, absol=1e-3, what="Vout bottom")  # 0.00 V
    return c, check


# ---------------------------------------------------------------------------
# 6. finite open-loop gain
# ---------------------------------------------------------------------------
def opamp_finite_gain():
    """1 mV input; G = 1000 and G = 10000 in one stage and in two stages."""
    c = Circuit("opamp_finite_gain",
                "Finite open-loop gain A = 100000: one stage vs. two stages")
    c.rail((96, 96), 1e-3, label_dir=(-32, 0))
    c.label((96, 96), "Vin", d=(0, -16))
    c.text((32, 32), "Vin = 1 mV,  A = 100000")
    rows = [("G = 1000, one stage", [999e3], "Vout_1000"),
            ("G = 1000 = 10 x 100", [9e3, 99e3], "Vout_10x100"),
            ("G = 10000, one stage", [9.999e6], "Vout_10000"),
            ("G = 10000 = 100 x 100", [99e3, 99e3], "Vout_100x100")]
    for k, (txt, r2s, out) in enumerate(rows):
        y = 176 + 176 * k
        c.text((288, y - 64), txt)
        x = 304
        inp = "Vin"
        for j, r2 in enumerate(r2s):
            o = out if j == len(r2s) - 1 else out + "_1"
            noninv(c, x, y, 1e3, r2, inp=inp if j == 0 else None, out=o)
            if j < len(r2s) - 1:
                c.wire((x + 128, y), (x + 160, y), (x + 160, y - 16),
                       (x + 192 + 64, y - 16))
                x += 320
                inp = None

    def check(s):
        s.dc()
        v1000 = 1e-3 * closed_loop(1000)
        v10x100 = 1e-3 * closed_loop(10) * closed_loop(100)
        v10000 = 1e-3 * closed_loop(10000)
        v100x100 = 1e-3 * closed_loop(100) ** 2
        approx(s.v("Vout_1000"), v1000, rel=1e-3, what="1000")
        approx(s.v("Vout_1000"), 0.990, rel=1e-3, what="1000")        # 0.990 V
        approx(s.v("Vout_10x100"), 0.9989, rel=1e-4, what="10x100")    # 0.999 V
        approx(s.v("Vout_10000"), 9.091, rel=1e-3, what="10000")       # 9.09 V
        approx(s.v("Vout_100x100"), 9.980, rel=1e-3, what="100x100")   # 9.98 V
        approx(v10x100, 0.9989, rel=1e-4)
        approx(v10000, 9.0909, rel=1e-4)
    return c, check


# ---------------------------------------------------------------------------
# 7. single supply and level shifting
# ---------------------------------------------------------------------------
def opamp_level_shift():
    """Single supply 0..5 V op-amp: a +-2 V sine through a follower is
    clipped; with Vout = Vin + 2.5 V it fits."""
    c = Circuit("opamp_level_shift", "Single supply (0 .. 5 V): level shifting",
                timestep=1e-5)
    c.rail((96, 208), 2.0, waveform="ac", freq=100, label_dir=(-32, 0))
    c.wire((96, 208), (160, 208))
    c.label((160, 208), "Vin", d=(0, -16))
    # follower on single supply
    op = c.opamp((336, 160), swap=True, vmax=5, vmin=0)
    c.label((272, 144), "Vin", d=(-16, 0))
    c.wire((272, 144), (336, 144))
    c.wire((336, 176), (336, 208), (432, 208), (432, 160))
    c.wire((400, 160), (432, 160), (464, 160))
    c.label((464, 160), "Vout_follower")
    c.text((240, 64), "follower, supply 0 .. 5 V")
    # level shifter: V+ = (Vin + Vref)/2, gain 2
    x, y = 336, 448
    c.opamp((x, y), swap=True, vmax=5, vmin=0)
    c.label((176, 368), "Vin", d=(-16, 0))
    c.res((176, 368), (272, 368), 10e3)
    c.rail((176, 480), 2.5, label_dir=(-32, 0))
    c.label((176, 480), "Vref", d=(0, 16))
    c.res((176, 480), (272, 480), 10e3)
    c.wire((272, 368), (272, 432), (272, 480))
    c.wire((272, 432), (x, 432))
    c.wire((x, 464), (x - 16, 464), (x - 16, 528))
    c.res((x - 16, 528), (x - 16, 608), 10e3)
    c.gnd((x - 16, 608))
    c.res((x - 16, 528), (x + 96, 528), 10e3)
    c.wire((x + 96, 528), (x + 96, y))
    c.wire((x + 64, y), (x + 96, y), (x + 128, y))
    c.label((x + 128, y), "Vout_shifted")
    c.text((176, 304), "level shifter: Vout = Vin + Vref")
    labs = labels(c)
    c.scope([labs["Vin"], labs["Vout_follower"]], speed=4, vscale=5)
    c.scope([labs["Vin"], labs["Vout_shifted"]], speed=4, vscale=5)

    def check(s):
        p = peak(s, 20e-3, ["Vin", "Vout_follower", "Vout_shifted"])
        approx(p["Vout_follower"][0], 2.0, rel=0.005, what="follower max")
        approx(p["Vout_follower"][1], 0.0, absol=1e-3, what="follower min")  # clipped
        approx(p["Vout_shifted"][0], 4.5, rel=0.005, what="shifted max")
        approx(p["Vout_shifted"][1], 0.5, rel=0.01, what="shifted min")
    return c, check


# ---------------------------------------------------------------------------
# 8. offset voltage and bias current
# ---------------------------------------------------------------------------
def opamp_offset():
    """G = 101 with grounded input: 1 mV offset source, 100 nA bias current
    through a 100k source resistance."""
    c = Circuit("opamp_offset", "Input offset voltage and bias current after G = 101")
    # (a) offset voltage modelled as a 1 mV source in series with +
    c.gnd((96, 160))
    c.wire((96, 144), (96, 160))
    c.vsrc((96, 144), (96, 96), 1e-3)
    c.wire((96, 96), (96, 80), (208, 80), (208, 144))
    c.text((32, 32), "(a) Vos = 1 mV, input at 0 V")
    noninv(c, 272, 160, 1e3, 100e3, out="Vout_offset")
    # (b) bias current 100 nA flowing into the + input through Rs = 100k
    c.text((32, 336), "(b) IB = 100 nA through Rs = 100k")
    c.res((128, 432), (208, 432), 100e3)
    c.gnd((128, 448))
    c.wire((128, 432), (128, 448))
    c.isrc((160, 528), (160, 576), 100e-9)
    c.wire((208, 432), (208, 496), (160, 496), (160, 528))
    c.gnd((160, 576))
    c.label((208, 496), "V_plus_b", d=(16, 0))
    noninv(c, 272, 448, 1e3, 100e3, out="Vout_bias")

    def check(s):
        s.dc()
        g = closed_loop(101)
        approx(s.v("Vout_offset"), 1e-3 * g, what="offset")
        approx(s.v("Vout_offset"), 0.101, rel=0.002, what="offset")      # 101 mV
        approx(s.v("V_plus_b"), -0.010, rel=0.001, what="V+ bias")       # -10 mV
        approx(s.v("Vout_bias"), -1.01, rel=0.002, what="bias")          # -1.01 V
    return c, check


CIRCUITS = [opamp_follower, opamp_noninv_inv, opamp_summing, opamp_diffamp,
            opamp_ina, opamp_finite_gain, opamp_level_shift, opamp_offset]
