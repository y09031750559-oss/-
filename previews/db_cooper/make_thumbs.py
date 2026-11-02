"""D.B. Cooper thumbnails — 5 variants from real (free-licence) photos."""
import os, sys, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "dbc", "src")
OUT = os.path.join(BASE, "dbc", "out")
FONTS = os.path.join(BASE, "fonts")
os.makedirs(OUT, exist_ok=True)
W, H = 1280, 720
rng = np.random.default_rng(7)

ANTON = os.path.join(FONTS, "Anton-Regular.ttf.ttf")
OSW = os.path.join(FONTS, "Oswald.ttf")
YEL = (255, 210, 0)
RED = (225, 38, 32)


def src(name):
    return Image.open(os.path.join(SRC, name)).convert("RGB")


def arr(im):
    return np.asarray(im).astype(np.float32) / 255.0


def img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def font(path, size):
    return ImageFont.truetype(path, size)


def cover(im, w, h, cx=0.5, cy=0.5, zoom=1.0):
    s = max(w / im.width, h / im.height) * zoom
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = int((im.width - w) * cx)
    y = int((im.height - h) * cy)
    return im.crop((x, y, x + w, y + h))


def grade(a, lift=0.0, gain=1.0, gamma=1.0, tint=(1, 1, 1), sat=1.0):
    lum = (a * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    a = lum + (a - lum) * sat
    a = np.clip(a, 0, 1) ** gamma
    a = a * gain + lift
    return a * np.array(tint, np.float32)


def vignette(a, strength=0.75, power=2.2, cx=0.5, cy=0.5):
    h, w = a.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x / w - cx) / 0.75) ** 2 + ((y / h - cy) / 0.75) ** 2)
    v = 1 - strength * np.clip(d, 0, 1) ** power
    return a * v[..., None]


def spot(a, cx, cy, rx, ry, floor=0.12):
    h, w = a.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
    m = floor + (1 - floor) * np.clip(1 - d, 0, 1) ** 1.6
    return a * m[..., None]


def grain(a, amt=0.035, size=1.0):
    h, w = a.shape[:2]
    n = rng.normal(0, 1, (int(h / size), int(w / size))).astype(np.float32)
    if size != 1.0:
        n = np.asarray(Image.fromarray(n).resize((w, h), Image.BILINEAR))
    return a + n[..., None] * amt


def text(im, xy, s, size, fill=(255, 255, 255), f=ANTON, anchor="la", shadow=10, stroke=0, stroke_fill=(0, 0, 0)):
    """Text with soft drop shadow (keeps it readable on any frame)."""
    fnt = font(f, size)
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).text((xy[0] + 4, xy[1] + 6), s, font=fnt, fill=230, anchor=anchor,
                            stroke_width=stroke + 6, stroke_fill=230)
    sh = sh.filter(ImageFilter.GaussianBlur(shadow))
    im.paste(Image.new("RGB", im.size, (0, 0, 0)), (0, 0), sh)
    d = ImageDraw.Draw(im)
    d.text(xy, s, font=fnt, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)
    return d.textbbox(xy, s, font=fnt, anchor=anchor, stroke_width=stroke)


def credit(im, s):
    d = ImageDraw.Draw(im)
    d.text((W - 14, H - 12), s, font=font(OSW, 15), fill=(200, 200, 200), anchor="rd")


