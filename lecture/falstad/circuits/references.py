"""Falstad examples for chapter 3: Voltage References."""
from falstad import Circuit, Elm, Sim
from _check import approx

TITLE = "Voltage References"


# ---------------------------------------------------------------------------
# dc_ramp(): operating point by ramping the DC sources up from zero
# (source stepping). Needed for the circuits with an op-amp and a
# transistor in the loop (Brokaw cell, TL431 model), where Newton started
# from 0 V does not converge in falstad.Sim. CircuitJS itself finds the
# operating point in its normal transient run.
# ---------------------------------------------------------------------------
def dc_ramp(circuit, steps=2000, only=None):
    """DC operating point found by ramping the DC sources up from 0
    (all of them, or the elements in `only`)."""
    s = Sim(circuit)
    srcs = [(e, e.params[2]) for e in circuit.elms
            if e.kind in ("v", "R") and int(e.params[0]) == 0
            and (only is None or e in only)]
    cur = [(e, e.params[0]) for e in circuit.elms if e.kind == "i"
           and (only is None or e in only)]
    try:
        for k in range(1, steps + 1):
            for e, v in srcs:
                e.params[2] = v * k / steps
            for e, i in cur:
                e.params[0] = i * k / steps
            s.step()
    finally:                    # restore the element values in any case
        for e, v in srcs:
            e.params[2] = v
        for e, i in cur:
            e.params[0] = i
    for _ in range(5):
        s.step()
    return s


# ---------------------------------------------------------------------------
def zener_resistor():
    """Zener 5.6 V fed through 1.2 kOhm: line and load regulation."""
    c = Circuit("zener_resistor", "Zener reference 5.6 V with series resistor: line and load regulation")
    c.text((48, 32), "Zener 5.6 V with series resistor 1.2k")
    srcs = []
    for i, (vs, load, name) in enumerate(((12, None, "Vz12"), (14, None, "Vz14"),
                                          (12, 2.2e3, "Vz12L"))):
        x = 64 + 320 * i
        srcs.append(c.vsrc((x, 384), (x, 128), vs))
        c.gnd((x, 384))
        c.wire((x, 128), (x + 128, 128))
        c.res((x + 128, 128), (x + 128, 256), 1.2e3)
        c.zener((x + 128, 384), (x + 128, 256), 5.6)
        c.wire((x, 384), (x + 128, 384))
        if load:
            c.wire((x + 128, 256), (x + 224, 256))
            c.res((x + 224, 256), (x + 224, 384), load)
            c.wire((x + 128, 384), (x + 224, 384))
            c.label((x + 224, 256), name)
        else:
            c.label((x + 128, 256), name)
        c.text((x, 96), "%d V%s" % (vs, ", load 2.2k" if load else ""))
    c.slider(srcs[0], 8, 16, "Supply V (left)")

    def check(s):
        s.dc()
        v12, v14, v12l = s.v("Vz12"), s.v("Vz14"), s.v("Vz12L")
        approx(v12, 5.602, rel=0.001, what="Vz at 12 V")
        approx(v14 - v12, 7.0e-3, rel=0.03, what="line regulation 2 V")
        approx(v12 - v12l, 16.6e-3, rel=0.03, what="load regulation 2.5 mA")
    return c, check


