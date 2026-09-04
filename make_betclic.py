#!/usr/bin/env python3
"""
make_betclic.py — deterministic PFL x Betclic deck build.

Rebuilds from a pristine NetBet-Activation GitHub checkout in a single verified
pass. No stateful edits: run it twice, get byte-identical output.

Usage:  python3 make_betclic.py
"""

import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import cairosvg
import numpy as np

from pp_slide import PP_CSS, PP_JS, PP_MODALS, PP_SLIDE
from PIL import Image
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

DAZN_SVG = ROOT / "dazn_pack" / "DAZN logo.svg"
SPORTKLUB_SRC = ROOT / "sportklub_src.png"

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


# Presenting Partner "in situ" examples. Each entry: source file, output stem,
# the caption shown in the modal, and which card it belongs to.
PP_EXAMPLES = [
    ("naming",    "GovX_Key_Art.png",             "pp_key_art",            "Key Art"),
    ("naming",    "GovX_Event_Naming.png",        "pp_event_naming",       "Event Naming"),
    ("broadcast", "GovX_Show_Presenter_1.mov",    "pp_show_presenter_1",   "Show Presenter 1"),
    ("broadcast", "GovX_Show_Presenter_2.mov",    "pp_show_presenter_2",   "Show Presenter 2"),
    ("broadcast", "Arkham_Tale_of_the_Tape.mov",  "pp_tale_of_the_tape",   "Tale of the Tape"),
    ("arena",     "Canvas.JPG",                   "pp_canvas",             "Canvas"),
    ("arena",     "External_LED_Bumper.JPG",      "pp_external_led_bumper","External LED Bumper"),
    ("arena",     "LED_Screens.JPG",              "pp_led_screens",        "LED Screens"),
    ("social",    "Main_Event_Presenter.png",     "pp_main_event_presenter","Main Event Presenter"),
    ("social",    "Fighter_Presenter.png",        "pp_fighter_presenter",  "Fighter Presenter"),
]

PP_UPLOADS = ROOT / "pp_uploads"


def build_pp_examples():
    """Prepare the in-situ example media for the Presenting Partner modals.

    The arena shots arrive as 6000x4000 camera files (~8MB each), so they are
    resized and re-encoded; at modal size nothing above ~1600px is visible.
    The .mov clips are remuxed to web-friendly mp4 with a poster frame each.
    """
    img_dir = OUT / "assets" / "images"
    vid_dir = OUT / "assets" / "video"

    for _, src_name, stem, _ in PP_EXAMPLES:
        src = PP_UPLOADS / src_name
        check(src.exists(), f"example asset present: {src_name}")
        if not src.exists():
            continue

        if src.suffix.lower() == ".mov":
            out = vid_dir / f"{stem}.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                 "-c:v", "libx264", "-preset", "slow", "-crf", "26",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                 "-an", str(out)],
                check=True)
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                 "-frames:v", "1", "-q:v", "4",
                 str(img_dir / f"{stem}_poster.jpg")],
                check=True)
            check(out.exists() and out.stat().st_size < 3_000_000,
                  f"{stem}.mp4 encoded and under 3MB")
        else:
            im = Image.open(src).convert("RGB")
            if max(im.size) > 1600:
                s = 1600 / max(im.size)
                im = im.resize((round(im.width * s), round(im.height * s)),
                               Image.LANCZOS)
            out = img_dir / f"{stem}.jpg"
            im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
            check(out.stat().st_size < 700_000,
                  f"{stem}.jpg under 700KB ({out.stat().st_size // 1024}KB)")

    print(f"  presenting-partner examples -> {len(PP_EXAMPLES)} assets")


