"""Falstad examples for chapter 6: Active Filters."""
import math

import numpy as np

from falstad import Circuit
from _check import approx

TITLE = "Active Filters"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def labels(c):
    out = {}
    for e in c.elms:
        if e.kind == "207":
            out.setdefault(e.params[0], e)
    return out


def sine_fit(t, v, f):
    """Least-squares fit v = a sin(wt) + b cos(wt) + c0 + c1 t.
    Returns (amplitude, phase in degrees relative to sin(wt), offset)."""
    w = 2 * math.pi * f
    m = np.column_stack([np.sin(w * t), np.cos(w * t), np.ones_like(t), t - t[0]])
    a, b, c0, _ = np.linalg.lstsq(m, v, rcond=None)[0]
    return math.hypot(a, b), math.degrees(math.atan2(b, a)), c0


def measure(s, t_end, t_from, f, names):
    rec = s.run(t_end, record=names)
    k = rec["t"] >= t_from
    return {n: sine_fit(rec["t"][k], rec[n][k], f) for n in names}


def lp1(f, fc):
    return 1 / math.sqrt(1 + (f / fc) ** 2)


def hp1(f, fc):
    x = f / fc
    return x / math.sqrt(1 + x * x)


def lp2(f, f0, q):
    x = f / f0
    return 1 / math.sqrt((1 - x * x) ** 2 + (x / q) ** 2)


def follower(c, x, y, inp_wire_from=None, out=None):
    """Voltage follower, + input on top at (x, y-16); output at (x+128, y)."""
    c.opamp((x, y), swap=True)
    if inp_wire_from is not None:
        c.wire(inp_wire_from, (x, y - 16))
    c.wire((x, y + 16), (x, y + 48), (x + 96, y + 48), (x + 96, y))
    c.wire((x + 64, y), (x + 96, y), (x + 128, y))
    if out:
        c.label((x + 128, y), out)


def source(c, p, amp, f, name, bias=0.0):
    """Sine rail drawn to the left of p, with a label above."""
    c.rail(p, amp, waveform="ac", freq=f, bias=bias, label_dir=(-32, 0))
    c.label(p, name, d=(0, -16))


# ---------------------------------------------------------------------------
# 1./2. passive RC low-pass and high-pass at three frequencies
# ---------------------------------------------------------------------------
R_RC, C_RC = 1.6e3, 100e-9
FC_RC = 1 / (2 * math.pi * R_RC * C_RC)          # 994.7 Hz
FREQS = (100, 1000, 10000)
FNAME = {100: "100Hz", 1000: "1kHz", 10000: "10kHz"}


def _rc_three(name, title, highpass):
    c = Circuit(name, title, timestep=2e-6)
    c.text((48, 32), "R = 1.6k, C = 100 nF, fc = 995 Hz, input 1 V amplitude")
    for k, f in enumerate(FREQS):
        y = 128 + 160 * k
        n = FNAME[f]
        source(c, (128, y), 1.0, f, "Vin_" + n)
        if highpass:
            c.cap((128, y), (256, y), C_RC)
            c.res((256, y), (256, y + 96), R_RC)
        else:
            c.res((128, y), (256, y), R_RC)
            c.cap((256, y), (256, y + 96), C_RC)
        c.gnd((256, y + 96))
        c.wire((256, y), (352, y))
        c.label((352, y), "Vout_" + n)
        c.text((400, y + 4), "f = " + n.replace("Hz", " Hz").replace("k ", " k"))
    lab = labels(c)
    for k, f in enumerate(FREQS):
        n = FNAME[f]
        c.scope([lab["Vin_" + n], lab["Vout_" + n]], speed=[64, 8, 1][k], vscale=1)
    return c


