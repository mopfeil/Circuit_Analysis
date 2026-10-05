"""Falstad examples for chapter 1: Basics."""
import math

from falstad import Circuit, Sim
from _check import approx

TITLE = "Basics"


def network():
    """Series-parallel network: 12 V, R1 = 100 in series with 220 || 330."""
    c = Circuit("network", "Series-parallel network: currents, voltages and power")
    c.text((96, 48), "Series-parallel network (hover over a resistor: I, V, P)")
    c.vsrc((96, 336), (96, 112), 12)
    c.wire((96, 112), (160, 112))
    r1 = c.res((160, 112), (288, 112), 100)
    c.wire((288, 112), (352, 112))
    r2 = c.res((352, 112), (352, 336), 220)
    c.wire((352, 112), (480, 112))
    r3 = c.res((480, 112), (480, 336), 330)
    c.wire((96, 336), (352, 336), (480, 336))
    c.gnd((352, 336))
    c.wire((480, 112), (544, 112))
    c.label((544, 112), "VA")
    c.text((192, 80), "R1")
    c.text((384, 224), "R2")
    c.text((512, 224), "R3")

    def check(s):
        s.dc()
        approx(s.v("VA"), 6.828, what="VA")
        i1 = approx(s.i_res(r1), 0.05172, what="I1")
        approx(s.i_res(r2), 0.03103, what="I2")
        approx(s.i_res(r3), 0.02069, what="I3")
        approx(i1 ** 2 * 100, 0.2675, what="P1")
        approx(s.v("VA") ** 2 / 220, 0.2119, what="P2")
    return c, check


def current_divider():
    """Current divider: 10 mA into 1k || 4.7k."""
    c = Circuit("current_divider", "Current divider: 10 mA into 1 kOhm parallel 4.7 kOhm")
    c.text((96, 48), "Current divider: the smaller resistor takes the larger current")
    c.isrc((96, 336), (96, 112), 10e-3)
    c.wire((96, 112), (224, 112), (352, 112))
    r1 = c.res((224, 112), (224, 336), 1e3)
    r2 = c.res((352, 112), (352, 336), 4.7e3)
    c.wire((96, 336), (224, 336), (352, 336))
    c.gnd((224, 336))
    c.wire((352, 112), (416, 112))
    c.label((416, 112), "V")
    c.text((128, 224), "10 mA")
    c.text((256, 224), "R1")
    c.text((384, 224), "R2")

    def check(s):
        s.dc()
        approx(s.i_res(r1), 8.246e-3, what="I1")
        approx(s.i_res(r2), 1.754e-3, what="I2")
        approx(s.v("V"), 8.246, what="V")
    return c, check


def divider_loaded():
    """Voltage divider 10 V, 10k/10k, with and without a 10k load."""
    c = Circuit("divider_loaded", "Voltage divider, unloaded and loaded with 10 kOhm")
    # unloaded divider
    c.vsrc((96, 336), (96, 112), 10)
    c.wire((96, 112), (224, 112))
    c.res((224, 112), (224, 224), 10e3)
    c.res((224, 224), (224, 336), 10e3)
    c.wire((96, 336), (224, 336))
    c.gnd((224, 336))
    c.label((224, 224), "Vout_open")
    # loaded divider
    c.vsrc((352, 336), (352, 112), 10)
    c.wire((352, 112), (480, 112))
    c.res((480, 112), (480, 224), 10e3)
    c.res((480, 224), (480, 336), 10e3)
    c.wire((480, 224), (576, 224))
    c.res((576, 224), (576, 336), 10e3)
    c.wire((352, 336), (480, 336), (576, 336))
    c.gnd((480, 336))
    c.label((480, 224), "Vout_load", d=(16, -16))
    c.text((96, 64), "Unloaded")
    c.text((352, 64), "Loaded with RL = 10k")

    def check(s):
        s.dc()
        approx(s.v("Vout_open"), 5.0, what="unloaded")
        approx(s.v("Vout_load"), 10 / 3, what="loaded")
    return c, check


