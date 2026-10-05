"""Falstad examples for chapter 4: Bridge Circuits.

Capstone bridge (same design as Capstone.tex / capstone.py):
  Pt100, 100 Ohm (0 degC) .. 138.5 Ohm (100 degC), bridge fed from the
  4.00 V reference, R1 = R3 = 3.9 kOhm, R4 = 100 Ohm;
  sensor current 1.000 mA .. 0.990 mA; bridge output 0 .. 37.18 mV;
  INA G1 = 100k/10k = 10, gain stage G2 = 1 + 97.6k/10k = 10.76 -> 0 .. 4.00 V.
Exercise variant: Pt1000 at 5 V with R1 = R3 = 4.7 kOhm, R4 = 1 kOhm.
"""
from falstad import Circuit, Elm, Sim
from _check import approx

TITLE = "Bridge Circuits"

VB = 4.0
R_TOP = 3.9e3
R0 = 100.0
R100 = 138.5
R50 = 119.25
G1_R, G1_RF = 10e3, 100e3
G2_RG, G2_RF = 10e3, 97.6e3


def voltmeter(c, p1, p2):
    """CircuitJS voltmeter (ProbeElm 'p'), shows V(p1) - V(p2).
    Ideal (resistance 0 = no load); the simulator ignores it."""
    return c.add(Elm("p", p1, p2, 3, [0, 0, 0.0]))


def bridge_vd(rs, vb=VB, rt=R_TOP, r4=R0):
    """Exact output of the capstone-type bridge, V(sensor node) - V(ref node)."""
    return vb * (rs / (rt + rs) - r4 / (rt + r4))


def _bridge(c, x, y, r1, rs, r3, r4, na, nb, vsrc=True, vb=VB, meter=True,
            noise=None):
    """Wheatstone bridge with its upper-left corner at (x, y).
    Left leg: r1 (top), rs (bottom, node na); right leg: r3, r4 (node nb).
    Supply 64 px left of the left leg. Returns dict of elements."""
    xl, xr = x + 160, x + 320
    ym, yb = y + 128, y + 256
    el = {}
    if vsrc:
        el["src"] = c.vsrc((x, yb), (x, y), vb)
        c.gnd((x, yb))
    c.wire((x, y), (xl, y), (xr, y))
    el["r1"] = c.res((xl, y), (xl, ym), r1)
    if noise is None:
        el["rs"] = c.res((xl, ym), (xl, yb), rs)
    else:
        el["rs"] = c.res((xl, ym), (xl, ym + 64), rs)
        el["noise"] = c.vsrc((xl, yb), (xl, ym + 64), noise, waveform="ac",
                             freq=50)
    el["r3"] = c.res((xr, y), (xr, ym), r3)
    el["r4"] = c.res((xr, ym), (xr, yb), r4)
    c.wire((x, yb), (xl, yb), (xr, yb))
    if meter:
        voltmeter(c, (xl, ym), (xr, ym))
    c.label((xl, ym), na, d=(-16, 0))
    c.label((xr, ym), nb, d=(16, 0))
    return el