def zener_current_source():
    """Resistor feed vs. current source feed (5 mA, 100 kOhm output resistance)."""
    c = Circuit("zener_current_source", "Zener fed by a resistor and by a current source")
    c.text((48, 32), "Supply 12 V (slider). Left: 1.2k, right: current source 5 mA")
    src = c.vsrc((64, 400), (64, 112), 12)
    c.gnd((64, 400))
    c.wire((64, 112), (224, 112), (480, 112))
    # resistor feed
    c.res((224, 112), (224, 256), 1.2e3)
    c.zener((224, 400), (224, 256), 5.6)
    c.label((224, 256), "VzR")
    # current source feed with output resistance 100k
    c.isrc((480, 112), (480, 256), 5e-3)
    c.wire((480, 112), (576, 112))
    c.res((576, 112), (576, 256), 100e3)
    c.wire((480, 256), (576, 256))
    c.zener((480, 400), (480, 256), 5.6)
    c.label((480, 256), "VzI", d=(-16, 0))
    c.wire((64, 400), (224, 400), (480, 400))
    c.text((608, 176), "real current source:")
    c.text((608, 200), "5 mA with 100k output resistance")
    c.slider(src, 8, 16, "Supply V")

    def check(s):
        res = {}
        for v in (12.0, 14.0):
            src.params[2] = v
            s2 = Sim(c).dc()
            res[v] = (s2.v("VzR"), s2.v("VzI"))
        src.params[2] = 12.0
        approx(res[12.0][1], 5.600, rel=0.001, what="VzI at 12 V")
        approx(res[14.0][0] - res[12.0][0], 7.0e-3, rel=0.03, what="dVzR")
        approx(res[14.0][1] - res[12.0][1], 0.10e-3, rel=0.05, what="dVzI")
    return c, check


def _parallel_npn(c, x, y, n):
    """n diode-connected NPN transistors in parallel. First base at (x, y).
    Returns (top node, bottom node) = (collector/base bus, emitter bus)."""
    pts_top, pts_bot = [], []
    for i in range(n):
        xb = x + 64 * i
        t = c.npn((xb, y))
        c.wire(t.pin["b"], (xb, y - 32))
        c.wire(t.pin["c"], (xb + 32, y - 32))
        c.wire(t.pin["e"], (xb + 32, y + 32))
        pts_top += [(xb, y - 32), (xb + 32, y - 32)]
        pts_bot += [(xb + 32, y + 32)]
    if len(pts_top) > 1:
        c.wire(*pts_top)
    if len(pts_bot) > 1:
        c.wire(*pts_bot)
    return pts_top[0], pts_bot[0]


def delta_vbe():
    """Delta-VBE: current density ratio 8 (area) and 10 (current)."""
    c = Circuit("delta_vbe", "Delta VBE = VT ln(N): 8 parallel transistors, current ratio 10")
    c.text((48, 32), "Diode-connected transistors: Q1 at 100 uA, 8 x Q at 100 uA, Q at 10 uA")
    c.vsrc((48, 416), (48, 96), 5)
    c.gnd((48, 416))
    groups = (("VBE1", 160, 1, 100e-6), ("VBE8", 320, 8, 100e-6),
              ("VBE10", 896, 1, 10e-6))
    top, bot = [(48, 96)], [(48, 416)]
    for name, x, n, i in groups:
        _parallel_npn(c, x, 288, n)
        xs = x + 32
        c.isrc((xs, 96), (xs, 224), i)
        c.wire((xs, 224), (xs, 256))
        c.wire((xs, 320), (xs, 416))
        c.label((xs, 224), name, d=(16, 0))
        c.text((x - 16, 456), "%d x Q, %g uA" % (n, i * 1e6))
        top.append((xs, 96))
        bot.append((xs, 416))
    c.wire(*top)
    c.wire(*bot)

    def check(s):
        s.dc()
        v1, v8, v10 = s.v("VBE1"), s.v("VBE8"), s.v("VBE10")
        approx(v1, 0.536, rel=0.002, what="VBE at 100 uA")
        approx(v1 - v8, 53.8e-3, rel=0.003, what="dVBE area 8")
        approx(v1 - v10, 59.6e-3, rel=0.003, what="dVBE current 10")
    return c, check


