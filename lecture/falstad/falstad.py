"""
Falstad (CircuitJS) toolkit for the lecture "Electronic Circuit Design".

Three parts:

1. Circuit builder  -- write circuits in Python, export the Falstad text
   format (File -> Import From Text) and a clickable URL
   (https://www.falstad.com/circuit/circuitjs.html?ctz=...).
2. lz-string        -- compressToEncodedURIComponent, as used by CircuitJS
   for the ctz= parameter.
3. Simulator        -- a small transient MNA simulator for the subset of
   elements used here. It uses the same pin geometry as CircuitJS
   (ported from CircuitElm.interpPoint and the element setPoints methods),
   so a check that passes here also proves that the wiring of the exported
   file is right.

Element formats follow CircuitJS (github.com/pfalstad/circuitjs1, 2026):

    $ flags maxTimeStep speed currentBar voltageRange powerBar minTimeStep
    w x1 y1 x2 y2 0                         wire
    r x1 y1 x2 y2 0 R                       resistor
    c x1 y1 x2 y2 0 C vdiff                 capacitor
    g x1 y1 x2 y2 0 0                       ground (post = point 1)
    v x1 y1 x2 y2 0 wf f Vmax bias phase duty   source, point 2 = plus
    R x1 y1 x2 y2 0 wf f Vmax bias phase duty   rail, post = point 1
    i x1 y1 x2 y2 0 I                       current source, I leaves at point 2
    d / z / 162                             diode / zener / LED, anode = point 1
    a x1 y1 x2 y2 8 Vmax Vmin gbw 0 0 gain  op-amp (in- top, in+ bottom)
    t x1 y1 x2 y2 0 pnp vbe vbc beta model  BJT, base = point 1
    159 x1 y1 x2 y2 0 Ron Roff Vth          analog switch, control below middle
    150..154 x1 y1 x2 y2 0 n vout Vhigh     AND NAND OR NOR XOR
    I x1 y1 x2 y2 0 slew Vhigh              inverter
    207 x1 y1 x2 y2 4 name                  labeled node (connects by name)
    x x1 y1 x2 y2 0 size text               text
    b x1 y1 x2 y2 0                         box
    o ...                                   scope
    38 elm F0 item min max text             slider

Note: the CircuitJS tokenizer splits on blanks AND on '+'.  Never put a '+'
into text; the builder replaces it by '%2B' (TextElm turns it back).
"""

import math
import numpy as np

GRID = 16

# --------------------------------------------------------------------------
# lz-string (compressToEncodedURIComponent)
# --------------------------------------------------------------------------
_KEY_URI = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-$"


def lz_compress_uri(s):
    """Port of LZString.compressToEncodedURIComponent."""
    if s is None or s == "":
        return ""
    bits_per_char = 6
    out = []
    dictionary = {}
    to_create = set()
    w = ""
    enlarge_in = 2
    dict_size = 3
    num_bits = 2
    data_val = 0
    data_pos = 0

    def write_bits(nbits, value):
        nonlocal data_val, data_pos
        for _ in range(nbits):
            data_val = (data_val << 1) | (value & 1)
            if data_pos == bits_per_char - 1:
                data_pos = 0
                out.append(_KEY_URI[data_val])
                data_val = 0
            else:
                data_pos += 1
            value >>= 1

    def emit_w():
        nonlocal enlarge_in, num_bits
        if w in to_create:
            code = ord(w[0])
            if code < 256:
                write_bits(num_bits, 0)
                write_bits(8, code)
            else:
                write_bits(num_bits, 1)
                write_bits(16, code)
            enlarge_in -= 1
            if enlarge_in == 0:
                enlarge_in = 2 ** num_bits
                num_bits += 1
            to_create.discard(w)
        else:
            write_bits(num_bits, dictionary[w])
        enlarge_in -= 1
        if enlarge_in == 0:
            enlarge_in = 2 ** num_bits
            num_bits += 1

    for c in s:
        if c not in dictionary:
            dictionary[c] = dict_size
            dict_size += 1
            to_create.add(c)
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            emit_w()
            dictionary[wc] = dict_size
            dict_size += 1
            w = c
    if w != "":
        emit_w()
    write_bits(num_bits, 2)
    # flush
    while True:
        data_val = data_val << 1
        if data_pos == bits_per_char - 1:
            out.append(_KEY_URI[data_val])
            break
        data_pos += 1
    return "".join(out)