def filter_rc_lowpass():
    """RC low-pass, fc = 995 Hz, driven with 100 Hz, 1 kHz and 10 kHz."""
    c = _rc_three("filter_rc_lowpass", "Passive RC low-pass at 100 Hz, 1 kHz, 10 kHz",
                  highpass=False)

    def check(s):
        approx(FC_RC, 994.7, rel=1e-3, what="fc")
        m = measure(s, 25e-3, 5e-3, 100, ["Vout_100Hz"])
        approx(m["Vout_100Hz"][0], lp1(100, FC_RC), rel=3e-3, what="100 Hz")   # 0.995
        approx(m["Vout_100Hz"][0], 0.995, rel=3e-3, what="100 Hz")
        s2 = s.__class__(c)
        m = measure(s2, 5e-3, 1e-3, 1000, ["Vout_1kHz", "Vout_10kHz"])
        approx(m["Vout_1kHz"][0], 0.705, rel=3e-3, what="1 kHz")               # 0.705
        approx(m["Vout_1kHz"][1], -45.2, rel=0.02, what="phase 1 kHz")       # -45 deg
        m = measure(s2, 6e-3, 5e-3, 10000, ["Vout_10kHz"])
        approx(m["Vout_10kHz"][0], lp1(10000, FC_RC), rel=5e-3, what="10 kHz")  # 0.099
        approx(m["Vout_10kHz"][0], 0.099, rel=0.01, what="10 kHz")
    return c, check


def filter_rc_highpass():
    """RC high-pass, fc = 995 Hz, driven with 100 Hz, 1 kHz and 10 kHz."""
    c = _rc_three("filter_rc_highpass", "Passive RC high-pass at 100 Hz, 1 kHz, 10 kHz",
                  highpass=True)

    def check(s):
        m = measure(s, 25e-3, 5e-3, 100, ["Vout_100Hz"])
        approx(m["Vout_100Hz"][0], hp1(100, FC_RC), rel=5e-3, what="100 Hz")
        approx(m["Vout_100Hz"][0], 0.100, rel=0.01, what="100 Hz")            # 0.100
        s2 = s.__class__(c)
        m = measure(s2, 5e-3, 1e-3, 1000, ["Vout_1kHz"])
        approx(m["Vout_1kHz"][0], 0.709, rel=3e-3, what="1 kHz")              # 0.709
        approx(m["Vout_1kHz"][1], 44.8, rel=0.02, what="phase 1 kHz")        # +45 deg
        m = measure(s2, 6e-3, 5e-3, 10000, ["Vout_10kHz"])
        approx(m["Vout_10kHz"][0], 0.995, rel=3e-3, what="10 kHz")            # 0.995
    return c, check


