"""Falstad examples for the chapter Noise and Interference.

Noise sources are CircuitJS noise generators (waveform 6): a new value,
uniformly distributed in +-A, at every time step. Their RMS value is
A/sqrt(3), their spectrum is white up to 1/(2 dt): the density is
sqrt(2 dt) * A/sqrt(3). Falstad cannot simulate thermal or shot noise
itself; the generators show how white noise behaves (bandwidth, adding
sources). Noise checks are statistical (fixed seed, tolerance 10 %);
Falstad shows slightly different values on every run.

Interference examples use the capstone numbers where possible:
bridge 4.00 V, 3.9k / Pt100 and 3.9k / 100 Ohm (0 .. 37.18 mV), INA
G1 = 10, gain stage G2 = 1 + 97.6k/10k = 10.76.
"""
import math

import numpy as np

from falstad import Circuit, Sim
from _check import approx
from bridges import _ina, voltmeter, VB, R_TOP, R0, R50

TITLE = "Noise and Interference"

DT_NOISE = 1e-5                       # time step of the noise examples


def labels(c):
    out = {}
    for e in c.elms:
        if e.kind == "207":
            out.setdefault(e.params[0], e)
    return out


def rms(rec, name, t_from):
    k = rec["t"] >= t_from
    v = rec[name][k]
    return float(np.sqrt(np.mean((v - v.mean()) ** 2)))


def amp(rec, name, t_from):
    """Half the peak-to-peak value after t_from."""
    k = rec["t"] >= t_from
    v = rec[name][k]
    return float((v.max() - v.min()) / 2)


def sine_amp(rec, name, t_from, f):
    k = rec["t"] >= t_from
    t, v = rec["t"][k], rec[name][k]
    w = 2 * math.pi * f
    m = np.column_stack([np.sin(w * t), np.cos(w * t), np.ones_like(t)])
    a, b, c0 = np.linalg.lstsq(m, v, rcond=None)[0]
    return math.hypot(a, b), c0


def noise_rail(c, p, a, name):
    """Noise generator (one terminal) at p, drawn to the left, with a label."""
    c.rail(p, a, waveform="noise", label_dir=(-32, 0))
    c.label(p, name, d=(0, -16))


def rc_rms(a, r, cap, dt=DT_NOISE):
    """Expected RMS behind an RC low-pass for a noise generator of amplitude a:
    density^2 * noise bandwidth = (2 dt a^2/3) * (pi/2) fc."""
    fc = 1 / (2 * math.pi * r * cap)
    return a / math.sqrt(3) * math.sqrt(2 * dt * math.pi / 2 * fc)


# ---------------------------------------------------------------------------
# 1. white noise and bandwidth
# ---------------------------------------------------------------------------
def noise_bandwidth():
    """White noise behind low-passes of 995 Hz and 99.5 Hz: RMS ~ sqrt(B)."""
    c = Circuit("noise_bandwidth", "White noise: the RMS value grows with the square root of the bandwidth",
                timestep=DT_NOISE, speed=40)
    c.text((48, 32), "Noise generator 1 V (uniform, white up to 50 kHz): RMS = 0.577 V")
    c.text((48, 56), "Low-pass 995 Hz: RMS 0.10 V.  Low-pass 99.5 Hz (10 x less bandwidth): RMS 0.032 V")
    noise_rail(c, (96, 160), 1.0, "Vn")
    c.wire((96, 160), (96, 304), (96, 448))
    # fc = 995 Hz
    c.res((96, 304), (224, 304), 1.6e3)
    c.cap((224, 304), (224, 384), 100e-9)
    c.gnd((224, 384))
    c.wire((224, 304), (320, 304))
    c.label((320, 304), "Vn_995Hz")
    c.text((368, 308), "1.6k / 100 nF: fc = 995 Hz")
    # fc = 99.5 Hz
    c.res((96, 448), (224, 448), 16e3)
    c.cap((224, 448), (224, 528), 100e-9)
    c.gnd((224, 528))
    c.wire((224, 448), (320, 448))
    c.label((320, 448), "Vn_99Hz")
    c.text((368, 452), "16k / 100 nF: fc = 99.5 Hz")
    lab = labels(c)
    for n in ("Vn", "Vn_995Hz", "Vn_99Hz"):
        c.scope([lab[n]], speed=16, vscale=1.0, rms=True)

    def check(s):
        r = s.run(0.3, record=["Vn", "Vn_995Hz", "Vn_99Hz"])
        approx(rms(r, "Vn", 0.02), 1 / math.sqrt(3), rel=0.02, what="raw RMS")       # 0.577
        e1 = rc_rms(1.0, 1.6e3, 100e-9)
        e2 = rc_rms(1.0, 16e3, 100e-9)
        approx(e1, 0.102, rel=0.01, what="theory 995 Hz")
        approx(e2, 0.0323, rel=0.01, what="theory 99.5 Hz")
        approx(rms(r, "Vn_995Hz", 0.02), e1, rel=0.10, what="RMS 995 Hz")             # 0.10
        approx(rms(r, "Vn_99Hz", 0.02), e2, rel=0.10, what="RMS 99.5 Hz")             # 0.032
    return c, check


