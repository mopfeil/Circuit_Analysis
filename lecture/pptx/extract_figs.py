"""Cut the circuit diagrams and plots out of slides.pdf as PNG files.

    python pptx/extract_figs.py slides.pdf build/pptx/figs

Every vector drawing on a slide page becomes one PNG (labels around it are
included). Figures are named after the chapter and the slide heading they
sit under, not after the page number, so the outlines stay valid when the
slides move by a page:

    build/pptx/figs/<ChapterFile>/<heading-slug>-<k>.png

k counts the figures under the same heading within the chapter (1, 2, ...).
catalog.json lists every figure with its page, so you can look them up.
"""
import json
import os
import re
import sys

import pymupdf

HEAD_SIZE = 13      # slide headings are bold and larger than this (pt)


def chapter_pages(tex_dir):
    """[(first page, chapter file)] from slides.toc and text.tex."""
    files = {}
    for m in re.finditer(r"^\\chap\{([^}]*)\}\{([^}]*)\}", open(os.path.join(tex_dir, "text.tex")).read(), re.M):
        files[m.group(1)] = m.group(2)
    out = []
    for m in re.finditer(r"\\contentsline \{chapter\}\{(.*?)\}\{(\d+)\}", open(os.path.join(tex_dir, "slides.toc")).read()):
        if m.group(1) in files:
            out.append((int(m.group(2)), files[m.group(1)]))
    return sorted(out)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "figure"


def clusters_of(page):
    W, H = page.rect.width, page.rect.height
    links = [pymupdf.Rect(l["from"]) for l in page.get_links()]
    rects = []
    for d in page.get_drawings():
        r = pymupdf.Rect(d["rect"])
        if r.y0 > H - 30:                       # footer and logo
            continue
        if r.width > 0.6 * W:                   # box backgrounds, rules
            continue
        if any(r.intersects(l + (-4, -4, 4, 4)) for l in links):   # Falstad link boxes
            continue
        if r.width < 5 and r.height < 5 and d.get("fill") and not d.get("color"):   # bullets
            continue
        rects.append(r)
    clusters = []
    for r in rects:
        r = pymupdf.Rect(r)
        merged = True
        while merged:
            merged = False
            for c in clusters:
                if (c + (-28, -12, 28, 12)).intersects(r):
                    clusters.remove(c)
                    r |= c
                    merged = True
                    break
        clusters.append(r)
    return [c for c in clusters
            if c.width * c.height >= 2500 and c.width >= 60 and c.height >= 30]


def text_lines(page):
    """(rect, is_heading, text) of all text lines."""
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            sp = [s for s in l["spans"] if s["text"].strip()]
            if sp:
                head = any(s["size"] > HEAD_SIZE and s["flags"] & 16 for s in sp)
                out.append((pymupdf.Rect(l["bbox"]), head, "".join(s["text"] for s in sp).strip()))
    return out


def with_labels(c, lines, page):
    """Grow the drawing's box by the labels that belong to it."""
    W, H = page.rect.width, page.rect.height
    e = pymupdf.Rect(c)
    for dx, dy, maxw in [(22, 9, 0.6 * W), (22, 9, 70)]:
        base = pymupdf.Rect(e)
        for t, head, _ in lines:
            if head or t.width > maxw or t.y1 > H - 30:
                continue
            near = (base + (-dx, -dy, dx, dy)).intersects(t)
            if near and (t.width < 50 or (t.x0 >= base.x0 - dx and t.x1 <= base.x1 + dx)):
                e |= t
    return (e + (-4, -4, 4, 4)) & page.rect


def main(pdf, out_dir):
    tex_dir = os.path.dirname(os.path.abspath(pdf))
    chapters = chapter_pages(tex_dir)
    doc = pymupdf.open(pdf)
    catalog, count = {}, {}
    heading, chapter = "", None
    for pno, page in enumerate(doc, 1):
        for first, f in chapters:
            if pno >= first:
                if f != chapter:
                    heading = ""
                chapter = f
        if chapter is None:
            continue
        lines = text_lines(page)
        heads = sorted((t.y0, txt) for t, h, txt in lines if h and not re.match(r"^\d+\.\d+ ", txt))
        for c in sorted(clusters_of(page), key=lambda r: (r.y0, r.x0)):
            above = [txt for y, txt in heads if y < (c.y0 + c.y1) / 2]
            h = above[-1] if above else heading
            key = (chapter, slug(h))
            count[key] = count.get(key, 0) + 1
            name = f"{slug(h)}-{count[key]}.png"
            os.makedirs(os.path.join(out_dir, chapter), exist_ok=True)
            page.get_pixmap(clip=with_labels(c, lines, page), dpi=220).save(
                os.path.join(out_dir, chapter, name))
            catalog[f"{chapter}/{name}"] = {"page": pno, "heading": h}
        if heads:
            heading = heads[-1][1]
    json.dump(catalog, open(os.path.join(out_dir, "catalog.json"), "w"), indent=1)
    print(f"{len(catalog)} figures -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