def brokaw_cell():
    """Brokaw bandgap cell: Q1 = 8 parallel transistors, Q2 = 1 transistor."""
    c = Circuit("brokaw_cell", "Brokaw bandgap cell (VBE of Q2 plus 2 R1/R2 dVBE)")
    c.text((48, 32), "Brokaw cell: the op-amp forces equal collector currents in Q2 (1x) and Q1 (8x)")
    c.vsrc((48, 528), (48, 80), 5)
    c.gnd((48, 528))
    c.wire((48, 80), (288, 80), (896, 80))
    # Q2, area 1
    q2 = c.npn((256, 288))
    c.res((288, 80), (288, 208), 10e3)
    c.wire((288, 208), q2.pin["c"])
    c.label((288, 208), "C2", d=(16, 0))
    # Q1, area 8: collectors, bases and emitters in parallel
    cols, bases, emis = [], [], []
    for i in range(8):
        xb = 416 + 64 * i
        t = c.npn((xb, 288))
        c.wire(t.pin["c"], (xb + 32, 240))
        c.wire(t.pin["e"], (xb + 32, 336))
        c.wire(t.pin["b"], (xb, 368))
        cols.append((xb + 32, 240))
        emis.append((xb + 32, 336))
        bases.append((xb, 368))
    c.wire(*cols)
    c.wire(*emis)
    c.res((896, 80), (896, 208), 10e3)
    c.wire((896, 208), (896, 240))
    c.label((896, 208), "C1", d=(16, 0))
    # bases of Q1 and Q2 = output
    c.wire(q2.pin["b"], (256, 368), *bases)
    c.label((256, 368), "VBG", d=(-16, 0))
    # emitter resistors
    r2 = c.res((896, 336), (896, 432), 1e3)
    c.wire(q2.pin["e"], (288, 432), (592, 432), (896, 432))
    r1 = c.res((592, 432), (592, 528), 5.6e3)
    c.label((592, 432), "VE", d=(0, -16))
    c.wire((48, 528), (592, 528))
    # op-amp: + = C2, - = C1, output drives the bases
    a = c.opamp((128, 160), vmax=5, vmin=0)
    c.label(a.pin["-"], "C1", d=(-16, 0))
    c.label(a.pin["+"], "C2", d=(-16, 0))
    c.label(a.pin["out"], "VBG")
    c.text((656, 464), "R2 = 1k: I = dVBE / R2")
    c.text((656, 496), "R1 = 5.6k: VE = 2 I R1 (PTAT)")
    c.slider(r1, 3e3, 9e3, "R1 (PTAT gain)")

    def check(s):
        s = dc_ramp(c)
        vbg, ve = s.v("VBG"), s.v("VE")
        dvbe = s.v(r2.p1) - s.v(r2.p2)
        approx(dvbe, 53.8e-3, rel=0.01, what="dVBE across R2")
        approx(s.v("C1"), s.v("C2"), rel=1e-4, what="equal collector voltages")
        approx(ve, 0.602, rel=0.005, what="VE (PTAT part)")
        approx(vbg - ve, 0.520, rel=0.005, what="VBE of Q2")
        approx(vbg, 1.122, rel=0.003, what="VBG")
    return c, check


def shunt_ref():
    """TL431-style shunt reference (behavioural model) set to 4.00 V."""
    c = Circuit("shunt_ref", "Shunt reference (TL431 model) set to 4.00 V with 12k / 20k")
    c.text((48, 32), "TL431 model: op-amp, internal 2.5 V, shunt transistor. Vout = 2.5 V (1 R1/R2)".replace("(1 ", "(1 + "))
    src = c.vsrc((48, 448), (48, 96), 12)
    c.gnd((48, 448))
    c.wire((48, 96), (176, 96))
    c.res((176, 96), (176, 192), 1e3)
    c.wire((176, 192), (336, 192), (576, 192), (608, 192))
    c.label((608, 192), "VK")
    # divider
    c.res((336, 192), (336, 288), 12e3)
    c.res((336, 288), (336, 448), 20e3)
    c.label((336, 288), "REF", d=(-16, 0))
    # TL431 model inside the box
    a = c.opamp((432, 320), swap=True, vmax=12, vmin=0, gain=1e4)   # + top (304), - bottom (336)
    c.wire((336, 288), (416, 288), (416, 304), a.pin["+"])
    c.rail((416, 400), 2.5, up=False)
    c.wire(a.pin["-"], (416, 336), (416, 400))
    c.res(a.pin["out"], (544, 320), 10e3)
    q = c.npn((544, 320))
    c.wire(q.pin["c"], (576, 192))
    c.wire(q.pin["e"], (576, 448))
    c.wire((48, 448), (336, 448), (576, 448))
    c.box((384, 240), (624, 432))
    c.text((400, 256), "TL431 (model)")
    c.slider(src, 6, 15, "Supply V")

    def check(s):
        s = dc_ramp(c, 10000, only=[src])
        approx(s.v("VK"), 4.00, rel=0.001, what="VK at 12 V")
        approx(s.v("REF"), 2.50, rel=0.001, what="REF")
        ik = (12 - s.v("VK")) / 1e3 - s.v("VK") / 32e3
        approx(ik, 7.875e-3, rel=0.005, what="cathode current")
        src.params[2] = 6.0
        s2 = dc_ramp(c, 10000, only=[src])
        src.params[2] = 12.0
        approx(s2.v("VK"), 4.00, rel=0.001, what="VK at 6 V")
    return c, check