# ---------------------------------------------------------------------------
# 2. adding noise sources: uncorrelated (RSS) and correlated (linear)
# ---------------------------------------------------------------------------
def noise_rss():
    """One source, two independent sources in series, one source doubled."""
    c = Circuit("noise_rss", "Adding noise: independent sources add in RMS, correlated ones linearly",
                timestep=DT_NOISE, speed=40)
    c.text((48, 32), "(a) one generator 1 V: RMS 0.577 V")
    c.text((48, 56), "(b) two independent generators in series: RMS sqrt(2) x 0.577 = 0.82 V (not 1.15 V)")
    c.text((48, 80), "(c) the same generator twice (amplifier G = 2): fully correlated, RMS 1.15 V")
    # (a)
    noise_rail(c, (96, 176), 1.0, "Na")
    c.wire((96, 176), (192, 176))
    c.label((192, 176), "Va")
    # (b) two noise sources in series
    x = 320
    c.vsrc((x, 336), (x, 256), 1.0, waveform="noise")
    c.vsrc((x, 256), (x, 176), 1.0, waveform="noise")
    c.gnd((x, 336))
    c.wire((x, 176), (x + 96, 176))
    c.label((x + 96, 176), "Vb")
    c.text((x + 32, 260), "N1")
    c.text((x + 32, 308), "N2")
    # (c) the generator of (a), amplified by 2
    x, y = 672, 192
    c.label((x - 32, y - 16), "Na", d=(-16, 0))
    c.wire((x - 32, y - 16), (x, y - 16))
    a = c.opamp((x, y), swap=True)
    c.wire(a.pin["-"], (x - 16, y + 16), (x - 16, y + 64))
    c.res((x - 16, y + 64), (x - 16, y + 144), 10e3)
    c.gnd((x - 16, y + 144))
    c.res((x - 16, y + 64), (x + 96, y + 64), 10e3)
    c.wire((x + 96, y + 64), (x + 96, y))
    c.wire(a.pin["out"], (x + 96, y), (x + 128, y))
    c.label((x + 128, y), "Vc")
    lab = labels(c)
    for n in ("Va", "Vb", "Vc"):
        c.scope([lab[n]], speed=16, vscale=2.0, rms=True)

    def check(s):
        r = s.run(0.1, record=["Va", "Vb", "Vc"])
        sa, sb, sc = rms(r, "Va", 0.0), rms(r, "Vb", 0.0), rms(r, "Vc", 0.0)
        approx(sa, 0.577, rel=0.02, what="(a)")
        approx(sb, 0.816, rel=0.03, what="(b) independent")
        approx(sc, 1.155, rel=0.02, what="(c) correlated")
    return c, check


# ---------------------------------------------------------------------------
# 3. capacitive coupling from the mains
# ---------------------------------------------------------------------------
MAINS = 325.0                         # 230 V rms