def _ina(c, x, y, inp, inm, out, rg=G1_R, rf=G1_RF):
    """Instrumentation amplifier: buffers for inm (top) and inp (bottom),
    difference amplifier Vout = rf/rg*(V(inp)-V(inm)). Upper buffer at (x, y).
    Output at (x + 352, y + 64)."""
    a1 = c.opamp((x, y), swap=False)            # - top, + bottom
    c.label(a1.pin["+"], inm, d=(-16, 0))
    c.wire(a1.pin["-"], (x - 16, y - 16), (x - 16, y - 48), (x + 80, y - 48),
           (x + 80, y), a1.pin["out"])
    a2 = c.opamp((x, y + 128), swap=False)
    c.label(a2.pin["+"], inp, d=(-16, 0))
    c.wire(a2.pin["-"], (x - 16, y + 112), (x - 16, y + 80), (x + 80, y + 80),
           (x + 80, y + 128), a2.pin["out"])
    # difference amplifier
    xd = x + 224
    c.wire((x + 80, y), (x + 96, y))
    c.res((x + 96, y), (x + 192, y), rg)
    c.wire((x + 80, y + 128), (x + 96, y + 128))
    c.res((x + 96, y + 128), (x + 192, y + 128), rg)
    a3 = c.opamp((xd, y + 64), swap=False)      # - at y+48, + at y+80
    c.wire((x + 192, y - 64), (x + 192, y), (x + 192, y + 48), a3.pin["-"])
    c.res((x + 192, y - 64), (xd + 96, y - 64), rf)
    c.wire((xd + 96, y - 64), (xd + 96, y + 64))
    c.wire(a3.pin["out"], (xd + 96, y + 64), (xd + 128, y + 64))
    c.label((xd + 128, y + 64), out, d=(0, -16))
    c.wire((x + 192, y + 128), (x + 192, y + 80), a3.pin["+"])
    c.res((x + 192, y + 128), (x + 192, y + 224), rf)
    c.gnd((x + 192, y + 224))
    return a3


def _gain_stage(c, x, y, inp, out, rg=G2_RG, rf=G2_RF):
    """Non-inverting amplifier, + input at (x, y-16) from label inp."""
    a = c.opamp((x, y), swap=True)              # + top (y-16), - bottom (y+16)
    c.label(a.pin["+"], inp, d=(-16, 0))
    c.wire(a.pin["-"], (x - 16, y + 16), (x - 16, y + 64))
    c.res((x - 16, y + 64), (x - 16, y + 160), rg)
    c.gnd((x - 16, y + 160))
    c.res((x - 16, y + 64), (x + 96, y + 64), rf)
    c.wire((x + 96, y + 64), (x + 96, y))
    c.wire(a.pin["out"], (x + 96, y), (x + 128, y))
    c.label((x + 128, y), out)
    return a


# ---------------------------------------------------------------------------
def wheatstone():
    """Wheatstone bridge 5 V, 1k/1k/1k and Rx = 1010 Ohm (slider)."""
    c = Circuit("wheatstone", "Wheatstone bridge: 1 percent change of Rx")
    c.text((48, 48), "Wheatstone bridge, 5 V: Rx = 1010 Ohm (dR/R = 1 %), drag the slider")
    el = _bridge(c, 64, 112, 1e3, 1010, 1e3, 1e3, "VA", "VB", vb=5.0)
    c.slider(el["rs"], 500, 1500, "Rx")
    c.text((448, 256), "voltmeter shows Vd = VA - VB")

    def check(s):
        s.dc()
        vd = s.v("VA") - s.v("VB")
        approx(vd, 12.44e-3, rel=0.003, what="Vd at 1010 Ohm")
        approx(5 / 4 * 0.01, 12.5e-3, what="small-signal estimate")
        # large change: Rx = 1500 Ohm -> exact 0.500 V, estimate 0.625 V
        el["rs"].params[0] = 1500.0
        s2 = Sim(c).dc()
        el["rs"].params[0] = 1010.0
        approx(s2.v("VA") - s2.v("VB"), 0.500, what="Vd at 1500 Ohm")
    return c, check


def bridge_types():
    """Quarter, half and full bridge with 350 Ohm strain gauges, dR/R = 0.2 %."""
    c = Circuit("bridge_types", "Quarter, half and full bridge (350 Ohm gauges, dR = 0.7 Ohm)")
    c.text((48, 32), "Strain gauges 350 Ohm, strain 1000 um/m, k = 2: dR = 0.7 Ohm, supply 5 V")
    R, d = 350.0, 0.7
    c.text((112, 80), "quarter bridge")
    _bridge(c, 48, 112, R, R + d, R, R, "Aq", "Bq", vb=5.0)
    c.text((496, 80), "half bridge")
    _bridge(c, 432, 112, R - d, R + d, R, R, "Ah", "Bh", vb=5.0)
    c.text((880, 80), "full bridge")
    _bridge(c, 816, 112, R - d, R + d, R + d, R - d, "Af", "Bf", vb=5.0)

    def check(s):
        s.dc()
        approx(s.v("Aq") - s.v("Bq"), 2.4975e-3, rel=0.002, what="quarter")
        approx(s.v("Ah") - s.v("Bh"), 5.000e-3, rel=0.002, what="half")
        approx(s.v("Af") - s.v("Bf"), 10.00e-3, rel=0.002, what="full")
    return c, check