def _ladder(c, x, ytop, n=8, r=1e3, step=48, prefix="T"):
    """Reference ladder of n resistors from (x, ytop) down; taps labelled."""
    els = []
    for k in range(n):
        y1, y2 = ytop + step * k, ytop + step * (k + 1)
        els.append(c.res((x, y1), (x, y2), r))
        if k < n - 1:
            c.label((x, y2), "%s%d" % (prefix, n - 1 - k), d=(16, 0))
    c.gnd((x, ytop + step * n))
    return els


def ref_divider_loaded():
    """5 V reference, divider to 4 V: open, loaded by the ladder (8k), buffered."""
    c = Circuit("ref_divider_loaded", "Divider 10k/40k from a 5 V reference: open, loaded by an 8k ladder, buffered")
    c.text((48, 32), "5.00 V reference, divider 10k / 40k. Ladder 8 x 1k = 8k")
    for i, name in enumerate(("Vopen", "Vload", "Vbuf")):
        x = 64 + 288 * i
        c.vsrc((x, 416), (x, 128), 5)
        c.gnd((x, 416))
        c.wire((x, 128), (x + 96, 128))
        c.res((x + 96, 128), (x + 96, 256), 10e3)
        c.res((x + 96, 256), (x + 96, 416), 40e3)
        c.wire((x, 416), (x + 96, 416))
        if i == 0:
            c.label((x + 96, 256), name)
            c.text((x, 96), "open")
        elif i == 1:
            c.wire((x + 96, 256), (x + 192, 256))
            c.res((x + 192, 256), (x + 192, 416), 8e3)
            c.wire((x + 96, 416), (x + 192, 416))
            c.label((x + 192, 256), name, d=(0, -16))
            c.text((x, 96), "ladder (8k) at the tap")
        else:
            c.text((x, 96), "follower, then ladder")
    # buffered version
    x = 64 + 576
    a = c.opamp((x + 160, 272), swap=True)    # + top at 256, - bottom 288
    c.wire((x + 96, 256), a.pin["+"])
    c.wire(a.pin["-"], (x + 144, 288), (x + 144, 336), (x + 240, 336), (x + 240, 272))
    c.wire(a.pin["out"], (x + 240, 272), (x + 272, 272))
    c.res((x + 272, 272), (x + 272, 416), 8e3)
    c.gnd((x + 272, 416))
    c.label((x + 272, 272), "Vbuf", d=(0, -16))

    def check(s):
        s.dc()
        approx(s.v("Vopen"), 4.00, rel=0.001, what="open")
        approx(s.v("Vload"), 2.00, rel=0.002, what="loaded")
        approx(s.v("Vbuf"), 4.00, rel=0.001, what="buffered")
    return c, check


