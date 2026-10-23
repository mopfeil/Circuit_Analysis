# Condensed PowerPoint deck

`make pptx` builds `pdf/CircuitDesign_Slides_Practical.pptx`: the practical
points of each section, the design recipes and all Falstad examples, without
the calculations. The students work the math from the script; the deck links
every Falstad example as a clickable box.

The deck is not generated from the LaTeX sources directly. Its content is
written by hand, one outline per chapter in `outline/<File>.json`. When a
chapter changes, update its outline.

| File | Content |
|---|---|
| `outline/<File>.json` | slide content of one chapter (File as in `text.tex`) |
| `extract_figs.py` | cuts the circuit diagrams and plots out of `slides.pdf` |
| `build_deck.py` | lays out the slides and writes the `.pptx` |
| `requirements.txt` | Python packages; `make pptx` installs them into `pptx/.venv` |

## Build

```
make pptx              slides.pdf -> figures -> pdf/CircuitDesign_Slides_Practical.pptx
make pptx PREVIEW=1    also draw every slide as PNG into build/pptx/preview/
```

`make pptx` needs `make falstad` to have run (it reads the URLs from
`links/*.tex`) and the font Carlito (metric-compatible with Calibri, the
deck font) for measuring text. Text that does not fit its box is printed as
a `warning`. Missing figures, unknown Falstad names or an example that is on
no slide are an `ERROR` and fail the build.

## Figures

`extract_figs.py` writes every drawing of `slides.pdf` to
`build/pptx/figs/<File>/<heading>-<k>.png`: the slug of the slide heading
the figure sits under, and k counting the figures under that heading in the
chapter. The names stay the same when the slides move by a page, but change
when a heading is renamed. `build/pptx/figs/catalog.json` lists every figure
with its page. Look at a figure before using it: some crops cut off a label
or catch text from the slide.

## Outline format

```json
{
  "chapter": "Basics", "file": "Basics", "number": 1,
  "subtitle": "one line: what the chapter is for",
  "takeaways": ["three short take-home messages"],
  "slides": [
    {"type": "points", "section": "The Voltage Divider", "title": "...",
     "bullets": ["2-5 bullets"], "rule": "key formula result or null",
     "figure": "loaded-divider-1.png",
     "falstad": [{"name": "divider_loaded", "hint": "what to watch in the sim"}],
     "notes": "speaker notes"},
    {"type": "example", "title": "Falstad: ...", "figure": "...",
     "falstad": [...], "observe": ["what to observe or try"], "notes": "..."},
    {"type": "recipe", "title": "Design recipe: ...", "steps": ["3-5 steps"],
     "figure": null, "notes": "..."},
    {"type": "compare", "title": "...",
     "left": {"head": "...", "bullets": ["..."]},
     "right": {"head": "...", "bullets": ["..."]},
     "figure": null, "notes": "..."}
  ],
  "exercises": ["Exercise 1.1: Title"]
}
```

- `figure` is a file name from the chapter's figure folder, `null`, or (on
  a compare slide) a list of two names.
- Every Falstad example of `links/*.tex` must be on exactly one slide.
- Formula markup: `V_{out}` subscript, `2^{N}` superscript; otherwise
  Unicode (· × ≈ ≤ ‖ Ω µ τ Δ →), no LaTeX.
- Keep bullets short (about 85 characters); the layout shrinks the font down
  to 16 pt and then reports an overflow.
