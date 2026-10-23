"""Build the condensed lecture deck (PPTX) from pptx/outline/*.json.

    python pptx/build_deck.py -o pdf/CircuitDesign_Slides_Practical.pptx [--preview DIR]

Needs the figures from extract_figs.py in build/pptx/figs and the Falstad
links in links/*.tex ("make falstad"). Every slide is first laid out as a
list of primitives (rect, text, image, ellipse); the same list is written
to the PPTX and, with --preview, drawn into a PNG per slide. Text is
measured with Carlito (metric-compatible with Calibri), so text that does
not fit its box is reported as a warning.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTLINE = os.path.join(HERE, "outline")
BUILD = os.path.join(ROOT, "build", "pptx")
FIGS = os.path.join(BUILD, "figs")
LOGO = os.path.join(BUILD, "rwu_logo.png")
# chapter order as in text.tex
ORDER = re.findall(r"^\\chap\{[^}]*\}\{([^}]*)\}", open(os.path.join(ROOT, "text.tex")).read(), re.M)


def falstad_links():
    """name -> {chapter, url} from links/<chapter>.tex ("make falstad")."""
    out = {}
    for f in glob.glob(os.path.join(ROOT, "links", "*.tex")):
        for m in re.finditer(r"\\falstaddef\{(\w+)\}\{(\w+)\}\{(\S+)\}", open(f).read()):
            out[m.group(1)] = {"chapter": m.group(2), "url": m.group(3)}
    return out


FALSTAD = falstad_links()

W, H = 13.333, 7.5
FONT = "Calibri"
VIOLET, VIOLET_L, VIOLET_D = "6638B6", "9B7DD4", "4E2A8C"
CYAN, CYAN_D = "00A9CE", "007F9B"
VTINT, CTINT, GTINT = "F1ECFA", "E5F6FB", "F4F4F6"
TEXT, MUTED, WHITE = "23232B", "62626E", "FFFFFF"

problems = []        # errors: the deck is incomplete
warnings = []        # layout: text does not fit its box
chapter = None       # outline file of the chapter being laid out (for figures)

# ---------------------------------------------------------------- text model
TOKEN = re.compile(r"([_^])\{([^}]*)\}")


def runs_of(s, **opt):
    """'V_{out} = x^{2}' -> [(text, opts)] with sub/superscript runs."""
    out, pos = [], 0
    for m in TOKEN.finditer(s):
        if m.start() > pos:
            out.append((s[pos:m.start()], dict(opt)))
        o = dict(opt)
        o["base"] = -25 if m.group(1) == "_" else 30
        out.append((m.group(2), o))
        pos = m.end()
    if pos < len(s):
        out.append((s[pos:], dict(opt)))
    return out


MATHCH = "≫≪"


def split_math(runs):
    out = []
    for t, o in runs:
        for part in re.split(f"([{MATHCH}])", t):
            if not part:
                continue
            oo = dict(o)
            if part in MATHCH:
                oo["font"] = "Cambria Math"
            out.append((part, oo))
    return out


def para(text, size=18, color=TEXT, bold=False, bullet=False, after=6,
         align="l", italic=False, link=None):
    r = split_math(runs_of(text, size=size, color=color, bold=bold, italic=italic, link=link))
    return {"runs": r, "bullet": bullet, "after": after, "align": align,
            "size": size}


_fonts, _files = {}, {}


def font_file(pattern):
    """Font file for a fontconfig pattern, e.g. 'Carlito:bold'."""
    if pattern not in _files:
        _files[pattern] = subprocess.run(["fc-match", "-f", "%{file}", pattern],
                                         capture_output=True, text=True).stdout
    return _files[pattern]


def pil_font(size, bold=False, italic=False, font=None):
    """Font for measuring (size in pt*4) or drawing; Carlito has Calibri's metrics."""
    style = ":bold" * bool(bold) + ":italic" * bool(italic)
    key = (round(size * 4), style, font)
    if key not in _fonts:
        pattern = "DejaVu Sans" if font else "Carlito" + style
        _fonts[key] = ImageFont.truetype(font_file(pattern), max(1, round(size * 4)))
    return _fonts[key]


def run_size(o):
    return o["size"] * (0.65 if o.get("base") else 1.0)


