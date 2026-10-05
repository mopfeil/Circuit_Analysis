"""Falstad examples for chapter 2: Voltage and Current Sources."""
import math

from falstad import Circuit, Elm, Sim, VT
from _check import approx

TITLE = "Voltage and Current Sources"


def zener(c, anode, cathode, vz):
    return c.zener(anode, cathode, vz)


def real_source():
    """Ideal and real voltage source (4.5 V, Ri = 1.25 Ohm) with 10 Ohm load."""
    c = Circuit("real_source", "Ideal and real voltage source with a 10 Ohm load")
    c.text((96, 48), "Ideal source")
    c.vsrc((96, 336), (96, 112), 4.5)
    c.wire((96, 112), (224, 112))
    c.res((224, 112), (224, 336), 10)
    c.wire((96, 336), (224, 336))
    c.gnd((224, 336))
    c.label((224, 112), "V_ideal", d=(16, 0))
    c.text((240, 240), "RL 10")
    # real source = ideal source + internal resistance
    c.text((416, 48), "Real source: V0 = 4.5 V, Ri = 1.25 Ohm")
    c.box((400, 80), (560, 368))
    c.vsrc((448, 336), (448, 208), 4.5)
    c.res((448, 208), (448, 112), 1.25)
    c.text((464, 160), "Ri")
    c.wire((448, 112), (608, 112))
    c.wire((448, 336), (608, 336))
    c.label((608, 112), "V_term", d=(16, 0))
    c.wire((608, 112), (704, 112))
    rl = c.res((704, 112), (704, 336), 10)
    c.wire((608, 336), (704, 336))
    c.gnd((608, 336))
    c.text((720, 240), "RL")
    c.slider(rl, 0.5, 20, "RL")

    def check(s):
        s.dc()
        approx(s.v("V_ideal"), 4.5, what="ideal")
        approx(s.v("V_term"), 4.0, what="terminal voltage")
        approx(s.i_res(rl), 0.4, what="load current")
        rl.params[0] = 1.25                  # slider at RL = Ri: power matching
        try:
            s2 = Sim(c).dc()
            approx(s2.v("V_term") ** 2 / 1.25, 4.05, what="P at RL = Ri")
        finally:
            rl.params[0] = 10.0
    return c, check


def source_transform():
    """Thevenin (10 V, 10k) and Norton (1 mA || 10k) with 4.7k load."""
    c = Circuit("source_transform", "Source transformation: Thevenin and Norton source, same load")
    c.text((96, 48), "Thevenin: 10 V with 10k in series")
    c.vsrc((96, 336), (96, 112), 10)
    c.wire((96, 112), (128, 112))
    c.res((128, 112), (256, 112), 10e3)
    c.wire((256, 112), (320, 112))
    c.res((320, 112), (320, 336), 4.7e3)
    c.wire((96, 336), (320, 336))
    c.gnd((320, 336))
    c.label((320, 112), "VL_thevenin", d=(16, 0))
    c.text((336, 240), "RL 4.7k")
    c.text((496, 48), "Norton: 1 mA with 10k in parallel")
    c.isrc((512, 336), (512, 112), 1e-3)
    c.wire((512, 112), (624, 112), (736, 112))
    c.res((624, 112), (624, 336), 10e3)
    c.res((736, 112), (736, 336), 4.7e3)
    c.wire((512, 336), (624, 336), (736, 336))
    c.gnd((624, 336))
    c.label((736, 112), "VL_norton", d=(16, 0))
    c.text((640, 240), "10k")
    c.text((752, 240), "RL 4.7k")

    def check(s):
        s.dc()
        approx(s.v("VL_thevenin"), 3.197, what="Thevenin")
        approx(s.v("VL_norton"), 3.197, what="Norton")
    return c, check


def zener_shunt():
    """Zener shunt regulator 12 V, 220 Ohm, 5.6 V; open and 270 Ohm load."""
    c = Circuit("zener_shunt", "Zener shunt regulator: 12 V, R = 220 Ohm, Vz = 5.6 V")

    def cell(x0, rl, name, title):
        c.text((x0, 48), title)
        c.vsrc((x0, 336), (x0, 112), 12)
        c.wire((x0, 112), (x0 + 32, 112))
        c.res((x0 + 32, 112), (x0 + 160, 112), 220)
        c.wire((x0 + 160, 112), (x0 + 224, 112))
        zener(c, (x0 + 224, 336), (x0 + 224, 112), 5.6)
        c.wire((x0, 336), (x0 + 224, 336))
        c.gnd((x0 + 224, 336))
        c.label((x0 + 224, 112), name, d=(0, -16))
        c.text((x0 + 64, 80), "220")
        r = None
        if rl:
            c.wire((x0 + 224, 112), (x0 + 320, 112))
            r = c.res((x0 + 320, 112), (x0 + 320, 336), rl)
            c.wire((x0 + 224, 336), (x0 + 320, 336))
            c.text((x0 + 336, 240), "RL")
        return r

    cell(96, None, "Vout_open", "No load")
    rl = cell(480, 270, "Vout_load", "Load RL = 270 Ohm (20 mA)")
    c.slider(rl, 100, 2000, "RL")

    def check(s):
        s = Sim(c).dc()
        vo = approx(s.v("Vout_open"), 5.645, rel=0.002, what="Vz no load")
        approx((12 - vo) / 220, 28.9e-3, rel=0.005, what="Iz no load")
        vl = approx(s.v("Vout_load"), 5.612, rel=0.002, what="Vz loaded")
        il = vl / 270
        approx(il, 20.8e-3, rel=0.005, what="IL")
        approx((12 - vl) / 220 - il, 8.25e-3, rel=0.01, what="Iz loaded")
    return c, check


