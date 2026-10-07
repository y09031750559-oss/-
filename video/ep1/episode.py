"""Episode 1 — "never answer the voice in the woods": timeline, scene art and frame renderer.

python3 episode.py frames START END OUT.mp4   # render video frames [START, END) seconds (no audio)
python3 episode.py info                       # print timeline
"""
import math, os, random, re, subprocess, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 24
PX, PY = 360, 60  # extra canvas for parallax pan / shake
CW, CH = W + PX, H + PY

SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
SERIF_R = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
RED = (178, 26, 26)
BONE = (226, 222, 212)

# ---------------------------------------------------------------- timeline ---

def load_srt(path="dl/voice.srt"):
    ts = lambda s: sum(float(x) * m for x, m in zip(s.replace(",", ".").split(":"), (3600, 60, 1)))
    subs = []
    for block in open(path, encoding="utf-8").read().strip().split("\n\n"):
        l = block.splitlines()
        a, b = l[1].split(" --> ")
        subs.append((ts(a), ts(b), " ".join(l[2:])))
    return subs


SUBS = load_srt()


def at(phrase, end=False):
    """Voice time where the subtitle starting with `phrase` begins (or ends)."""
    for s in SUBS:
        if s[2].startswith(phrase):
            return s[1] if end else s[0]
    raise KeyError(phrase)


def gap_before(phrase):
    """Middle of the silence before `phrase` — a safe place to cut the voice."""
    i = next(k for k, s in enumerate(SUBS) if s[2].startswith(phrase))
    return (SUBS[i - 1][1] + SUBS[i][0]) / 2


LEAD, TAIL = 0.6, 7.0
TITLE_GAP, CHAPTER_GAP = 7.0, 3.2
# (cut point in voice time, inserted silence, chapter card or None)
INSERTS = [
    (gap_before("There is an old rule"), TITLE_GAP, "TITLE"),
    (gap_before("This account was shared"), CHAPTER_GAP, ("PART I", "THE QUIET FOREST")),
    (gap_before("On the second evening"), CHAPTER_GAP, ("PART II", "THE FIRST CALL")),
    (gap_before("They did not go to look"), CHAPTER_GAP, ("PART III", "2 A.M.")),
    (gap_before("At first light"), CHAPTER_GAP, ("PART IV", "FIRST LIGHT")),
    (gap_before("At the trailhead"), CHAPTER_GAP, ("PART V", "THE RANGER")),
    (gap_before("Daniel and Claire never"), CHAPTER_GAP, ("PART VI", "LAST SPRING")),
]
VOICE_END = SUBS[-1][1]


def T(v):
    """Voice time -> video time."""
    return LEAD + v + sum(g for c, g, _ in INSERTS if c <= v)


def TP(phrase, end=False):
    return T(at(phrase, end))


TOTAL = T(VOICE_END) + TAIL

# -------------------------------------------------------------- primitives ---

def font(path, size):
    return ImageFont.truetype(path, size)