def wrap(p, width_in):
    """Wrap a paragraph; returns list of lines, each a list of (text, opts)."""
    indent = 0.3 if p["bullet"] else 0.0
    avail = (width_in - indent) * 72 * 4          # in pil units (size*4 px per pt)
    words = []                                    # (text, opts, space_before)
    for text, o in p["runs"]:
        parts = re.split(r"( )", text)
        for part in parts:
            if part == "":
                continue
            if part == " ":
                words.append((" ", o))
            else:
                words.append((part, o))
    # group into unbreakable tokens: break only at spaces
    tokens, cur = [], []
    for w in words:
        if w[0] == " ":
            if cur:
                tokens.append(cur)
            tokens.append([w])
            cur = []
        else:
            cur.append(w)
    if cur:
        tokens.append(cur)

    def tw(tok):
        return sum(pil_font(run_size(o), o.get("bold"), o.get("italic"), o.get("font")).getlength(t)
                   for t, o in tok)
    lines, line, lw = [], [], 0.0
    for tok in tokens:
        w = tw(tok)
        if tok[0][0] == " " and not line:
            continue
        if lw + w > avail and line and tok[0][0] != " ":
            while line and line[-1][0] == " ":
                line.pop()
            lines.append(line)
            line, lw = [], 0.0
            if w > avail:
                warnings.append(f"word too long for box: {''.join(t for t, _ in tok)!r}")
        line.extend(tok)
        lw += w
    if line:
        lines.append(line)
    return lines or [[]]


def text_height(paras, width_in):
    h = 0.0
    for i, p in enumerate(paras):
        n = len(wrap(p, width_in))
        h += n * p["size"] * 1.2 / 72
        if i < len(paras) - 1:
            h += p["after"] / 72
    return h


# ---------------------------------------------------------------- primitives
def R(x, y, w, h, fill=None, line=None, radius=None, name=None, lw=1.0, link=None):
    return {"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill,
            "line": line, "radius": radius, "name": name, "lw": lw, "link": link}


def E(x, y, d, fill, name=None):
    return {"k": "ellipse", "x": x, "y": y, "w": d, "h": d, "fill": fill, "name": name}


def T(x, y, w, h, paras, valign="t", name=None, check=True, link=None):
    return {"k": "text", "x": x, "y": y, "w": w, "h": h, "paras": paras,
            "valign": valign, "name": name, "check": check, "link": link}


def I(path, x, y, w, h, name=None):
    return {"k": "img", "path": path, "x": x, "y": y, "w": w, "h": h, "name": name}


def fit_image(path, x, y, w, h, pad=0.15, name=None):
    im = Image.open(path)
    ar = im.width / im.height
    bw, bh = w - 2 * pad, h - 2 * pad
    if bw / bh > ar:
        ih, iw = bh, bh * ar
    else:
        iw, ih = bw, bw / ar
    # do not blow tiny crops up beyond ~2.2x their size on the A5 slide
    nat_w = im.width / 220 * (4.5 if ar > 2.6 else 3.2)
    if iw > nat_w:
        iw, ih = nat_w, nat_w / ar
    return I(path, x + (w - iw) / 2, y + (h - ih) / 2, iw, ih, name)


# ---------------------------------------------------------------- PPTX output
def rgb(h):
    return RGBColor.from_string(h)


def set_bullet(p, color=CYAN):
    pPr = p._p.get_or_add_pPr()
    pPr.set("marL", str(Inches(0.3)))
    pPr.set("indent", str(-Inches(0.3)))
    for tag in ("a:buClr", "a:buFont", "a:buChar", "a:buNone"):
        for e in pPr.findall(qn(tag)):
            pPr.remove(e)
    buClr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(buClr, qn("a:srgbClr")).set("val", color)
    etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
    etree.SubElement(pPr, qn("a:buChar")).set("char", "•")


def no_bullet(p):
    pPr = p._p.get_or_add_pPr()
    etree.SubElement(pPr, qn("a:buNone"))