# ---------------------------------------------------------------------------
# 3. first-order active filters
# ---------------------------------------------------------------------------
def filter_active_first_order():
    """Three first-order active filters with fc = 995 Hz, driven with
    0.1 V at 1 kHz: non-inverting low-pass G = 2, inverting low-pass
    G = -10, inverting high-pass G = -10."""
    c = Circuit("filter_active_first_order",
                "First-order active filters, fc = 995 Hz, input 0.1 V at 1 kHz",
                timestep=2e-6)
    source(c, (96, 96), 0.1, 1000, "Vin")
    # (a) RC + non-inverting amplifier G = 2
    x, y = 336, 208
    c.text((160, 128), "(a) low-pass 16k / 10 nF, then G = 2")
    c.label((144, 192), "Vin", d=(-16, 0))
    c.res((144, 192), (240, 192), 16e3)
    c.cap((240, 192), (240, 272), 10e-9)
    c.gnd((240, 272))
    c.wire((240, 192), (x, 192))
    c.opamp((x, y), swap=True)
    c.wire((x, y + 16), (x - 32, y + 16), (x - 32, y + 64))
    c.res((x - 32, y + 64), (x - 32, y + 128), 10e3)
    c.gnd((x - 32, y + 128))
    c.res((x - 32, y + 64), (x + 96, y + 64), 10e3)
    c.wire((x + 96, y + 64), (x + 96, y))
    c.wire((x + 64, y), (x + 96, y), (x + 128, y))
    c.label((x + 128, y), "Vout_a")
    # (b) inverting low-pass: R1 = 10k, R2 = 100k parallel C = 1.6 nF
    x, y = 336, 512
    c.text((160, 384), "(b) inverting low-pass, R2 = 100k parallel 1.6 nF")
    c.label((208, y - 16), "Vin", d=(-16, 0))
    c.res((208, y - 16), (x - 32, y - 16), 10e3)
    c.wire((x - 32, y - 16), (x, y - 16))
    c.opamp((x, y))
    c.wire((x, y + 16), (x, y + 32))
    c.gnd((x, y + 32))
    c.wire((x - 32, y - 16), (x - 32, y - 48))
    c.res((x - 32, y - 48), (x + 96, y - 48), 100e3)
    c.wire((x + 96, y - 48), (x + 96, y))
    c.wire((x - 32, y - 48), (x - 32, y - 96))
    c.cap((x - 32, y - 96), (x + 96, y - 96), 1.6e-9)
    c.wire((x + 96, y - 96), (x + 96, y - 48))
    c.wire((x + 64, y), (x + 96, y), (x + 128, y))
    c.label((x + 128, y), "Vout_b")
    # (c) inverting high-pass: C1 = 16 nF in series with R1 = 10k, R2 = 100k
    x, y = 896, 512
    c.text((672, 384), "(c) inverting high-pass, 16 nF in series with 10k")
    c.label((704, y - 16), "Vin", d=(-16, 0))
    c.cap((704, y - 16), (784, y - 16), 16e-9)
    c.res((784, y - 16), (x - 32, y - 16), 10e3)
    c.wire((x - 32, y - 16), (x, y - 16))
    c.opamp((x, y))
    c.wire((x, y + 16), (x, y + 32))
    c.gnd((x, y + 32))
    c.wire((x - 32, y - 16), (x - 32, y - 64))
    c.res((x - 32, y - 64), (x + 96, y - 64), 100e3)
    c.wire((x + 96, y - 64), (x + 96, y))
    c.wire((x + 64, y), (x + 96, y), (x + 128, y))
    c.label((x + 128, y), "Vout_c")
    lab = labels(c)
    c.scope([lab["Vin"], lab["Vout_a"]], speed=8, vscale=1)
    c.scope([lab["Vin"], lab["Vout_b"], lab["Vout_c"]], speed=8, vscale=1)

    def check(s):
        fc = 1 / (2 * math.pi * 16e3 * 10e-9)
        approx(fc, 994.7, rel=1e-3)
        m = measure(s, 6e-3, 2e-3, 1000, ["Vout_a", "Vout_b", "Vout_c"])
        approx(m["Vout_a"][0], 0.2 * lp1(1000, fc), rel=3e-3, what="a")
        approx(m["Vout_a"][0], 0.141, rel=3e-3, what="a")        # 0.141 V
        approx(m["Vout_b"][0], 0.705, rel=3e-3, what="b")        # 0.705 V
        approx(m["Vout_c"][0], 0.709, rel=3e-3, what="c")        # 0.709 V
    return c, check


# ---------------------------------------------------------------------------
# 4. integrator
# ---------------------------------------------------------------------------
def filter_integrator():
    """Inverting integrator R = 10k, C = 100 nF, Rp = 1M, square wave
    +-1 V at 500 Hz -> triangle 1 V peak-to-peak."""
    c = Circuit("filter_integrator", "Integrator: square wave in, triangle out",
                timestep=1e-5)
    c.rail((96, 208), 1.0, waveform="square", freq=500, label_dir=(-32, 0))
    c.label((96, 208), "Vin", d=(0, -16))
    x, y = 336, 224
    c.res((96, 208), (x - 32, 208), 10e3)
    c.wire((x - 32, 208), (x, 208))
    c.opamp((x, y))
    c.wire((x, y + 16), (x, y + 32))
    c.gnd((x, y + 32))
    c.wire((x - 32, 208), (x - 32, 160))
    c.cap((x - 32, 160), (x + 96, 160), 100e-9)
    c.wire((x + 96, 160), (x + 96, y))
    c.wire((x - 32, 160), (x - 32, 96))
    c.res((x - 32, 96), (x + 96, 96), 1e6)
    c.wire((x + 96, 96), (x + 96, 160))
    c.wire((x + 64, y), (x + 96, y), (x + 160, y))
    c.label((x + 160, y), "Vout")
    c.text((48, 32), "R = 10k, C = 100 nF, Rp = 1M limits the DC gain")
    c.text((48, 304), "slope = -Vin/(RC) = 1000 V/s")
    lab = labels(c)
    c.scope([lab["Vin"], lab["Vout"]], speed=16, vscale=1)

    def check(s):
        rec = s.run(5e-3, record=["Vout"])
        v = rec["Vout"]
        t = rec["t"]
        k = t <= 1.5e-3
        approx(v[k].min(), -1.0, rel=0.025, what="after 1 ms")         # ~ -1 V
        k = t >= 3e-3
        approx(v[k].max() - v[k].min(), 1.0, rel=0.01, what="pk-pk")            # 1.0 V
    return c, check


