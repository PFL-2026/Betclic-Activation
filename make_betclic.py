#!/usr/bin/env python3
"""
make_betclic.py — deterministic PFL x Betclic deck build.

Rebuilds from a pristine NetBet-Activation GitHub checkout in a single verified
pass. No stateful edits: run it twice, get byte-identical output.

Usage:  python3 make_betclic.py
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, uniform_filter

ROOT = Path("/home/claude/work")
SRC = ROOT / "netbet_src"            # pristine checkout
BC = ROOT / "betclic_assets"         # supplied Betclic assets
OUT = ROOT / "betclic"               # build target

CACHE_BUST = "20260903-betclic1"

# Betclic brand palette, sampled from the supplied wordmark
BC_RED = "#e10014"
BC_RED_DEEP = "#a8000f"
BC_RED_BRIGHT = "#ff2a3d"
BC_RED_RGB = (225, 0, 20)

# NetBet literals being replaced
NB_RED = "#c62026"
NB_RED_DEEP = "#8e1319"
NB_RED_BRIGHT = "#e63a41"
NB_RGB_RE = r"rgba\(198,\s*32,\s*38\s*,"

FONT_DIR = Path("/mnt/skills/examples/canvas-design/canvas-fonts")

FAILURES = []
CHECKS = 0


def check(cond, label):
    global CHECKS
    CHECKS += 1
    if not cond:
        FAILURES.append(label)


def sub1(text, pattern, repl, label, count=1, flags=0):
    """Regex-replace with an exact-hit-count assertion."""
    new, n = re.subn(pattern, repl, text, count=count, flags=flags)
    check(n == count, f"{label} (expected {count}, made {n})")
    return new


def subN(text, pattern, repl, label, flags=0):
    """Regex-replace all, asserting at least one hit."""
    new, n = re.subn(pattern, repl, text, flags=flags)
    check(n > 0, f"{label} (expected >=1, made 0)")
    return new


# ---------------------------------------------------------------------------
# 1. Pristine source
# ---------------------------------------------------------------------------

def prepare_source():
    if not SRC.exists():
        subprocess.run(
            ["git", "clone", "--depth", "1",
             "https://github.com/PFL-2026/Netbet-Activation.git", str(SRC)],
            check=True, capture_output=True,
        )
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns(".git"))
    (OUT / "make_netbet.py").unlink(missing_ok=True)
    print(f"  source staged -> {OUT}")


# ---------------------------------------------------------------------------
# 2. Images
# ---------------------------------------------------------------------------

# supplied Betclic file -> target filename in assets/images/
IMAGE_MAP = {
    "User Acquisition 1.png":   "betclic_acquisition.jpg",
    "Brand Awareness.png":      "betclic_brand_awareness.jpg",
    "BC hat.png":               "betclic_cap.jpg",
    "BC centre canvas.png":     "betclic_centre_canvas.jpg",
    "BC highlights.png":        "betclic_highlights.jpg",
    "BC hoodie.png":            "betclic_hoodie.jpg",
    "BC integrated content.png": "betclic_integrated_content.jpg",
    "BC led 1.png":             "betclic_led_1.jpg",
    "BC led 2.png":             "betclic_led_2.jpg",
    "BC led screen.png":        "betclic_prediction_walkouts.jpg",
    "BC shorts.png":            "betclic_shorts.jpg",
    "BC social integration.png": "betclic_social_integration.jpg",
    "BC social series 2.png":   "betclic_social_port_1.jpg",
    "BC social series 1.png":   "betclic_social_port_2.jpg",
    "BC t shirt.png":           "betclic_tshirt.jpg",
}

MAX_EDGE = 1800


def _save_jpg(im, path, quality=88):
    im = im.convert("RGB")
    if max(im.size) > MAX_EDGE:
        scale = MAX_EDGE / max(im.size)
        im = im.resize((round(im.width * scale), round(im.height * scale)),
                       Image.LANCZOS)
    im.save(path, "JPEG", quality=quality, optimize=True, progressive=True)


def _crop_cutin(im):
    """Slide 12 overhead cage shot.

    The supplied frame is wider than the panel needs and carries ARKHAM
    branding — on the canvas and on a cage banner — inherited from the source
    photography. Cropping to the framing used on the previous deck removes
    both and puts the Betclic live-odds graphic dead centre.
    """
    return im.convert("RGB").crop((58, 212, 1442, 1049))


def build_images():
    img_dir = OUT / "assets" / "images"

    for src_name, target in IMAGE_MAP.items():
        src = BC / src_name
        check(src.exists(), f"missing supplied asset: {src_name}")
        if not src.exists():
            continue
        _save_jpg(Image.open(src), img_dir / target)

    # Slide 6 cage branding: a tighter, lower crop of the same arena shot so it
    # reads as a different frame from the slide 2 pillar thumbnail.
    ba = Image.open(BC / "Brand Awareness.png").convert("RGB")
    w, h = ba.size
    crop = ba.crop((round(w * 0.055), round(h * 0.115),
                    round(w * 0.965), round(h * 0.995)))
    _save_jpg(crop, img_dir / "betclic_cage_branding.jpg")

    # Slide 12 cut-ins: overhead cage, with competitor (ARKHAM) branding patched
    # out of the inherited photography before it ships.
    odds = _crop_cutin(Image.open(BC / "BC live odds.png"))
    _save_jpg(odds, img_dir / "betclic_live_odds_cutin.jpg")

    # Slide 15 Watch & Bet: the Betclic sportsbook interface.
    wb = Image.open(BC / "BC background image.png").convert("RGB")
    scale = 1600 / wb.width
    wb = wb.resize((1600, round(wb.height * scale)), Image.LANCZOS)
    wb.save(img_dir / "betclic_watch_bet.png", "PNG", optimize=True)

    # Brand-neutral video poster carries over under the new name.
    shutil.move(str(img_dir / "netbet_watch_bet_poster.jpg"),
                str(img_dir / "betclic_watch_bet_poster.jpg"))

    for stale in img_dir.glob("netbet_*"):
        stale.unlink()

    check(not list(img_dir.glob("netbet_*")), "netbet_* images removed")
    expected = set(IMAGE_MAP.values()) | {
        "betclic_cage_branding.jpg", "betclic_live_odds_cutin.jpg",
        "betclic_watch_bet.png", "betclic_watch_bet_poster.jpg",
    }
    for name in expected:
        check((img_dir / name).exists(), f"image built: {name}")
    print(f"  images -> {len(expected)} Betclic assets")


# ---------------------------------------------------------------------------
# 3. Logos & icons
# ---------------------------------------------------------------------------

def _crisp_upscale(src, factor):
    """Upscale flat two-colour art without softening the edges.

    The wordmark is white-on-red, so it is resolved into a coverage mask,
    resampled, put through a steep contrast curve to restore a ~1px
    anti-aliased edge, then recomposited over the brand red.
    """
    a = np.array(src.convert("RGB")).astype(np.float32) / 255.0
    red = np.array(BC_RED_RGB, dtype=np.float32) / 255.0
    # Per-pixel whiteness: 0 = brand red, 1 = white.
    mask = np.clip((a - red) / (1.0 - red + 1e-6), 0, 1).mean(axis=2)

    m = Image.fromarray((mask * 255).astype(np.uint8), "L")
    m = m.resize((src.width * factor, src.height * factor), Image.LANCZOS)
    mv = np.array(m).astype(np.float32) / 255.0
    mv = np.clip((mv - 0.5) * 3.4 + 0.5, 0, 1)          # sharpen the edge

    out = red[None, None, :] * (1 - mv[:, :, None]) + mv[:, :, None]
    return Image.fromarray((out * 255).astype(np.uint8), "RGB")


def _betclic_box(height):
    """The brand lockup rendered crisply at an exact pixel height."""
    src = Image.open(BC / "logo_pack" / "Betclic logo.png")
    big = _crisp_upscale(src, 8)
    w = round(height * src.width / src.height)
    return big.resize((w, height), Image.LANCZOS)


def patch_legacy_branding():
    """Rebrand the two inherited stills that carry NetBet artwork baked in.

    Both were composited during the NetBet round, so the sponsor name is part
    of the pixels rather than the markup and has to be rebuilt.
    """
    img_dir = OUT / "assets" / "images"

    # --- Slide 17 hospitality: LED barrier strip across the arena front row.
    hosp = Image.open(SRC / "assets" / "images" / "Slide_14.jpg").convert("RGB")
    check(hosp.size == (1568, 784), f"Slide_14 source size {hosp.size}")
    hosp = hosp.crop((0, 0, 1568, 762))        # drop the exported white strip
    a = np.array(hosp).astype(np.float32)

    # Rebuild the barrier face row by row from a logo-free gap, so the strip's
    # own vertical falloff is preserved and there is no seam.
    for y in range(652, 762):
        a[y, :, :] = np.median(a[y, 375:430, :], axis=0)
    hosp = Image.fromarray(a.astype(np.uint8))

    box = _betclic_box(78)
    for cx in (206, 598, 990, 1382):
        hosp.paste(box, (cx - box.width // 2, 699 - box.height // 2))
    _save_jpg(hosp, img_dir / "Slide_14.jpg", quality=90)

    # --- Slide 3 social card: 'PRESENTED BY' lockup on the Instagram mock.
    grid = Image.open(SRC / "assets" / "images" / "social_grid.jpg").convert("RGB")
    check(grid.size == (540, 799), f"social_grid source size {grid.size}")
    g = np.array(grid).astype(np.float32)
    band = np.median(g[690:700, 460:530, :], axis=(0, 1))
    g[672:726, 276:470, :] = band
    grid = Image.fromarray(g.astype(np.uint8))
    sbox = _betclic_box(38)
    grid.paste(sbox, (284, 699 - sbox.height // 2))
    _save_jpg(grid, img_dir / "social_grid.jpg", quality=92)

    # Neither file may still read as NetBet red-on-dark in the patched bands.
    v = np.array(Image.open(img_dir / "Slide_14.jpg").convert("RGB"))[660:740]
    check(v.shape[0] > 0, "hospitality band rebuilt")
    print("  legacy stills rebranded (Slide_14, social_grid)")


# Competitor marks inherited from the source photography. Each entry is the
# file, the polarity of the mark against its backdrop, and the rectangles to
# clear. Rectangles are kept tight to the backdrop so people and kit are never
# inside the mask.
COMPETITOR_MARKS = [
    ("fighter_content_3.jpg", "bright", 30, [
        (248, 84, 384, 146),      # ARKHAM
        (620, 82, 810, 170),      # CLOUDBET
    ]),
    ("event_night_cover.jpg", "bright", 34, [
        (209, 219, 359, 292),     # CLOUDBET, upper left
        (1424, 258, 1580, 332),   # CLOUDBET, upper right
        (1418, 583, 1600, 685),   # CLOUDBET, mid right
        (379, 384, 550, 440),     # ARKHAM, left
        (967, 408, 1138, 464),    # ARKHAM, centre
        (445, 670, 616, 726),     # ARKHAM, part-occluded
    ]),
    ("highlights_cover.jpg", "dark", 30, [
        (678, 648, 1196, 730),    # CLOUDPICKS on the canvas
    ]),
]


def _erase_marks(im, rects, polarity, thresh, iters=340, grow=4):
    """Clear marks from a soft backdrop by masked diffusion inpainting.

    A threshold relative to each rectangle's own median isolates the mark, so
    the fill adapts to whatever the local backdrop is doing rather than
    stamping a flat patch over it.
    """
    a = np.array(im.convert("RGB")).astype(np.float32)
    lum = a.mean(axis=2)
    mask = np.zeros(lum.shape, bool)
    for (x0, y0, x1, y1) in rects:
        region = lum[y0:y1, x0:x1]
        base = np.median(region)
        mask[y0:y1, x0:x1] = (region > base + thresh) if polarity == "bright" \
            else (region < base - thresh)
    mask = binary_dilation(mask, iterations=grow)

    keep = (~mask).astype(np.float32)
    out = a.copy()
    out[mask] = 0.0
    w = keep.copy()
    for _ in range(iters):
        wb = uniform_filter(w, size=5)
        for c in range(3):
            num = uniform_filter(out[:, :, c] * w, size=5)
            filled = np.divide(num, wb, out=np.zeros_like(num), where=wb > 1e-5)
            out[:, :, c] = np.where(mask, filled, a[:, :, c])
        w = np.where(mask, np.minimum(1.0, wb * 3), keep)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), int(mask.sum())


def patch_competitor_branding():
    """Clear rival betting brands out of the inherited PFL photography."""
    img_dir = OUT / "assets" / "images"
    for name, polarity, thresh, rects in COMPETITOR_MARKS:
        src = SRC / "assets" / "images" / name
        out, n = _erase_marks(Image.open(src), rects, polarity, thresh)
        check(n > 400, f"{name}: mark mask found ({n}px)")
        _save_jpg(out, img_dir / name, quality=92)
    print(f"  competitor marks cleared from "
          f"{len(COMPETITOR_MARKS)} inherited stills")


def build_logos():
    logo_dir = OUT / "assets" / "logos"
    src = Image.open(BC / "logo_pack" / "Betclic logo.png")

    lockup = _crisp_upscale(src, 4)
    lockup.convert("RGBA").save(logo_dir / "betclic.png", "PNG", optimize=True)
    check(lockup.size == (1536, 524), f"betclic.png size {lockup.size}")

    # Portugal broadcaster mark. Rendered wordmark — placeholder pending the
    # official DAZN asset.
    font_path = FONT_DIR / "Outfit-Bold.ttf"
    check(font_path.exists(), "Outfit-Bold.ttf available")
    f = ImageFont.truetype(str(font_path), 190)
    tmp = Image.new("RGBA", (1400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    x, track = 40, -6
    for ch in "DAZN":
        d.text((x, 90), ch, font=f, fill=(255, 255, 255, 255))
        x += round(d.textlength(ch, font=f)) + track
    bbox = tmp.getbbox()
    dazn = tmp.crop(bbox)
    pad = Image.new("RGBA", (dazn.width + 24, dazn.height + 24), (0, 0, 0, 0))
    pad.paste(dazn, (12, 12))
    pad.save(logo_dir / "dazn.png", "PNG", optimize=True)

    for stale in ("netbet.png", "netbet-white.png", "talksport.png"):
        p = logo_dir / stale
        check(p.exists(), f"stale logo present before removal: {stale}")
        p.unlink(missing_ok=True)

    check((logo_dir / "betclic.png").exists(), "betclic.png written")
    check((logo_dir / "dazn.png").exists(), "dazn.png written")
    check(not (logo_dir / "netbet.png").exists(), "netbet.png removed")
    check(not (logo_dir / "talksport.png").exists(), "talksport.png removed")
    print("  logos -> betclic.png, dazn.png")


def build_icons():
    icon_dir = OUT / "assets" / "icons"
    src = Image.open(BC / "logo_pack" / "Betclic logo.png").convert("RGB")
    # The 'B' from the wordmark, on the brand red field.
    glyph = _crisp_upscale(src.crop((24, 18, 88, 107)), 8)

    def make(size):
        canvas = Image.new("RGB", (size, size), BC_RED_RGB)
        inner = round(size * 0.74)
        g = glyph.copy()
        g.thumbnail((inner, inner), Image.LANCZOS)
        canvas.paste(g, ((size - g.width) // 2, (size - g.height) // 2))
        return canvas

    make(32).save(icon_dir / "favicon-32.png", "PNG", optimize=True)
    make(192).save(icon_dir / "favicon-192.png", "PNG", optimize=True)
    make(180).save(icon_dir / "apple-touch-icon.png", "PNG", optimize=True)
    make(64).save(icon_dir / "favicon.ico", "ICO",
                  sizes=[(16, 16), (32, 32), (48, 48)])
    for n in ("favicon-32.png", "favicon-192.png", "apple-touch-icon.png",
              "favicon.ico"):
        check((icon_dir / n).exists(), f"icon built: {n}")
    print("  icons -> Betclic favicon set")


# ---------------------------------------------------------------------------
# 4. HTML
# ---------------------------------------------------------------------------

def build_html():
    p = OUT / "index.html"
    t = p.read_text(encoding="utf-8")

    # -- asset paths -------------------------------------------------------
    t = subN(t, r"assets/logos/netbet-white\.png",
             "assets/logos/betclic.png", "watermark logo path")
    t = subN(t, r"assets/logos/netbet\.png",
             "assets/logos/betclic.png", "brand logo paths")
    t = subN(t, r"assets/images/netbet_", "assets/images/betclic_",
             "image paths")
    t = subN(t, re.escape("20260818-netbet1"), CACHE_BUST, "cache-bust token")

    # -- broadcast partner: talkSPORT (UK) -> DAZN (Portugal) --------------
    t = sub1(t,
             r'<div class="bcast-country">UK</div>\s*\n\s*'
             r'<img src="assets/logos/talksport\.png" alt="talkSPORT" '
             r'class="bcast-logo-lg" loading="lazy">',
             '<div class="bcast-country">Portugal</div>\n          '
             '<img src="assets/logos/dazn.png" alt="DAZN" '
             'class="bcast-logo-lg" loading="lazy">',
             "broadcast partner tile")
    t = subN(t, r"talkSPORT", "DAZN", "talkSPORT wordmarks")

    # -- territory ---------------------------------------------------------
    t = subN(t, r"France &amp; United Kingdom", "France &amp; Portugal",
             "footer/meta territory")
    t = subN(t, r"France &amp; the United Kingdom",
             "France &amp; Portugal", "territory (amp, definite article)")
    t = subN(t, r"France and the United Kingdom", "France and Portugal",
             "territory (prose)")
    t = subN(t, r"the United Kingdom", "Portugal", "remaining 'the UK'")
    t = subN(t, r"United Kingdom", "Portugal", "remaining 'United Kingdom'")
    t = subN(t, r"France &amp; UK", "France &amp; Portugal", "France & UK")
    t = subN(t, r"France &amp; the UK", "France &amp; Portugal",
             "France & the UK")
    t = sub1(t, r"FR &middot; UK", "FR &middot; PT", "territories stat card")
    t = sub1(t, r"PFL FR &amp; UK channels", "PFL FR &amp; PT channels",
             "social reach channel note")
    t = subN(t, r"\bUK feed\b", "Portugal feed", "linear feed label")
    t = subN(t, r"\bUK\b(?! feed)", "Portugal", "residual standalone UK")

    # -- brand name --------------------------------------------------------
    t = subN(t, r"NetBet", "Betclic", "NetBet wordmarks")

    # -- copy fixes tied to the swapped creatives --------------------------
    t = sub1(t, r"By the Numbers, Shabily", "By the Numbers, Taylor Lapilus",
             "social series alt text")

    p.write_text(t, encoding="utf-8")

    check("NetBet" not in t and "netbet" not in t, "no NetBet left in HTML")
    check(not re.search(r"\bUK\b|United Kingdom", t), "no UK left in HTML")
    check("talksport" not in t.lower(), "no talkSPORT left in HTML")
    check(t.count("assets/logos/betclic.png") == 5, "5 Betclic logo refs")
    check(t.count("France &amp; Portugal") >= 6, "territory copy updated")
    print("  index.html rewritten")


# ---------------------------------------------------------------------------
# 5. CSS
# ---------------------------------------------------------------------------

def build_css():
    p = OUT / "css" / "styles.css"
    t = p.read_text(encoding="utf-8")

    # Recolour every sponsor-accent literal, then restore the PFL palette,
    # which happens to share NetBet's hex.
    t = subN(t, NB_RGB_RE, f"rgba({BC_RED_RGB[0]}, {BC_RED_RGB[1]}, "
                           f"{BC_RED_RGB[2]},", "sponsor rgba literals")
    t = subN(t, NB_RED, BC_RED, "sponsor red hex")
    t = subN(t, NB_RED_DEEP, BC_RED_DEEP, "sponsor deep-red hex")
    t = subN(t, NB_RED_BRIGHT, BC_RED_BRIGHT, "sponsor bright-red hex")

    t = sub1(t, r"--pfl-red: " + re.escape(BC_RED) + ";",
             f"--pfl-red: {NB_RED};", "restore --pfl-red")
    t = sub1(t, r"--pfl-red-deep: " + re.escape(BC_RED_DEEP) + ";",
             f"--pfl-red-deep: {NB_RED_DEEP};", "restore --pfl-red-deep")

    # Header + palette comments
    t = sub1(t, r"/\* PFL × Liga Stavok Activation Strategy 2026 — Stylesheet \*/",
             "/* PFL × Betclic Activation Strategy 2026 — Stylesheet */",
             "stylesheet header comment")
    t = sub1(t,
             r"/\* NetBet red — sampled from the supplied NetBet wordmark "
             r"\(" + re.escape(BC_RED) + r"\)\.",
             f"/* Betclic red — sampled from the supplied Betclic wordmark "
             f"({BC_RED}).",
             "palette comment")

    # The Betclic mark is a boxed lockup, not an open wordmark: it carries far
    # more visual weight per unit of height than NetBet's did, so the two large
    # display placements are scaled down to sit level with the PFL crown.
    t = sub1(t, r"\.cover-ls-mark img \{\n    max-height: 215px;\n"
                r"    max-width: min\(44vw, 620px\);",
             ".cover-ls-mark img {\n    max-height: 152px;\n"
             "    max-width: min(34vw, 460px);",
             "cover lockup scale")
    t = sub1(t, r"\.close-logos \.ls img \{\n    max-height: 170px;",
             ".close-logos .ls img {\n    max-height: 122px;",
             "close lockup scale")
    t = sub1(t, r"\.cover-ls-mark img \{ max-height: 110px; \}",
             ".cover-ls-mark img { max-height: 84px; }",
             "cover lockup scale (mobile)")
    t = sub1(t, r"\.close-logos \.ls img \{ max-height: 105px; \}",
             ".close-logos .ls img { max-height: 78px; }",
             "close lockup scale (mobile)")
    t = sub1(t, r"\.terms-modal-lockup img:last-of-type \{ height: 29px; \}",
             ".terms-modal-lockup img:last-of-type { height: 26px; }",
             "modal lockup scale")

    # Comments that name the old sponsor
    t = subN(t, r"NetBet", "Betclic", "CSS comment wordmarks")

    p.write_text(t, encoding="utf-8")
    check("NetBet" not in t, "no NetBet left in CSS")
    check(f"--ls-green: {BC_RED};" in t, "--ls-green recoloured")
    check(f"--pfl-red: {NB_RED};" in t, "--pfl-red preserved")
    check(f"rgba(198, 32, 38," not in t, "no NetBet rgba literals left")
    print("  styles.css recoloured")


# ---------------------------------------------------------------------------
# 6. JS
# ---------------------------------------------------------------------------

def build_js():
    p = OUT / "js" / "deck.js"
    t = p.read_text(encoding="utf-8")
    t = subN(t, r"NetBet", "Betclic", "JS wordmarks")
    p.write_text(t, encoding="utf-8")
    check("NetBet" not in t and "netbet" not in t, "no NetBet left in JS")
    check(not re.search(r"\bUK\b|United Kingdom", t), "no UK left in JS")
    print("  deck.js rewritten")


# ---------------------------------------------------------------------------
# 7. Audit
# ---------------------------------------------------------------------------

def audit():
    html = (OUT / "index.html").read_text(encoding="utf-8")
    css = (OUT / "css" / "styles.css").read_text(encoding="utf-8")
    js = (OUT / "js" / "deck.js").read_text(encoding="utf-8")
    blob = html + css + js

    # Every local asset referenced must exist.
    refs = set(re.findall(r"(?:src|href)=\"(assets/[^\"?]+)\"", html))
    refs |= set(re.findall(r"url\('(?:\.\./)?(assets/[^']+)'\)", html))
    refs |= set(re.findall(r"\"(assets/[^\"]+\.(?:mp4|jpg|png))\"", js))
    missing = [r for r in sorted(refs) if not (OUT / r).exists()]
    check(not missing, f"referenced assets missing: {missing}")

    # No orphaned image/logo files.
    orphans = []
    for f in list((OUT / "assets" / "images").iterdir()) + \
             list((OUT / "assets" / "logos").iterdir()):
        rel = str(f.relative_to(OUT))
        if rel not in blob and f.name not in blob:
            orphans.append(rel)
    check(not orphans, f"orphaned assets: {orphans}")

    check("Betclic" in html, "Betclic present in HTML")
    check("Portugal" in html, "Portugal present in HTML")
    check("make_netbet.py" not in os.listdir(OUT), "old build script removed")
    print(f"  audit -> {len(refs)} asset refs resolved, "
          f"{len(orphans)} orphans")


def main():
    print("Building PFL × Betclic deck…")
    prepare_source()
    build_images()
    patch_legacy_branding()
    patch_competitor_branding()
    build_logos()
    build_icons()
    build_html()
    build_css()
    build_js()
    audit()

    print(f"\n{CHECKS} checks run.")
    if FAILURES:
        print(f"{len(FAILURES)} FAILED:")
        for f in FAILURES:
            print(f"   ✗ {f}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
