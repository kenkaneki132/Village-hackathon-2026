"""
Build a genuine-vs-tampered ID image dataset from the synthetic ID generator.

Every image is a SYNTHETIC test document (Faker data, drawn with Pillow). No real IDs are used.

Tampering types (applied to the "tampered" class only):
  font_swap    a field value is erased and re-typed in a different font/size
  splice       a field region is pasted in from a different card (seams, color shift)
  photo_swap   the portrait is replaced by a recompressed, slightly misaligned photo
  misalign     a field value is re-typed a few pixels off the layout grid in a near-identical color
  clone        a region is copy-moved within the same card (classic copy-move forgery)

Shared augmentations (applied to BOTH classes so the model can't shortcut on them):
  JPEG recompression, small rotation, blur, brightness/contrast jitter, glare spots, crop jitter.

Usage:
  python training/make_tamper_dataset.py --n 800 --out training/data
"""

import argparse
import io
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate_test_ids as g  # noqa: E402

OUT_SIZE = (428, 270)        # half resolution keeps CPU training fast
VALUE_X = 215
VALUE_YS = [108, 152, 196, 240, 284, 328, 372]   # y of each left-column field value in draw_id_card
TAMPERS = ["font_swap", "splice", "photo_swap", "misalign", "clone"]

SKIN = ["#f1c27d", "#e0ac69", "#c68642", "#8d5524", "#ffdbac", "#d4a373"]
HAIR = ["#2c1b10", "#4b2e1e", "#a67b5b", "#e6c98f", "#111111", "#7f7f7f"]
SHIRT = ["#34495e", "#2e86c1", "#7d3c98", "#1e8449", "#922b21", "#566573"]


def draw_face(img: Image.Image, rng: random.Random, box=(20, 85, 195, 295)) -> None:
    """Draw a simple synthetic portrait, clipped to the photo box."""
    bx0, by0, bx1, by1 = box
    portrait = Image.new("RGB", (bx1 - bx0 - 4, by1 - by0 - 4), rng.choice(["#dfe6ec", "#cfd8dc", "#e8eaf0", "#d6dbdf"]))
    _draw_face_on(portrait, rng)
    img.paste(portrait, (bx0 + 2, by0 + 2))