# ---------------------------------------------------------------------------
# 5. Sallen-Key vs first order
# ---------------------------------------------------------------------------
R_SK, C1_SK, C2_SK = 10.7e3, 22e-9, 10e-9
F0_SK = 1 / (2 * math.pi * R_SK * math.sqrt(C1_SK * C2_SK))   # 1003 Hz
Q_SK = 0.5 * math.sqrt(C1_SK / C2_SK)                          # 0.742


def sallen_key(c, x, y, r1, r2, c1, c2, inp=None, out=None):
    """Unity-gain Sallen-Key low-pass; op-amp + on top at (x, y-16).
    Input at (x-224, y-16), output at (x+128, y). C1 to the output, C2 to
    ground."""
    a = (x - 128, y - 16)
    b = (x - 32, y - 16)
    c.res((x - 224, y - 16), a, r1)
    c.res(a, b, r2)
    c.wire(b, (x, y - 16))
    c.cap(b, (x - 32, y + 64), c2)
    c.gnd((x - 32, y + 64))
    c.wire(a, (x - 128, y - 80))
    c.cap((x - 128, y - 80), (x + 96, y - 80), c1)
    c.wire((x + 96, y - 80), (x + 96, y))
    c.opamp((x, y), swap=True)
    c.wire((x, y + 16), (x, y + 48), (x + 96, y + 48), (x + 96, y))
    c.wire((x + 64, y), (x + 96, y), (x + 128, y))
    if inp:
        c.label((x - 224, y - 16), inp, d=(-16, 0))
    if out:
        c.label((x + 128, y), out)


def filter_sallen_key():
    """Second-order Sallen-Key (f0 = 1 kHz, Q = 0.74) against a first-order
    RC low-pass (fc = 995 Hz), both at 1 kHz and 10 kHz."""
    c = Circuit("filter_sallen_key",
                "Second-order Sallen-Key vs. first-order RC, 1 kHz and 10 kHz",
                timestep=2e-6)
    source(c, (96, 96), 1.0, 1000, "Vin_1kHz")
    source(c, (96, 192), 1.0, 10000, "Vin_10kHz")
    for k, (inp, n) in enumerate((("Vin_1kHz", "1kHz"), ("Vin_10kHz", "10kHz"))):
        y = 352 + 256 * k
        # first order
        c.label((96, y), inp, d=(-16, 0))
        c.res((96, y), (208, y), R_RC)
        c.cap((208, y), (208, y + 80), C_RC)
        c.gnd((208, y + 80))
        c.wire((208, y), (288, y))
        c.label((288, y), "V1st_" + n)
        # Sallen-Key
        sallen_key(c, 672, y + 16, R_SK, R_SK, C1_SK, C2_SK, inp=inp,
                   out="VSK_" + n)
    c.text((48, 272), "1st order: 1.6k, 100 nF")
    c.text((448, 256), "Sallen-Key: R1 = R2 = 10.7k, C1 = 22 nF, C2 = 10 nF")
    lab = labels(c)
    c.scope([lab["Vin_10kHz"], lab["V1st_10kHz"], lab["VSK_10kHz"]], speed=1, vscale=1)

    def check(s):
        approx(F0_SK, 1003, rel=1e-3, what="f0")
        approx(Q_SK, 0.742, rel=1e-3, what="Q")
        m = measure(s, 5e-3, 2e-3, 1000, ["V1st_1kHz", "VSK_1kHz"])
        approx(m["V1st_1kHz"][0], 0.705, rel=3e-3, what="1st 1k")
        approx(m["VSK_1kHz"][0], lp2(1000, F0_SK, Q_SK), rel=3e-3, what="SK 1k")
        approx(m["VSK_1kHz"][0], 0.744, rel=2e-3, what="SK 1k")         # 0.744
        m = measure(s, 6e-3, 5e-3, 10000, ["V1st_10kHz", "VSK_10kHz"])
        approx(m["V1st_10kHz"][0], 0.099, rel=0.01, what="1st 10k")      # 0.099
        approx(m["VSK_10kHz"][0], lp2(10000, F0_SK, Q_SK), rel=0.01, what="SK 10k")
        approx(m["VSK_10kHz"][0], 0.0101, rel=0.02, what="SK 10k")       # 0.010
    return c, check


