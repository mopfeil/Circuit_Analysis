# Electronic Circuit Design

Lecture material for Electronic Circuit Design (Schaltungsentwurf) at RWU,
Prof. Dr. Markus Pfeil, winter semester 2026/27. Script and slides come from
one LaTeX source, in the style of the lecture *Embedded Computing*. Every
example circuit also exists as a Falstad simulation.

| Folder / file | Content |
|---|---|
| `*.tex` | LaTeX sources of script and slides |
| `examples/` | Falstad circuits for each chapter (`.txt`, plus README with browser links) |
| `falstad/` | Python generator and checker for the Falstad circuits |
| `links/` | generated: Falstad links for the LaTeX sources |
| `pdf/` | built PDFs (`make publish`) |
| `fonts/` | Barlow Semi Condensed, the RWU font (SIL OFL) |
| `AUTHORING.md` | conventions for writing chapters and circuits |

## Chapters

1. Basics
2. Voltage and Current Sources
3. Voltage References
4. Bridge Circuits
5. Operational Amplifiers
6. Active Filters
7. Sample and Hold
8. Analog-to-Digital Conversion
9. From Sensor to Digital Value (capstone: complete chain from a Pt100 bridge to a 3-bit code)

## Build

```
make            examples + docu.pdf (script) + docu_students.pdf + slides.pdf
make falstad    generate and check all Falstad examples
make script     only the script (with solutions)
make students   the script without solutions
make slides     only the slides
make ch CH=ADC  one chapter -> build/ch-ADC-script.pdf, build/ch-ADC-slides.pdf
make publish    build everything and copy the PDFs into pdf/
make clean      remove LaTeX build artifacts
```

Requires TeX Live with latexmk and lualatex (circuitikz, siunitx, pgfplots),
and python3 with numpy (matplotlib only for `falstad/preview.py`).
`make PDFTEX=1` builds with pdflatex and Latin Modern instead of the RWU font.

## Script and slides

- `\nsl{...}`: text only in the script
- `\os{...}`: text only on the slides (typically `\os{\newpage}` = slide break)
- `\exercise{...}` with `\begin{solution}...\end{solution}`: solutions are
  shown in `docu.pdf` and on the slides, and left out of `docu_students.pdf`
- `\falstad{name}`: clickable box that opens `examples/<chapter>/<name>.txt`
  directly in the Falstad simulator in the browser

## Falstad examples

The circuits are not drawn by hand. `falstad/circuits/<chapter>.py`
describes each circuit in Python. `falstad/build_all.py` exports it in the
Falstad text format, makes a `circuitjs.html?ctz=...` link, and simulates it
with a small transient simulator (`falstad/falstad.py`). The simulator uses
the pin geometry of CircuitJS, so wiring mistakes such as a post lying on a
wire without a junction make the build fail. Every number that the script
quotes as "Falstad shows ..." is asserted in the circuit's check function.

To use a circuit: click its box in the PDF, open the link in
`examples/<chapter>/README.md`, or load the `.txt` file with
**File → Import From Text** at <https://www.falstad.com/circuit/circuitjs.html>.

`python3 falstad/preview.py <chapter> <name> out.png` draws a rough preview
of a layout without a browser.