def grad(top, bottom, w=CW, h=CH, curve=1.0):
    y = (np.linspace(0, 1, h) ** curve)[:, None, None]
    a = np.array(top, np.float32)[None, None] * (1 - y) + np.array(bottom, np.float32)[None, None] * y
    return Image.fromarray(np.repeat(a, w, axis=1).clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")


def layer():
    return Image.new("RGBA", (CW, CH), (0, 0, 0, 0))


def conifer(d, x, base, h, w, col, rnd):
    """Pacific-Northwest fir: trunk + jagged stacked tiers."""
    d.line([(x, base), (x, base - h)], fill=col, width=max(2, int(w * 0.06)))
    tiers = rnd.randint(7, 11)
    for k in range(tiers):
        f = k / tiers
        ty = base - h * (0.12 + 0.88 * f)
        tw = w * (1 - f) * rnd.uniform(0.75, 1.1) + w * 0.06
        th = h / tiers * 1.9
        pts = [(x, ty - th)]
        for s in (1, -1):
            pass
        pts = [(x - tw / 2, ty + rnd.uniform(-6, 6)), (x, ty - th),
               (x + tw / 2, ty + rnd.uniform(-6, 6)), (x + tw * 0.2, ty - th * 0.15), (x - tw * 0.2, ty - th * 0.12)]
        d.polygon(pts, fill=col)


def treeline(seed, base, hmin, hmax, n, col, x0=-60, x1=CW + 60, wscale=0.32, blur=0, jitter=40):
    rnd = random.Random(seed)
    L = layer()
    d = ImageDraw.Draw(L)
    for k in range(n):
        x = x0 + (x1 - x0) * (k + rnd.random() * 0.8) / n
        h = rnd.uniform(hmin, hmax)
        conifer(d, x, base + rnd.uniform(0, jitter), h, h * wscale, col, rnd)
    d.rectangle([0, base + jitter * 0.5, CW, CH], fill=col)
    return L.filter(ImageFilter.GaussianBlur(blur)) if blur else L


def trunks(seed, n, col, wmin, wmax, blur=0, branches=True):
    rnd = random.Random(seed)
    L = layer()
    d = ImageDraw.Draw(L)
    for _ in range(n):
        x = rnd.uniform(-60, CW + 60)
        w = rnd.uniform(wmin, wmax)
        lean = rnd.uniform(-18, 18)
        d.polygon([(x, -10), (x + w, -10), (x + w * 1.25 + lean, CH), (x - w * 0.25 + lean, CH)], fill=col)
        if branches:
            for _ in range(rnd.randint(1, 4)):
                by = rnd.uniform(0, CH * 0.55)
                bl = rnd.uniform(60, 240) * rnd.choice([-1, 1])
                d.line([(x + w / 2, by), (x + w / 2 + bl, by - abs(bl) * rnd.uniform(.2, .6))],
                       fill=col, width=max(2, int(w / 7)))
    return L.filter(ImageFilter.GaussianBlur(blur)) if blur else L


def glow(L, cx, cy, r, color, strength=1.0):
    g = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(g).ellipse([cx - r, cy - r, cx + r, cy + r], fill=int(255 * strength))
    g = g.filter(ImageFilter.GaussianBlur(r * 0.45))
    col = Image.new("RGBA", (CW, CH), color + (255,))
    col.putalpha(g)
    L.alpha_composite(col)


def person(d, x, base, h, col, kneel=False, tall=1.0, arms=False):
    """Simple human silhouette, feet at (x, base)."""
    h *= tall
    hr = h * 0.075
    if kneel:
        d.ellipse([x - hr, base - h * 0.62 - hr * 2, x + hr, base - h * 0.62], fill=col)
        d.polygon([(x - h * .1, base - h * .6), (x + h * .1, base - h * .6), (x + h * .14, base - h * .25),
                   (x + h * .32, base - h * .22), (x + h * .32, base), (x - h * .12, base)], fill=col)
        return
    d.ellipse([x - hr, base - h, x + hr, base - h + hr * 2], fill=col)
    d.polygon([(x - h * .11, base - h * .84), (x + h * .11, base - h * .84), (x + h * .09, base - h * .45),
               (x + h * .07, base), (x + h * .02, base), (x, base - h * .4), (x - h * .02, base),
               (x - h * .07, base), (x - h * .09, base - h * .45)], fill=col)
    if arms:
        d.line([(x - h * .1, base - h * .8), (x - h * .14, base - h * .4)], fill=col, width=max(3, int(h * .04)))
        d.line([(x + h * .1, base - h * .8), (x + h * .14, base - h * .4)], fill=col, width=max(3, int(h * .04)))


def mimic_figure(d, x, base, h, col):
    """Too-tall, too-thin figure: long limbs, no clear features."""
    hr = h * 0.045
    d.ellipse([x - hr, base - h, x + hr, base - h + hr * 2.6], fill=col)
    d.polygon([(x - h * .05, base - h * .9), (x + h * .05, base - h * .9), (x + h * .035, base - h * .45),
               (x + h * .03, base), (x + h * .012, base), (x, base - h * .42), (x - h * .012, base),
               (x - h * .03, base), (x - h * .035, base - h * .45)], fill=col)
    for s in (-1, 1):
        d.line([(x + s * h * .045, base - h * .86), (x + s * h * .07, base - h * .42), (x + s * h * .06, base - h * .3)],
               fill=col, width=max(2, int(h * .018)))


def moon(L, cx, cy, r, alpha=1.0):
    glow(L, cx, cy, r * 3.2, (150, 165, 180), 0.35 * alpha)
    d = ImageDraw.Draw(L)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(205, 210, 205, int(255 * alpha)))


def stars(L, seed, n, ymax):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(L)
    for _ in range(n):
        x, y = rnd.uniform(0, CW), rnd.uniform(0, ymax)
        v = rnd.randint(90, 200)
        d.point((x, y), fill=(v, v, v + 10, 255))

# ------------------------------------------------------------ scene art ---
# Each builder returns a list of (RGBA image, parallax px/s) from back to front.

def sc_dusk_ridge(figures=True, darker=0.0, watcher=False):
    k = 1 - darker
    sky = grad((int(38 * k), int(36 * k), int(52 * k)), (int(150 * k), int(78 * k), int(48 * k)), curve=1.4)
    stars(sky, 3, 120, 300)
    far = treeline(11, 640, 140, 260, 70, (int(40 * k), int(34 * k), int(44 * k)), blur=3)
    mid = treeline(12, 760, 260, 470, 34, (int(18 * k), int(16 * k), int(22 * k)), blur=1)
    ridge = layer()
    d = ImageDraw.Draw(ridge)
    rc = (6, 6, 8, 255)
    d.polygon([(0, 905), (500, 860), (1100, 835), (1650, 870), (CW, 880), (CW, CH), (0, CH)], fill=rc)
    if figures:
        glow(ridge, 1180, 860, 120, (255, 140, 50), 0.75)
        d = ImageDraw.Draw(ridge)
        person(d, 1180, 850, 190, rc, kneel=True)
        person(d, 1430, 868, 250, rc)
        d.rectangle([1215, 838, 1250, 852], fill=rc)  # stove
    out = [(sky, 2), (far, 6), (mid, 12)]
    if watcher:
        w = layer()
        mimic_figure(ImageDraw.Draw(w), 560, 805, 330, (70, 64, 66, 120))
        out.append((w.filter(ImageFilter.GaussianBlur(2.5)), 12))
    out.append((ridge, 20))
    return out


def sc_deep_woods(seed=0, tint=(14, 20, 24), figure=0):
    bg = grad((tint[0] + 16, tint[1] + 20, tint[2] + 24), tint)
    a = trunks(seed + 1, 40, (40, 48, 52, 255), 6, 18, blur=6)
    glow(a, CW * .5, CH * .55, 600, (90, 100, 104), 0.25)
    b = trunks(seed + 2, 20, (18, 22, 25, 255), 16, 36, blur=2)
    c = trunks(seed + 3, 8, (4, 5, 6, 255), 40, 90)
    out = [(bg, 0), (a, 8), (b, 18)]
    if figure:
        f = layer()
        mimic_figure(ImageDraw.Draw(f), CW * 0.47, CH * 0.86, 520, (120, 118, 112, int(70 * figure)))
        out.append((f.filter(ImageFilter.GaussianBlur(4)), 18))
    out.append((c, 34))
    return out