# ---------------------------------------------------------------------------
# 6. anti-aliasing filter for the capstone
# ---------------------------------------------------------------------------
R_AA, C_AA = 6.8e3, 10e-6                                   # capstone values
FC_AA = 1 / (2 * math.pi * R_AA * C_AA)                     # 2.34 Hz
V_NOISE = 4.875e-3 * 107.6     # 5 mV x 3.9k/4k at the bridge tap, x G = 0.5245 V
R_AA2, C1_AA2, C2_AA2 = 91e3, 1e-6, 470e-9
F0_AA2 = 1 / (2 * math.pi * R_AA2 * math.sqrt(C1_AA2 * C2_AA2))   # 2.55 Hz
Q_AA2 = 0.5 * math.sqrt(C1_AA2 / C2_AA2)                    # 0.729


def filter_antialias():
    """Signal 2 V DC plus 0.52 V, 50 Hz interference (capstone):
    first-order RC 6.8k / 10 uF with buffer vs. Sallen-Key 91k, 1 uF, 470 nF."""
    c = Circuit("filter_antialias",
                "Anti-aliasing low-pass fc = 2.34 Hz: 2 V DC with 0.52 V at 50 Hz",
                timestep=2.5e-4, speed=40)
    source(c, (96, 112), V_NOISE, 50, "Vin", bias=2.0)
    c.text((48, 32), "Vin = 2 V signal with 0.52 V, 50 Hz interference (4.9 mV x 107.6)")
    y = 256
    c.text((48, y - 64), "1st order: R = 6.8k, C = 10 uF, buffer")
    c.label((96, y - 16), "Vin", d=(-16, 0))
    c.res((96, y - 16), (208, y - 16), R_AA)
    c.cap((208, y - 16), (208, y + 64), C_AA)
    c.gnd((208, y + 64))
    follower(c, 304, y, inp_wire_from=(208, y - 16), out="Vout_1st")
    y = 496
    c.text((48, y - 128), "Sallen-Key: R1 = R2 = 91k, C1 = 1 uF, C2 = 470 nF")
    sallen_key(c, 320, y, R_AA2, R_AA2, C1_AA2, C2_AA2, inp="Vin", out="Vout_SK")
    lab = labels(c)
    c.scope([lab["Vin"], lab["Vout_1st"], lab["Vout_SK"]], speed=64, vscale=3)

    def check(s):
        approx(FC_AA, 2.34, rel=1e-3, what="fc 1st")
        approx(lp1(50, FC_AA), 0.0468, rel=2e-3, what="|H(50)|")     # 0.047, -26.6 dB
        approx(20 * math.log10(lp1(50, FC_AA)), -26.6, rel=2e-3)
        approx(V_NOISE, 0.5245, rel=1e-3, what="noise")
        approx(F0_AA2, 2.551, rel=1e-3, what="f0 SK")
        approx(Q_AA2, 0.729, rel=1e-3, what="Q SK")
        m = measure(s, 1.2, 1.0, 50, ["Vout_1st", "Vout_SK"])
        a1, _, dc1 = m["Vout_1st"]
        a2, _, dc2 = m["Vout_SK"]
        approx(dc1, 2.0, rel=0.002, what="DC 1st")
        approx(dc2, 2.0, rel=0.002, what="DC SK")
        approx(a1, V_NOISE * lp1(50, FC_AA), rel=0.01, what="ripple 1st")
        approx(a1, 0.0245, rel=0.01, what="ripple 1st")      # 25 mV
        approx(a2, V_NOISE * lp2(50, F0_AA2, Q_AA2), rel=0.03, what="ripple SK")
        approx(a2, 0.00137, rel=0.03, what="ripple SK")      # 1.4 mV
    return c, check