def stamp(word, size, color=RED, angle=-12):
    """Rubber-stamp style word with rough ink."""
    fnt = font(ANTON, size)
    tw, th = fnt.getbbox(word)[2:]
    pad = int(size * 0.28)
    L = Image.new("L", (tw + pad * 2, th + pad * 2), 0)
    d = ImageDraw.Draw(L)
    d.rectangle((6, 6, L.width - 7, L.height - 7), outline=255, width=max(6, size // 14))
    d.text((pad, pad - size * 0.08), word, font=fnt, fill=255)
    ink = arr(L.convert("RGB"))[..., 0]
    noise = np.asarray(Image.fromarray(rng.random((L.height // 3 + 1, L.width // 3 + 1)).astype(np.float32))
                       .resize((L.width, L.height), Image.BILINEAR))
    ink = ink * np.clip((noise - 0.18) * 3.0, 0, 1) * 0.92
    A = Image.fromarray((ink * 255).astype(np.uint8)).rotate(angle, expand=True, resample=Image.BICUBIC)
    C = Image.new("RGB", A.size, color)
    return C, A


def border_flood(bright):
    from scipy import ndimage
    lab, n = ndimage.label(bright)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    return np.isin(lab, list(edge))


def largest_component(mask):
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    best, best_n, cur = 0, 0, 0
    for sy in range(0, h, 2):
        for sx in range(0, w, 2):
            if mask[sy, sx] and not lab[sy, sx]:
                cur += 1
                q = collections.deque([(sy, sx)])
                lab[sy, sx] = cur
                n = 0
                while q:
                    y, x = q.popleft()
                    n += 1
                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = cur
                            q.append((ny, nx))
                if n > best_n:
                    best, best_n = cur, n
    return lab == best


def plane_cutout():
    """Cut the real N467US out of its overcast sky (sky is bluish + bright)."""
    cache = os.path.join(BASE, "dbc", "plane_rgba.png")
    if os.path.exists(cache):
        return Image.open(cache)
    im = src("Northwest_Airlines_Boeing_727-51_N467US.jpg")
    a = np.asarray(im).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    sky = ((b - r) > 12) & (lum > 165)
    notsky = ~sky
    notsky[300:, :300] = False  # low cloud bank left of the tail cone
    notsky[:200, :] = False     # clouds above the fin
    m = Image.fromarray((notsky * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    keep = largest_component(np.asarray(m) > 128)
    m = Image.fromarray((keep * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.copy()
    rgba.putalpha(m)
    rgba = rgba.crop(m.getbbox())
    rgba.save(cache)
    return rgba


def clouds(w, h, seed=1, octaves=6):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = 2 ** (o + 2)
        n = r.random((max(2, h * s // w + 1), s + 1)).astype(np.float32)
        acc += amp * np.asarray(Image.fromarray(n).resize((w, h), Image.BICUBIC))
        tot += amp
        amp *= 0.55
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min())


def rain(w, h, n=1600, angle=0.18, alpha=0.22, length=(18, 46), seed=3):
    r = np.random.default_rng(seed)
    L = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(L)
    for _ in range(n):
        x, y = r.uniform(-100, w), r.uniform(-50, h)
        l = r.uniform(*length)
        d.line((x, y, x + l * angle, y + l), fill=int(255 * r.uniform(0.3, 1)), width=1)
    return arr(L.filter(ImageFilter.GaussianBlur(0.6)).convert("RGB"))[..., :1] * alpha


# ---------------------------------------------------------------- 1. plane at night
def t1():
    land = src("merwin.jpg").crop((940, 60, 1920, 1031))
    land = cover(land, W, H, cy=0.6)
    a = arr(land)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = (a * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    # day-for-night: clouds become dim moonlit, forest nearly black, lake keeps a cold sheen
    water = np.clip(((b - g) - 0.02) / 0.10, 0, 1)[..., None] * (lum < 0.45)
    a = grade(a, gain=0.6, gamma=1.6, tint=(0.55, 0.72, 1.0), sat=0.25)
    a = a + water * np.array([0.05, 0.08, 0.12], np.float32)
    a = a + lum ** 3 * np.array([0.10, 0.13, 0.18]) * 0.9
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    a = a * (1.0 - 0.35 * ys)
    base = img(a)
    p = plane_cutout()
    s = 820 / p.width
    p = p.resize((int(p.width * s), int(p.height * s)), Image.LANCZOS).rotate(3, expand=True, resample=Image.BICUBIC)
    pa = arr(p.convert("RGB"))
    al = p.split()[-1]
    hh = pa.shape[0]
    ramp = np.linspace(1.05, 0.40, hh, dtype=np.float32)[:, None, None]
    pa = grade(pa, gain=0.62, gamma=1.25, tint=(0.78, 0.86, 1.0), sat=0.85) * ramp
    pimg = img(pa)
    pimg.putalpha(al)
    px, py = 420, 150
    base.paste(pimg, (px, py), pimg)
    a = arr(base) + rain(W, H, n=1400, alpha=0.13)
    a = vignette(a, 0.55, cx=0.6)
    a = grain(a, 0.028)
    im = img(a)
    text(im, (56, 360), "HE NEVER", 120)
    text(im, (56, 505), "LANDED.", 120, fill=YEL)
    credit(im, "727 N467US, 1972: Clint Groves, CC BY-SA 4.0 · Lake Merwin, WA: Ryan Harvey, CC BY-SA 2.0")
    return im


# ---------------------------------------------------------------- 2. the face
def t2():
    sk = src("sketch.jpg")
    face = sk.crop((236, 4, 440, 303))  # FBI composite with sunglasses
    s = 780 / face.height
    face = face.resize((int(face.width * s), 780), Image.LANCZOS)
    fa = arr(face)
    lum = (fa * [0.299, 0.587, 0.114]).sum(-1)
    paper = border_flood(lum > 0.80).astype(np.float32)
    paper = np.asarray(Image.fromarray((paper * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
                       .filter(ImageFilter.GaussianBlur(2.5))).astype(np.float32) / 255
    fa = grade(fa, gain=0.95, gamma=1.2, tint=(0.95, 0.98, 1.04), sat=0.0)
    fa = fa * (1 - paper[..., None])
    a = np.zeros((H, W, 3), np.float32) + [0.015, 0.018, 0.022]
    x0 = W - face.width - 30
    a[:, x0:x0 + face.width] = np.maximum(a[:, x0:x0 + face.width], fa[40:40 + H])
    xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
    a = a * (0.35 + 0.85 * np.clip((xs - 0.48) / 0.40, 0, 1) ** 0.8)
    a = vignette(a, 0.5, cx=0.72)
    a = grain(a, 0.04, size=1.3)
    im = img(a)
    text(im, (60, 120), "WHO", 160)
    text(im, (60, 300), "WAS HE?", 160, fill=YEL)
    C, A = stamp("UNSOLVED", 66, angle=-7)
    im.paste(C, (60, 535), A)
    credit(im, "FBI composite sketch, 1971")
    return im


# ---------------------------------------------------------------- 3. the money
def t3():
    m = src("Money_stolen_by_D._B._Cooper.jpg")
    a0 = arr(m)
    lum = (a0 * [0.299, 0.587, 0.114]).sum(-1)
    sat = a0.max(-1) - a0.min(-1)
    paper = border_flood((lum > 0.70) & (sat < 0.10)).astype(np.float32)
    paper = np.asarray(Image.fromarray((paper * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
                       .filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255
    table = np.array([0.05, 0.045, 0.04], np.float32) + clouds(m.width, m.height, seed=41, octaves=7)[..., None] * 0.05
    a0 = a0 * (1 - paper[..., None]) + table * paper[..., None]
    im = img(a0).crop((30, 70, 1400, 841))
    im = cover(im, W, H, cx=0.5, cy=0.5, zoom=1.0)
    a = grade(arr(im), gain=1.08, gamma=1.05, tint=(1.03, 1.0, 0.9), sat=0.95)
    a = spot(a, 380, 400, 720, 560, floor=0.10)
    a = grain(a, 0.03)
    im = img(a)
    text(im, (W - 46, 40), "$5,800", 170, fill=YEL, anchor="ra")
    text(im, (W - 46, 245), "FOUND.", 130, anchor="ra")
    text(im, (W - 46, 430), "HE WASN'T.", 96, anchor="ra")
    credit(im, "Ransom bills found on the Columbia River, 1980 · FBI photo")
    return im


# ---------------------------------------------------------------- 4. the airstair
def t4():
    s = src("Northwest_Boeing_727_airstair_(1975).jpg")
    s = s.crop((231, 70, 764, 370))
    s = s.resize((W, round(s.height * W / s.width)), Image.LANCZOS)
    s = s.filter(ImageFilter.UnsharpMask(2, 70, 2))
    im = cover(s, W, H)
    a = arr(im)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    skym = np.clip(((b - r) - 0.12) / 0.15, 0, 1) * (a.mean(-1) > 0.45)
    skym = np.asarray(Image.fromarray((skym * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)[..., None] / 255
    night = grade(a, gain=0.5, gamma=1.3, tint=(0.66, 0.80, 1.0), sat=0.6)
    skyc = np.array([0.015, 0.022, 0.04], np.float32) + clouds(W, H, seed=21)[..., None] * [0.03, 0.04, 0.06]
    a = night * (1 - skym) + skyc * skym
    sx, sy = 0.36 * W, 0.80 * H  # airstair
    a = a + spot(np.ones_like(a) * [1.0, 0.80, 0.50], sx, sy - 40, 230, 200, floor=0.0) * 0.30
    a = a + rain(W, H, n=1300, alpha=0.13, seed=9)
    a = vignette(a, 0.5)
    a = grain(a, 0.035, size=1.4)
    im = img(a)
    text(im, (W - 50, 30), "THE BACK", 112, anchor="ra")
    text(im, (W - 50, 160), "DOOR.", 112, fill=YEL, anchor="ra")
    d = ImageDraw.Draw(im)
    tip = (sx + 40, sy - 60)
    tail = (tip[0] + 250, tip[1] - 150)
    d.line((tail, (tip[0] + 30, tip[1] - 18)), fill=YEL, width=14)
    v = np.array(tip) - np.array(tail); v = v / np.linalg.norm(v); n = np.array([-v[1], v[0]])
    t = np.array(tip)
    d.polygon([tuple(t), tuple(t - v * 60 + n * 30), tuple(t - v * 60 - n * 30)], fill=YEL)
    credit(im, "Northwest 727 aft airstair, 1975 · photo: R. W. Rynerson, CC BY 2.0")
    return im


# ---------------------------------------------------------------- 5. the file
def t5():
    p = src("DB_Cooper_Wanted_Poster.jpg")
    s = 900 / p.height
    p = p.resize((int(p.width * s), 900), Image.LANCZOS)
    pa = grade(arr(p), gain=0.93, lift=0.03, tint=(1.0, 0.95, 0.82), sat=1.0)
    # desk
    desk = clouds(W, H, seed=31, octaves=7)[..., None]
    a = np.array([0.10, 0.07, 0.05], np.float32) * (0.6 + 0.6 * desk)
    a = np.broadcast_to(a, (H, W, 3)).copy()
    poster = img(pa).convert("RGBA").rotate(-5, expand=True, resample=Image.BICUBIC)
    base = img(a)
    sh = Image.new("L", (W, H), 0)
    sh.paste(poster.split()[-1], (740 + 18, -14 + 24))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    base.paste(Image.new("RGB", (W, H), 0), (0, 0), sh.point(lambda v: int(v * 0.8)))
    base.paste(poster, (740, -14), poster)
    a = arr(base)
    a = spot(a, 940, 300, 560, 520, floor=0.16)
    a = grain(a, 0.03)
    im = img(a)
    C, A = stamp("UNSOLVED", 96, angle=-14)
    im.paste(C, (700, 420), A)
    text(im, (60, 110), "55 YEARS.", 140)
    text(im, (60, 290), "NO NAME.", 140, fill=YEL)
    credit(im, "FBI wanted bulletin, 1971")
    return im


if __name__ == "__main__":
    which = sys.argv[1:] or ["1", "2", "3", "4", "5"]
    for k in which:
        im = globals()["t" + k]()
        im.save(os.path.join(OUT, f"dbcooper_thumb_{k}.png"))
        im.save(os.path.join(OUT, f"dbcooper_thumb_{k}.jpg"), quality=92)
        print("ok", k)