def pt100_bridge():
    """Capstone bridge: 4.00 V, 3.9k/3.9k/100, Pt100 100..138.5 Ohm."""
    c = Circuit("pt100_bridge", "Pt100 bridge of the capstone task (0 .. 100 degC)")
    c.text((48, 48), "Pt100 bridge from the 4.00 V reference: R1 = R3 = 3.9k, R4 = 100 Ohm")
    el = _bridge(c, 64, 112, R_TOP, R0, R_TOP, R0, "Vs", "Vr")
    c.slider(el["rs"], 100, 138.5, "Sensor R (0..100 C)")
    c.text((448, 224), "0 C: 100 Ohm, 50 C: 119.25 Ohm, 100 C: 138.5 Ohm")

    def check(s):
        rs = el["rs"]
        res = {}
        for r in (R0, R50, R100):
            rs.params[0] = r
            s2 = Sim(c).dc()
            res[r] = (s2.v("Vs") - s2.v("Vr"), s2.i_res(rs), s2.v("Vr"), s2.v("Vs"))
        rs.params[0] = R0
        approx(res[R0][0], 0.0, absol=1e-7, what="Vd 0 C")
        approx(res[R50][0], 18.68e-3, rel=0.002, what="Vd 50 C")
        approx(res[R100][0], 37.18e-3, rel=0.001, what="Vd 100 C")
        approx(res[R0][1], 1.000e-3, rel=0.001, what="I 0 C")
        approx(res[R100][1], 0.990e-3, rel=0.002, what="I 100 C")
        approx(res[R0][2], 0.100, rel=0.001, what="Vr")
        approx(res[R100][3], 0.1372, rel=0.002, what="Vs 100 C")
        approx(bridge_vd(R100), 37.18e-3, rel=0.001, what="formula")
        approx(res[R50][0] - res[R100][0] / 2, 0.089e-3, rel=0.03, what="nonlinearity 50 C")
    return c, check


def pt1000_bridge():
    """Exercise variant: Pt1000 at 5 V with 4.7k/4.7k/1k."""
    c = Circuit("pt1000_bridge", "Pt1000 bridge at 5 V with R1 = R3 = 4.7 kOhm (exercise)")
    c.text((48, 48), "Pt1000 bridge: 5 V, R1 = R3 = 4.7k, R4 = 1k; sensor 1000 .. 1385 Ohm")
    el = _bridge(c, 64, 112, 4.7e3, 1000, 4.7e3, 1000, "Vs", "Vr", vb=5.0)
    c.slider(el["rs"], 1000, 1385, "Sensor R (0..100 C)")

    def check(s):
        rs = el["rs"]
        res = {}
        for r in (1000.0, 1192.5, 1385.0):
            rs.params[0] = r
            s2 = Sim(c).dc()
            res[r] = (s2.v("Vs") - s2.v("Vr"), s2.i_res(rs))
        rs.params[0] = 1000.0
        approx(res[1000.0][0], 0.0, absol=1e-6, what="Vd 0 C")
        approx(res[1192.5][0], 0.1347, rel=0.002, what="Vd 50 C")
        approx(res[1385.0][0], 0.2609, rel=0.002, what="Vd 100 C")
        approx(res[1000.0][1], 0.877e-3, rel=0.002, what="I 0 C")
        approx(res[1385.0][1], 0.822e-3, rel=0.002, what="I 100 C")
    return c, check


