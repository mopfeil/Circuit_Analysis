"""Rough PNG preview of a Falstad circuit layout (to check the drawing
without a browser): python3 falstad/preview.py <chapter> <name> out.png"""
import importlib
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "circuits"))

COLORS = {"w": "0.3", "r": "tab:blue", "c": "tab:orange", "a": "tab:purple",
          "159": "tab:red", "207": "tab:green", "162": "tab:red"}


def render(c, out):
    xs = [p for e in c.elms for p in (e.p1[0], e.p2[0])]
    ys = [p for e in c.elms for p in (e.p1[1], e.p2[1])]
    w, h = max(xs) - min(xs) + 100, max(ys) - min(ys) + 100
    fig, ax = plt.subplots(figsize=(w / 80, h / 80))
    for e in c.elms:
        k = e.kind
        if k == "x":
            ax.text(e.p1[0], e.p1[1], e.params[1].replace("%2B", "+"), fontsize=7,
                    va="center")
            continue
        if k == "b":
            (x1, y1), (x2, y2) = e.p1, e.p2
            ax.plot([x1, x2, x2, x1, x1], [y1, y1, y2, y2, y1], color="0.7", lw=0.8)
            continue
        po = e.posts()
        col = COLORS.get(k, "k")
        if k == "a":
            (mx, my), (px, py), (ox, oy) = po
            ax.fill([e.p1[0], e.p1[0], ox], [my - 8, py + 8, oy], color=col, alpha=.25)
            ax.text(e.p1[0] + 4, my, "-", fontsize=7, va="center")
            ax.text(e.p1[0] + 4, py, "+", fontsize=7, va="center")
        elif k == "207":
            ax.text(e.p2[0], e.p2[1], e.params[0], fontsize=6, color=col,
                    ha="center", va="center")
        elif k in ("150", "151", "152", "153", "154", "I"):
            ax.add_patch(plt.Rectangle((e.p1[0] + 8, e.p1[1] - 16 * max(1, len(po) // 2)),
                                       e.p2[0] - e.p1[0] - 16, 32 * max(1, len(po) // 2),
                                       color="tab:cyan", alpha=.3))
            ax.text((e.p1[0] + e.p2[0]) / 2, e.p1[1], {"150": "&", "152": ">=1",
                    "151": "&o", "153": ">=1o", "154": "=1", "I": "1o"}[k],
                    fontsize=6, ha="center", va="center")
        else:
            if k == "r":
                lbl = "%g" % e.params[0]
            elif k == "R":
                lbl = "%g V" % e.params[2]
            else:
                lbl = {"c": "C", "v": "V", "g": "", "162": "LED", "d": "D",
                       "z": "Z", "t": "T", "159": "SW", "i": "I"}.get(k, k)
            mx, my = (e.p1[0] + e.p2[0]) / 2, (e.p1[1] + e.p2[1]) / 2
            ax.text(mx + 4, my, lbl, fontsize=5, color=col)
        ax.plot([e.p1[0], e.p2[0]], [e.p1[1], e.p2[1]], color=col, lw=1)
        for p in po:
            ax.plot(*p, "o", ms=1.5, color="k")
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.axis("off")
    fig.savefig(out, dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    mod, name, out = sys.argv[1:4]
    m = importlib.import_module(mod)
    for fn in m.CIRCUITS:
        c, _ = fn()
        if c.name == name:
            render(c, out)
            break
