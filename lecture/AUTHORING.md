# Authoring guide

How the script, the slides and the Falstad examples are written. Applies to
every chapter file (`Basics.tex`, `Sources.tex`, ...). The style follows the
lecture *Embedded Computing* (`/home/shared/embeddedcomputing/Lecture`).

## One source, two documents

`docu.tex` (A4 script) and `slides.tex` (A5 landscape slides) both input
`text.tex`, which inputs the chapter files. The same text is set twice:

| Macro | Script | Slides |
|---|---|---|
| `\nsl{...}` | shown | hidden: prose, derivations, background |
| `\os{...}` | hidden | shown: typically `\os{\newpage}` = next slide |
| `\section{}` | section | new slide with a centred heading |
| `\subsection{}` | subsection | new slide with a heading |

Chapter skeleton (copy this pattern):

```latex
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\section{The Voltage Divider}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\nsl{Introductory prose for the script: why this topic matters, how it
connects to the previous one. Several sentences.\newpage}

\begin{description}
\item[{\rot\bf Topic of one slide}]~\\[-\lblskip]
\bi
	\ite short bullet points, as on a slide
	\ite formulas with siunitx: \SI{4.7}{\kilo\ohm}, \SI{2.5}{\hertz}
\ei
\nsl{Longer explanation that only belongs into the script.}
\os{\newpage}

\item[{\rot\bf Next slide}]~\\[-\lblskip]
...
\os{\newpage}
\end{description}
```

Rules:

- A slide is the content between two `\os{\newpage}`. It must fit on one A5
  landscape page (195 x 138 mm, 12 pt): about 8 bullet lines, or a figure
  plus 3 bullets. Check the slide PDF.
- Prose for the script goes into `\nsl{}`: complete sentences, derivations,
  design reasoning, practical hints. The script must be readable on its own
  as a textbook; the slides alone as a lecture.
- English, simple sentences, no marketing language.
- `\nsl{}` is a macro argument: no `\verb`, no `lstlisting` inside it, and
  no blank line problems (use `\newline` or `\par` for paragraphs).

## Macros (macros.tex, mathmacros.tex)

- `\bi \ite ... \ei` bullet list, `\itee` second level bullet.
- `\defn{label}{text}` definition box, `\satz{label}{text}` rule box.
- `\keyeq{Title}{formula}` box for formulas worth remembering.
- `\designcard{Title}{content}` compact design recipe (as handed out in the
  lab, e.g. "Comparator", "Reference ladder and quantization").
- `\falstad{name}` link box to `examples/<chapter>/<name>.txt`; it opens the
  circuit in the browser. The name must exist in the chapter's
  `falstad/circuits/<chapter>.py`.
- Exercises:

```latex
\exercise{Loaded voltage divider}
Problem text.
\begin{talist}
\ta first part
\ta second part
\end{talist}

\begin{solution}
\begin{talist}
\ta worked solution with numbers and units
\ta ... and what Falstad shows: \falstad{divider_loaded}
\end{talist}
\end{solution}
```

  Solutions appear in `docu.pdf` and `slides.pdf` (on their own slide), and
  are removed in `docu_students.pdf`. Every exercise gets a paper solution
  (formula, numbers, units, result) and, where it makes sense, a Falstad
  verification with the value the simulation shows.
- Symbols: `\Vin`, `\Vout`, `\Vref`, `\Vcc`, `\LSB`, `\parallelto` (parallel).

## Circuit diagrams (circuitikz)

- Loaded with `[siunitx,european,RPvoltages]`: European resistors (boxes),
  voltage arrows.
- Always inside `\begin{center} ... \end{center}`, or a `figure` with
  `\caption` in the script style (`\begin{figure}[!hbtp]`).
- Keep diagrams small enough for a slide: width up to about 12 cm,
  height up to about 6 cm; use `[scale=0.8, transform shape]` if needed.
- Op-amps: `node[op amp]`, use anchors `-`, `+`, `out`. Ground with
  `node[ground]{}`. Supply rails with `node[vcc]{$+V_S$}`.
- Draw the same circuit as the Falstad example, with the same names and
  values, so that students can compare.