def ref_buffer_ladder():
    """2.5 V reference, non-inverting amplifier G = 1.6 -> 4.00 V, 8 x 1k ladder."""
    c = Circuit("ref_buffer_ladder", "2.5 V reference scaled to 4.00 V (G = 1.6) driving the 8 x 1k ladder")
    c.text((48, 32), "2.5 V reference, non-inverting amplifier G = 1 + 12k/20k = 1.6")
    c.vsrc((64, 416), (64, 240), 2.5)
    c.gnd((64, 416))
    c.label((64, 240), "V25", d=(0, -16))
    a = c.opamp((192, 256), swap=True)       # + top 240, - bottom 272
    c.wire((64, 240), a.pin["+"])
    c.wire(a.pin["-"], (176, 272), (176, 336))
    c.res((176, 336), (176, 432), 20e3)
    c.gnd((176, 432))
    c.res((176, 336), (288, 336), 12e3)
    c.wire((288, 336), (288, 256))
    c.wire(a.pin["out"], (288, 256), (352, 256), (352, 128), (448, 128))
    c.label((352, 128), "VREF4", d=(0, -16))
    lad = _ladder(c, 448, 128)
    c.text((512, 64), "ladder 8 x 1k: taps T7 .. T1 every 0.5 V")

    def check(s):
        s.dc()
        approx(s.v("VREF4"), 4.00, rel=0.001, what="VREF4")
        approx(s.v("T4"), 2.00, rel=0.001, what="T4")
        approx(s.v("T1"), 0.50, rel=0.001, what="T1")
        approx(s.i_res(lad[0]), 0.5e-3, rel=0.001, what="ladder current")
    return c, check


def ratiometric():
    """Ratiometric: sensor divider and ladder from the same reference."""
    c = Circuit("ratiometric", "Ratiometric measurement: mini flash ADC with 3 comparators")
    c.text((48, 24), "Left: sensor divider and ladder from VREF (ratiometric).")
    c.text((48, 48), "Right: sensor divider from a fixed 4.00 V, ladder from VREF. Change VREF")
    vref = c.vsrc((48, 448), (48, 112), 4.0)
    c.gnd((48, 448))
    c.label((48, 112), "VREF", d=(0, -16))
    c.vsrc((48 + 1024, 448), (48 + 1024, 304), 4.0)
    c.gnd((48 + 1024, 448))
    c.label((48 + 1024, 304), "V4", d=(0, -16))

    def adc(x0, vsup, vin, prefix):
        # sensor divider
        c.label((x0, 112), vsup, d=(0, -16))
        c.res((x0, 112), (x0, 208), 1e3)
        rs = c.res((x0, 208), (x0, 336), 2.7e3)
        c.gnd((x0, 336))
        c.label((x0, 208), vin, d=(-16, 0))
        # ladder 4 x 1k
        xl = x0 + 112
        c.label((xl, 112), "VREF", d=(0, -16))
        for k in range(4):
            c.res((xl, 112 + 80 * k), (xl, 192 + 80 * k), 1e3)
        c.gnd((xl, 432))
        for k in range(3):        # taps 3/4, 1/2, 1/4 VREF
            ty = 192 + 80 * k
            cmp_ = c.comparator((xl + 128, ty + 16))     # - at ty, + at ty+32
            c.wire((xl, ty), cmp_.pin["-"])
            c.label(cmp_.pin["+"], vin, d=(-16, 0))
            c.label(cmp_.pin["out"], "%s%d" % (prefix, 3 - k))
        return rs

    rs1 = adc(176, "VREF", "VIN1", "D")
    rs2 = adc(608, "V4", "VIN2", "E")
    c.slider(vref, 3.0, 5.0, "VREF")
    c.slider(rs1, 500, 4000, "Sensor R left")
    c.slider(rs2, 500, 4000, "Sensor R right")

    def codes(sim, p):
        return sum(1 for k in (1, 2, 3) if sim.v("%s%d" % (p, k)) > 2.5)

    def check(s):
        out = {}
        for v in (4.0, 3.6, 4.4):
            vref.params[2] = v
            s2 = Sim(c).dc()
            out[v] = (codes(s2, "D"), codes(s2, "E"), s2.v("VIN1"))
        vref.params[2] = 4.0
        assert out[4.0][:2] == (2, 2), out
        assert out[3.6][:2] == (2, 3), out
        assert out[4.4][:2] == (2, 2), out
        approx(out[4.0][2], 2.919, rel=0.002, what="VIN1")
    return c, check


CIRCUITS = [zener_resistor, zener_current_source, delta_vbe, brokaw_cell,
            shunt_ref, ref_divider_loaded, ref_buffer_ladder, ratiometric]