def build_logos():
    logo_dir = OUT / "assets" / "logos"
    src = Image.open(BC / "logo_pack" / "Betclic logo.png")

    lockup = _crisp_upscale(src, 4)
    lockup.convert("RGBA").save(logo_dir / "betclic.png", "PNG", optimize=True)
    check(lockup.size == (1536, 524), f"betclic.png size {lockup.size}")

    # Portugal broadcaster mark, rendered from the supplied official SVG.
    # DAZN ships the mark in near-black (#0c0c1c); this deck places it on a
    # dark panel, so it is recoloured to the brand's reversed-out white.
    svg = (DAZN_SVG).read_text(encoding="utf-8")
    check("#0c0c1c" in svg, "DAZN SVG uses the expected brand fill")
    svg = svg.replace("#0c0c1c", "#ffffff")
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=720)
    dazn = Image.open(io.BytesIO(png)).convert("RGBA")
    dazn = dazn.crop(dazn.getbbox())
    dazn.save(logo_dir / "dazn.png", "PNG", optimize=True)
    check(dazn.size[0] > 400, f"dazn.png rendered at {dazn.size}")

    # Poland broadcaster mark. Supplied flat on white; the deck places it on a
    # dark panel, so the white is resolved into an alpha channel rather than
    # left as a card behind the logo.
    sk = Image.open(SPORTKLUB_SRC).convert("RGB")
    arr = np.array(sk).astype(np.float32)
    ink = np.array([172.0, 26.0, 27.0])
    # Each pixel is a blend of white and the brand red; recover the coverage.
    alpha = np.clip((255.0 - arr) / (255.0 - ink), 0, 1).max(axis=2)
    up = Image.fromarray((alpha * 255).astype(np.uint8), "L").resize(
        (sk.width * 2, sk.height * 2), Image.LANCZOS)
    av = np.clip((np.array(up).astype(np.float32) / 255 - 0.5) * 2.6 + 0.5, 0, 1)
    rgba = np.zeros((av.shape[0], av.shape[1], 4), np.uint8)
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2] = 172, 26, 27
    rgba[:, :, 3] = (av * 255).astype(np.uint8)
    sk_img = Image.fromarray(rgba, "RGBA")
    sk_img = sk_img.crop(sk_img.getbbox())
    sk_img.save(logo_dir / "sportklub.png", "PNG", optimize=True)
    check(sk_img.mode == "RGBA" and sk_img.getextrema()[3][0] == 0,
          "sportklub.png has a transparent background")

    for stale in ("netbet.png", "netbet-white.png", "talksport.png",
                  "youtube.png"):
        p = logo_dir / stale
        check(p.exists(), f"stale logo present before removal: {stale}")
        p.unlink(missing_ok=True)

    check((logo_dir / "betclic.png").exists(), "betclic.png written")
    check((logo_dir / "dazn.png").exists(), "dazn.png written")
    check((logo_dir / "sportklub.png").exists(), "sportklub.png written")
    check(not (logo_dir / "youtube.png").exists(), "youtube.png removed")
    check(not (logo_dir / "netbet.png").exists(), "netbet.png removed")
    check(not (logo_dir / "talksport.png").exists(), "talksport.png removed")
    print("  logos -> betclic.png, dazn.png, sportklub.png")


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
             'class="bcast-logo-lg bcast-logo-compact" loading="lazy">',
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




    # -- new Awareness slide: Presenting Partner asset stack ---------------
    # Inserted at the head of the Awareness run, so the umbrella status is
    # stated before the individual assets that sit under it. Everything from
    # the old slide 4 onward shifts by one; renumbering runs high-to-low so
    # the substitutions can't collide.
    total_before, total_after = 18, 19

    for n in range(total_before, 3, -1):
        t = sub1(t, r'<section class="slide([^"]*)" data-slide="%d">' % n,
                 r'<section class="slide\1" data-slide="%d">' % (n + 1),
                 f"reindex slide {n}")
        t = sub1(t, r'<div class="slide-num">%02d / %d</div>' % (n, total_before),
                 '<div class="slide-num">%02d / %d</div>' % (n + 1, total_after),
                 f"renumber slide-num {n}")

    # Slides 1-3 keep their index but the denominator moves.
    for n in (1, 2, 3):
        old = '<div class="slide-num">%02d / %d</div>' % (n, total_before)
        if old in t:
            t = sub1(t, re.escape(old),
                     '<div class="slide-num">%02d / %d</div>' % (n, total_after),
                     f"renumber slide-num {n}")
    t = sub1(t, r'<span class="cur" id="curSlide">01</span> / %d' % total_before,
             '<span class="cur" id="curSlide">01</span> / %d' % total_after,
             "slide counter total")

    t = t.replace(PP_SLIDE.replace("PLACEHOLDER", ""), "")  # no-op guard
    marker = '<section class="slide content-slide" data-slide="5">'
    check(marker in t, "insertion point located")
    t = sub1(t, re.escape(marker), lambda m: PP_SLIDE + marker,
             "insert Presenting Partner slide")

    modal_anchor = '<!-- === Presenting Partner example modals'
    check(modal_anchor not in t, "modals not already present")
    wb_anchor = '<div class="wb-video-modal" id="wristbandModal"'
    check(wb_anchor in t, "modal insertion point located")
    t = sub1(t, re.escape(wb_anchor), lambda m: PP_MODALS + wb_anchor,
             "insert Presenting Partner modals")

    # Section nav targets shift for every section after Awareness.
    for sec, old_target in ((3, 9), (4, 14), (5, 17), (6, 18)):
        t = sub1(t, r'data-section="%d" data-target="%d"' % (sec, old_target),
                 'data-section="%d" data-target="%d"' % (sec, old_target + 1),
                 f"nav target section {sec}")

    # -- Poland added as a 2027 market ------------------------------------
    # Slide 4: the third broadcast tile moves from a both-territories YouTube
    # stream to the Polish linear partner.
    t = sub1(t,
             r'<div class="bcast-country">France &amp; Portugal</div>\s*\n\s*'
             r'<img src="assets/logos/youtube\.png" alt="YouTube" '
             r'class="bcast-logo-lg" loading="lazy">',
             '<div class="bcast-country">Poland</div>\n          '
             '<img src="assets/logos/sportklub.png" alt="SportKlub" '
             'class="bcast-logo-lg bcast-logo-compact" loading="lazy">',
             "Poland broadcast tile")
    t = subN(t, r"RMC Sport, DAZN and YouTube", "RMC Sport, DAZN and SportKlub",
             "broadcast partner list")
    t = sub1(t, r'<div class="num">FR &middot; PT</div>',
             '<div class="num num-wide">FR &middot; PT &middot; PL</div>',
             "territories stat card")
    t = sub1(t, r'<div class="num">450k</div>', '<div class="num">500k</div>',
             "slide 4 unique viewers")
    t = sub1(t, r'<div class="dist-metric-num">450<span class="dist-metric-unit">k</span></div>',
             '<div class="dist-metric-num">500<span class="dist-metric-unit">k</span></div>',
             "modal unique viewers")

    # Broadcast modal: swap the streaming section for the Polish feed.
    t = sub1(t,
             r'<h3 class="terms-section-title">Streaming</h3>\s*\n\s*'
             r'<div class="dist-channel-grid">\s*\n\s*'
             r'<div class="dist-channel">\s*\n\s*'
             r'<div class="dist-channel-tag">Digital feed</div>\s*\n\s*'
             r'<h4>YouTube</h4>\s*\n\s*<ul>\s*\n'
             r'\s*<li>Live and on-demand PFL coverage carried across '
             r'<strong>YouTube</strong> in both territories</li>\s*\n'
             r'\s*<li>Same co-branded overlay and sponsor-graphic package as '
             r'the linear feeds</li>\s*\n'
             r'\s*<li>Geo-targeted to France and Portugal</li>',
             '<h3 class="terms-section-title">Poland '
             '<span class="dist-section-sub">new market from 2027</span></h3>\n'
             '        <div class="dist-channel-grid">\n'
             '          <div class="dist-channel">\n'
             '            <div class="dist-channel-tag">Linear feed &middot; from 2027</div>\n'
             '            <h4>SportKlub</h4>\n'
             '            <ul>\n'
             '              <li>Poland joins the Territory from '
             '<strong>1 January 2027</strong>, with all broadcast integrations '
             'delivered via the <strong>SportKlub Polish feed</strong></li>\n'
             '              <li>Same co-branded overlay and sponsor-graphic '
             'package as the France and Portugal feeds</li>\n'
             '              <li>Geo-targeted to Poland</li>',
             "Poland broadcast section")
    t = sub1(t,
             r'<div class="terms-print-meta">PFL × Betclic · 2026–2027 · '
             r'France &amp; Portugal</div>',
             '<div class="terms-print-meta">PFL × Betclic · 2026–2027 · '
             'France, Portugal &amp; Poland</div>',
             "broadcast modal print meta")
    t = sub1(t,
             r'<div>PFL × Betclic · Broadcast Distribution · Confidential</div>\s*\n'
             r'\s*<div>2026–2027 · France &amp; Portugal</div>',
             '<div>PFL × Betclic · Broadcast Distribution · Confidential</div>\n'
             '        <div>2026–2027 · France, Portugal &amp; Poland</div>',
             "broadcast modal footer")

    # Commercials modal: Poland is a 2027 market, not a 2026 one.
    t = sub1(t, r"<dt>Territories</dt>\s*\n\s*<dd>France and Portugal</dd>",
             "<dt>Territories</dt>\n          <dd>France and Portugal, "
             "with <strong>Poland added as a market from 1 January 2027</strong>"
             "\n            <ul>\n"
             "              <li><strong>2026:</strong> France and Portugal</li>\n"
             "              <li><strong>2027:</strong> France, Portugal and Poland</li>\n"
             "            </ul>\n          </dd>",
             "territories row")
    t = sub1(t,
             r"2026&ndash;2027 &mdash; &lsquo;Exclusive Betting Partner of PFL "
             r"in France &amp; Portugal&rsquo;;",
             "2026 &mdash; &lsquo;Exclusive Betting Partner of PFL in France "
             "&amp; Portugal&rsquo;; 2027 &mdash; &lsquo;Exclusive Betting "
             "Partner of PFL in France, Portugal &amp; Poland&rsquo;;",
             "official designations")
    t = sub1(t, r'<div class="terms-print-meta">2026–2027 · France &amp; Portugal</div>',
             '<div class="terms-print-meta">2026–2027 · France, Portugal '
             '&amp; Poland <span style="opacity:.7">(Poland from 2027)</span></div>',
             "commercials modal print meta")
    t = sub1(t,
             r'<div>PFL × Betclic · Heads of Terms · Confidential</div>\s*\n'
             r'\s*<div>2026–2027 · France &amp; Portugal</div>',
             '<div>PFL × Betclic · Heads of Terms · Confidential</div>\n'
             '        <div>2026–2027 · France, Portugal &amp; Poland</div>',
             "commercials modal footer")


    # -- commercial terms, per Jacques' 3 Sep amendments -------------------
    t = sub1(t,
             r"<li><strong>2027:</strong> A minimum of two \(2\) PFL Events "
             r"hosted within the Territory</li>",
             "<li><strong>2027:</strong> A minimum of one (1) PFL Event "
             "hosted within the Territory</li>",
             "2027 in-Territory baseline")
    t = sub1(t, r'<span class="terms-grid-sub">two events p\.a\.</span>',
             '<span class="terms-grid-sub">one event p.a.</span>',
             "guaranteed events sub-label")
    t = sub1(t,
             r"PFL guarantees a minimum of two \(2\) Events per calendar year "
             r"hosted within the Territory, comprising one \(1\) Event in France "
             r"and one \(1\) Event in Portugal\.",
             "PFL guarantees a minimum of one (1) Event per calendar year "
             "hosted within the Territory, in France.",
             "guaranteed territory events")
    t = sub1(t, r"<li>Three \(3\) VIP tickets</li>",
             "<li>Five (5) VIP tickets</li>", "VIP ticket allocation")

    # -- 2027 restructured: 1 in-Territory + 3 out-of-Territory European -----
    t = sub1(t,
             r"<li><strong>2027:</strong> A minimum of one \(1\) PFL Event "
             r"hosted within the Territory</li>",
             "<li><strong>2027:</strong> Four (4) Events in total &mdash; "
             "one (1) PFL Event hosted within the Territory, plus three (3) "
             "Europe-based Events hosted outside the Territory</li>",
             "2027 franchises & events")
    t = sub1(t, r"<li><strong>2027:</strong> &euro;300,000</li>",
             "<li><strong>2027:</strong> &euro;350,000 &mdash; inclusive of "
             "all four (4) Events and of virtual overlay branding at the "
             "three (3) out-of-Territory Events</li>",
             "2027 fee")
    t = sub1(t,
             r"<li>Virtual overlay branding at out-of-Territory events: "
             r"&euro;35,000 per event, per market</li>",
             "<li>Virtual overlay branding at any further out-of-Territory "
             "event &mdash; in 2026, or beyond the three (3) included in 2027 "
             "&mdash; &euro;35,000 per event, per market</li>",
             "virtual overlay pricing")

    t = sub1(t, r'<h3 class="terms-section-title">Guaranteed Territory Events '
                r'&amp; Status</h3>',
             '<h3 class="terms-section-title">Guaranteed Events '
             '&amp; Status</h3>', "guaranteed events section title")
    t = sub1(t,
             r'<dt>From Jan 1, 2027<span class="terms-grid-sub">one event p\.a\.'
             r'</span></dt>\s*\n\s*<dd>PFL guarantees a minimum of one \(1\) '
             r'Event per calendar year hosted within the Territory, in France\. '
             r'All guaranteed Territory Events shall include the rights and '
             r'deliverables set out under <em>Partnership Assets</em> below\.</dd>',
             '<dt>From Jan 1, 2027<span class="terms-grid-sub">four events p.a.'
             '</span></dt>\n'
             '          <dd>Four (4) Events per calendar year, all within the '
             'annual fee:\n'
             '            <ul>\n'
             '              <li><strong>One (1) in-Territory Event</strong>, '
             'hosted in France &mdash; Presenting Partner status and the full '
             'asset package set out under <em>Partnership Assets</em> below.</li>\n'
             '              <li><strong>Three (3) out-of-Territory Events</strong>, '
             'hosted elsewhere in Europe &mdash; virtual overlay branding, '
             'broadcast integrations, digital &amp; video content access and '
             'VIP hospitality. These Events are broadcast into the Betclic '
             'Territories, where <strong>Betclic will be the exclusive betting '
             'partner in the broadcast</strong>.</li>\n'
             '            </ul>\n'
             '            Social content distribution applies to the '
             'in-Territory Event only.\n          </dd>',
             "2027 guaranteed events")

    # Asset 02 — integrations now reach the out-of-Territory Events too.
    t = sub1(t,
             r"(<li>Betclic to receive access to custom broadcast opportunities "
             r"per event[^<]*</li>)",
             r"\1\n              <li>From 2027, broadcast integrations apply at "
             "all four (4) Events &mdash; the in-Territory Event and the three "
             "(3) Europe-based Events hosted outside the Territory</li>",
             "asset 02 out-of-territory reach")

    # Asset 05 — social is in-Territory only.
    t = sub1(t, r"<h4>Social Content Distribution</h4>",
             '<h4>Social Content Distribution '
             '<span class="terms-asset-sub">in-Territory Events only</span></h4>',
             "asset 05 heading")
    t = sub1(t, r"<li>A total of three \(3\) social media posts per event</li>",
             "<li>A total of three (3) social media posts per in-Territory "
             "Event</li>\n              <li>Social content distribution does "
             "not apply to out-of-Territory Events</li>",
             "asset 05 scope")

    # Asset 06 — overlay is bundled into the 2027 fee, not an add-on.
    t = sub1(t,
             r'<h4>Virtual Overlay Branding <span class="terms-asset-sub">'
             r'optional add-on &middot; out-of-Territory events</span></h4>',
             '<h4>Virtual Overlay Branding <span class="terms-asset-sub">'
             'included in 2027 &middot; out-of-Territory events</span></h4>',
             "asset 06 heading")
    t = sub1(t,
             r"<li><strong>Optional additional asset</strong>, available at "
             r"Events hosted outside the Territory and taken up at Betclic"
             r"&rsquo;s election</li>",
             "<li><strong>Included within the 2027 fee</strong> at the three "
             "(3) Europe-based Events hosted outside the Territory</li>",
             "asset 06 inclusion")
    t = sub1(t,
             r"<li><strong>Betclic will be the exclusive betting operator "
             r"featured on the canvas</strong></li>",
             "<li><strong>Betclic will be the exclusive betting operator "
             "featured on the canvas</strong>, and the exclusive betting "
             "partner in the broadcast of these Events into the Betclic "
             "Territories</li>",
             "asset 06 exclusivity")
    t = sub1(t, r"<li>Charged at &euro;35,000 per event, per market</li>",
             "<li>Further out-of-Territory events beyond the three (3) "
             "included: &euro;35,000 per event, per market</li>",
             "asset 06 pricing")

    # Asset 08 — content access follows the Events.
    t = sub1(t,
             r"(<li>All content may be used across Betclic-owned channels, "
             r"with specified rules</li>)",
             r"\1\n              <li>From 2027, content access applies at all "
             "four (4) Events, in and out of Territory</li>",
             "asset 08 scope")

    # Asset 11 — VIP access follows the Events.
    t = sub1(t,
             r"(<li>Five \(5\) GA tickets</li>)",
             r"\1\n              <li>From 2027, the per-event allocation "
             "applies at all four (4) Events, in and out of Territory</li>",
             "asset 11 scope")


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


    # The DAZN and SportKlub marks are compact where RMC Sport is wide, so at
    # a shared height they read noticeably smaller. They get their own size,
    # sitting flush to the tile. The
    # country label gets a floor so the wrapped 'France & Portugal' caption
    # doesn't push the third logo out of line with the other two.
    t = sub1(t, r"\.bcast-partner > img\.bcast-logo-lg \{\n"
                r"    padding: 4px 8px;\n\}",
             ".bcast-partner > img.bcast-logo-lg {\n"
             "    padding: 4px 8px;\n}\n"
             ".bcast-partner > img.bcast-logo-lg.bcast-logo-compact {\n"
             "    height: 100%;\n"
             "    width: auto;\n"
             "    padding: 0;\n}",
             "compact broadcast logo sizing")
    t = sub1(t, r"(\.bcast-country \{\n    font-family: var\(--font-cond\);\n)",
             r"\1    min-height: 29px;\n", "broadcast label height floor")

    t = sub1(t, r"(\.stat-card \.num \{\n    font-family: var\(--font-display\);\n)",
             r"\1    white-space: nowrap;\n", "stat number nowrap")
    t = sub1(t, r"(\.stat-card \.label \{\n)",
             ".stat-card .num.num-wide { font-size: 23px; letter-spacing: 0.01em; }\n"
             r"\1", "wide stat number size")


    # Slide 4 stat cards: the three numbers are set at different sizes, so
    # without a shared number band their baselines and the labels beneath them
    # all start at different heights. Fixing the band and pinning labels to the
    # card floor lines the row up whatever the copy length.
    t = sub1(t, r"\.stat-card \{\n"
                r"    background: rgba\(255,255,255,0\.03\);\n"
                r"    border: 1px solid rgba\(255,255,255,0\.08\);\n"
                r"    border-radius: 4px;\n"
                r"    padding: 16px 14px;\n\}",
             ".stat-card {\n"
             "    background: rgba(255,255,255,0.03);\n"
             "    border: 1px solid rgba(255,255,255,0.08);\n"
             "    border-radius: 4px;\n"
             "    padding: 16px 14px;\n"
             "    display: flex;\n"
             "    flex-direction: column;\n}",
             "stat card flex column")
    t = sub1(t, r"    color: var\(--pfl-red\);\n    line-height: 1;\n"
                r"    margin-bottom: 6px;\n\}",
             "    color: var(--pfl-red);\n"
             "    line-height: 1;\n"
             "    margin-bottom: 10px;\n"
             "    min-height: 30px;\n"
             "    display: flex;\n"
             "    align-items: flex-end;\n}",
             "stat number band")
    t = sub1(t, r"(\.stat-card \.label \{\n    font-family: var\(--font-cond\);\n)",
             r"\1    line-height: 1.5;\n",
             "stat label leading")
    t = sub1(t, r"(\.stat-card \.label \{[^}]*?)letter-spacing: 0\.16em;",
             r"\1letter-spacing: 0.10em;", "stat label tracking")
    t = sub1(t, r"(\.stat-card \.label \{[^}]*?)font-size: 11px;",
             r"\1font-size: 10px;", "stat label size")

    # Broadcast partner tiles: taller, tighter, so the marks themselves carry
    # more of the tile instead of the padding.
    t = sub1(t, r"(\.bcast-partner \{\n    display: flex;\n"
                r"    flex-direction: column;\n    align-items: center;\n"
                r"    justify-content: flex-start;\n)    gap: 12px;\n"
                r"    height: 108px;\n    padding: 12px;",
             r"\1    gap: 10px;\n    height: 132px;\n    padding: 12px 10px;",
             "broadcast tile size")
    t = sub1(t, r"\.bcast-partner > img\.bcast-logo-lg \{\n    padding: 4px 8px;\n\}",
             ".bcast-partner > img.bcast-logo-lg {\n"
             "    padding: 0;\n"
             "    max-width: 100%;\n}",
             "wide logo padding")

    t = t.rstrip() + "\n" + PP_CSS

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
    t = sub1(t, r"\{ idx: 2, slides: \[4, 5, 6, 7, 8\] \},",
             "{ idx: 2, slides: [4, 5, 6, 7, 8, 9] },", "section 2 range")
    t = sub1(t, r"\{ idx: 3, slides: \[9, 10, 11, 12, 13\] \},",
             "{ idx: 3, slides: [10, 11, 12, 13, 14] },", "section 3 range")
    t = sub1(t, r"\{ idx: 4, slides: \[14, 15, 16\] \},",
             "{ idx: 4, slides: [15, 16, 17] },", "section 4 range")
    t = sub1(t, r"\{ idx: 5, slides: \[17\] \},",
             "{ idx: 5, slides: [18] },", "section 5 range")
    t = sub1(t, r"\{ idx: 6, slides: \[18\] \}",
             "{ idx: 6, slides: [19] }", "section 6 range")
    t = sub1(t, r"\[data-slide=\"16\"\] \.wb-frame",
             '[data-slide="17"] .wb-frame', "watch & bet slide reference")
    t = sub1(t, r"(    const fgcModal = document\.getElementById\('fgcModal'\);\n)",
             r"\1    const ppModals = document.querySelectorAll('.pp-modal');\n",
             "pp modal handle in key guard")
    t = sub1(t, r"(    for \(const m of distModals\) \{\n"
                r"      if \(m\.classList\.contains\('is-open'\)\) return;\n"
                r"    \}\n)",
             r"\1    for (const m of ppModals) {\n"
             "      if (m.classList.contains('is-open')) return;\n    }\n",
             "pp modal guard clause")
    t = t.rstrip()
    check(t.endswith("})();"), "deck.js IIFE terminator found")
    t = t[:-len("})();")] + PP_JS + "})();\n"
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

    check("&euro;350,000" in html, "year 2 at EUR350k")
    check("&euro;200,000" not in html, "old year 2 fee gone")
    check(html.count("out-of-Territory") >= 7, "out-of-Territory copy")
    check("youtube.png" not in html, "YouTube logo dereferenced")
    check(html.count("Poland") >= 8, "Poland copy present")
    check("450" not in html, "viewer figure updated everywhere")
    check("Three (3) VIP" not in html, "VIP allocation updated")
    check("Event in Portugal" not in html, "PT in-territory event removed")
    check(html.count("data-slide=") == 19, "19 slides present")
    check("/ 18</div>" not in html, "no stale 18-slide numbering")
    check(html.count('class="pp-card') == 6, "6 presenting-partner cards")
    check(html.count("data-open-pp=") == 4, "4 clickable cards")
    check(html.count('class="pp-modal"') == 4, "4 example modals")
    check(html.count("pp-cell") == 10, "10 in-situ examples")
    check("Ticketing &amp; Promotion" in html.replace("<br>", " "),
          "card 6 renamed")
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
    build_pp_examples()
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