def noise_cap_coupling():
    """325 V / 50 Hz couples through 1 pF into nodes of 1 MOhm, 10 kOhm,
    100 Ohm, and into a shielded 1 MOhm node (0.01 pF residual)."""
    c = Circuit("noise_cap_coupling", "Capacitive coupling: 1 pF from the mains into nodes of different impedance",
                timestep=2e-5, speed=60, voltage_range=1)
    c.text((48, 32), "Mains 230 V (325 V peak), 50 Hz, couples through 1 pF (stray capacitance) into a node")
    c.text((48, 56), "Coupled current 0.10 uA: the voltage is I x R, so a low node impedance helps")
    c.rail((64, 352), MAINS, waveform="ac", freq=50, label_dir=(-32, 0))
    c.label((64, 352), "MAINS", d=(0, -16))
    c.wire((64, 352), (64, 160))
    xs = [160, 400, 640]
    rs = [1e6, 10e3, 100.0]
    names = ["V_1M", "V_10k", "V_100"]
    texts = ["1 MOhm: 0.10 V", "10 kOhm: 1.0 mV", "100 Ohm: 10 uV"]
    prev = (64, 160)
    for x, r, n, t in zip(xs, rs, names, texts):
        c.wire(prev, (x, 160))
        prev = (x, 160)
        c.cap((x, 160), (x, 256), 1e-12)
        c.res((x, 256), (x, 352), r)
        c.gnd((x, 352))
        c.wire((x, 256), (x + 64, 256))
        c.label((x + 64, 256), n)
        c.text((x - 16, 384), t)
    # shielded node: the shield (grounded) takes the 1 pF, 0.01 pF remain
    x = 880
    c.wire(prev, (x, 160), (x + 128, 160))
    c.cap((x, 160), (x, 224), 1e-12)
    c.wire((x, 224), (x, 240))
    c.gnd((x, 240))
    c.cap((x + 128, 160), (x + 128, 256), 0.01e-12)
    c.res((x + 128, 256), (x + 128, 352), 1e6)
    c.gnd((x + 128, 352))
    c.cap((x + 128, 256), (x + 224, 256), 10e-12)
    c.wire((x + 224, 256), (x + 224, 288))
    c.gnd((x + 224, 288))
    c.label((x + 128, 256), "V_shield", d=(-16, 0))
    c.text((x - 16, 384), "1 MOhm, shielded: 1.0 mV")
    c.text((x - 16, 408), "1 pF ends on the grounded shield,")
    c.text((x - 16, 432), "0.01 pF (holes) remain; 10 pF to the shield")
    lab = labels(c)
    c.scope([lab["V_1M"]], speed=32, vscale=0.2)
    c.scope([lab["V_10k"]], speed=32, vscale=0.002)
    c.scope([lab["V_shield"]], speed=32, vscale=0.002)

    def check(s):
        r = s.run(0.08, record=names + ["V_shield"])
        i = 2 * math.pi * 50 * 1e-12 * MAINS
        approx(i, 0.102e-6, rel=0.01, what="coupled current")
        approx(sine_amp(r, "V_1M", 0.04, 50)[0], 0.102, rel=0.02, what="1 MOhm")
        approx(sine_amp(r, "V_10k", 0.04, 50)[0], 1.02e-3, rel=0.02, what="10 kOhm")
        approx(sine_amp(r, "V_100", 0.04, 50)[0], 10.2e-6, rel=0.02, what="100 Ohm")
        approx(sine_amp(r, "V_shield", 0.04, 50)[0], 1.02e-3, rel=0.02, what="shielded")
    return c, check


# ---------------------------------------------------------------------------
# 4. magnetic coupling: wide loop versus twisted pair
# ---------------------------------------------------------------------------
def _bridge_sources(c, x, y, sources, na, nb):
    """Capstone bridge (4 V, 3.9k / Pt100 100 Ohm, 3.9k / 100 Ohm) with the
    upper-left corner at (x, y). sources: list of (amplitude, phase) of 50 Hz
    sources in series with the sensor (the induced voltages in the leads)."""
    xl, xr = x + 160, x + 320
    ym, yb = y + 128, y + 352
    c.vsrc((x, yb), (x, y), VB)
    c.gnd((x, yb))
    c.wire((x, y), (xl, y), (xr, y))
    c.res((xl, y), (xl, ym), R_TOP)
    c.res((xl, ym), (xl, ym + 64), R0)
    yy = ym + 64
    for k, (a, ph) in enumerate(sources):
        y2 = yy + 64 if k < len(sources) - 1 else yb
        c.vsrc((xl, y2), (xl, yy), a, waveform="ac", freq=50, phase=ph)
        yy = y2
    if yy != yb:
        c.wire((xl, yy), (xl, yb))
    c.res((xr, y), (xr, ym), R_TOP)
    c.res((xr, ym), (xr, yb), R0)
    c.wire((x, yb), (xl, yb), (xr, yb))
    voltmeter(c, (xl, ym), (xr, ym))
    c.label((xl, ym), na, d=(-16, 0))
    c.label((xr, ym), nb, d=(16, 0))


