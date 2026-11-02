"""Ukraine thumbnails in the 'top white line / bottom yellow line / red circle + arrow' format."""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "ua", "out")
os.makedirs(OUT, exist_ok=True)
W, H = 1280, 720
MONT = os.path.join(BASE, "fonts", "Montserrat.ttf")
YEL = (255, 222, 60)
RED = (230, 30, 30)


def font(size):
    f = ImageFont.truetype(MONT, size)
    f.set_variation_by_name("Black")
    return f


def arr(im):
    return np.asarray(im.convert("RGB")).astype(np.float32) / 255


def img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def frame(path, box=None, zoom=1.0, cx=0.5, cy=0.5, pad_top=0):
    """Returns the 1280x720 frame and a function mapping source px -> frame px."""
    im = Image.open(path).convert("RGB")
    bx, by = (box[0], box[1]) if box else (0, 0)
    if box:
        im = im.crop(box)
    h = H - pad_top
    s = max(W / im.width, h / im.height) * zoom
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x = int((im.width - W) * cx)
    y = int((im.height - h) * cy)
    im = im.crop((x, y, x + W, y + h))
    if pad_top:
        # extend the room upward with a soft, darkened mirror of the top strip
        strip = im.crop((0, 0, W, pad_top)).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(14))
        strip = img(arr(strip) * 0.55)
        full = Image.new("RGB", (W, H))
        full.paste(strip, (0, 0))
        full.paste(im, (0, pad_top))
        fade = Image.linear_gradient("L").resize((W, 40))
        full.paste(strip.crop((0, pad_top - 40, W, pad_top)) if pad_top >= 40 else strip, (0, pad_top), fade.transpose(Image.FLIP_TOP_BOTTOM).point(lambda v: int(v * 0.6)))
        im = full
    to = lambda px, py: ((px - bx) * s - x, (py - by) * s - y + pad_top)
    return im, to, s


def look(im, warm=1.0):
    """Punchy thumbnail grade: contrast, a bit of saturation, top/bottom shade for text."""
    a = arr(im)
    lum = (a * [0.299, 0.587, 0.114]).sum(-1, keepdims=True)
    a = lum + (a - lum) * 1.18
    a = (a - 0.5) * 1.12 + 0.5
    a = a * np.array([1.0 + 0.03 * warm, 1.0, 1.0 - 0.04 * warm], np.float32)
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    shade = 1 - 0.45 * np.clip(1 - y / 0.22, 0, 1) ** 1.5 - 0.5 * np.clip((y - 0.74) / 0.26, 0, 1) ** 1.5
    a = a * shade
    a = a.clip(0, 1)
    im = img(a).filter(ImageFilter.UnsharpMask(1.6, 60, 2))
    return im


def headline(im, s, y, fill, size=118, max_w=W - 80):
    while font(size).getlength(s) > max_w:
        size -= 4
    f = font(size)
    x = W // 2
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).text((x, y + 6), s, font=f, anchor="mm", fill=255, stroke_width=14, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    im.paste((0, 0, 0), (0, 0), sh.point(lambda v: int(v * 0.85)))
    d = ImageDraw.Draw(im)
    d.text((x, y), s, font=f, anchor="mm", fill=fill, stroke_width=7, stroke_fill=(0, 0, 0))


def ring(im, cx, cy, rx, ry, width=9):
    d = ImageDraw.Draw(im)
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=RED, width=width)


def arrow(im, tail, tip, width=22, head=60):
    t, p = np.array(tail, float), np.array(tip, float)
    v = p - t
    v /= np.linalg.norm(v)
    n = np.array([-v[1], v[0]])
    base = p - v * head
    sh = Image.new("L", im.size, 0)
    ds = ImageDraw.Draw(sh)
    poly_body = [tuple(t + n * width / 2), tuple(base + n * width / 2), tuple(base - n * width / 2), tuple(t - n * width / 2)]
    poly_head = [tuple(p), tuple(base + n * head * 0.62), tuple(base - n * head * 0.62)]
    for poly in (poly_body, poly_head):
        ds.polygon([(x + 3, y + 5) for x, y in poly], fill=200)
    im.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im)
    d.polygon(poly_body, fill=RED)
    d.polygon(poly_head, fill=RED)


def make(spec):
    im, to, sc = frame(spec["src"], spec.get("box"), spec.get("zoom", 1.0), spec.get("cx", 0.5), spec.get("cy", 0.5), spec.get("pad_top", 0))
    im = look(im, spec.get("warm", 1.0))
    for r in spec.get("rings", []):  # source coords: cx, cy, rx, ry
        cx, cy = to(r[0], r[1])
        ring(im, cx, cy, r[2] * sc, r[3] * sc)
    for a in spec.get("arrows", []):  # source coords: tail, tip
        arrow(im, to(*a[0]), to(*a[1]))
    headline(im, spec["top"], spec.get("top_y", 70), (255, 255, 255), spec.get("size", 118))
    headline(im, spec["bottom"], H - 72, YEL, spec.get("size", 118))
    return im


if __name__ == "__main__":
    specs = json.load(open(sys.argv[1]))
    only = sys.argv[2:]
    for k, spec in specs.items():
        if only and k not in only:
            continue
        make(spec).save(os.path.join(OUT, f"ukraine_thumb_{k}.jpg"), quality=92)
        print("ok", k)