# ---------------------------------------------------------------------------
# 7. twin-T notch at 50 Hz
# ---------------------------------------------------------------------------
R_TT, C_TT = 31.8e3, 100e-9
F0_TT = 1 / (2 * math.pi * R_TT * C_TT)      # 50.05 Hz


def twin_t(c, x, y, inp, out):
    """Passive twin-T between (x, y) and (x+256, y), buffered output."""
    # resistor path on top
    c.wire((x, y), (x, y - 64))
    c.res((x, y - 64), (x + 128, y - 64), R_TT)
    c.res((x + 128, y - 64), (x + 256, y - 64), R_TT)
    c.cap((x + 128, y - 64), (x + 128, y - 16), 2 * C_TT)
    c.gnd((x + 128, y - 16))
    c.wire((x + 256, y - 64), (x + 256, y))
    # capacitor path below
    c.wire((x, y), (x, y + 32))
    c.cap((x, y + 32), (x + 128, y + 32), C_TT)
    c.cap((x + 128, y + 32), (x + 256, y + 32), C_TT)
    c.res((x + 128, y + 32), (x + 128, y + 112), R_TT / 2)
    c.gnd((x + 128, y + 112))
    c.wire((x + 256, y + 32), (x + 256, y))
    c.label((x, y), inp, d=(-16, 0))
    follower(c, x + 352, y + 16, inp_wire_from=(x + 256, y), out=out)


def filter_twin_t():
    """Twin-T notch R = 31.8k, C = 100 nF (f0 = 50 Hz) at 50 Hz and 5 Hz."""
    c = Circuit("filter_twin_t", "Twin-T notch filter at 50 Hz", timestep=1e-4,
                speed=40)
    source(c, (96, 64), 1.0, 50, "Vin_50Hz")
    source(c, (352, 64), 1.0, 5, "Vin_5Hz")
    c.text((496, 48), "R = 31.8k, R/2 = 15.9k, C = 100 nF, 2C = 200 nF")
    twin_t(c, 128, 240, "Vin_50Hz", "Vout_50Hz")
    twin_t(c, 128, 496, "Vin_5Hz", "Vout_5Hz")
    lab = labels(c)
    c.scope([lab["Vin_50Hz"], lab["Vout_50Hz"]], speed=16, vscale=1)
    c.scope([lab["Vin_5Hz"], lab["Vout_5Hz"]], speed=64, vscale=1)

    def check(s):
        approx(F0_TT, 50.05, rel=1e-3, what="f0")
        m = measure(s, 0.8, 0.4, 5, ["Vout_5Hz"])
        approx(m["Vout_5Hz"][0], 0.927, rel=3e-3, what="5 Hz")       # 0.927
        m = measure(s, 0.9, 0.8, 50, ["Vout_50Hz"])
        assert m["Vout_50Hz"][0] < 1e-3, m["Vout_50Hz"]               # 0.45 mV < 1 mV
    return c, check


CIRCUITS = [filter_rc_lowpass, filter_rc_highpass, filter_active_first_order,
            filter_integrator, filter_sallen_key, filter_antialias, filter_twin_t]
