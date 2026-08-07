#!/usr/bin/env python3
"""Render the GitHub stats card for the profile README.

Self-hosted on purpose: the popular third-party stats services
(github-readme-stats, streak-stats) go down regularly, and a broken image on
a profile README looks worse than no image at all.

Languages are ranked by *repository count*, not bytes of code. Ranking by
bytes lets a couple of large coursework repos dominate and misrepresent what
someone actually works with day to day.

Run:  python scripts/generate_stats.py
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import os
import pathlib
import urllib.request

USER = "Basil-Yaqoob"
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "stats.png"

# Palette — matches the portfolio (sampled from the portrait).
BG = (14, 12, 9)
PANEL = (26, 23, 18)
LINE = (42, 36, 28)
BRASS = (217, 160, 91)
TEXT = (242, 237, 228)
MUTED = (168, 157, 142)
DIM = (124, 118, 110)

# Tonal brass ramp for the bar — deliberately monochrome, not rainbow.
RAMP = [(217, 160, 91), (191, 137, 74), (163, 114, 60), (135, 93, 48),
        (108, 74, 38), (82, 56, 29), (60, 41, 22)]

FONT_CANDIDATES = {
    "bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             r"C:\Windows\Fonts\segoeuib.ttf"],
    "regular": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                r"C:\Windows\Fonts\segoeui.ttf"],
    "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
             r"C:\Windows\Fonts\consolab.ttf"],
}


def api(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-stats"})
    if token := os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def font(kind: str, size: int):
    from PIL import ImageFont
    for path in FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    from PIL import Image, ImageDraw

    repos = [r for r in api(f"https://api.github.com/users/{USER}/repos?per_page=100")
             if not r["fork"]]
    counts = collections.Counter(r["language"] for r in repos if r.get("language"))
    total = sum(counts.values())
    if not total:
        raise SystemExit("no languages found")

    ranked = counts.most_common(7)

    W, H = 1200, 300
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([1, 1, W - 2, H - 2], radius=18, fill=PANEL, outline=LINE, width=2)

    M = 48
    d.text((M, 40), "G I T H U B   ·   A T   A   G L A N C E", font=font("mono", 17), fill=BRASS)
    d.text((W - M, 42), dt.date.today().isoformat(), font=font("mono", 15), fill=DIM, anchor="ra")

    # Stacked bar
    bar_y, bar_h, bar_w = 100, 22, W - 2 * M
    x = M
    for i, (_lang, n) in enumerate(ranked):
        seg = bar_w * n / total
        # last segment absorbs rounding so the bar always ends flush
        if i == len(ranked) - 1:
            seg = (M + bar_w) - x
        d.rectangle([x, bar_y, x + seg, bar_y + bar_h], fill=RAMP[i % len(RAMP)])
        x += seg

    # Legend
    lx, ly = M, 158
    for i, (lang, n) in enumerate(ranked):
        pct = f"{n / total * 100:.1f}%"
        d.ellipse([lx, ly + 5, lx + 11, ly + 16], fill=RAMP[i % len(RAMP)])
        label = f"{lang}  {pct}"
        d.text((lx + 21, ly), label, font=font("regular", 19), fill=TEXT if i == 0 else MUTED)
        lx += int(d.textlength(label, font=font("regular", 19))) + 58
        if lx > W - 220:
            lx, ly = M, ly + 34

    d.line([(M, 234), (W - M, 234)], fill=LINE, width=2)
    d.text((M, 252), f"{len(repos)} public repositories  ·  share by repository count",
           font=font("regular", 17), fill=DIM)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    for lang, n in ranked:
        print(f"  {lang:20s} {n:2d} repos  {n / total * 100:5.1f}%")


if __name__ == "__main__":
    main()