def series_regulator():
    """Emitter follower with Zener reference: 12 V -> about 4.9 V."""
    c = Circuit("series_regulator", "Series regulator: Zener 5.6 V and emitter follower")

    def cell(x0, rl, name, title):
        c.text((x0, 48), title)
        c.vsrc((x0, 352), (x0, 96), 12)
        c.wire((x0, 96), (x0 + 128, 96), (x0 + 240, 96))
        c.res((x0 + 128, 96), (x0 + 128, 208), 1e3)
        q = c.npn((x0 + 208, 208))
        c.wire((x0 + 128, 208), (x0 + 208, 208))
        zener(c, (x0 + 128, 352), (x0 + 128, 208), 5.6)
        c.label((x0 + 128, 208), name + "_Z", d=(-16, 0))
        c.wire(q.pin["c"], (x0 + 240, 96))
        c.wire(q.pin["e"], (x0 + 240, 256), (x0 + 320, 256))
        r = c.res((x0 + 320, 256), (x0 + 320, 352), rl)
        c.wire((x0, 352), (x0 + 128, 352), (x0 + 320, 352))
        c.gnd((x0 + 128, 352))
        c.label((x0 + 320, 256), name, d=(0, -16))
        c.text((x0 + 64, 144), "1k")
        c.text((x0 + 336, 304), "RL")
        return r

    r1 = cell(96, 470, "Vout_10mA", "RL = 470 Ohm")
    r2 = cell(560, 47, "Vout_100mA", "RL = 47 Ohm")
    c.slider(r2, 20, 1000, "RL")

    def check(s):
        s = Sim(c).dc()
        approx(s.v("Vout_10mA"), 4.950, rel=0.002, what="Vout 470")
        v2 = approx(s.v("Vout_100mA"), 4.886, rel=0.002, what="Vout 47")
        approx(v2 / 47, 0.104, rel=0.005, what="IL 47")
        approx(s.v("Vout_10mA_Z"), 5.606, rel=0.002, what="VZ 470")
        approx(s.v("Vout_100mA_Z"), 5.602, rel=0.002, what="VZ 47")
    return c, check


def bjt_current_source():
    """BJT current source 1 mA: divider 10k/2.2k, RE = 1.5k, loads 1k/4.7k/15k."""
    c = Circuit("bjt_current_source", "BJT current source, about 1 mA, three loads")
    c.text((64, 32), "BJT current source: VB from 10k/2.2k, RE = 1.5k, 12 V supply")
    res = []
    for k, rl in enumerate((1e3, 4.7e3, 15e3)):
        x0 = 96 + 288 * k
        n = k + 1
        c.text((x0, 64), "RL = %s" % {1e3: "1k", 4.7e3: "4.7k", 15e3: "15k"}[rl])
        c.rail((x0, 96), 12)
        c.wire((x0, 96), (x0 + 128, 96))
        c.res((x0, 96), (x0, 224), 10e3)
        c.res((x0, 224), (x0, 352), 2.2e3)
        c.wire((x0, 224), (x0 + 48, 224), (x0 + 96, 224))
        q = c.npn((x0 + 96, 224))
        r = c.res((x0 + 128, 96), q.pin["c"], rl)
        c.wire(q.pin["e"], (x0 + 128, 256))
        c.res((x0 + 128, 256), (x0 + 128, 352), 1.5e3)
        c.wire((x0, 352), (x0 + 128, 352))
        c.gnd((x0, 352))
        c.label((x0 + 48, 224), "VB%d" % n, d=(0, -16))
        c.label((x0 + 128, 256), "VE%d" % n, d=(16, 0))
        c.label(q.pin["c"], "VC%d" % n, d=(16, 0))
        res.append(r)

    def check(s):
        s.dc()
        approx(s.v("VB1"), 2.146, rel=0.003, what="VB")
        i1 = approx(s.i_res(res[0]), 1.023e-3, rel=0.003, what="IC 1k")
        approx(s.i_res(res[1]), 1.023e-3, rel=0.003, what="IC 4.7k")
        approx(s.v("VC2"), 12 - 4.7e3 * i1, rel=0.005, what="VC 4.7k")
        approx(s.v("VE1"), 1.549, rel=0.003, what="VE")
        approx(s.i_res(res[2]), 0.710e-3, rel=0.005, what="IC 15k saturated")
    return c, check