def bridge_single_ended():
    """Why a single-ended amplifier fails: gain 107.6 applied to Vs alone."""
    c = Circuit("bridge_single_ended", "Single-ended amplifier at a bridge node fails")
    c.text((48, 48), "Non-inverting amplifier G = 1 + 1066k/10k = 107.6 at Vs only: it amplifies the common mode")
    el = _bridge(c, 64, 112, R_TOP, R0, R_TOP, R0, "Vs", "Vr")
    c.slider(el["rs"], 100, 138.5, "Sensor R (0..100 C)")
    _gain_stage(c, 576, 240, "Vs", "Vout", rg=10e3, rf=1066e3)
    c.text((448, 448), "op-amp supply 15 V: Vout = 10.75 V at 0 C instead of 0 V")

    def check(s):
        s.dc()
        approx(s.v("Vs"), 0.100, rel=0.001, what="Vs")
        approx(s.v("Vout"), 10.75, rel=0.001, what="Vout 0 C")
        el["rs"].params[0] = R100
        s2 = Sim(c).dc()
        el["rs"].params[0] = R0
        approx(s2.v("Vout"), 14.76, rel=0.002, what="Vout 100 C")
    return c, check


def _front_end(c, noise=None):
    el = _bridge(c, 48, 112, R_TOP, R0, R_TOP, R0, "Vs", "Vr", noise=noise)
    c.slider(el["rs"], 100, 138.5, "Sensor R (0..100 C)")
    _ina(c, 512, 176, "Vs", "Vr", "Vdiff")
    _gain_stage(c, 976, 256, "Vdiff", "Vout")
    return el


def bridge_ina():
    """Bridge + instrumentation amplifier (G1 = 10) + gain stage (10.76)."""
    c = Circuit("bridge_ina", "Pt100 bridge, instrumentation amplifier and gain stage: 0 .. 4.00 V")
    c.text((48, 32), "Bridge, instrumentation amplifier G1 = 100k/10k = 10, gain stage G2 = 1 + 97.6k/10k = 10.76")
    el = _front_end(c)
    c.text((448, 464), "buffers: no load on the bridge; difference amplifier: rejects the 0.1 V common mode")

    def check(s):
        out = {}
        for r in (R0, R50, R100):
            el["rs"].params[0] = r
            s2 = Sim(c).dc()
            out[r] = (s2.v("Vdiff"), s2.v("Vout"))
        el["rs"].params[0] = R0
        approx(out[R0][1], 0.0, absol=2e-3, what="Vout 0 C")
        approx(out[R100][0], 0.3718, rel=0.002, what="Vdiff 100 C")
        approx(out[R50][1], 2.010, rel=0.003, what="Vout 50 C")
        approx(out[R100][1], 4.00, rel=0.002, what="Vout 100 C")
    return c, check


def bridge_50hz():
    """Capstone front end with 5 mV / 50 Hz interference in series with the sensor."""
    c = Circuit("bridge_50hz", "50 Hz interference (5 mV) in series with the sensor",
                timestep=2e-5, speed=60)
    c.text((48, 32), "5 mV, 50 Hz in series with the sensor (overhead lamps): it is a differential signal")
    _front_end(c, noise=0.005)
    labels = {e.params[0]: e for e in c.elms if e.kind == "207"}
    c.scope([labels["Vs"]], speed=32, vscale=0.01)
    c.scope([labels["Vout"]], speed=32, vscale=1)

    def check(s):
        r = s.run(0.06, record=["Vs", "Vout"])
        m = r["t"] > 0.02
        app_vs = (r["Vs"][m].max() - r["Vs"][m].min()) / 2
        app_out = (r["Vout"][m].max() - r["Vout"][m].min()) / 2
        approx(app_vs, 4.875e-3, rel=0.01, what="noise amplitude at Vs")
        approx(app_out, 0.5245, rel=0.01, what="noise amplitude at Vout")
        approx(r["Vout"][m].mean(), 0.0, absol=5e-3, what="mean Vout")
    return c, check