def noise_mag_coupling():
    """Induced 50 Hz voltage in the sensor loop: wide loop (5 mV) versus
    twisted pair (neighbouring twists cancel; 10 % imbalance remains)."""
    c = Circuit("noise_mag_coupling", "Magnetic coupling: wide loop versus twisted pair (50 Hz, capstone bridge)",
                timestep=2e-5, speed=60)
    c.text((48, 32), "The sensor leads form a loop; the 50 Hz field induces a voltage in series with the sensor")
    c.text((48, 56), "Left: wide loop, 5 mV.  Right: twisted pair, the twists induce 2.5 mV and -2.25 mV: 0.25 mV remain")
    _bridge_sources(c, 48, 128, [(0.005, 0.0)], "Aw", "Bw")
    _ina(c, 528, 192, "Aw", "Bw", "Vw")
    _bridge_sources(c, 48, 640, [(0.0025, 0.0), (0.00225, math.pi)], "At", "Bt")
    _ina(c, 528, 704, "At", "Bt", "Vt")
    c.text((256, 560), "wide loop: 5 mV induced")
    c.text((256, 1072), "twisted pair: 2.5 mV - 2.25 mV")
    c.text((560, 480), "INA G = 10: 48.8 mV amplitude")
    c.text((560, 992), "INA G = 10: 2.4 mV amplitude")
    lab = labels(c)
    c.scope([lab["Vw"]], speed=32, vscale=0.05)
    c.scope([lab["Vt"]], speed=32, vscale=0.05)

    def check(s):
        r = s.run(0.06, record=["Aw", "Bw", "At", "Bt", "Vw", "Vt"])
        r["Dw"] = r["Aw"] - r["Bw"]
        r["Dt"] = r["At"] - r["Bt"]
        approx(sine_amp(r, "Dw", 0.02, 50)[0], 4.875e-3, rel=0.01, what="wide loop at tap")
        approx(sine_amp(r, "Dt", 0.02, 50)[0], 0.244e-3, rel=0.01, what="twisted at tap")
        approx(sine_amp(r, "Vw", 0.02, 50)[0], 48.75e-3, rel=0.01, what="wide loop INA")
        approx(sine_amp(r, "Vt", 0.02, 50)[0], 2.44e-3, rel=0.01, what="twisted INA")
    return c, check


# ---------------------------------------------------------------------------
# 5. ground loop: single-ended versus differential input
# ---------------------------------------------------------------------------
V_SENS = 37.18e-3                     # full-scale bridge signal