def sc_cedars():
    bg = grad((92, 104, 104), (40, 50, 46))
    a = trunks(21, 26, (70, 80, 76, 255), 30, 60, blur=8, branches=False)
    b = trunks(22, 12, (38, 44, 38, 255), 60, 110, blur=3, branches=False)
    river = layer()
    d = ImageDraw.Draw(river)
    d.polygon([(0, 930), (CW, 900), (CW, CH), (0, CH)], fill=(26, 34, 36, 255))
    rnd = random.Random(5)
    for _ in range(140):  # glints on the water
        x, y = rnd.uniform(0, CW), rnd.uniform(930, CH)
        d.line([(x, y), (x + rnd.uniform(20, 70), y)], fill=(120, 140, 140, rnd.randint(40, 120)), width=2)
    c = trunks(23, 4, (14, 16, 14, 255), 120, 200, branches=False)
    return [(bg, 0), (a, 6), (b, 14), (river, 22), (c, 32)]


def sc_tent(night=True):
    sky = grad((8, 10, 18), (22, 26, 34))
    stars(sky, 7, 400, 600)
    moon(sky, 1520, 190, 46, 0.9)
    far = treeline(31, 620, 200, 360, 50, (12, 14, 20, 255), blur=2)
    near = treeline(32, 760, 380, 620, 14, (5, 6, 9, 255))
    ground = layer()
    d = ImageDraw.Draw(ground)
    d.polygon([(0, 900), (CW, 870), (CW, CH), (0, CH)], fill=(10, 11, 14, 255))
    tent = layer()
    td = ImageDraw.Draw(tent)
    tx, ty = CW // 2 - 40, 930
    td.polygon([(tx - 330, ty), (tx, ty - 330), (tx + 330, ty)], fill=(58, 66, 62, 255))  # fly
    td.polygon([(tx - 330, ty), (tx, ty - 330), (tx - 60, ty)], fill=(46, 52, 50, 255))
    td.line([(tx, ty - 330), (tx, ty)], fill=(30, 34, 33, 255), width=4)
    glow(tent, tx, ty - 120, 160, (120, 110, 80), 0.18)
    return [(sky, 1), (far, 4), (near, 8), (ground, 10), (tent, 10)]


TENT_X, TENT_Y = CW // 2 - 40, 930