FALSTAD_URL = "https://www.falstad.com/circuit/circuitjs.html?ctz="

# --------------------------------------------------------------------------
# geometry (ported from CircuitElm)
# --------------------------------------------------------------------------


def _jfloor(v):
    return int(math.floor(v + .48))


def interp(a, b, f, g=0.0):
    """CircuitElm.interpPoint(a, b, f, g)."""
    gx = b[1] - a[1]
    gy = a[0] - b[0]
    n = math.sqrt(gx * gx + gy * gy)
    g = g / n if n else 0
    return (_jfloor(a[0] * (1 - f) + b[0] * f + g * gx),
            _jfloor(a[1] * (1 - f) + b[1] * f + g * gy))


def _sign(x):
    return (x > 0) - (x < 0)


class Elm:
    """One CircuitJS element. kind is the dump type (str)."""

    def __init__(self, kind, p1, p2, flags=0, params=(), **attr):
        self.kind = str(kind)
        self.p1 = tuple(p1)
        self.p2 = tuple(p2)
        self.flags = flags
        self.params = list(params)
        self.attr = attr
        self.index = None

    def dump(self):
        def fmt(v):
            if isinstance(v, float):
                return repr(v) if v != int(v) or abs(v) >= 1e15 else str(v)
            return str(v)
        return " ".join([self.kind, str(self.p1[0]), str(self.p1[1]),
                         str(self.p2[0]), str(self.p2[1]), str(self.flags)]
                        + [fmt(p) for p in self.params])

    # posts in CircuitJS order
    def posts(self):
        k = self.kind
        p1, p2 = self.p1, self.p2
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        dsign = _sign(dx) if dy == 0 else _sign(dy)
        if k in ("g", "R", "207", "O", "M", "L"):
            return [p1]
        if k in ("x", "b"):
            return []
        if k == "a":
            hs = 16 * dsign
            if self.flags & 1:
                hs = -hs
            return [interp(p1, p2, 0, hs), interp(p1, p2, 0, -hs), p2]
        if k == "159":
            openhs = -16 if (self.flags & 16) else 16
            if bool(self.flags & 4) != bool(self.flags & 8):
                openhs = -openhs
            return [p1, p2, interp(p1, p2, .5, -openhs)]
        if k in ("150", "151", "152", "153", "154"):
            n = self.params[0]
            hs = 16
            pts = []
            i0 = -(n // 2)
            for i in range(n):
                if i0 == 0 and n % 2 == 0:
                    i0 += 1
                pts.append(interp(p1, p2, 0, hs * i0))
                i0 += 1
            return pts + [p2]
        if k == "t":
            pnp = self.params[0]
            ds = dsign
            if self.flags & 1:      # FLAG_FLIP
                ds = -ds
            hs2 = 16 * ds * pnp
            return [p1, interp(p1, p2, 1, hs2), interp(p1, p2, 1, -hs2)]
        return [p1, p2]


class Circuit:
    """Builder for one Falstad circuit."""

    def __init__(self, name, title="", timestep=5e-6, speed=10.0,
                 voltage_range=5, current_bar=50, dots=True):
        self.name = name
        self.title = title
        self.timestep = timestep
        self.speed = speed
        self.voltage_range = voltage_range
        self.current_bar = current_bar
        self.dots = dots
        self.elms = []
        self.scopes = []
        self.sliders = []

    # -- generic -----------------------------------------------------------
    def add(self, e):
        e.index = len(self.elms)
        self.elms.append(e)
        return e

    def wire(self, *pts):
        """Polyline of wires through the given points."""
        es = []
        for a, b in zip(pts[:-1], pts[1:]):
            if tuple(a) != tuple(b):
                es.append(self.add(Elm("w", a, b, 0)))
        return es

    # -- passive -----------------------------------------------------------
    def res(self, p1, p2, r):
        return self.add(Elm("r", p1, p2, 0, [float(r)]))

    def cap(self, p1, p2, c, v0=0.0):
        return self.add(Elm("c", p1, p2, 0, [float(c), float(v0)]))

    def diode(self, anode, cathode):
        return self.add(Elm("d", anode, cathode, 2, ["default"]))

    def zener(self, anode, cathode, vz=5.6):
        # old-style parameters: forward drop 0.806 V, breakdown vz
        return self.add(Elm("z", anode, cathode, 1, [0.805904783, float(vz)]))

    def led(self, anode, cathode, color=(1, 0, 0)):
        return self.add(Elm("162", anode, cathode, 2,
                            ["default-led", color[0], color[1], color[2], 0.01]))

    # -- sources -----------------------------------------------------------
    def gnd(self, p):
        return self.add(Elm("g", p, (p[0], p[1] + GRID), 0, [0]))

    @staticmethod
    def _wave(waveform, freq, vmax, bias, phase, duty):
        wf = {"dc": 0, "ac": 1, "square": 2, "triangle": 3,
              "sawtooth": 4, "pulse": 5}[waveform]
        return [wf, float(freq), float(vmax), float(bias), float(phase),
                float(duty)]

    def rail(self, p, v, up=True, waveform="dc", freq=40, bias=0.0,
             phase=0.0, duty=0.5, label_dir=None):
        """One-terminal source at p. For "dc" the voltage is v."""
        d = label_dir or ((0, -GRID * 2) if up else (0, GRID * 2))
        return self.add(Elm("R", p, (p[0] + d[0], p[1] + d[1]), 0,
                            self._wave(waveform, freq, v, bias, phase, duty)))

    def vsrc(self, neg, pos, v, waveform="dc", freq=40, bias=0.0, phase=0.0,
             duty=0.5):
        return self.add(Elm("v", neg, pos, 0,
                            self._wave(waveform, freq, v, bias, phase, duty)))

    def isrc(self, p_from, p_to, i):
        """Current i flows through the source from p_from to p_to."""
        return self.add(Elm("i", p_from, p_to, 0, [float(i), 1000.0]))

    # -- active ------------------------------------------------------------
    def opamp(self, p, length=64, swap=False, vmax=15, vmin=-15, gain=1e5,
              left=False):
        """Op-amp with the input side centred at p.
        Returns the element; pins in e.pin['-'], e.pin['+'], e.pin['out'].
        Default: inverting input on top. swap=True puts + on top."""
        x, y = p
        p2 = (x - length, y) if left else (x + length, y)
        e = self.add(Elm("a", p, p2, 8 | (1 if swap else 0),
                         [float(vmax), float(vmin), 1e6, 0.0, 0.0, float(gain)]))
        po = e.posts()
        e.pin = {"-": po[0], "+": po[1], "out": po[2]}
        return e

    def comparator(self, p, length=64, swap=False, vhigh=5.0, gain=1e5):
        """Open-loop op-amp with output rails 0 .. vhigh (logic compatible)."""
        return self.opamp(p, length, swap, vmax=vhigh, vmin=0, gain=gain)

    def npn(self, base, length=32, flip=False, beta=100.0):
        """BJT, base at `base`, body to the right. Collector on top
        (y-16), emitter below (y+16) unless flip."""
        p2 = (base[0] + length, base[1])
        e = self.add(Elm("t", base, p2, 1 if flip else 0,
                         [1, 0.0, 0.0, float(beta), "default"]))
        po = e.posts()
        e.pin = {"b": po[0], "c": po[1], "e": po[2]}
        return e

    def pnp(self, base, length=32, flip=False, beta=100.0):
        p2 = (base[0] + length, base[1])
        e = self.add(Elm("t", base, p2, 1 if flip else 0,
                         [-1, 0.0, 0.0, float(beta), "default"]))
        po = e.posts()
        e.pin = {"b": po[0], "c": po[1], "e": po[2]}
        return e

    def aswitch(self, p1, p2, ron=20.0, roff=1e10, vth=2.5, flip=False):
        """Analog switch (CMOS transmission gate). Control pin 16 px
        below (or above if flip) the middle for a left-to-right switch."""
        e = self.add(Elm("159", p1, p2, 16 if flip else 0,
                         [float(ron), float(roff), float(vth)]))
        po = e.posts()
        e.pin = {"a": po[0], "b": po[1], "ctl": po[2]}
        return e

    def gate(self, kind, p, n=2, length=64, vhigh=5.0):
        """Logic gate kind in and/nand/or/nor/xor; inputs at p (centre)."""
        code = {"and": "150", "nand": "151", "or": "152", "nor": "153",
                "xor": "154"}[kind]
        e = self.add(Elm(code, p, (p[0] + length, p[1]), 0, [n, 0.0, float(vhigh)]))
        po = e.posts()
        e.pin = {"in": po[:-1], "out": po[-1]}
        return e

    def inverter(self, p, length=48, vhigh=5.0):
        e = self.add(Elm("I", p, (p[0] + length, p[1]), 0, [0.5, float(vhigh)]))
        e.pin = {"in": p, "out": (p[0] + length, p[1])}
        return e

    # -- annotation ----------------------------------------------------------
    def label(self, p, name, d=(GRID, 0)):
        """Labeled node: all labels with the same name are connected."""
        return self.add(Elm("207", p, (p[0] + d[0], p[1] + d[1]), 4,
                            [name.replace(" ", "\\s")]))

    def text(self, p, s, size=16):
        s = s.replace("+", "%2B")
        return self.add(Elm("x", p, (p[0] + 8 * len(s), p[1] + 4), 0, [size, s]))

    def box(self, p1, p2):
        return self.add(Elm("b", p1, p2, 0))

    def scope(self, elms, speed=64, vscale=5.0, position=None):
        """Scope showing the voltages of one-terminal elements (labels)."""
        self.scopes.append((list(elms), speed, vscale,
                            len(self.scopes) if position is None else position))

    def slider(self, elm, vmin, vmax, text, item=0):
        self.sliders.append((elm, item, vmin, vmax, text))

    # -- export --------------------------------------------------------------
    def text_export(self):
        flags = 1 if self.dots else 0
        lines = ["$ %d %g %g %d %g 50 5e-11" % (flags, self.timestep, self.speed,
                                                self.current_bar, self.voltage_range)]
        lines += [e.dump() for e in self.elms]
        for elms, speed, vscale, pos in self.scopes:
            first = elms[0].index
            rest = " ".join("%d 0" % e.index for e in elms[1:])
            lines.append(("o %d %d 0 4098 %g 0.1 %d %d %s" %
                          (first, speed, vscale, pos, len(elms), rest)).strip())
        for elm, item, vmin, vmax, text in self.sliders:
            lines.append("38 %d F0 %d %g %g %s" % (elm.index, item, vmin, vmax,
                                                    text.replace(" ", "\\s")))
        return "\n".join(lines) + "\n"

    def url(self):
        return FALSTAD_URL + lz_compress_uri(self.text_export())


# --------------------------------------------------------------------------
# simulator
# --------------------------------------------------------------------------
VT = 0.025865


class _DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _wave_value(params, t):
    wf, f, vmax, bias, phase, duty = (params + [0, 40, 5, 0, 0, .5])[:6]
    wf = int(wf)
    w = 2 * math.pi * t * f + phase
    if wf == 0:
        return vmax + bias
    if wf == 1:
        return math.sin(w) * vmax + bias
    if wf == 2:
        return bias + (vmax if (w % (2 * math.pi)) < 2 * math.pi * duty else -vmax)
    if wf == 3:
        x = w % (2 * math.pi)
        tri = x * (2 / math.pi) - 1 if x < math.pi else 1 - (x - math.pi) * (2 / math.pi)
        return bias + tri * vmax
    if wf == 4:
        return bias + (w % (2 * math.pi)) * (vmax / math.pi) - vmax
    if wf == 5:
        return bias + (vmax if (w % (2 * math.pi)) < 1 else 0)
    raise ValueError("waveform %d not simulated" % wf)


class Sim:
    """Transient simulation of a Circuit (subset of CircuitJS elements)."""

    def __init__(self, circuit, dt=None):
        self.c = circuit
        self.dt = dt or circuit.timestep
        self.t = 0.0
        self._build()

    # ---- topology ---------------------------------------------------------
    def _build(self):
        dsu = _DSU()
        GND = ("GND",)
        dsu.find(GND)
        for e in self.c.elms:
            po = e.posts()
            for p in po:
                dsu.find(("P",) + tuple(p))
            if e.kind == "w":
                dsu.union(("P",) + po[0], ("P",) + po[1])
            elif e.kind == "g":
                dsu.union(("P",) + po[0], GND)
            elif e.kind == "207":
                name = e.params[0]
                if name.lower() == "gnd":
                    dsu.union(("P",) + po[0], GND)
                else:
                    dsu.union(("P",) + po[0], ("N", name))
        roots = {}
        roots[dsu.find(GND)] = -1          # ground
        idx = 0
        for k in list(dsu.p.keys()):
            r = dsu.find(k)
            if r not in roots:
                roots[r] = idx
                idx += 1
        self.dsu = dsu
        self.roots = roots
        self.nn = idx

        def node(p):
            return roots[dsu.find(("P",) + tuple(p))]
        self.node = node
        # elements that need an extra unknown (branch current)
        self.vs = []
        self.items = []
        for e in self.c.elms:
            k = e.kind
            if k in ("w", "g", "207", "x", "b", "O", "M", "p"):
                continue
            po = [node(p) for p in e.posts()]
            it = {"e": e, "k": k, "n": po}
            if k in ("v", "R", "a", "I", "150", "151", "152", "153", "154"):
                it["vs"] = len(self.vs)
                self.vs.append(it)
            if k == "c":
                it["v"] = e.params[1]
                it["i"] = 0.0
            if k in ("150", "151", "152", "153", "154", "I"):
                it["out"] = 0.0
            if k in ("d", "z", "162"):
                it["vd"] = 0.0
            if k == "t":
                it["vbe"] = 0.0
                it["vbc"] = 0.0
            self.items.append(it)
        self.N = self.nn + len(self.vs)
        self.x = np.zeros(self.N)
        # floating-node check: every node must touch a two-terminal element
        self._check_connectivity()
        self._check_wire_interiors()

    def _check_wire_interiors(self):
        """A post lying inside a wire is NOT connected in CircuitJS (only end
        points connect). That is almost always a drawing mistake."""
        posts = set()
        for e in self.c.elms:
            if e.kind not in ("x", "b"):
                posts.update(e.posts())
        for e in self.c.elms:
            if e.kind != "w":
                continue
            (ax, ay), (bx, by) = e.p1, e.p2
            for (px, py) in posts:
                if (px, py) in (e.p1, e.p2):
                    continue
                inside = ((ax == bx == px and min(ay, by) < py < max(ay, by)) or
                          (ay == by == py and min(ax, bx) < px < max(ax, bx)))
                if inside and self.node((px, py)) != self.node(e.p1):
                    raise RuntimeError("%s: post (%d,%d) lies inside wire %s but is "
                                       "not connected (split the wire there)" %
                                       (self.c.name, px, py, e.dump()))

    def _check_connectivity(self):
        count = np.zeros(self.nn, dtype=int)
        for it in self.items:
            if it["k"] == "a":
                ns = it["n"][2:]          # inputs carry no current
            elif it["k"] in ("150", "151", "152", "153", "154", "I"):
                ns = it["n"][-1:]
            elif it["k"] == "159":
                ns = it["n"][:2]
            else:
                ns = it["n"]
            for n in ns:
                if n >= 0:
                    count[n] += 1
        bad = [i for i in range(self.nn) if count[i] == 0]
        if bad:
            names = self.node_names()
            raise RuntimeError("%s: floating node(s): %s" %
                               (self.c.name, [names.get(b, b) for b in bad]))

    def node_names(self):
        out = {}
        for k in self.dsu.p:
            r = self.roots[self.dsu.find(k)]
            if k[0] == "N":
                out[r] = k[1]
            elif r not in out:
                out[r] = "(%d,%d)" % (k[1], k[2]) if k[0] == "P" else "GND"
        return out

    # ---- access -----------------------------------------------------------
    def v(self, what):
        """Voltage of a label name, a point (x, y), or an element (diff)."""
        if isinstance(what, str):
            k = self.dsu.find(("N", what))
            n = self.roots[k]
        elif isinstance(what, Elm):
            po = what.posts()
            return self.v(po[0]) - self.v(po[1])
        else:
            n = self.node(what)
        return 0.0 if n < 0 else float(self.x[n])

    def i_vs(self, elm):
        """Current through a voltage source / rail / op-amp output."""
        for it in self.vs:
            if it["e"] is elm:
                return float(self.x[self.nn + it["vs"]])
        raise KeyError

    def i_res(self, elm):
        return self.v(elm) / elm.params[0]

    # ---- stamping ---------------------------------------------------------
    def _stamp(self, A, b, x, t, final=False):
        nn = self.nn
        dt = self.dt

        def g(n1, n2, gv):
            if n1 >= 0:
                A[n1, n1] += gv
            if n2 >= 0:
                A[n2, n2] += gv
            if n1 >= 0 and n2 >= 0:
                A[n1, n2] -= gv
                A[n2, n1] -= gv

        def isrc(n1, n2, i):       # current i from n1 to n2 through element
            if n1 >= 0:
                b[n1] -= i
            if n2 >= 0:
                b[n2] += i

        def vsrc(n1, n2, k, v):    # V(n2) - V(n1) = v
            r = nn + k
            if n2 >= 0:
                A[r, n2] += 1
                A[n2, r] += 1
            if n1 >= 0:
                A[r, n1] -= 1
                A[n1, r] -= 1
            b[r] += v

        def V(n):
            return 0.0 if n < 0 else x[n]

        for it in self.items:
            k, n, e = it["k"], it["n"], it["e"]
            if k == "r":
                g(n[0], n[1], 1.0 / e.params[0])
            elif k == "c":
                # trapezoidal companion model
                C = e.params[0]
                geq = 2 * C / dt
                ieq = -geq * it["v"] - it["i"]   # current source n0->n1
                g(n[0], n[1], geq)
                isrc(n[0], n[1], ieq)
            elif k in ("v",):
                vsrc(n[0], n[1], it["vs"], _wave_value(e.params, t))
            elif k == "R":
                vsrc(-1, n[0], it["vs"], _wave_value(e.params, t))
            elif k == "i":
                isrc(n[0], n[1], e.params[0])
            elif k == "159":
                ron, roff, vth = e.params
                closed = V(n[2]) >= vth
                if e.flags & 1:
                    closed = not closed
                g(n[0], n[1], 1.0 / (ron if closed else roff))
            elif k == "a":
                vmax, vmin, _gbw, _v0, _v1, gain = e.params
                mid = (vmax + vmin) / 2
                vd = V(n[1]) - V(n[0])
                r = nn + it["vs"]
                vout_lin = mid + gain * vd
                if n[2] >= 0:
                    A[n[2], r] += 1
                    A[r, n[2]] += 1
                if vout_lin > vmax:
                    b[r] += vmax
                elif vout_lin < vmin:
                    b[r] += vmin
                else:
                    if n[0] >= 0:
                        A[r, n[0]] += gain
                    if n[1] >= 0:
                        A[r, n[1]] -= gain
                    b[r] += mid
            elif k in ("150", "151", "152", "153", "154", "I"):
                vsrc(-1, n[-1], it["vs"], it["out"])
            elif k in ("d", "z", "162"):
                if k == "162":
                    Is, rs, nem, bv = 93.2e-12, .042, 3.73, 0.0
                elif k == "d":
                    Is, rs, nem, bv = 1.7143528192808883e-7, 0, 2, 0.0
                else:
                    fw, bv = e.params[0], e.params[1]
                    nem = 2
                    Is = 1 / (math.exp(fw / (nem * VT)) - 1)
                    rs = 0
                vte = nem * VT
                # CircuitJS (Diode.setup): breakdown calibrated to 5 mA at bv
                zoff = bv - VT * math.log(0.005 / Is - 1) if bv > 0 else 0.0
                vd = V(n[0]) - V(n[1])
                vd = self._limit(vd, it["vd"], vte, Is)
                if bv > 0 and vd < 0:
                    vd = -zoff - self._limit(-vd - zoff, -it["vd"] - zoff, VT, Is)
                it["vd"] = vd
                ex = math.exp(min(vd / vte, 80))
                i = Is * (ex - 1)
                gd = Is * ex / vte
                if bv > 0:
                    exz = math.exp(min((-vd - zoff) / VT, 80))
                    i -= Is * exz
                    gd += Is * exz / VT
                gd += 1e-12
                g(n[0], n[1], gd)
                isrc(n[0], n[1], i - gd * vd)
            elif k == "t":
                pnp = e.params[0]
                beta = e.params[3]
                Is = 1e-13
                br = 1.0
                vb, vc, ve = V(n[0]), V(n[1]), V(n[2])
                vbe = pnp * (vb - ve)
                vbc = pnp * (vb - vc)
                vbe = self._limit(vbe, it["vbe"], VT)
                vbc = self._limit(vbc, it["vbc"], VT)
                it["vbe"], it["vbc"] = vbe, vbc
                ebe = math.exp(min(vbe / VT, 80))
                ebc = math.exp(min(vbc / VT, 80))
                it_ = Is * (ebe - ebc)
                ibe = Is / beta * (ebe - 1)
                ibc = Is / br * (ebc - 1)
                ic = it_ - ibc
                ib = ibe + ibc
                # derivatives wrt vbe, vbc
                dic_dvbe = Is * ebe / VT
                dic_dvbc = -Is * ebc / VT - Is / br * ebc / VT
                dib_dvbe = Is / beta * ebe / VT
                dib_dvbc = Is / br * ebc / VT
                # currents into collector = pnp*ic, into base = pnp*ib
                # linearize: I = I0 + dI/dvbe*(dvbe) + dI/dvbc*(dvbc)
                nb, nc, ne = n

                def add_lin(nrow, I0, dvbe, dvbc):
                    # current flowing INTO the device at nrow
                    if nrow < 0:
                        return
                    # vbe = pnp*(vb-ve), vbc = pnp*(vb-vc)
                    coef_b = pnp * (dvbe + dvbc)
                    coef_e = -pnp * dvbe
                    coef_c = -pnp * dvbc
                    for col, cf in ((nb, coef_b), (ne, coef_e), (nc, coef_c)):
                        if col >= 0:
                            A[nrow, col] += pnp * cf
                    b[nrow] -= pnp * (I0 - dvbe * vbe - dvbc * vbc)
                add_lin(nc, ic, dic_dvbe, dic_dvbc)
                add_lin(nb, ib, dib_dvbe, dib_dvbc)
                add_lin(ne, -(ic + ib), -(dic_dvbe + dib_dvbe), -(dic_dvbc + dib_dvbc))
                # tiny conductances for convergence
                g(nb, ne, 1e-12)
                g(nb, nc, 1e-12)
        # gmin to ground on all nodes
        for i in range(nn):
            A[i, i] += 1e-12

    @staticmethod
    def _limit(vnew, vold, vt, Is=1e-13):
        vcrit = vt * math.log(vt / (math.sqrt(2) * Is))
        if vnew > vcrit and abs(vnew - vold) > 2 * vt:
            if vold > 0:
                arg = 1 + (vnew - vold) / vt
                vnew = vold + vt * math.log(arg) if arg > 0 else vcrit
            else:
                vnew = vt * math.log(vnew / vt)
        return vnew

    def _digital(self, x):
        def V(n):
            return 0.0 if n < 0 else x[n]
        for it in self.items:
            k, n, e = it["k"], it["n"], it["e"]
            if k == "I":
                vh = e.params[1]
                it["out"] = 0.0 if V(n[0]) > vh / 2 else vh
            elif k in ("150", "151", "152", "153", "154"):
                vh = e.params[2]
                ins = [V(m) > vh / 2 for m in n[:-1]]
                if k in ("150", "151"):
                    r = all(ins)
                elif k in ("152", "153"):
                    r = any(ins)
                else:
                    r = sum(ins) % 2 == 1
                if k in ("151", "153"):
                    r = not r
                it["out"] = vh if r else 0.0

    def step(self):
        t = self.t + self.dt
        x = self.x.copy()
        self._digital(self.x)
        for itn in range(200):
            A = np.zeros((self.N, self.N))
            b = np.zeros(self.N)
            self._stamp(A, b, x, t)
            xn = np.linalg.solve(A, b)
            if np.max(np.abs(xn - x)) < 1e-7:
                x = xn
                break
            # damping after many iterations breaks op-amp clamp oscillations
            x = xn if itn < 40 else x + 0.25 * (xn - x)
        else:
            raise RuntimeError("%s: no convergence at t=%g" % (self.c.name, t))
        # update capacitor states
        for it in self.items:
            if it["k"] == "c":
                n = it["n"]
                vnew = (0 if n[0] < 0 else x[n[0]]) - (0 if n[1] < 0 else x[n[1]])
                C = it["e"].params[0]
                geq = 2 * C / self.dt
                it["i"] = geq * (vnew - it["v"]) - it["i"]
                it["v"] = vnew
        self.x = x
        self.t = t

    def dc(self, settle=None):
        """Operating point: run until capacitors settle (simple approach),
        or solve once if there are no capacitors."""
        if not any(it["k"] == "c" for it in self.items):
            for _ in range(5):          # digital parts need a few passes
                self.step()
            return self
        self.run(settle or 1.0)
        return self

    def run(self, t_end, record=(), every=1):
        """Run until absolute time t_end. record: list of label names or
        points; returns dict of numpy arrays incl. 't'."""
        rec = {"t": []}
        for r in record:
            rec[r if isinstance(r, str) else str(r)] = []
        i = 0
        while self.t < t_end - self.dt / 2:
            self.step()
            if record and i % every == 0:
                rec["t"].append(self.t)
                for r in record:
                    rec[r if isinstance(r, str) else str(r)].append(self.v(r))
            i += 1
        return {k: np.array(v) for k, v in rec.items()}