def thevenin():
    """Divider 12 V, 2.2k/3.3k with 1k load and its Thevenin equivalent."""
    c = Circuit("thevenin", "Thevenin equivalent of a loaded voltage divider")
    c.text((96, 48), "Original circuit")
    c.vsrc((96, 336), (96, 112), 12)
    c.wire((96, 112), (224, 112))
    c.res((224, 112), (224, 224), 2.2e3)
    c.res((224, 224), (224, 336), 3.3e3)
    c.wire((224, 224), (320, 224))
    rl1 = c.res((320, 224), (320, 336), 1e3)
    c.wire((96, 336), (224, 336), (320, 336))
    c.gnd((224, 336))
    c.label((320, 224), "VL_orig")
    c.text((256, 160), "2.2k")
    c.text((160, 288), "3.3k")
    c.text((336, 288), "RL 1k")
    # Thevenin equivalent
    c.text((480, 48), "Thevenin equivalent: Vth = 7.2 V, Rth = 1.32k")
    c.vsrc((480, 336), (480, 112), 7.2)
    c.wire((480, 112), (528, 112))
    c.res((528, 112), (656, 112), 1.32e3)
    c.wire((656, 112), (720, 112), (720, 224))
    rl2 = c.res((720, 224), (720, 336), 1e3)
    c.wire((480, 336), (720, 336))
    c.gnd((480, 336))
    c.label((720, 224), "VL_equiv")
    c.text((736, 288), "RL 1k")

    def check(s):
        s.dc()
        approx(s.v("VL_orig"), 3.103, what="VL original")
        approx(s.v("VL_equiv"), 3.103, what="VL equivalent")
        for r in (rl1, rl2):                 # load replaced by a wire
            r.params[0] = 1e-6
        try:
            s2 = Sim(c).dc()
            approx(s2.i_res(rl1), 5.45e-3, what="Isc original")
            approx(s2.i_res(rl2), 5.45e-3, what="Isc equivalent")
        finally:
            for r in (rl1, rl2):
                r.params[0] = 1e3
    return c, check


def superposition():
    """Two sources: 12 V/1k and 5 V/2k feed 2k. Each alone and both."""
    c = Circuit("superposition", "Superposition: each source alone, then both")

    def cell(x0, v1, v2, name, title):
        c.text((x0, 48), title)
        if v1:
            c.vsrc((x0, 336), (x0, 112), 12)
        else:
            c.wire((x0, 336), (x0, 112))
        c.res((x0, 112), (x0 + 128, 112), 1e3)
        c.res((x0 + 128, 112), (x0 + 128, 336), 2e3)
        c.res((x0 + 128, 112), (x0 + 256, 112), 2e3)
        if v2:
            c.vsrc((x0 + 256, 336), (x0 + 256, 112), 5)
        else:
            c.wire((x0 + 256, 336), (x0 + 256, 112))
        c.wire((x0, 336), (x0 + 128, 336), (x0 + 256, 336))
        c.gnd((x0 + 128, 336))
        c.label((x0 + 128, 112), name, d=(0, -16))
        c.text((x0 + 32, 160), "1k")
        c.text((x0 + 144, 240), "2k")
        c.text((x0 + 176, 160), "2k")

    cell(96, True, False, "VX1", "12 V alone")
    cell(448, False, True, "VX2", "5 V alone")
    cell(800, True, True, "VX", "both sources")

    def check(s):
        s.dc()
        approx(s.v("VX1"), 6.0, what="VX1")
        approx(s.v("VX2"), 1.25, what="VX2")
        approx(s.v("VX"), 7.25, what="VX")
    return c, check


