"""Dark forest title cards, 1920x1080."""
import random, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"

CARDS = [
    ("NEVER ANSWER\nTHE VOICE IN THE WOODS", "17 disturbing mimic encounters"),
    ("17 ENCOUNTERS", "seventeen people who answered anyway"),
    ("#1", "his wife called from the treeline.\nshe was standing beside him."),
    ("#4", "her mother sings outside the window at 3 a.m.\nher mother is asleep beside her."),
    ("#9", "it called for help for two miles.\nit repeated his words, one second behind."),
    ("#13", "it knows your name.\nit knows what you said at dinner."),
    ("#17", "he answered once.\nnow it answers back. from inside the house."),
    ("IF YOU HEAR YOUR NAME", "in the dark. in the trees."),
    ("KEEP WALKING.", "never answer the voice in the woods."),
]


def forest(seed):
    rnd = random.Random(seed)
    y = np.linspace(0, 1, H)[:, None]
    base = np.zeros((H, W, 3), np.float32)
    tint = np.array([14, 20, 22], np.float32) if seed % 2 else np.array([20, 16, 18], np.float32)
    base += tint * (1 - y)[..., None] * 1.4
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    # three layers of trunks, far (lighter, blurred) to near (black)
    for layer, (shade, blur, n, wmin, wmax) in enumerate(
            [(26, 6, 34, 6, 18), (14, 3, 20, 14, 34), (3, 0, 9, 30, 80)]):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for _ in range(n):
            x = rnd.uniform(-50, W + 50)
            w = rnd.uniform(wmin, wmax)
            lean = rnd.uniform(-25, 25)
            d.polygon([(x, -10), (x + w, -10), (x + w * 1.3 + lean, H), (x - w * 0.3 + lean, H)],
                      fill=(shade, shade + 2, shade + 3, 255))
            for _ in range(rnd.randint(1, 4)):  # bare branches
                by = rnd.uniform(0, H * 0.6)
                bl = rnd.uniform(60, 260) * rnd.choice([-1, 1])
                d.line([(x + w / 2, by), (x + w / 2 + bl, by - abs(bl) * rnd.uniform(.2, .7))],
                       fill=(shade, shade + 2, shade + 3, 255), width=max(2, int(w / 6)))
        if blur:
            lay = lay.filter(ImageFilter.GaussianBlur(blur))
        img.paste(lay, (0, 0), lay)
        if layer == 0:  # fog band between far and mid trees
            fog = Image.new("L", (W, H), 0)
            fd = ImageDraw.Draw(fog)
            fd.ellipse([-400, H * .55, W + 400, H * 1.25], fill=38)
            fog = fog.filter(ImageFilter.GaussianBlur(120))
            img = Image.composite(Image.new("RGB", (W, H), (70, 78, 80)), img, fog)
    # vignette
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = np.clip(1.15 - r * 0.75, 0.15, 1)[..., None]
    arr = np.asarray(img, np.float32) * v
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


def text_center(d, txt, font, cy, fill, spacing=14):
    bb = d.multiline_textbbox((0, 0), txt, font=font, align="center", spacing=spacing)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pos = ((W - bb[0] - bb[2]) / 2, cy - th / 2 - bb[1])
    d.multiline_text((pos[0] + 4, pos[1] + 4), txt, font=font, fill=(0, 0, 0), align="center", spacing=spacing)
    d.multiline_text(pos, txt, font=font, fill=fill, align="center", spacing=spacing)
    return th


def card(i, big, small, out):
    img = forest(1000 + i)
    d = ImageDraw.Draw(img)
    is_num = big.startswith("#")
    fbig = ImageFont.truetype(SERIF, 220 if is_num else (96 if "\n" in big else 120))
    fsm = ImageFont.truetype(SERIF_I, 54)
    red = (176, 24, 24)
    th = text_center(d, big, fbig, H * 0.40, red if is_num or i in (0, 8) else (225, 222, 214))
    sb = d.multiline_textbbox((0, 0), small, font=fsm, spacing=14)
    text_center(d, small, fsm, H * 0.40 + th / 2 + 60 + (sb[3] - sb[1]) / 2, (200, 198, 190))
    img.save(out)


if __name__ == "__main__":
    os.makedirs("frames", exist_ok=True)
    for i, (b, s) in enumerate(CARDS):
        card(i, b, s, f"frames/{i:02d}.png")
    print(len(CARDS), "cards")