def _draw_face_on(canvas: Image.Image, rng: random.Random) -> None:
    x0, y0, x1, y1 = 0, 0, canvas.width, canvas.height
    d = ImageDraw.Draw(canvas)
    cx = (x0 + x1) // 2 + rng.randint(-8, 8)
    head_w, head_h = rng.randint(58, 72), rng.randint(74, 90)
    top = y0 + rng.randint(24, 38)
    d.ellipse([(cx - 70, y1 - 60), (cx + 70, y1 + 60)], fill=rng.choice(SHIRT))           # shoulders
    d.rectangle([(cx - 14, top + head_h - 10), (cx + 14, top + head_h + 20)], fill=rng.choice(SKIN))  # neck
    skin = rng.choice(SKIN)
    d.ellipse([(cx - head_w // 2, top), (cx + head_w // 2, top + head_h)], fill=skin)    # head
    d.chord([(cx - head_w // 2 - 3, top - 6), (cx + head_w // 2 + 3, top + head_h // 2)], 180, 360, fill=rng.choice(HAIR))
    ey = top + head_h // 2
    for ex in (cx - 13, cx + 13):
        d.ellipse([(ex - 4, ey - 3), (ex + 4, ey + 3)], fill="#222")
    d.arc([(cx - 12, ey + 12), (cx + 12, ey + 26)], 20, 160, fill="#7b3f3f", width=2)


def render_card(rng: random.Random, fraud_type: str = "none") -> Image.Image:
    random.seed(rng.random())          # generate_test_ids uses the global RNG
    data = g.make_id(fraud_type=fraud_type)
    img = g.draw_id_card(data, fraud_type="none")   # visual tampering is added separately
    draw_face(img, rng)
    return img


def bg_at(img: Image.Image, x: int, y: int):
    return img.getpixel((min(x, img.width - 1), min(y, img.height - 1)))


def random_value(rng: random.Random) -> str:
    return rng.choice([
        f"{rng.randint(1, 12):02d}/{rng.randint(1, 28):02d}/{rng.randint(1950, 2006)}",
        f"{rng.randint(1, 12):02d}/{rng.randint(1, 28):02d}/{rng.randint(2027, 2033)}",
        f"D{rng.randint(10_000_000, 99_999_999)}",
        g.fake.last_name().upper() + ", " + g.fake.first_name().upper(),
    ])


# ── tampering operations ──────────────────────────────────────────────────────

def t_font_swap(img, rng):
    vy = rng.choice(VALUE_YS[:6])
    d = ImageDraw.Draw(img)
    d.rectangle([(VALUE_X - 2, vy - 1), (530, vy + 21)], fill=bg_at(img, 528, vy + 8))
    font = g.find_font(rng.choice(["mono", "serif", "bold"]), rng.randint(14, 17))
    d.text((VALUE_X + rng.randint(-1, 2), vy + rng.randint(-1, 1)), random_value(rng), font=font, fill="#1a1a2e")
    return img


def t_splice(img, rng):
    donor = render_card(rng)
    vy = rng.choice(VALUE_YS)
    w = rng.randint(140, 300)
    patch = donor.crop((VALUE_X - 4, vy - 4, VALUE_X - 4 + w, vy + 24))
    patch = ImageEnhance.Brightness(patch).enhance(rng.uniform(0.9, 1.1))
    if rng.random() < 0.5:
        patch = patch.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.9)))
    img.paste(patch, (VALUE_X - 4 + rng.randint(-3, 3), vy - 4 + rng.randint(-2, 2)))
    return img


def t_photo_swap(img, rng):
    other = Image.new("RGB", (175, 210), "#ddd")
    draw_face(other, rng, box=(0, 0, 175, 210))
    buf = io.BytesIO()
    other.save(buf, "JPEG", quality=rng.randint(25, 55))   # double-compression artifacts
    other = Image.open(buf).convert("RGB")
    scale = rng.uniform(0.92, 1.06)
    other = other.resize((int(175 * scale), int(210 * scale)))
    img.paste(other, (20 + rng.randint(-6, 8), 85 + rng.randint(-6, 8)))
    return img


def t_misalign(img, rng):
    vy = rng.choice(VALUE_YS[:6])
    d = ImageDraw.Draw(img)
    d.rectangle([(VALUE_X - 2, vy - 1), (530, vy + 21)], fill=bg_at(img, 528, vy + 8))
    dx, dy = rng.choice([-1, 1]) * rng.randint(4, 12), rng.choice([-1, 1]) * rng.randint(2, 6)
    d.text((VALUE_X + dx, vy + dy), random_value(rng), font=g.find_font("regular", rng.choice([14, 15, 16])),
           fill=rng.choice(["#2b2b3d", "#101020", "#1a1a2e", "#333344"]))
    return img


def t_clone(img, rng):
    sy, ty = rng.sample(VALUE_YS, 2)
    w = rng.randint(60, 180)
    sx = VALUE_X + rng.randint(0, 120)
    patch = img.crop((sx, sy - 2, sx + w, sy + 22))
    img.paste(patch, (VALUE_X + rng.randint(0, 160), ty - 2))
    return img


OPS = {"font_swap": t_font_swap, "splice": t_splice, "photo_swap": t_photo_swap, "misalign": t_misalign, "clone": t_clone}


# ── shared augmentations ─────────────────────────────────────────────────────

def augment(img: Image.Image, rng: random.Random) -> Image.Image:
    if rng.random() < 0.35:   # glare spots (an imaging condition, not fraud)
        over = Image.new("L", img.size, 0)
        od = ImageDraw.Draw(over)
        for _ in range(rng.randint(1, 3)):
            gx, gy, r = rng.randint(0, img.width), rng.randint(0, img.height), rng.randint(30, 90)
            od.ellipse([(gx - r, gy - r), (gx + r, gy + r)], fill=rng.randint(60, 140))
        over = over.filter(ImageFilter.GaussianBlur(25))
        img = Image.composite(Image.new("RGB", img.size, "white"), img, over)
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.85, 1.15))
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.85, 1.15))
    if rng.random() < 0.6:
        img = img.rotate(rng.uniform(-3, 3), resample=Image.BICUBIC, expand=False, fillcolor=(40, 40, 40))
    if rng.random() < 0.4:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 0.9)))
    l, t = rng.randint(0, 12), rng.randint(0, 8)
    img = img.crop((l, t, img.width - rng.randint(0, 12), img.height - rng.randint(0, 8)))
    img = img.resize(OUT_SIZE, Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=rng.randint(60, 95))
    return Image.open(buf).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=800, help="images per class")
    ap.add_argument("--out", default=str(Path(__file__).parent / "data"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    g.fake.seed_instance(args.seed)
    out = Path(args.out)
    for c in ("genuine", "tampered"):
        (out / c).mkdir(parents=True, exist_ok=True)
    manifest = []
    for i in range(args.n):
        # genuine: rendered with any of the generator's non-visual "fraud" types so the
        # model doesn't confuse expired/expiring cards (a compliance issue) with tampering
        gen = augment(render_card(rng, rng.choice(["none", "none", "expired", "expiring_soon"])), rng)
        gp = out / "genuine" / f"g_{i:04d}.jpg"
        gen.save(gp, quality=95)
        tt = TAMPERS[i % len(TAMPERS)]
        tam = augment(OPS[tt](render_card(rng), rng), rng)
        tp = out / "tampered" / f"t_{i:04d}_{tt}.jpg"
        tam.save(tp, quality=95)
        manifest += [{"file": str(gp.relative_to(out)), "label": "genuine"},
                     {"file": str(tp.relative_to(out)), "label": "tampered", "tamper": tt}]
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{args.n} pairs")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"Done: {len(manifest)} images -> {out}")


if __name__ == "__main__":
    main()