def current_mirror():
    """Current mirror with Rref = 11k at 12 V, loads 4.7k and 1k."""
    c = Circuit("current_mirror", "Current mirror: Iref set by 11k, copied to the load")
    c.text((96, 32), "Current mirror (12 V): Iref = (12 V - VBE) / 11k")
    c.rail((160, 80), 12)
    c.wire((160, 80), (160, 96), (352, 96))
    rref = c.res((160, 96), (160, 208), 11e3)
    # Q1 (diode connected) on the left, mirrored drawing: base to the left
    q1 = c.add(Elm("t", (192, 240), (160, 240), 0, [1, 0.0, 0.0, 100.0, "default"]))
    po = q1.posts()          # [base, collector, emitter]
    c.wire((160, 208), po[1])
    c.wire(po[1], (192, 224))
    c.wire((192, 240), (192, 224))
    q2 = c.npn((320, 240))
    c.wire((192, 240), (320, 240))
    c.wire(po[2], (160, 288))
    c.wire(q2.pin["e"], (352, 288))
    c.wire((160, 288), (160, 320), (352, 320), (352, 288))
    c.gnd((160, 320))
    rl = c.res((352, 96), q2.pin["c"], 4.7e3)
    c.label((192, 224), "VBE", d=(0, -16))
    c.label(q2.pin["c"], "VC2", d=(16, 0))
    c.text((64, 160), "Rref 11k")
    c.text((368, 160), "RL 4.7k")
    c.slider(rl, 100, 15e3, "RL")

    def check(s):
        s.dc()
        iref = approx(s.i_res(rref), 1.036e-3, rel=0.005, what="Iref")
        iout = approx(s.i_res(rl), 1.015e-3, rel=0.005, what="Iout")
        approx(iout / iref, 100 / 102, rel=0.002, what="mirror ratio")
    return c, check


def opamp_current_source():
    """Op-amp + NPN V-to-I converter: Vset = 1 V, RS = 1k, sensor 1.385k."""
    c = Circuit("opamp_current_source", "Op-amp current source (op-amp and transistor), 1 mA")
    c.text((64, 32), "I = Vset / RS = 1 V / 1k (sensor in the collector)")
    c.rail((96, 240), 1.0, label_dir=(-32, 0))
    c.text((32, 208), "Vset")
    c.wire((96, 240), (192, 240))
    op = c.opamp((192, 256), swap=True)          # + on top, - below
    c.res(op.pin["out"], (368, 256), 1e3)
    c.text((288, 224), "1k")
    q = c.npn((368, 256))
    c.rail((400, 80), 12)
    c.wire((400, 80), (400, 96))
    rs_sensor = c.res((400, 96), q.pin["c"], 1385)
    c.wire(q.pin["e"], (400, 336))
    rs = c.res((400, 336), (400, 448), 1e3)
    c.gnd((400, 448))
    c.wire((400, 336), (160, 336), (160, 272), op.pin["-"])
    c.label((400, 336), "VS", d=(16, 0))
    c.label(q.pin["c"], "VC", d=(16, 0))
    c.text((416, 160), "sensor 1.385k")
    c.text((416, 400), "RS 1k")
    # second version: floating sensor in the feedback path
    c.text((592, 32), "Floating load in the feedback path: I = Vset / RS exactly")
    c.rail((656, 304), 1.0, label_dir=(-32, 0))
    c.wire((656, 304), (720, 304))
    op2 = c.opamp((720, 288))                     # - on top
    c.wire(op2.pin["out"], (816, 288), (816, 192))
    sensor2 = c.res((816, 192), (688, 192), 1385)
    c.wire((688, 192), (688, 272), (720, 272))
    c.wire((688, 272), (688, 352))
    c.res((688, 352), (688, 448), 1e3)
    c.gnd((688, 448))
    c.label((816, 192), "VOUT2", d=(16, 0))
    c.label((688, 352), "VS2", d=(-16, 0))
    c.text((704, 160), "sensor 1.385k")
    c.text((704, 416), "RS 1k")

    def check(s):
        # Start Newton's method near the operating point: from all-zero
        # node voltages the clamped op-amp output of falstad.Sim toggles
        # between +15 V and -15 V (the transistor is off at 0 V).
        for p, v in ((op.pin["+"], 1.0), (op.pin["-"], 1.0), (op.pin["out"], 2.6),
                     (q.pin["b"], 1.6), (q.pin["c"], 10.6)):
            s.x[s.node(p)] = v
        for it in s.items:
            if it["e"] is q:
                it["vbe"], it["vbc"] = 0.6, -9.0
        s.dc()
        approx(s.v("VS"), 1.0, rel=0.001, what="VS = Vset")
        approx(s.i_res(rs_sensor), 0.990e-3, rel=0.002, what="sensor current (IC)")
        approx(s.i_res(sensor2), 1.000e-3, rel=0.001, what="floating sensor current")
        approx(s.v("VOUT2"), 2.385, rel=0.002, what="op-amp output")
    return c, check


CIRCUITS = [real_source, source_transform, zener_shunt, series_regulator,
            bjt_current_source, current_mirror, opamp_current_source]