def bridge_3wire():
    """2-wire and 3-wire connection of a Pt100 with 0.5 Ohm per lead."""
    c = Circuit("bridge_3wire", "Lead resistance: 2-wire and 3-wire connection (0.5 Ohm per lead)")
    c.text((48, 32), "Pt100, leads 0.5 Ohm each. Left: 2-wire, right: 3-wire")
    RL = 0.5
    # 2-wire: two leads in series with the sensor
    x, y = 48, 112
    c.vsrc((x, y + 320), (x, y), VB)
    c.gnd((x, y + 320))
    c.wire((x, y), (x + 160, y), (x + 320, y))
    c.res((x + 160, y), (x + 160, y + 96), R_TOP)
    c.res((x + 160, y + 96), (x + 160, y + 160), RL)
    rs2 = c.res((x + 160, y + 160), (x + 160, y + 256), R0)
    c.res((x + 160, y + 256), (x + 160, y + 320), RL)
    c.res((x + 320, y), (x + 320, y + 96), R_TOP)
    c.res((x + 320, y + 96), (x + 320, y + 320), R0)
    c.wire((x, y + 320), (x + 160, y + 320), (x + 320, y + 320))
    voltmeter(c, (x + 160, y + 96), (x + 320, y + 96))
    c.label((x + 160, y + 96), "A2", d=(-16, 0))
    c.label((x + 320, y + 96), "B2")
    c.box((x + 112, y + 128), (x + 240, y + 288))
    c.text((x + 64, y + 368), "sensor and 2 leads")
    # 3-wire: lead 1 in the sensor arm, lead 2 in the R4 arm, lead 3 in the supply return
    x = 528
    c.vsrc((x, y + 320), (x, y), VB)
    c.gnd((x, y + 320))
    c.wire((x, y), (x + 160, y), (x + 320, y))
    c.res((x + 160, y), (x + 160, y + 96), R_TOP)
    c.res((x + 160, y + 96), (x + 160, y + 160), RL)
    rs3 = c.res((x + 160, y + 160), (x + 160, y + 256), R0)
    c.res((x + 320, y), (x + 320, y + 96), R_TOP)
    c.res((x + 320, y + 96), (x + 320, y + 192), R0)
    c.res((x + 320, y + 192), (x + 320, y + 256), RL)
    c.wire((x + 160, y + 256), (x + 240, y + 256), (x + 320, y + 256))
    c.res((x + 240, y + 256), (x + 240, y + 320), RL)
    c.wire((x, y + 320), (x + 240, y + 320))
    voltmeter(c, (x + 160, y + 96), (x + 320, y + 96))
    c.label((x + 160, y + 96), "A3", d=(-16, 0))
    c.label((x + 320, y + 96), "B3")
    c.text((x + 64, y + 368), "lead 3 carries the supply current")
    c.slider(rs2, 100, 138.5, "Sensor R 2-wire")
    c.slider(rs3, 100, 138.5, "Sensor R 3-wire")

    def check(s):
        s.dc()
        approx(s.v("A2") - s.v("B2"), 0.9753e-3, rel=0.003, what="2-wire error 0 C")
        approx(s.v("A3") - s.v("B3"), 0.0, absol=1e-7, what="3-wire 0 C")
        rs2.params[0] = rs3.params[0] = R100
        s2 = Sim(c).dc()
        rs2.params[0] = rs3.params[0] = R0
        approx(s2.v("A2") - s2.v("B2"), 38.13e-3, rel=0.002, what="2-wire 100 C")
        approx(s2.v("A3") - s2.v("B3"), 37.16e-3, rel=0.002, what="3-wire 100 C")
    return c, check


CIRCUITS = [wheatstone, bridge_types, pt100_bridge, pt1000_bridge,
            bridge_single_ended, bridge_ina, bridge_50hz, bridge_3wire]