def emit(slide, prims):
    for e in prims:
        k = e["k"]
        if k in ("rect", "ellipse"):
            shp = MSO_SHAPE.OVAL if k == "ellipse" else (
                MSO_SHAPE.ROUNDED_RECTANGLE if e.get("radius") else MSO_SHAPE.RECTANGLE)
            s = slide.shapes.add_shape(shp, Inches(e["x"]), Inches(e["y"]),
                                       Inches(e["w"]), Inches(e["h"]))
            if e.get("radius"):
                s.adjustments[0] = min(0.5, e["radius"] / min(e["w"], e["h"]))
            if e.get("fill"):
                s.fill.solid()
                s.fill.fore_color.rgb = rgb(e["fill"])
            else:
                s.fill.background()
            if e.get("line"):
                s.line.color.rgb = rgb(e["line"])
                s.line.width = Pt(e.get("lw", 1.0))
            else:
                s.line.fill.background()
            s.shadow.inherit = False
            if e.get("link"):
                s.click_action.hyperlink.address = e["link"]
            if e.get("name"):
                s.name = e["name"]
        elif k == "tri":
            s = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, Inches(e["x"] + (e["w"] - e["h"]) / 2),
                                       Inches(e["y"] + (e["h"] - e["w"]) / 2), Inches(e["h"]), Inches(e["w"]))
            s.rotation = 90
            s.fill.solid(); s.fill.fore_color.rgb = rgb(e["fill"]); s.line.fill.background()
            s.shadow.inherit = False
            s.name = "Play icon"
        elif k == "img":
            s = slide.shapes.add_picture(e["path"], Inches(e["x"]), Inches(e["y"]),
                                         Inches(e["w"]), Inches(e["h"]))
            if e.get("name"):
                s.name = e["name"]
        elif k == "text":
            s = slide.shapes.add_textbox(Inches(e["x"]), Inches(e["y"]),
                                         Inches(e["w"]), Inches(e["h"]))
            if e.get("name"):
                s.name = e["name"]
            tf = s.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE,
                                  "b": MSO_ANCHOR.BOTTOM}[e["valign"]]
            bodyPr = tf._txBody.find(qn("a:bodyPr"))
            for a in list(bodyPr):
                bodyPr.remove(a)
            etree.SubElement(bodyPr, qn("a:noAutofit"))
            for i, pd in enumerate(e["paras"]):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER,
                               "r": PP_ALIGN.RIGHT}[pd["align"]]
                p.space_after = Pt(pd["after"])
                p.line_spacing = 1.0
                if pd["bullet"]:
                    set_bullet(p)
                else:
                    no_bullet(p)
                for text, o in pd["runs"]:
                    r = p.add_run()
                    r.text = text
                    f = r.font
                    f.name = o.get("font", FONT)
                    f.size = Pt(o["size"])
                    f.bold = bool(o.get("bold"))
                    f.italic = bool(o.get("italic"))
                    f.color.rgb = rgb(o["color"])
                    if o.get("base"):
                        r._r.get_or_add_rPr().set("baseline", str(o["base"] * 1000))
                    if o.get("link"):
                        r.hyperlink.address = o["link"]
                        # keep our colour instead of the theme hyperlink colour
                        rPr = r._r.get_or_add_rPr()
                        hl = rPr.find(qn("a:hlinkClick"))
                        if hl is not None:
                            ext = etree.SubElement(hl, qn("a:extLst"))
                            ext_e = etree.SubElement(ext, qn("a:ext"))
                            ext_e.set("uri", "{A12FA001-AC4F-418D-AE19-62706E023703}")
                            hc = etree.SubElement(ext_e, "{http://schemas.microsoft.com/office/drawing/2018/hyperlinkcolor}hlinkClr", nsmap={"ahyp": "http://schemas.microsoft.com/office/drawing/2018/hyperlinkcolor"})
                            hc.set("val", "tx")
            if e.get("link"):
                s.click_action.hyperlink.address = e["link"]


# ---------------------------------------------------------------- PNG preview
DPI = 60


def px(v):
    return int(round(v * DPI))


def hexc(h):
    return "#" + h