def led_resistor():
    """LED with 330 Ohm at 5 V; LEDs driven (source/sink) by logic outputs."""
    c = Circuit("led_resistor", "LED with series resistor, driven from 5 V and from logic outputs",
                timestep=1e-4, speed=60)
    # A: LED on a 5 V supply, resistor with slider
    c.text((64, 32), "5 V supply")
    c.rail((96, 96), 5)
    ra = c.res((96, 96), (96, 208), 330)
    c.led((96, 208), (96, 320))
    c.gnd((96, 320))
    c.label((96, 208), "VLED", d=(16, 0))
    c.slider(ra, 100, 1000, "R series")
    # clock = output of a logic circuit, 1 Hz
    c.text((240, 32), "Logic output sources the current")
    c.rail((240, 208), 2.5, waveform="square", freq=1, bias=2.5, label_dir=(-32, 0))
    c.wire((240, 208), (272, 208))
    c.label((272, 208), "CLK", d=(0, -16))
    c.wire((272, 208), (304, 208))
    inv1 = c.inverter((304, 208))
    c.wire(inv1.pin["out"], (384, 208))
    c.label((384, 208), "OUT1", d=(0, -16))
    c.res((384, 208), (496, 208), 330)
    c.led((496, 208), (496, 320))
    c.gnd((496, 320))
    # sink configuration
    c.text((592, 32), "Logic output sinks the current")
    c.rail((800, 96), 5)
    c.res((800, 96), (800, 192), 330)
    c.led((800, 192), (800, 288))
    c.label((608, 320), "CLK", d=(0, -16))
    c.wire((608, 320), (640, 320))
    inv2 = c.inverter((640, 320))
    c.wire(inv2.pin["out"], (736, 320))
    c.label((736, 320), "OUT2", d=(0, 16))
    c.wire((736, 320), (800, 320), (800, 288))

    def check(s):
        s.run(0.25)                       # CLK high: OUT1 low, OUT2 low
        vf = approx(s.v("VLED"), 1.78, rel=0.005, what="VF at 10 mA")
        approx((5 - vf) / 330, 9.76e-3, rel=0.005, what="IF supply")
        approx(s.v("OUT1"), 0.0, absol=1e-6, what="OUT1 low")
        approx((5 - s.v((800, 192))) / 330, 9.76e-3, rel=0.005, what="IF sink")
        s.run(0.75)                       # CLK low: OUT1 high
        approx(s.v("OUT1"), 5.0, what="OUT1 high")
        approx((5 - s.v((496, 208))) / 330, 9.76e-3, rel=0.005, what="IF source")
        approx(5 - s.v((800, 192)), 0.0, absol=0.01, what="sink LED off")
    return c, check


def rc_charging():
    """RC charging/discharging: 10k, 10 uF, square wave 0/5 V, 1 Hz."""
    c = Circuit("rc_charging", "RC circuit: charging and discharging, tau = 0.1 s",
                timestep=1e-4, speed=60)
    c.text((96, 48), "R = 10k, C = 10 uF, tau = RC = 0.1 s")
    c.vsrc((96, 336), (96, 112), 2.5, waveform="square", freq=1, bias=2.5)
    vin = c.label((96, 112), "Vin", d=(0, -16))
    c.wire((96, 112), (160, 112))
    c.res((160, 112), (288, 112), 10e3)
    c.wire((288, 112), (352, 112))
    c.cap((352, 112), (352, 336), 10e-6)
    c.wire((96, 336), (352, 336))
    c.gnd((352, 336))
    vc = c.label((352, 112), "Vc", d=(16, 0))
    c.scope([vin, vc], speed=64, vscale=5)

    def check(s):
        r = s.run(1.0, record=["Vc"])
        t, v = r["t"], r["Vc"]
        approx(float(v[abs(t - 0.1).argmin()]), 3.16, what="Vc at tau")
        approx(float(v[abs(t - 0.5).argmin()]), 4.97, what="Vc at 5 tau")
        t4 = float(t[(v >= 4.0).argmax()])
        approx(t4, 0.161, what="time to 4 V")
        approx(float(v[abs(t - 0.6).argmin()]), 4.97 * math.exp(-1), what="discharge 1 tau")
    return c, check


def rc_lowpass():
    """RC low-pass 1.6k / 100 nF (fc = 995 Hz) with a 1 kHz sine."""
    c = Circuit("rc_lowpass", "RC low-pass: fc = 995 Hz, input 1 kHz sine")
    c.text((96, 48), "RC low-pass, R = 1.6k, C = 100 nF, fc = 995 Hz")
    c.vsrc((96, 336), (96, 112), 1.0, waveform="ac", freq=1000)
    vin = c.label((96, 112), "Vin", d=(0, -16))
    c.wire((96, 112), (160, 112))
    c.res((160, 112), (288, 112), 1.6e3)
    c.wire((288, 112), (352, 112))
    c.cap((352, 112), (352, 336), 100e-9)
    c.wire((96, 336), (352, 336))
    c.gnd((352, 336))
    vo = c.label((352, 112), "Vout", d=(16, 0))
    c.scope([vin, vo], speed=2, vscale=1)

    def check(s):
        s.run(0.010)
        r = s.run(0.012, record=["Vout"])
        amp = (r["Vout"].max() - r["Vout"].min()) / 2
        approx(amp, 0.705, what="output amplitude at 1 kHz")
    return c, check


CIRCUITS = [network, current_divider, divider_loaded, thevenin, superposition,
            led_resistor, rc_charging, rc_lowpass]