def noise_ground_loop():
    """Remote sensor whose ground is 0.1 V (50 Hz) away from the amplifier
    ground: single-ended G = 10 amplifies it, a difference amplifier G = 10
    rejects it (ideal resistors and one resistor 1 % off)."""
    c = Circuit("noise_ground_loop", "Ground loop: single-ended versus differential measurement",
                timestep=1e-4, speed=60)
    c.text((48, 32), "Remote sensor (37.2 mV) with its own ground. 1 V, 50 Hz between the two earth points drives")
    c.text((48, 56), "200 mA through the loop (PE 4.5 Ohm, cable ground 0.5 Ohm): the remote ground moves by 0.1 V")
    # ground loop: amplifier ground (global) -- 1 V source -- PE 4.5 Ohm -- remote gnd -- cable 0.5 Ohm -- gnd
    c.vsrc((96, 512), (96, 432), 1.0, waveform="ac", freq=50)
    c.gnd((96, 512))
    c.res((96, 432), (96, 336), 4.5)
    c.wire((96, 336), (208, 336))
    c.res((208, 336), (208, 512), 0.5)
    c.gnd((208, 512))
    c.text((112, 400), "PE")
    c.text((224, 452), "cable ground")
    c.label((96, 336), "GND_remote", d=(0, -16))
    c.text((16, 560), "earth potential difference 1 V")
    # remote sensor
    c.vsrc((96, 336), (96, 208), V_SENS)
    c.wire((96, 208), (208, 208))
    c.label((208, 208), "SIG")
    c.text((112, 176), "sensor 37.2 mV")
    # (a) single-ended non-inverting G = 10 (90k / 10k)
    x, y = 448, 192
    c.text((x - 48, 128), "(a) single-ended, G = 10")
    c.label((x - 32, y - 16), "SIG", d=(-16, 0))
    c.wire((x - 32, y - 16), (x, y - 16))
    a = c.opamp((x, y), swap=True)
    c.wire(a.pin["-"], (x - 16, y + 16), (x - 16, y + 64))
    c.res((x - 16, y + 64), (x - 16, y + 144), 10e3)
    c.gnd((x - 16, y + 144))
    c.res((x - 16, y + 64), (x + 96, y + 64), 90e3)
    c.wire((x + 96, y + 64), (x + 96, y))
    c.wire(a.pin["out"], (x + 96, y), (x + 128, y))
    c.label((x + 128, y), "Vout_se")

    # (b), (c) difference amplifiers G = 10: SIG to +, GND_remote (sense wire) to -
    def diffamp(x, y, rplus, out, title):
        c.text((x - 176, y - 96), title)
        a = c.opamp((x, y), swap=False)                 # - at y-16, + at y+16
        c.label((x - 160, y - 16), "GND_remote", d=(-16, 0))
        c.res((x - 160, y - 16), (x - 48, y - 16), 10e3)
        c.wire((x - 48, y - 16), a.pin["-"])
        c.wire((x - 48, y - 16), (x - 48, y - 64))
        c.res((x - 48, y - 64), (x + 96, y - 64), 100e3)
        c.wire((x + 96, y - 64), (x + 96, y))
        c.wire(a.pin["out"], (x + 96, y), (x + 128, y))
        c.label((x + 128, y), out)
        c.label((x - 160, y + 16), "SIG", d=(-16, 0))
        c.res((x - 160, y + 16), (x - 48, y + 16), 10e3)
        c.wire((x - 48, y + 16), a.pin["+"])
        c.wire((x - 48, y + 16), (x - 48, y + 48))
        c.res((x - 48, y + 48), (x - 48, y + 144), rplus)
        c.gnd((x - 48, y + 144))
    diffamp(960, 208, 100e3, "Vout_diff", "(b) difference amplifier, G = 10")
    diffamp(960, 480, 101e3, "Vout_diff1", "(c) the same, one resistor 101k (1 %)")
    lab = labels(c)
    c.scope([lab["Vout_se"]], speed=32, vscale=2.0)
    c.scope([lab["Vout_diff"], lab["Vout_diff1"]], speed=32, vscale=0.5)

    def check(s):
        r = s.run(0.1, record=["GND_remote", "Vout_se", "Vout_diff", "Vout_diff1"])
        g, _ = sine_amp(r, "GND_remote", 0.04, 50)
        approx(g, 0.100, rel=0.01, what="ground difference")
        a_se, m_se = sine_amp(r, "Vout_se", 0.04, 50)
        approx(m_se, 0.372, rel=0.01, what="single-ended DC")
        approx(a_se, 1.00, rel=0.01, what="single-ended hum")
        a_d, m_d = sine_amp(r, "Vout_diff", 0.04, 50)
        approx(m_d, 0.372, rel=0.01, what="diff DC")
        approx(a_d, 0.0, absol=20e-6, what="diff hum (ideal)")
        a_d1, m_d1 = sine_amp(r, "Vout_diff1", 0.04, 50)
        approx(m_d1, 0.3721, rel=0.01, what="diff1 DC")
        approx(a_d1, 0.90e-3, rel=0.03, what="diff hum (1 % resistor)")
    return c, check


# ---------------------------------------------------------------------------
# 6. common return impedance: LED current in the ground of the gain stage
# ---------------------------------------------------------------------------
G2_RG, G2_RF = 10e3, 97.6e3
VIN_G2 = 0.18587                       # -> 2.000 V behind G2 = 10.76
R_TRACE = 0.1
R_LED = 100.0                          # 5 V / 100 Ohm = 50 mA (e.g. 5 LEDs)