def preview(prims, bg, out, label):
    im = Image.new("RGB", (px(W), px(H)), hexc(bg))
    d = ImageDraw.Draw(im)
    for e in prims:
        x0, y0, x1, y1 = px(e["x"]), px(e["y"]), px(e["x"] + e["w"]), px(e["y"] + e["h"])
        if e["k"] == "rect":
            if e.get("radius"):
                d.rounded_rectangle([x0, y0, x1, y1], radius=px(e["radius"]),
                                    fill=hexc(e["fill"]) if e.get("fill") else None,
                                    outline=hexc(e["line"]) if e.get("line") else None)
            else:
                d.rectangle([x0, y0, x1, y1], fill=hexc(e["fill"]) if e.get("fill") else None,
                            outline=hexc(e["line"]) if e.get("line") else None)
        elif e["k"] == "tri":
            d.polygon([(x0, y0), (x1, (y0 + y1) // 2), (x0, y1)], fill=hexc(e["fill"]))
        elif e["k"] == "ellipse":
            d.ellipse([x0, y0, x1, y1], fill=hexc(e["fill"]))
        elif e["k"] == "img":
            pic = Image.open(e["path"]).convert("RGBA").resize((max(1, x1 - x0), max(1, y1 - y0)))
            im.paste(pic, (x0, y0), pic)
        elif e["k"] == "text":
            draw_text(d, e)
    if label:
        d.text((4, 2), label, fill="red")
    im.save(out)


def check_fit(e):
    """True if the text fits its box, else a warning."""
    total = text_height(e["paras"], e["w"])
    if total > e["h"] + 0.02:
        warnings.append(f"slide {e.get('_slide')}: overflow {total:.2f}in > {e['h']:.2f}in in "
                        f"{e.get('name') or 'text'}: {''.join(t for t, _ in e['paras'][0]['runs'])[:50]!r}")
        return False
    return True


def draw_text(d, e):
    total = text_height(e["paras"], e["w"])
    if e.get("check", True) and not check_fit(e):
        d.rectangle([px(e["x"]), px(e["y"]), px(e["x"] + e["w"]), px(e["y"] + e["h"])], outline="red", width=2)
    y = e["y"] + {"t": 0, "m": (e["h"] - total) / 2, "b": e["h"] - total}[e["valign"]]
    sc = DPI / 72 / 4
    for p in e["paras"]:
        indent = 0.3 if p["bullet"] else 0
        for li, line in enumerate(wrap(p, e["w"])):
            lw = sum(pil_font(run_size(o), o.get("bold"), o.get("italic"), o.get("font")).getlength(t)
                     for t, o in line) * sc
            x = e["x"] + indent
            if p["align"] == "c":
                x = e["x"] + (e["w"] - lw / DPI) / 2
            if p["bullet"] and li == 0:
                d.ellipse([px(e["x"] + 0.06), px(y + p["size"] * 0.55 / 72) - 2,
                           px(e["x"] + 0.06) + 4, px(y + p["size"] * 0.55 / 72) + 2], fill=hexc(CYAN))
            xx = px(x)
            for t, o in line:
                f = pil_font(run_size(o) * DPI / 72, o.get("bold"), o.get("italic"), o.get("font"))
                f = ImageFont.truetype(f.path, max(1, round(run_size(o) * DPI / 72)))
                dy = 0 if not o.get("base") else (o["size"] * 0.35 / 72 if o["base"] < 0 else -o["size"] * 0.1 / 72)
                d.text((xx, px(y + dy)), t, font=f, fill=hexc(o["color"]))
                xx += f.getlength(t)
            y += p["size"] * 1.2 / 72
        y += p["after"] / 72


# ---------------------------------------------------------------- slide parts
TITLE_Y, TITLE_H = 0.42, 0.75
TOP, BOTTOM = 1.42, 6.72
ML, MR = 0.6, 0.6


def footer(ch, num, dark=False):
    c = WHITE if dark else MUTED
    out = []
    if not dark:
        out.append(I(LOGO, ML, 6.98, 0.30 * 2748 / 912, 0.30, name="RWU logo"))
    label = "Electronic Circuit Design" + (f"  ·  {ch}" if ch else "")
    out.append(T(ML + 1.25 if not dark else ML, 7.02, 8.0, 0.25,
                 [para(label, 11, c)], name="Footer"))
    out.append(T(W - MR - 1.0, 7.02, 1.0, 0.25, [para(str(num), 11, c, align="r")],
                 name="Slide number"))
    return out


def title(text, kicker=None):
    out = []
    if kicker:
        out.append(T(ML, 0.22, 9.0, 0.28, [para(kicker.upper(), 12, CYAN_D, bold=True)],
                     name="Section"))
    out.append(T(ML, TITLE_Y + 0.08, W - ML - MR, TITLE_H,
                 [para(text, 32, VIOLET, bold=True)], valign="m", name="Title"))
    return out


def falstad_chip(name, hint, x, y, w):
    """Clickable chip that opens the example in the Falstad simulator."""
    info = FALSTAD.get(name)
    if not info:
        problems.append(f"unknown falstad example {name}")
        return [], 0
    url = info["url"]
    hint_p = [para(hint, 13, TEXT)] if hint else []
    hh = text_height(hint_p, w - 0.85) if hint else 0
    h = 0.32 + hh + 0.24
    out = [R(x, y, w, h, fill=CTINT, line=CYAN, radius=0.12, name=f"Falstad {name}", link=url),
           E(x + 0.16, y + h / 2 - 0.22, 0.44, CYAN, name="Play icon"),
           {"k": "tri", "x": x + 0.33, "y": y + h / 2 - 0.11, "w": 0.18, "h": 0.22, "fill": WHITE},
           T(x + 0.75, y + 0.12, w - 0.85, 0.3,
             [{"runs": [("Falstad  ", {"size": 13, "color": CYAN_D, "bold": True, "link": url}),
                        (f"{info['chapter']}/{name}", {"size": 13, "color": CYAN_D, "link": url})],
               "bullet": False, "after": 0, "align": "l", "size": 13}],
             link=url, name=f"Falstad link {name}")]
    if hint:
        out.append(T(x + 0.75, y + 0.42, w - 0.85, hh + 0.02, hint_p, name="Falstad hint"))
    return out, h


def chips(items, x, y, w, gap=0.14):
    out, yy = [], y
    for it in items:
        o, h = falstad_chip(it["name"], it.get("hint"), x, yy, w)
        out += o
        yy += h + gap
    return out, yy - y - (gap if items else 0)


def chips_height(items, w, gap=0.14):
    return sum(falstad_chip(it["name"], it.get("hint"), 0, 0, w)[1] for it in items) + gap * max(0, len(items) - 1)


def rule_box(text, x, y, w):
    p = [para(text, 17, VIOLET_D, bold=True)]
    th = text_height(p, w - 0.5)
    h = th + 0.62
    return [R(x, y, w, h, fill=VTINT, radius=0.12, name="Key rule"),
            T(x + 0.25, y + 0.12, w - 0.5, 0.24, [para("KEY RULE", 11, VIOLET, bold=True)], name="Key rule label"),
            T(x + 0.25, y + 0.42, w - 0.5, th + 0.02, p, name="Key rule text")], h


def rule_height(text, w):
    return text_height([para(text, 17, VIOLET_D, bold=True)], w - 0.5) + 0.62


def fig_path(fig):
    return os.path.join(FIGS, chapter, fig)


def figure_panel(fig, x, y, w, h):
    if isinstance(fig, list):
        if len(fig) == 1:
            fig = fig[0]
        else:
            out = [R(x, y, w, h, fill=WHITE, line="DDDDE3", radius=0.12, name="Figure panel")]
            sh = h / len(fig)
            for i, f in enumerate(fig):
                out.append(fit_image(fig_path(f), x, y + i * sh, w, sh, pad=0.2, name="Circuit figure"))
            return out
    path = fig_path(fig)
    if not os.path.exists(path):
        problems.append(f"missing figure {fig}")
        return []
    return [R(x, y, w, h, fill=WHITE, line="DDDDE3", radius=0.12, name="Figure panel"),
            fit_image(path, x, y, w, h, pad=0.22, name="Circuit figure")]


def bullets_block(items, size=20):
    return [para(b, size, TEXT, bullet=True, after=10) for b in items]


# ---------------------------------------------------------------- slide types
def lay_points(s, ch):
    fig = s.get("figure")
    if isinstance(fig, str) and os.path.exists(fig_path(fig)):
        im = Image.open(fig_path(fig))
        if im.width / im.height > 2.6:
            out = _lay_points(s, True)
            if out is not None:
                return out
    return _lay_points(s, False, force=True)


def _lay_points(s, wide, force=False):
    out = title(s["title"], s.get("section"))
    fig = s.get("figure")
    fal = s.get("falstad") or []
    rule = s.get("rule")
    colw = 6.35 if fig and not wide else W - ML - MR
    if fig and not wide:
        out += figure_panel(fig, ML + colw + 0.35, TOP, W - MR - (ML + colw + 0.35), BOTTOM - TOP)
    ch_h = chips_height(fal, colw) if fal else 0
    r_h = rule_height(rule, colw) if rule else 0
    y_b = BOTTOM
    if fal:
        o, _ = chips(fal, ML, y_b - ch_h, colw)
        out += o
        y_b -= ch_h + 0.3
    if wide:
        out += figure_panel(fig, ML, y_b - 2.3, colw, 2.3)
        y_b -= 2.3 + 0.3
    room = y_b - TOP - (r_h + 0.35 if rule else 0)
    size = 20
    bl = bullets_block(s.get("bullets", []), size)
    while text_height(bl, colw) > room and size > 16:
        size -= 1
        bl = bullets_block(s.get("bullets", []), size)
    if not force and text_height(bl, colw) > room:
        return None
    bh = min(text_height(bl, colw) + 0.05, room)
    out.append(T(ML, TOP, colw, max(bh, room) if not rule else bh, bl, name="Bullets"))
    if rule:
        o, _ = rule_box(rule, ML, TOP + bh + 0.35, colw)
        out += o
    return out


def lay_example(s, ch):
    out = title(s["title"], s.get("section"))
    fig = s.get("figure")
    fal = s.get("falstad") or []
    if fig:
        colx = ML + 7.35
        out += figure_panel(fig, ML, TOP, 7.0, BOTTOM - TOP)
    else:
        colx = ML
    colw = W - MR - colx
    out.append(T(colx, TOP, colw, 0.35, [para("TRY IT IN FALSTAD", 12, CYAN_D, bold=True)], name="Label"))
    o, ch_h = chips(fal, colx, TOP + 0.45, colw)
    out += o
    y = TOP + 0.45 + ch_h + 0.4
    obs = s.get("observe") or []
    if obs:
        out.append(T(colx, y, colw, 0.35, [para("OBSERVE", 12, VIOLET, bold=True)], name="Label"))
        size = 18
        bl = bullets_block(obs, size)
        while text_height(bl, colw) > BOTTOM - y - 0.45 and size > 15:
            size -= 1
            bl = bullets_block(obs, size)
        out.append(T(colx, y + 0.45, colw, BOTTOM - y - 0.45, bl, name="Observe"))
    return out


def lay_recipe(s, ch):
    out = title(s["title"], s.get("section"))
    fig = s.get("figure")
    steps = s.get("steps", [])
    colw = 6.6 if fig else W - ML - MR
    if fig:
        out += figure_panel(fig, ML + colw + 0.35, TOP, W - MR - (ML + colw + 0.35), BOTTOM - TOP)
    avail = BOTTOM - TOP
    size = 20
    while True:
        hs = [max(0.62, text_height([para(t, size)], colw - 0.95)) for t in steps]
        gap = 0.22
        if sum(hs) + gap * (len(steps) - 1) <= avail or size <= 16:
            break
        size -= 1
    y = TOP
    for i, (t, h) in enumerate(zip(steps, hs)):
        out.append(E(ML, y + (min(h, 0.62) - 0.52) / 2 if h > 0.62 else y + 0.05, 0.52, VIOLET, name=f"Step {i+1}"))
        out.append(T(ML, (y + 0.05) if h > 0.62 else y + 0.05, 0.52, 0.52,
                     [para(str(i + 1), 18, WHITE, bold=True, align="c")], valign="m", check=False))
        out.append(T(ML + 0.8, y + (0.62 - text_height([para(t, size)], colw - 0.95)) / 2 if h <= 0.62 else y,
                     colw - 0.95, h, [para(t, size, TEXT)], name=f"Step text {i+1}"))
        y += h + gap
    return out


def lay_compare(s, ch):
    out = title(s["title"], s.get("section"))
    fig = s.get("figure")
    sides = [(s["left"], VTINT, VIOLET), (s["right"], CTINT, CYAN_D)]
    if fig:
        colw = 6.6
        out += figure_panel(fig, ML + colw + 0.35, TOP, W - MR - (ML + colw + 0.35), BOTTOM - TOP)
        ch_ = (BOTTOM - TOP - 0.3) / 2
        boxes = [(ML, TOP, colw, ch_), (ML, TOP + ch_ + 0.3, colw, ch_)]
    else:
        cw = (W - ML - MR - 0.4) / 2
        boxes = [(ML, TOP, cw, BOTTOM - TOP), (ML + cw + 0.4, TOP, cw, BOTTOM - TOP)]
    if not fig:
        need = max(text_height(bullets_block(sd["bullets"], 20), boxes[0][2] - 0.7) for sd, _, _ in sides) + 1.35
        hh = min(BOTTOM - TOP, max(2.6, need))
        boxes = [(bx, by, bw, hh) for bx, by, bw, _ in boxes]
    for (side, fill, hc), (x, y, w, h) in zip(sides, boxes):
        out.append(R(x, y, w, h, fill=fill, radius=0.14, name="Compare card"))
        out.append(T(x + 0.35, y + 0.3, w - 0.7, 0.5, [para(side["head"], 22, hc, bold=True)], name="Card head"))
        size = 20
        bl = bullets_block(side["bullets"], size)
        while text_height(bl, w - 0.7) > h - 1.15 and size > 16:
            size -= 1
            bl = bullets_block(side["bullets"], size)
        out.append(T(x + 0.35, y + 0.95, w - 0.7, h - 1.15, bl, name="Card bullets"))
    return out


def lay_exercises(chap):
    out = title("Now work it out in the script", "Exercises")
    ex = chap.get("exercises") or []
    out.append(T(ML, TOP, W - ML - MR, 0.7,
                 [para(f"Derivations, worked numbers and solutions: script, chapter {chap['number']} "
                       f"“{chap['chapter']}”. Check each result in the Falstad examples.", 18, MUTED)],
                 name="Intro"))
    n = len(ex)
    cols = 2 if n > 4 else 1
    rows = (n + cols - 1) // cols
    gw = (W - ML - MR - 0.3 * (cols - 1)) / cols
    top = TOP + 0.95
    rh = min(0.8, (BOTTOM - top - 0.18 * (rows - 1)) / max(rows, 1))
    for i, t in enumerate(ex):
        c, r = divmod(i, rows)
        x, y = ML + c * (gw + 0.3), top + r * (rh + 0.18)
        m = re.match(r"\s*(?:Exercise\s+)?(\d+\.\d+)\s*[:.]?\s*(.*)", t)
        num, txt = (m.group(1), m.group(2)) if m else ("", t)
        out.append(R(x, y, gw, rh, fill=GTINT, radius=0.1, name="Exercise card"))
        out.append(R(x, y, 1.0, rh, fill=VIOLET, radius=0.1, name="Exercise number"))
        out.append(T(x, y, 1.0, rh, [para(num, 17, WHITE, bold=True, align="c")], valign="m"))
        size = 17
        while text_height([para(txt, size)], gw - 1.35) > rh - 0.1 and size > 13:
            size -= 1
        out.append(T(x + 1.2, y, gw - 1.35, rh, [para(txt, size, TEXT)], valign="m", name="Exercise title"))
    return out


def lay_chapter(chap):
    out = [T(ML, 0.9, 3.0, 1.6, [para(f"{chap['number']:02d}", 96, VIOLET_L, bold=True)], name="Chapter number"),
           T(ML, 2.55, W - ML - MR, 1.0, [para(chap["chapter"], 44, WHITE, bold=True)], name="Chapter title", valign="m"),
           T(ML, 3.55, W - ML - MR, 0.5, [para(chap.get("subtitle", ""), 20, "CFE9F3")], name="Chapter subtitle")]
    tk = chap.get("takeaways", [])[:3]
    if tk:
        cw = (W - ML - MR - 0.3 * (len(tk) - 1)) / len(tk)
        for i, t in enumerate(tk):
            x = ML + i * (cw + 0.3)
            out.append(R(x, 4.55, cw, 1.75, fill="7A50C8", radius=0.14, name="Takeaway card"))
            out.append(T(x + 0.3, 4.72, cw - 0.6, 0.3, [para(f"TAKE-HOME {i+1}", 11, "CFE9F3", bold=True)]))
            out.append(T(x + 0.3, 5.07, cw - 0.6, 1.1, [para(t, 18, WHITE, bold=True)], name="Takeaway"))
    return out


# ---------------------------------------------------------------- front matter
def lay_cover():
    return [R(0, 0, W, H, fill=VIOLET, name="Background"),
            R(ML, 0.6, 3.3, 1.2, fill=WHITE, radius=0.12, name="Logo card"),
            I(LOGO, ML + 0.25, 0.6 + 0.2, 0.8 * 2748 / 912, 0.8, name="RWU logo"),
            T(ML, 2.6, W - 2 * ML, 1.1, [para("Electronic Circuit Design", 54, WHITE, bold=True)], valign="m"),
            T(ML, 3.75, W - 2 * ML, 0.6, [para("The practical points — with Falstad examples", 26, "CFE9F3")]),
            T(ML, 5.4, 8, 0.45, [para("Prof. Dr. Markus Pfeil", 20, WHITE, bold=True)]),
            T(ML, 5.85, 8, 0.4, [para("Winter semester 2026/27", 18, "CFE9F3")])]


def lay_howto():
    out = title("How to use this deck", "Introduction")
    cards = [("Slides", VIOLET, "The practical points of each section: rules of thumb, design recipes, pitfalls"),
             ("Script", CYAN_D, "All derivations, worked numbers and the exercises: work the math there"),
             ("Falstad", CYAN, "Every example is one click away: the chips open the circuit in the browser")]
    cw = (W - ML - MR - 0.6) / 3
    for i, (h, c, t) in enumerate(cards):
        x = ML + i * (cw + 0.3)
        out += [R(x, TOP + 0.2, cw, 3.1, fill=GTINT, radius=0.14, name="Info card"),
                E(x + 0.35, TOP + 0.5, 0.75, c, name="Card icon"),
                T(x + 0.35, TOP + 0.5, 0.75, 0.75, [para(str(i + 1), 24, WHITE, bold=True, align="c")], valign="m", check=False),
                T(x + 0.35, TOP + 1.45, cw - 0.7, 0.5, [para(h, 24, c, bold=True)]),
                T(x + 0.35, TOP + 2.0, cw - 0.7, 1.2, [para(t, 17, TEXT)])]
    o, _ = chips([{"name": "led_resistor", "hint": "Example chip: click it to open the circuit in the simulator"}],
                 ML, 5.3, 7.2)
    out += o
    out.append(T(ML + 7.6, 5.3, W - MR - ML - 7.6, 1.2,
                 [para("Thread through all chapters: the capstone chain Pt100 bridge → amplifier → "
                       "anti-aliasing filter → sample & hold → 3-bit flash ADC", 15, MUTED)]))
    return out


def lay_agenda(chaps):
    out = title("Contents", "Introduction")
    cw = (W - ML - MR - 0.4) / 2
    rh = 0.86
    for i, c in enumerate(chaps):
        col, row = divmod(i, 5)
        x, y = ML + col * (cw + 0.4), TOP + 0.1 + row * (rh + 0.16)
        out += [R(x, y, cw, rh, fill=GTINT, radius=0.1, name="Agenda item"),
                T(x + 0.25, y, 0.9, rh, [para(f"{c['number']:02d}", 26, VIOLET, bold=True)], valign="m"),
                T(x + 1.15, y, cw - 1.3, rh, [para(c["chapter"], 19, TEXT, bold=True),
                                               para(c.get("subtitle", ""), 13, MUTED, after=0)], valign="m")]
    return out


# ---------------------------------------------------------------- sections XML
def add_sections(prs, sections):
    """sections: list of (name, [slide indices]) -> p14:sectionLst."""
    pres = prs.part._element
    sldIds = [s.get("id") for s in pres.find(qn("p:sldIdLst"))]
    P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
    extLst = pres.find(qn("p:extLst"))
    if extLst is None:
        extLst = etree.SubElement(pres, qn("p:extLst"))
    ext = etree.SubElement(extLst, qn("p:ext"))
    ext.set("uri", "{521415D9-36F7-43E2-AB2F-B90AF26B5E84}")
    sl = etree.SubElement(ext, f"{{{P14}}}sectionLst", nsmap={"p14": P14})
    import uuid
    for name, idx in sections:
        sec = etree.SubElement(sl, f"{{{P14}}}section")
        sec.set("name", name)
        sec.set("id", "{" + str(uuid.uuid4()).upper() + "}")
        lst = etree.SubElement(sec, f"{{{P14}}}sldIdLst")
        for i in idx:
            etree.SubElement(lst, f"{{{P14}}}sldId").set("id", sldIds[i])


# ---------------------------------------------------------------- main
def render_logo():
    import pymupdf
    os.makedirs(BUILD, exist_ok=True)
    doc = pymupdf.open(os.path.join(ROOT, "rwu_logo_hor_lila-cyan_cmyk.pdf"))
    doc[0].get_pixmap(dpi=400, alpha=True).save(LOGO)


def main(out_path, prev_dir=None):
    global chapter
    render_logo()
    chaps = []
    for f in ORDER:
        p = os.path.join(OUTLINE, f + ".json")
        if os.path.exists(p):
            chaps.append(json.load(open(p)))
        else:
            problems.append(f"missing outline {f}")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    prs.core_properties.title = "Electronic Circuit Design: the practical points"
    prs.core_properties.author = "Prof. Dr. Markus Pfeil"
    blank = prs.slide_layouts[6]
    if prev_dir:
        os.makedirs(prev_dir, exist_ok=True)
        for f in glob.glob(os.path.join(prev_dir, "s*.png")):
            os.remove(f)
    sections, n = [], 0
    used = set()

    def add(prims, bg=WHITE, notes=None, chname=None, dark=False, cover=False):
        nonlocal n
        n += 1
        if not cover:
            prims = prims + footer(chname, n, dark)
        for e in prims:
            e["_slide"] = n
        sl = prs.slides.add_slide(blank)
        if bg != WHITE:
            sl.background.fill.solid()
            sl.background.fill.fore_color.rgb = rgb(bg)
        else:
            sl.background.fill.solid()
            sl.background.fill.fore_color.rgb = rgb(WHITE)
        emit(sl, prims)
        if notes:
            sl.notes_slide.notes_text_frame.text = notes
        if prev_dir:
            preview(prims, bg, os.path.join(prev_dir, f"s{n:03d}.png"), str(n))
        else:
            for e in prims:
                if e["k"] == "text" and e.get("check", True):
                    check_fit(e)
        return n - 1

    intro = [add(lay_cover(), VIOLET, cover=True,
                 notes="Condensed deck: practical points per section, all Falstad examples. "
                       "Derivations and exercises are in the script."),
             add(lay_howto(), notes="Explain the split: slides for the ideas, script for the math, Falstad for the proof."),
             add(lay_agenda(chaps))]
    sections.append(("Introduction", intro))
    for c in chaps:
        chapter = c["file"]
        idx = [add(lay_chapter(c), VIOLET, notes=f"Chapter {c['number']}: {c['chapter']}. "
                   + " ".join(c.get("takeaways", [])), chname=c["chapter"], dark=True)]
        for s in c["slides"]:
            lay = {"points": lay_points, "example": lay_example, "recipe": lay_recipe,
                   "compare": lay_compare}.get(s["type"])
            if not lay:
                problems.append(f"{c['file']}: unknown slide type {s['type']}")
                continue
            for it in s.get("falstad") or []:
                if it["name"] in used:
                    problems.append(f"duplicate falstad {it['name']}")
                used.add(it["name"])
            idx.append(add(lay(s, c), notes=s.get("notes"), chname=c["chapter"]))
        if c.get("exercises"):
            idx.append(add(lay_exercises(c), notes="Exercises with full solutions are in the script "
                           "(docu.pdf); the student version has no solutions.", chname=c["chapter"]))
        sections.append((f"{c['number']}  {c['chapter']}", idx))
    add_sections(prs, sections)
    prs.save(out_path)
    missing = sorted(set(FALSTAD) - used)
    if len(chaps) == len(ORDER) and missing:
        problems.append(f"falstad examples not used: {missing}")
    print(f"{n} slides -> {out_path}")
    for w in warnings:
        print("warning:", w)
    for p in problems:
        print("ERROR:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-o", "--output", default=os.path.join(ROOT, "pdf", "CircuitDesign_Slides_Practical.pptx"))
    ap.add_argument("--preview", metavar="DIR", help="also draw every slide as PNG into DIR")
    a = ap.parse_args()
    sys.exit(main(a.output, a.preview))