def sc_frost():
    """Top-down frosty ground. Footprints are animated in extras."""
    rnd = np.random.default_rng(4)
    base = rnd.normal(150, 22, (CH // 4, CW // 4)).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(base).resize((CW, CH), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.5))
    arr = np.asarray(img, np.float32)[..., None] * np.array([0.78, 0.86, 0.95])[None, None]
    speck = (rnd.random((CH, CW)) > 0.996)[..., None] * 90
    arr = (arr + speck).clip(0, 255)
    g = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(g)
    for _ in range(60):  # grass blades & pebbles
        x, y = rnd.uniform(0, CW), rnd.uniform(0, CH)
        d.ellipse([x, y, x + rnd.uniform(6, 22), y + rnd.uniform(4, 14)], fill=(70, 74, 78, 255))
    return [(g, 3)]


def sc_fog_trail():
    bg = grad((120, 126, 128), (64, 70, 72))
    a = treeline(41, 700, 300, 520, 26, (100, 106, 108, 255), blur=10)
    b = treeline(42, 820, 420, 700, 14, (62, 68, 70, 255), blur=4)
    c = layer()
    d = ImageDraw.Draw(c)
    d.polygon([(700, CH), (1000, 840), (1180, 840), (1500, CH)], fill=(46, 48, 48, 255))  # trail
    e = treeline(43, 980, 700, 1000, 5, (14, 16, 16, 255), x0=-100, x1=CW + 100)
    return [(bg, 0), (a, 5), (b, 12), (c, 18), (e, 30)]


def sc_trailhead():
    sky = grad((70, 78, 90), (150, 140, 132))
    a = treeline(51, 620, 200, 380, 40, (70, 76, 84, 255), blur=6)
    b = treeline(52, 700, 300, 520, 18, (34, 38, 42, 255), blur=2)
    lot = layer()
    d = ImageDraw.Draw(lot)
    d.rectangle([0, 860, CW, CH], fill=(30, 32, 34, 255))
    col = (12, 13, 15, 255)
    x, y = 820, 900  # pickup truck
    d.rounded_rectangle([x, y - 120, x + 520, y - 30], 18, fill=col)
    d.polygon([(x + 40, y - 120), (x + 90, y - 200), (x + 250, y - 200), (x + 280, y - 120)], fill=col)
    d.rectangle([x + 110, y - 190, x + 240, y - 130], fill=(60, 66, 72, 255))  # window
    for wx in (x + 100, x + 420):
        d.ellipse([wx - 48, y - 78, wx + 48, y + 18], fill=(4, 4, 5, 255))
    d.rectangle([x + 120, y - 212, x + 220, y - 200], fill=(150, 90, 20, 255))  # light bar
    glow(lot, x + 170, y - 206, 90, (255, 150, 40), 0.35)
    d = ImageDraw.Draw(lot)
    person(d, 1480, 905, 260, col)
    d.polygon([(1440, 905 - 252), (1520, 905 - 252), (1500, 905 - 270), (1460, 905 - 270)], fill=col)  # hat
    return [(sky, 1), (a, 5), (b, 10), (lot, 16)]


def sc_house(door_close=0.0):
    sky = grad((10, 12, 22), (28, 30, 40))
    stars(sky, 9, 160, 400)
    trees = treeline(61, 640, 260, 480, 40, (8, 9, 13, 255), blur=1)
    yard = layer()
    d = ImageDraw.Draw(yard)
    d.rectangle([0, 720, CW, CH], fill=(16, 20, 18, 255))
    for fx in range(-20, CW + 40, 46):  # fence
        d.rectangle([fx, 610, fx + 34, 735], fill=(20, 20, 22, 255))
    d.rectangle([0, 640, CW, 652], fill=(20, 20, 22, 255))
    house = layer()
    d = ImageDraw.Draw(house)
    hc = (24, 24, 28, 255)
    d.rectangle([1050, 380, CW, 900], fill=hc)
    d.polygon([(1010, 390), (1450, 170), (CW + 40, 390)], fill=(18, 18, 22, 255))
    d.rectangle([1170, 520, 1420, 700], fill=(220, 170, 90, 255))  # kitchen window
    d.line([(1295, 520), (1295, 700)], fill=hc, width=10)
    d.line([(1170, 610), (1420, 610)], fill=hc, width=10)
    glow(house, 1295, 660, 260, (230, 170, 80), 0.35)
    d = ImageDraw.Draw(house)
    d.rectangle([1530, 560, 1680, 900], fill=(34, 30, 28, 255))  # back door
    d.ellipse([1650, 730, 1662, 742], fill=(150, 130, 90, 255))
    d.rectangle([1500, 890, 1720, 910], fill=(30, 30, 32, 255))  # step
    return [(sky, 1), (trees, 4), (yard, 8), (house, 12)]


def sc_map():
    """Hand-drawn topo map; the trail is drawn by an extra."""
    W2, H2 = CW, CH
    yy, xx = np.mgrid[0:H2:4, 0:W2:4].astype(np.float32)
    z = (np.sin(xx / 210) * np.cos(yy / 170) + 0.6 * np.sin((xx + yy) / 330) + 0.4 * np.cos(xx / 90 - yy / 140))
    lines = (np.abs((z * 6) % 1 - 0.5) < 0.06).astype(np.float32)
    paper = np.zeros((H2 // 4 + (H2 % 4 > 0), W2 // 4 + (W2 % 4 > 0), 3), np.float32) + np.array([40, 38, 32])
    paper = paper[:lines.shape[0], :lines.shape[1]]
    paper += lines[..., None] * np.array([46, 44, 36])
    img = Image.fromarray(paper.clip(0, 255).astype(np.uint8)).resize((W2, H2), Image.BILINEAR).convert("RGBA")
    d = ImageDraw.Draw(img)
    d.line(MAP_RIVER, fill=(70, 96, 110, 255), width=9, joint="curve")
    f = font(SERIF_I, 34)
    d.text((MAP_RIVER[3][0] + 20, MAP_RIVER[3][1] - 60), "cold river", font=f, fill=(110, 130, 140, 255))
    d.text((1460, 300), "RIDGE", font=font(SERIF_B, 40), fill=(150, 140, 120, 255))
    d.text((300, 860), "TRAILHEAD", font=font(SERIF_B, 34), fill=(150, 140, 120, 255))
    for _ in range(70):  # tree glyphs
        r = random.Random(_)
        x, y = r.uniform(100, CW - 100), r.uniform(100, CH - 100)
        d.polygon([(x, y - 16), (x - 9, y + 8), (x + 9, y + 8)], fill=(66, 74, 56, 255))
    return [(img, 4)]


MAP_RIVER = [(100, 700), (500, 620), (900, 680), (1300, 560), (1700, 600), (2200, 520)]
MAP_TRAIL = [(380, 840), (560, 760), (700, 640), (900, 560), (1150, 470), (1380, 400), (1520, 360),
             (1640, 450), (1600, 600), (1400, 700), (1100, 760), (800, 820), (520, 860), (380, 840)]

# ------------------------------------------------------------- overlays ---

@lru_cache(maxsize=None)
def text_img(txt, path, size, color, glow_col=None, spacing=12, stroke=0):
    f = font(path, size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bb = [int(math.floor(v)) if i < 2 else int(math.ceil(v)) for i, v in enumerate(
        tmp.multiline_textbbox((0, 0), txt, font=f, align="center", spacing=spacing, stroke_width=stroke))]
    pad = 60
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pos = (pad - bb[0], pad - bb[1])
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).multiline_text(pos, txt, font=f, fill=(0, 0, 0, 230), align="center", spacing=spacing,
                                      stroke_width=stroke + 2)
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    if glow_col:
        gl = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(gl).multiline_text(pos, txt, font=f, fill=glow_col + (200,), align="center", spacing=spacing)
        im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(14)))
    d.multiline_text(pos, txt, font=f, fill=color + (255,), align="center", spacing=spacing, stroke_width=stroke)
    return np.asarray(im, np.float32) / 255.0


class Ov:
    """Text overlay: kind decides the look and placement."""
    def __init__(self, t0, t1, txt, kind="caption", fade=0.45):
        self.t0, self.t1, self.txt, self.kind, self.fade = t0, t1, txt, kind, fade

    def img(self):
        k = self.kind
        if k == "quote":
            return text_img(self.txt, SERIF_I, 76, BONE)
        if k == "ghost":
            return text_img(self.txt, SERIF_I, 110, (200, 205, 210), glow_col=(150, 170, 190))
        if k == "redcap":
            return text_img(self.txt, SERIF_B, 64, RED)
        if k == "red":
            longest = max(len(l) for l in self.txt.split("\n"))
            return text_img(self.txt, SERIF_B, 96 if longest <= 24 else 70, RED)
        if k == "big":
            return text_img(self.txt, SERIF_B, 120, BONE)
        if k == "label":
            return text_img(self.txt, MONO, 34, (200, 196, 186))
        return text_img(self.txt, SERIF_B, 58, BONE)  # caption

    def pos(self, im):
        h, w = im.shape[:2]
        if self.kind == "label":
            return 90, H - 150 - h // 2
        if self.kind in ("caption", "redcap"):
            return (W - w) // 2, int(H * 0.78) - h // 2
        if self.kind == "ghost":
            return (W - w) // 2, int(H * 0.38) - h // 2
        return (W - w) // 2, (H - h) // 2

    def alpha(self, t):
        if t < self.t0 or t > self.t1:
            return 0.0
        return min(1.0, (t - self.t0) / self.fade, (self.t1 - t) / self.fade)

# ------------------------------------------------------------------ extras ---
# Animated elements drawn per frame: fn(frame_float_rgb, t_local, scene) -> None

def ex_trail(t0, t1):
    pts = MAP_TRAIL
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg)

    def fn(fr, t, s):
        p = max(0.0, min(1.0, (t - t0) / (t1 - t0)))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        left = p * total
        ox = -s.pan(t)[0]
        for (a, b), sl in zip(zip(pts, pts[1:]), seg):
            if left <= 0:
                break
            f = min(1, left / sl)
            e = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            n = int(sl * f / 22)
            for k in range(n):  # dashed trail
                q0 = k / max(n, 1) * f
                q1 = (k + 0.55) / max(n, 1) * f
                d.line([(a[0] + (b[0] - a[0]) * q0 + ox, a[1] + (b[1] - a[1]) * q0),
                        (a[0] + (b[0] - a[0]) * q1 + ox, a[1] + (b[1] - a[1]) * q1)], fill=(200, 60, 50, 255), width=7)
            left -= sl
            last = e
        if p > 0:
            d.ellipse([last[0] - 12 + ox, last[1] - 12, last[0] + 12 + ox, last[1] + 12], fill=(230, 80, 60, 255))
        if p > 0.45:  # camp marker
            cx, cy = 1520 + ox, 360
            d.line([(cx - 22, cy - 22), (cx + 22, cy + 22)], fill=(235, 220, 200, 255), width=8)
            d.line([(cx - 22, cy + 22), (cx + 22, cy - 22)], fill=(235, 220, 200, 255), width=8)
        blend(fr, np.asarray(L, np.float32) / 255.0, 0, 0)
    return fn


def ex_distance(t0, t1):
    """Dashed range line from the treeline to the camp with a '50 YARDS' tag."""
    def fn(fr, t, s):
        a = max(0.0, min(1.0, (t - t0) / 0.6, (t1 - t) / 0.6))
        if a <= 0:
            return
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        ox = -s.pan(t)[0]
        x0, x1, y = 560 + ox, 1150 + ox, 780
        for x in range(int(x0), int(x1), 34):
            d.line([(x, y), (x + 18, y)], fill=(230, 220, 200, int(220 * a)), width=4)
        d.text(((x0 + x1) / 2 - 90, y - 60), "≈ 50 YARDS", font=font(MONO, 36), fill=(230, 220, 200, int(240 * a)))
        blend(fr, np.asarray(L, np.float32) / 255.0, 0, 0)
    return fn


def ex_shadow(t0, t_stop, t_hide):
    """A too-tall figure walks in from the right and stops by the tent wall at Claire's head."""
    def fn(fr, t, s):
        if t < t0 or t > t_hide:
            return
        p = min(1.0, (t - t0) / (t_stop - t0))
        ox, oy = -s.pan(t)[0], -s.pan(t)[1]
        x = TENT_X + 900 - 1260 * p
        bob = abs(math.sin(t * 2.6)) * 8 if p < 1 else 0
        a = min(1.0, (t - t0) / 1.5, (t_hide - t) / 1.0)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        mimic_figure(ImageDraw.Draw(L), x + ox, TENT_Y + oy - 20 - bob, 470, (2, 2, 3, int(235 * a)))
        blend(fr, np.asarray(L.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255.0, 0, 0)
    return fn


def ex_rec(t0, t1, clock0, clock1):
    """Camcorder overlay with a clock that runs from clock0 to clock1 (minutes after midnight)."""
    def fn(fr, t, s):
        if t < t0 or t > t1:
            return
        m = clock0 + (clock1 - clock0) * min(1, (t - t0) / (t1 - t0))
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        f = font(MONO, 40)
        if int(t * 2) % 2 == 0:
            d.ellipse([80, 72, 108, 100], fill=(210, 30, 30, 230))
        d.text((124, 64), "REC", font=f, fill=(235, 235, 235, 230))
        d.text((W - 360, 64), f"{int(m // 60):02d}:{int(m % 60):02d} AM", font=f, fill=(235, 235, 235, 230))
        for (x, y, sx, sy) in ((60, 50, 1, 1), (W - 60, 50, -1, 1), (60, H - 50, 1, -1), (W - 60, H - 50, -1, -1)):
            d.line([(x, y), (x + 70 * sx, y)], fill=(235, 235, 235, 200), width=4)
            d.line([(x, y), (x, y + 70 * sy)], fill=(235, 235, 235, 200), width=4)
        blend(fr, np.asarray(L, np.float32) / 255.0, 0, 0)
    return fn


def ex_footprints(t0, t_change, t1):
    """Boot prints walk across the frost, then turn long, narrow and heel-less."""
    steps = [(220 + k * 150, 640 + (40 if k % 2 else -40)) for k in range(13)]

    def fn(fr, t, s):
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        ox = -s.pan(t)[0]
        for k, (x, y) in enumerate(steps):
            appear = t0 + k * (t1 - t0) / len(steps)
            if t < appear:
                break
            a = min(1.0, (t - appear) / 0.5)
            col = (60, 66, 74, int(230 * a))
            x += ox
            changed = k >= 7 and t >= t_change
            if k < 7:
                d.rounded_rectangle([x - 34, y - 30, x + 34, y + 30], 26, fill=col)
                d.ellipse([x + 22, y - 24, x + 70, y + 24], fill=col)
                for g in range(-24, 34, 14):  # tread
                    d.line([(x + g, y - 22), (x + g, y + 22)], fill=(110, 116, 124, int(160 * a)), width=4)
            elif changed:
                d.ellipse([x - 70, y - 16, x + 70, y + 16], fill=col)
                for dx in (66, 82, 92):
                    d.ellipse([x + dx - 6, y - 20 + (dx - 66), x + dx + 10, y - 6 + (dx - 66)], fill=col)
        blend(fr, np.asarray(L, np.float32) / 255.0, 0, 0)
    return fn


def ex_wave(t0, t1, seed=1):
    """'Playback' waveform with a rewind tag — the stolen dinner conversation."""
    rnd = np.random.default_rng(seed)
    env = np.convolve(rnd.random(4000), np.ones(25) / 25, mode="same")

    def fn(fr, t, s):
        a = max(0.0, min(1.0, (t - t0) / 0.6, (t1 - t) / 0.6))
        if a <= 0:
            return
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        cy, n = int(H * 0.42), 120
        i0 = int((t - t0) * 40) % 3000
        for k in range(n):
            v = env[i0 + k] * (0.5 + 0.5 * math.sin(k * 0.3 + t * 3))
            h = 8 + v * 200
            x = W * 0.2 + k * (W * 0.6 / n)
            d.rectangle([x, cy - h / 2, x + 7, cy + h / 2], fill=(220, 214, 200, int(200 * a)))
        f = font(MONO, 36)
        d.text((W * 0.2, cy - 190), "◀◀  PLAYBACK", font=f, fill=(210, 40, 40, int(230 * a)))
        blend(fr, np.asarray(L, np.float32) / 255.0, 0, 0)
    return fn


def ex_counter(t0, t1, n=11):
    def fn(fr, t, s):
        if t < t0:
            return
        k = min(n, 1 + int((t - t0) / (t1 - t0) * n))
        a = min(1.0, (t - t0) / 0.4)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        d.text((110, 110), "TIMES IT CALLED HER NAME", font=font(MONO, 34), fill=(200, 196, 186, int(220 * a)))
        d.text((104, 150), f"{k:02d}", font=font(SERIF_B, 150), fill=RED + (int(255 * a),))
        blend(fr, np.asarray(L, np.float32) / 255.0, 0, 0)
    return fn

# ------------------------------------------------------------------ scenes ---

class Scene:
    def __init__(self, t0, build, pan=(1, 0), shake=0.0, fog=0.25, fog_col=(150, 160, 165), bars=True,
                 dark=0.0, extras=(), tint=None):
        self.t0, self.build, self.pan_dir, self.shake = t0, build, pan, shake
        self.fog, self.fog_col, self.bars, self.dark, self.extras, self.tint = fog, fog_col, bars, dark, extras, tint
        self.layers = None

    def load(self):
        if self.layers is None:
            self.layers = [(np.asarray(im, np.float32) / 255.0, sp) for im, sp in self.build()]
        return self.layers

    def crop(self, t, speed):
        sx, sy, lt = self.pan(t)
        return (int(PX / 2 - self.pan_dir[0] * min(speed * lt * 0.9, PX / 2 - 10) + sx), int(PY / 2 + sy))

    def pan(self, t):
        lt = t - self.t0
        sx = self.shake * (math.sin(t * 13.1) + 0.6 * math.sin(t * 7.3)) * 6
        sy = self.shake * (math.cos(t * 11.7) + 0.5 * math.sin(t * 5.1)) * 6
        return sx, sy, lt


def build_timeline():
    S, O = [], []
    title_t = T(INSERTS[0][0]) - TITLE_GAP  # the inserted gap ends where the voice resumes
    S.append(Scene(0, lambda: sc_dusk_ridge(), pan=(1, 0), fog=0.15, fog_col=(150, 110, 90)))
    O.append(Ov(TP("He heard his wife"), TP("the trees.", True) + 0.3, "“Danny.”", "ghost"))
    S.append(Scene(title_t - 0.3, lambda: sc_deep_woods(1), fog=0.35, bars=False))
    O.append(Ov(title_t + 0.4, title_t + TITLE_GAP - 0.2, "NEVER ANSWER\nTHE VOICE IN THE WOODS", "red", fade=0.8))
    S.append(Scene(TP("There is an old rule"), lambda: sc_deep_woods(2, (12, 16, 20)), fog=0.3))
    O += [Ov(TP("Hunters know it"), TP("Search and rescue"), "HUNTERS KNOW IT."),
          Ov(TP("Rangers know it"), TP("Search and rescue") + 0.2, "RANGERS KNOW IT.", "label"),
          Ov(TP("Search and rescue"), TP("they will never say", True), "SEARCH & RESCUE KNOW IT."),
          Ov(TP("If you hear someone"), TP("you do not answer") - 0.1,
             "If you hear someone you love\ncalling to you from the trees…", "quote"),
          Ov(TP("you do not answer"), TP("Because whatever"), "YOU DO NOT ANSWER.", "red"),
          Ov(TP("It is learning"), TP("It is learning", True) + 1.6, "IT IS LEARNING.", "red")]

    def chapter(c):
        cut, gap, card = c
        t = T(cut) - gap
        S.append(Scene(t - 0.2, lambda: sc_deep_woods(9, (6, 8, 10)), fog=0.45, bars=False, dark=0.55))
        O.append(Ov(t + 0.2, t + gap - 0.1, card[0], "label"))
        O.append(Ov(t + 0.2, t + gap - 0.1, card[1], "big", fade=0.5))

    chapter(INSERTS[1])
    S.append(Scene(TP("This account was shared"), sc_map, fog=0.0, bars=False,
                   extras=[ex_trail(TP("In the fall of 2019"), TP("They had done the same") + 1)]))
    O += [Ov(TP("In the fall of 2019"), TP("They had done the same"), "PACIFIC NORTHWEST  ·  FALL 2019", "label")]
    S.append(Scene(TP("Old growth cedar"), sc_cedars, fog=0.2, fog_col=(170, 180, 175)))
    O += [Ov(TP("The forest was quiet"), TP("Not peaceful"), "THE FOREST WAS QUIET."),
          Ov(TP("No birds"), TP("own footsteps.", True), "NO BIRDS.  NO SQUIRRELS.", "label")]

    chapter(INSERTS[2])
    S.append(Scene(TP("On the second evening"), lambda: sc_dusk_ridge(), fog=0.12, fog_col=(150, 110, 90),
                   extras=[ex_distance(TP("It came from the treeline"), TP("Claire's voice.") + 6)]))
    O += [Ov(TP("\"Danny.\""), TP("It came from") + 0.5, "“Danny.”", "ghost", fade=0.25),
          Ov(TP("And only one person"), TP("He turned around"), "ONLY ONE PERSON\nCALLED HIM DANNY."),
          Ov(TP("much, she said"), TP("He told her yes"), "“Did you hear me just now?”", "quote"),
          Ov(TP("She said: \"I didn't"), TP("Then it called again"), "“I didn’t say anything.”", "quote")]
    S.append(Scene(TP("Then it called again"), lambda: sc_dusk_ridge(figures=False, darker=0.35, watcher=True),
                   pan=(-1, 0), fog=0.2, shake=0.25))
    O += [Ov(TP("\"Danny."), TP("Daniel says the worst"),
             "“Danny. Come here.\nI need to show you something.”", "ghost")]
    S.append(Scene(TP("Daniel says the worst"), lambda: sc_deep_woods(4, (16, 14, 18), figure=0.8), fog=0.3))
    O += [Ov(TP("It was the pauses"), TP("The voice would speak"), "IT WAS THE PAUSES."),
          Ov(TP("A little different"), TP("A little closer", True) + 1.2, "A little different.\nA little closer to right.",
             "quote")]

    chapter(INSERTS[3])
    t_steps = TP("Something was walking")
    S.append(Scene(TP("They did not go to look"), lambda: sc_tent(), fog=0.18, fog_col=(90, 100, 120), shake=0.1,
                   bars=False,
                   extras=[ex_rec(TP("Around two in the morning"), TP("At first light") - 0.5, 2 * 60 + 7, 3 * 60 + 1),
                           ex_shadow(t_steps, TP("Then, right against"), TP("At first light") - 0.6)]))
    O += [Ov(TP("Two legs"), TP("Stopping every") + 2, "TWO LEGS.", "label"),
          Ov(TP("It was Daniel's voice"), TP("\"Claire.") , "IT WAS DANIEL’S VOICE.", "red"),
          Ov(TP("\"Claire."), TP("Daniel was lying"),
             "“Claire. It’s me. I went to pee.\nOpen the tent, it’s cold.”", "ghost"),
          Ov(TP("Daniel was lying"), TP("Claire did not answer"), "HE WAS LYING RIGHT NEXT TO HER."),
          Ov(TP("Word for word"), TP("Like a recording", True) + 0.6, "WORD FOR WORD.", "label"),
          Ov(TP("It did that for almost"), TP("It did that", True) + 2.0, "IT DID THAT FOR ALMOST AN HOUR.")]

    chapter(INSERTS[4])
    S.append(Scene(TP("At first light"), sc_frost, fog=0.1, fog_col=(200, 210, 220), bars=False,
                   extras=[ex_footprints(TP("Daniel unzipped"), TP("changed."), TP("With no clear heel"))]))
    O += [Ov(TP("Longer"), TP("They packed in") - 0.2, "LONGER.  NARROWER.  NO HEEL.", "label")]
    S.append(Scene(TP("They packed in ten"), sc_fog_trail, fog=0.45, fog_col=(180, 186, 188),
                   extras=[ex_wave(TP("Their conversation"), TP("back again.", True) + 1)]))
    O += [Ov(TP("The one they had had"), TP("Both voices"), "…Claire’s sister…\n…the dishwasher…", "quote"),
          Ov(TP("Played back perfectly"), TP("back again.", True) + 1, "PLAYED BACK. AGAIN.", "redcap")]

    chapter(INSERTS[5])
    S.append(Scene(TP("At the trailhead"), sc_trailhead, fog=0.35, fog_col=(170, 170, 170)))
    O += [Ov(TP("\"You didn't answer"), TP("said no.", True), "“You didn’t answer it, did you?”", "quote"),
          Ov(TP("The ranger nodded"), TP("Then it's still") - 0.1, "“Good.”", "quote"),
          Ov(TP("Then it's still"), TP("Then it's still", True) + 2.2, "“Then it’s still guessing.”", "red")]

    chapter(INSERTS[6])
    S.append(Scene(TP("Daniel and Claire never"), lambda: sc_house(), fog=0.12, fog_col=(80, 90, 110),
                   extras=[ex_counter(TP("The voice called her"), TP("The last time"))]))
    O += [Ov(TP("Until last spring"), TP("Claire was home"), "LAST SPRING", "label"),
          Ov(TP("\"Claire, come outside"), TP("Daniel was on a business"),
             "“Claire, come outside.\nI need to show you something.”", "ghost"),
          Ov(TP("Daniel was on a business"), TP("She did not answer"), "HE WAS 2,000 MILES AWAY."),
          Ov(TP("it was much closer"), TP("People who study") , "IT WAS MUCH CLOSER TO THE DOOR.", "red")]
    S.append(Scene(TP("People who study"), lambda: sc_deep_woods(7, (10, 12, 14), figure=0.5), fog=0.4, pan=(-1, 0)))
    O += [Ov(TP("Something old"), TP("Something that only"), "SOMETHING OLD.  SOMETHING HUNGRY.", "label"),
          Ov(TP("It needs you to answer"), TP("So if you are ever"), "IT NEEDS YOU TO ANSWER.", "red"),
          Ov(TP("keep walking"), TP("Don't look back"), "KEEP WALKING.", "big"),
          Ov(TP("Don't look back"), TP("And never, ever"), "DON’T LOOK BACK.", "big")]
    S.append(Scene(TP("And never, ever"), lambda: sc_deep_woods(1), fog=0.4, bars=False, dark=0.2))
    O.append(Ov(TP("And never, ever") + 0.3, TOTAL - 0.4, "NEVER ANSWER\nTHE VOICE IN THE WOODS", "red", fade=1.0))
    return S, O


SCENES, OVERLAYS = build_timeline()
XFADE = 0.6

# ---------------------------------------------------------------- compositor ---

def blend(fr, rgba, x, y):
    """Alpha-blend float RGBA (0..1) onto float RGB frame (0..1) at x, y (clipped)."""
    h, w = rgba.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    src = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = src[..., 3:4]
    dst = fr[y0:y1, x0:x1]
    dst *= 1 - a
    dst += src[..., :3] * a


rng = np.random.default_rng(0)
GRAIN = [np.repeat(np.repeat(rng.normal(0, 0.035, (H // 2, W // 2)).astype(np.float32), 2, 0), 2, 1)[..., None]
         for _ in range(6)]
FOG = None
VIGN = None


def fog_tex():
    global FOG
    if FOG is None:
        r = np.random.default_rng(1)
        n = sum(np.asarray(Image.fromarray((r.random((H // s, (2 * W) // s)) * 255).astype(np.uint8))
                           .resize((2 * W, H), Image.BICUBIC), np.float32) * w for s, w in ((180, .55), (60, .3), (20, .15)))
        n = (n / 255.0)
        y = np.linspace(0, 1, H)[:, None]
        FOG = (np.clip((n - 0.35) * 2.0, 0, 1) * (0.35 + 0.65 * y)).astype(np.float32)
    return FOG


def vignette():
    global VIGN
    if VIGN is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        VIGN = np.clip(1.18 - r * 0.62, 0.2, 1)[..., None].astype(np.float32)
    return VIGN


def render_scene(s, t):
    fr = np.zeros((H, W, 3), np.float32)
    for arr, speed in s.load():
        x, y = s.crop(t, speed)
        crop = arr[y:y + H, x:x + W]
        a = crop[..., 3:4]
        fr *= 1 - a
        fr += crop[..., :3] * a
    if s.fog > 0:
        f = fog_tex()
        off = int((t * 28) % W)
        fa = f[:, off:off + W, None] * s.fog
        fr = fr * (1 - fa) + np.array(s.fog_col, np.float32)[None, None] / 255.0 * fa
    for ex in s.extras:
        ex(fr, t, _PanView(s, t))
    if s.dark:
        fr *= 1 - s.dark
    return fr


class _PanView:
    """What extras see: crop origin of the scene's front layer, so canvas coords map to screen = X - crop."""
    def __init__(self, s, t):
        self.s, self.t = s, t

    def pan(self, t):
        return self.s.crop(t, self.s.load()[-1][1])


def scene_at(t):
    idx = max(i for i, s in enumerate(SCENES) if s.t0 <= t + 1e-6) if t >= 0 else 0
    return idx


def frame(t, fi):
    i = scene_at(t)
    s = SCENES[i]
    fr = render_scene(s, t)
    if i > 0 and t - s.t0 < XFADE:  # crossfade from the previous scene
        p = (t - s.t0) / XFADE
        fr = fr * p + render_scene(SCENES[i - 1], t) * (1 - p)
    for o in OVERLAYS:
        a = o.alpha(t)
        if a > 0:
            im = o.img()
            if o.kind == "ghost":  # ghostly jitter
                im = im.copy()
                im[..., 3] *= 0.75 + 0.25 * math.sin(t * 17) * math.sin(t * 5)
            x, y = o.pos(im)
            if a < 1:
                im = im.copy()
                im[..., 3] *= a
            blend(fr, im, x, y)
    # film look: flicker, vignette, grain, letterbox, fades
    fr *= 1 + 0.025 * math.sin(t * 23) * math.sin(t * 7.7)
    fr *= vignette()
    fr += GRAIN[fi % len(GRAIN)]
    if s.bars:
        fr[:110] = 0
        fr[-110:] = 0
    fade = min(1.0, t / 1.2, (TOTAL - t) / 2.0)
    if fade < 1:
        fr *= max(0.0, fade)
    return (fr.clip(0, 1) * 255).astype(np.uint8)


def render(t_start, t_end, out):
    n0, n1 = int(round(t_start * FPS)), int(round(t_end * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for fi in range(n0, n1):
        t = fi / FPS
        i = scene_at(t)
        for k, s in enumerate(SCENES):  # free scenes we are done with
            if k < i - 1 and s.layers is not None:
                s.layers = None
        p.stdin.write(frame(t, fi).tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    if sys.argv[1] == "info":
        print(f"total {TOTAL:.2f}s  scenes {len(SCENES)}  overlays {len(OVERLAYS)}")
        for s in SCENES:
            print(f"  scene @ {s.t0:7.2f}  {s.build.__name__ if hasattr(s.build, '__name__') else s.build}")
        for c, g, card in INSERTS:
            print(f"  insert {g}s at voice {c:.2f} -> video {T(c):.2f} {card}")
    elif sys.argv[1] == "still":
        t = float(sys.argv[2])
        Image.fromarray(frame(t, int(t * FPS))).save(sys.argv[3])
    elif sys.argv[1] == "frames":
        render(float(sys.argv[2]), float(sys.argv[3]), sys.argv[4])
