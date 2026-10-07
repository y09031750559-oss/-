"""YouTube thumbnail (1280x720) from the tent scene."""
import sys
sys.argv = ["x", "info"]
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import episode as E

s = E.Scene(0, E.sc_tent, fog=0.2, fog_col=(90, 100, 120), bars=False,
            extras=[E.ex_shadow(-10, -5, 99)])
fr = E.render_scene(s, 0.0)
fr *= E.vignette()
img = Image.fromarray((fr.clip(0, 1) * 255).astype(np.uint8)).resize((1280, 720), Image.LANCZOS)
img = Image.eval(img, lambda v: min(255, int(v * 1.35)))  # thumbnails need to read on small screens
d = ImageDraw.Draw(img)
big = E.font(E.SERIF_B, 118)
small = E.font(E.SERIF_B, 54)
for txt, f, y, col in (("DON'T", big, 40, E.RED), ("ANSWER.", big, 160, E.BONE)):
    d.text((54 + 5, y + 5), txt, font=f, fill=(0, 0, 0))
    d.text((54, y), txt, font=f, fill=col)
d.text((58, 610), "“It’s me. Open the tent.”", font=E.font(E.SERIF_I, 50), fill=(225, 225, 225))
img.save("thumbnail.png")