- Use pgfplots for curves (Bode plots, transfer characteristics, time
  signals). Colours: `rwuviolet`, `rwucyan`, `rwucyandark`.

## Falstad examples (falstad/)

Each chapter has `falstad/circuits/<chapter>.py` with a list `CIRCUITS` of
functions. Each function returns `(circuit, check)`:

```python
from falstad import Circuit
from _check import approx

def divider_loaded():
    c = Circuit("divider_loaded", "Voltage divider, unloaded and loaded")
    c.vsrc((96, 336), (96, 112), 10)        # minus at first point
    c.wire((96, 112), (224, 112))
    c.res((224, 112), (224, 224), 10e3)
    ...
    c.label((224, 224), "Vout_open")        # named node, probe by name
    def check(s):                           # s = falstad.Sim(c)
        s.dc()                              # or s.run(t_end, record=[...])
        approx(s.v("Vout_open"), 5.0, what="unloaded")
    return c, check

CIRCUITS = [divider_loaded]
```

`python3 falstad/build_all.py <chapter>` builds, simulates and checks the
circuits, writes `examples/<chapter>/*.txt`, `examples/<chapter>/README.md`
and `links/<chapter>.tex`. The numbers you write into the script (solution
values, readings in Falstad) must be the ones asserted in `check`.

Builder API (see the docstrings in `falstad/falstad.py`):

| Call | Element |
|---|---|
| `wire(p1, p2, p3, ...)` | wire polyline |
| `res(p1, p2, R)`, `cap(p1, p2, C)` | resistor, capacitor |
| `diode(a, k)`, `zener(a, k, vz)`, `led(a, k)` | diodes (anode first) |
| `gnd(p)` | ground |
| `rail(p, V, up=True, waveform="dc"/"ac"/"square", freq, bias, duty)` | one-terminal source |
| `vsrc(neg, pos, V, waveform=..., ...)` | two-terminal source |
| `isrc(p_from, p_to, I)` | current source |
| `opamp(p, swap=False, vmax, vmin, gain=1e5)` | op-amp; pins `e.pin['-'], ['+'], ['out']`; inputs at p±(0,16), output at p+(64,0) |
| `comparator(p, vhigh=5)` | op-amp with 0..5 V output |
| `npn(base)`, `pnp(base)` | BJT; pins `b`, `c`, `e` |
| `aswitch(p1, p2)` | analog switch, control pin `pin['ctl']` 16 px below the middle |
| `gate('and'/'or'/'nand'/'nor'/'xor', p, n)` | logic gate; `pin['in']` list, `pin['out']` |
| `inverter(p)` | NOT gate |
| `label(p, name)` | labeled node: all labels with the same name are connected |
| `text(p, s)`, `box(p1, p2)` | annotation |
| `scope([label1, label2], speed, vscale)` | scope with the voltages of labels |
| `slider(elm, min, max, "text")` | slider for the element value |

Gotchas (the simulator checks most of them and fails the build):

- Coordinates on a 16 px grid. Wires connect **only at their end points**;
  a post lying inside a wire is not connected (in Falstad as well). Split
  the wire at junctions: `c.wire(a, junction, b)`.
- Op-amp model: output = `(vmax+vmin)/2 + gain*(V+ - V-)`, clamped to
  `vmin..vmax`. No bandwidth limit (GBW is not simulated by Falstad).
- Do not use `+` in texts (the Falstad tokenizer splits at `+`;
  `text()` escapes it).
- Probe node voltages by label name; scopes must point at labels
  (one-terminal elements), not at two-terminal elements.
- Choose `timestep` to suit the signals (default 5 µs; for 5 Hz sampling
  use 1e-4 s). Keep check simulations short (a few seconds of CPU).
- Lay circuits out readably: signal flow left to right, supply on top,
  ground at the bottom, a `text()` title, values visible.

## Building

```
make falstad          all examples (python3, numpy)
make ch CH=Bridges    one chapter -> build/ch-Bridges-script.pdf / -slides.pdf
make                  everything: docu.pdf, docu_students.pdf, slides.pdf
```