def noise_shared_ground():
    """Gain stage G = 10.76 whose 10k returns through a ground trace (0.1 Ohm)
    shared with a switched 50 mA LED current, versus a star ground."""
    c = Circuit("noise_shared_ground", "Common ground impedance: LED current in the return path of the gain stage",
                timestep=1e-3, speed=40)
    c.text((48, 32), "Gain stage G = 1 + 97.6k/10k = 10.76, input 0.186 V -> 2.000 V. The LEDs (50 mA, switched at 5 Hz)")
    c.text((48, 56), "share 0.1 Ohm of ground trace with the 10k resistor (a). Star ground (b): separate returns.")
    c.rail((96, 192), VIN_G2, label_dir=(-32, 0))
    c.label((96, 192), "Vin", d=(0, -16))

    def stage(x, y, ground_node, out, title):
        c.text((x - 64, y - 64), title)
        c.label((x - 32, y - 16), "Vin", d=(-16, 0))
        c.wire((x - 32, y - 16), (x, y - 16))
        a = c.opamp((x, y), swap=True)
        c.wire(a.pin["-"], (x - 16, y + 16), (x - 16, y + 64))
        c.res((x - 16, y + 64), (x - 16, y + 160), G2_RG)
        if ground_node:
            c.label((x - 16, y + 160), ground_node, d=(0, 16))
        else:
            c.gnd((x - 16, y + 160))
        c.res((x - 16, y + 64), (x + 96, y + 64), G2_RF)
        c.wire((x + 96, y + 64), (x + 96, y))
        c.wire(a.pin["out"], (x + 96, y), (x + 128, y))
        c.label((x + 128, y), out)

    stage(320, 208, "GND_shared", "Vout_shared", "(a) shared return")
    stage(720, 208, None, "Vout_star", "(b) star ground")
    # LED driver and the shared trace
    x, y = 320, 544
    c.text((x - 192, y - 48), "LED load: 5 V / 100 Ohm = 50 mA, 5 Hz")
    c.rail((x - 96, y), 2.5, waveform="square", freq=5, bias=2.5, label_dir=(-32, 0))
    c.label((x - 96, y), "LED_drive", d=(0, -16))
    c.res((x - 96, y), (x - 96, y + 96), R_LED)
    c.wire((x - 96, y + 96), (x - 16, y + 96))
    c.label((x - 16, y + 96), "GND_shared", d=(0, -16))
    c.res((x - 16, y + 96), (x - 16, y + 192), R_TRACE)
    c.gnd((x - 16, y + 192))
    c.text((x + 16, y + 148), "ground trace 0.1 Ohm (10 cm, 0.3 mm)")
    lab = labels(c)
    c.scope([lab["Vout_shared"], lab["Vout_star"]], speed=64, vscale=2.5)
    c.scope([lab["GND_shared"]], speed=64, vscale=0.01)

    def check(s):
        r = s.run(0.4, record=["GND_shared", "Vout_shared", "Vout_star", "LED_drive"])
        on = r["LED_drive"] > 2.5
        off = ~on
        g_on = r["GND_shared"][on].mean()
        approx(g_on, 4.995e-3, rel=0.01, what="ground shift")
        approx(r["Vout_star"].mean(), 2.000, rel=0.002, what="star output")
        approx(r["Vout_shared"][off].mean(), 2.000, rel=0.002, what="shared, LEDs off")
        approx(r["Vout_shared"][on].mean(), 2.000 - 9.76 * 4.995e-3, rel=0.002,
               what="shared, LEDs on")                                     # 1.951 V
    return c, check


# ---------------------------------------------------------------------------
# 7. supply ripple and the RC filter
# ---------------------------------------------------------------------------
def noise_supply_filter():
    """5 V switching regulator with 50 mV pp ripple at 100 kHz; RC filter
    10 Ohm / 10 uF (fc = 1.6 kHz) for the analog supply (1 mA load)."""
    c = Circuit("noise_supply_filter", "Supply ripple: RC filter for the analog supply",
                timestep=1e-7, speed=10)
    c.text((48, 32), "Switching regulator: 5 V with 50 mV peak-to-peak ripple at 100 kHz")
    c.text((48, 56), "RC filter 10 Ohm / 10 uF (fc = 1.6 kHz), analog load 1 mA: ripple 0.63 mV pp, DC drop 10 mV")
    c.rail((96, 176), 0.025, waveform="triangle", freq=100e3, bias=5.0, label_dir=(-32, 0))
    c.label((96, 176), "V5_raw", d=(0, -16))
    c.res((96, 176), (256, 176), 10.0)
    c.cap((256, 176), (256, 304), 10e-6)
    c.gnd((256, 304))
    c.wire((256, 176), (416, 176))
    c.res((416, 176), (416, 304), 5e3)
    c.gnd((416, 304))
    c.text((432, 244), "analog part, 1 mA")
    c.wire((416, 176), (512, 176))
    c.label((512, 176), "V5_analog")
    lab = labels(c)
    c.scope([lab["V5_raw"]], speed=1, vscale=5.0)
    c.scope([lab["V5_analog"]], speed=1, vscale=5.0)

    def check(s):
        # start near the operating point: the capacitor needs 5 tau to charge
        for it in s.items:
            if it["k"] == "c":
                it["v"] = 5.0 * 5e3 / 5010.0
        r = s.run(0.6e-3, record=["V5_raw", "V5_analog"])
        k = r["t"] >= 0.5e-3
        pp_raw = r["V5_raw"][k].max() - r["V5_raw"][k].min()
        pp = r["V5_analog"][k].max() - r["V5_analog"][k].min()
        approx(pp_raw, 0.050, rel=0.01, what="raw ripple")
        est = 0.025 * 10e-6 / (4 * (10.0 * 5e3 / 5010.0) * 10e-6)  # A T / (4 R C)
        approx(est, 0.626e-3, rel=0.01, what="estimate")
        approx(pp, 0.63e-3, rel=0.03, what="filtered ripple")
        approx(r["V5_analog"][k].mean(), 4.990, rel=1e-3, what="DC after filter")
    return c, check


# ---------------------------------------------------------------------------
# 8. thermoelectric voltage and excitation reversal
# ---------------------------------------------------------------------------
V_TH = 20e-6


def _bridge_emf(c, x, y, vb, na, nb):
    """Capstone bridge at 50 C (Pt100 119.25 Ohm) fed with vb; a 20 uV
    thermoelectric voltage sits in the lead from the sensor tap to na."""
    xl, xr = x + 160, x + 320
    ym, yb = y + 128, y + 256
    c.vsrc((x, yb), (x, y), vb)
    c.gnd((x, yb))
    c.wire((x, y), (xl, y), (xr, y))
    c.res((xl, y), (xl, ym), R_TOP)
    c.res((xl, ym), (xl, yb), R50)
    c.res((xr, y), (xr, ym), R_TOP)
    c.res((xr, ym), (xr, yb), R0)
    c.wire((x, yb), (xl, yb), (xr, yb))
    c.vsrc((xl, ym), (xl - 96, ym), V_TH)          # thermal EMF in the lead
    c.label((xl - 96, ym), na, d=(0, -16))
    c.label((xr, ym), nb, d=(16, 0))
    voltmeter(c, (xl - 96, ym), (xr, ym))
    c.text((xl - 112, ym + 40), "20 uV")


def noise_thermal_emf():
    """Bridge with +4 V and -4 V excitation and 20 uV thermal EMF:
    (V+ - V-)/2 = Vd, (V+ + V-)/2 = thermal EMF."""
    c = Circuit("noise_thermal_emf", "Thermoelectric voltage: excitation reversal separates it from the signal",
                timestep=1e-4, speed=40)
    c.text((48, 32), "Pt100 at 50 C (119.25 Ohm): Vd = 18.68 mV. A copper / solder junction adds 20 uV (thermal EMF).")
    c.text((48, 56), "Reversing the excitation reverses Vd but not the EMF: (V1 - V2)/2 = 18.68 mV, (V1 %2B V2)/2 = 20 uV")
    c.text((112, 112), "excitation 4 V: V1 = Vd %2B 20 uV = 18.70 mV")
    _bridge_emf(c, 64, 144, VB, "A1", "B1")
    _ina(c, 592, 208, "A1", "B1", "V1x10")
    c.text((112, 512), "excitation -4 V: V2 = -Vd %2B 20 uV = -18.66 mV")
    _bridge_emf(c, 64, 544, -VB, "A2", "B2")
    _ina(c, 592, 608, "A2", "B2", "V2x10")

    def check(s):
        s.dc()
        vd = VB * (R50 / (R_TOP + R50) - R0 / (R_TOP + R0))
        approx(vd, 18.68e-3, rel=1e-3, what="Vd 50 C")
        v1 = s.v("A1") - s.v("B1")
        v2 = s.v("A2") - s.v("B2")
        approx(v1, 18.70e-3, rel=1e-3, what="V1")
        approx(v2, -18.66e-3, rel=1e-3, what="V2")
        approx((v1 - v2) / 2, vd, rel=1e-4, what="difference")
        approx((v1 + v2) / 2, V_TH, rel=1e-3, what="sum")
        approx(s.v("V1x10"), 0.1870, rel=1e-3, what="INA 1")
        approx(s.v("V2x10"), -0.1866, rel=1e-3, what="INA 2")
    return c, check


CIRCUITS = [noise_bandwidth, noise_rss, noise_cap_coupling, noise_mag_coupling,
            noise_ground_loop, noise_shared_ground, noise_supply_filter,
            noise_thermal_emf]
