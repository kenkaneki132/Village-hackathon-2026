"""Tests for the synthetic data generator, tamper dataset builder and the authenticity model.

Light tests need only Pillow + Faker. Model tests are skipped unless torch/torchvision are
installed (pip install -r requirements-local.txt) and weights exist.
"""

import io
import random
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "training"))

pytest.importorskip("PIL")
pytest.importorskip("faker")

import generate_test_ids as g  # noqa: E402
import make_tamper_dataset as mt  # noqa: E402


def test_find_font_returns_a_usable_font_on_any_os():
    for kind in ("regular", "bold", "mono", "serif"):
        f = g.find_font(kind, 15)
        assert f.getbbox("ABC123")[2] > 0


def test_font_mismatch_is_visible():
    """Regression: on Windows/macOS every font fell back to the same default, hiding this fraud type."""
    import os
    if not any(os.path.exists(f) for f in g.FONT_CANDIDATES["mono"]):
        pytest.skip("no monospace system font installed")
    reg, mono = g.find_font("regular", 15), g.find_font("mono", 15)
    text = "illiterate 1111"
    assert reg.getbbox(text)[2] != mono.getbbox(text)[2]


@pytest.mark.parametrize("fraud", ["none", "expired", "expiring_soon", "wrong_format", "font_mismatch", "glare"])
def test_make_id_and_draw_card(fraud):
    data = g.make_id(fraud)
    img = g.draw_id_card(data, fraud)
    assert img.size == (856, 540)
    assert data["label"] == ("genuine" if fraud == "none" else f"fraud_{fraud}")


def test_expired_and_expiring_dates():
    from datetime import date
    assert date.fromisoformat(g.make_id("expired")["expiration_iso"]) < date.today()
    exp = date.fromisoformat(g.make_id("expiring_soon")["expiration_iso"])
    assert 0 < (exp - date.today()).days < 30


def test_import_has_no_side_effects(monkeypatch):
    """Importing the generator must not create synthetic_data/ (it used to mkdir at import time)."""
    import importlib
    calls = []
    monkeypatch.setattr(Path, "mkdir", lambda self, *a, **k: calls.append(self))
    importlib.reload(g)
    assert calls == []


@pytest.mark.parametrize("op", mt.TAMPERS)
def test_each_tamper_changes_the_card(op):
    rng = random.Random(1)
    base = mt.render_card(random.Random(5))
    tampered = mt.OPS[op](base.copy(), rng)
    assert tampered.size == base.size
    from PIL import ImageChops
    assert ImageChops.difference(base, tampered).getbbox() is not None, f"{op} produced an identical image"


def test_portrait_stays_inside_photo_box():
    """Regression: shoulders used to spill outside the photo frame."""
    from PIL import Image
    img = Image.new("RGB", (856, 540), "white")
    mt.draw_face(img, random.Random(3))
    for x, y in [(10, 300), (200, 150), (100, 320)]:     # just outside the (20,85)-(195,295) box
        assert img.getpixel((x, y)) == (255, 255, 255)


def test_augment_output_size_and_format():
    out = mt.augment(mt.render_card(random.Random(2)), random.Random(2))
    assert out.size == mt.OUT_SIZE and out.mode == "RGB"


def test_dataset_cli_writes_balanced_classes(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x", "--n", "5", "--out", str(tmp_path)])
    mt.main()
    assert len(list((tmp_path / "genuine").glob("*.jpg"))) == 5
    assert len(list((tmp_path / "tampered").glob("*.jpg"))) == 5
    assert (tmp_path / "manifest.json").exists()


# ── model tests (optional) ────────────────────────────────────────────────────

WEIGHTS = BACKEND / "weights" / "authenticity_mobilenetv3.pt"


@pytest.fixture(scope="module")
def auth():
    pytest.importorskip("torch")
    pytest.importorskip("torchvision")
    if not WEIGHTS.exists():
        pytest.skip("weights not trained: run training/train_authenticity.py")
    import models.authenticity as a
    return a


def _jpeg(img):
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def test_authenticity_output_contract(auth):
    r = auth.score_authenticity(_jpeg(mt.augment(mt.render_card(random.Random(11)), random.Random(11))))
    assert 0.0 <= r["score"] <= 1.0
    assert r["verdict"] in {"PASS", "WARN", "FAIL"}
    assert r["model"]["arch"] == "mobilenet_v3_small"


def test_model_separates_fresh_genuine_and_tampered_samples(auth):
    """Held-out samples generated with a seed never used in training.

    Ranking check (AUC) rather than a fixed gap between mean scores, which swung between ~0.16 and ~0.29
    across samples for this ~74%-accurate model. With Faker seeded the sample is reproducible; the shipped
    weights score AUC 0.69 on it (0.74-0.86 on other 60 + 60 samples). 0.65 still rules out a model that has
    stopped separating the classes (chance is 0.5).
    """
    rng = random.Random(987654)
    g.fake.seed_instance(987654)                 # card text comes from Faker; seed it so the sample is reproducible
    n = 40
    genuine = [auth.score_authenticity(_jpeg(mt.augment(mt.render_card(rng), rng)))["score"] for _ in range(n)]
    tampered = [auth.score_authenticity(_jpeg(mt.augment(mt.OPS[mt.TAMPERS[i % 5]](mt.render_card(rng), rng), rng)))["score"]
                for i in range(n)]
    auc = sum((s > t) + 0.5 * (s == t) for s in genuine for t in tampered) / (n * n)
    assert auc >= 0.65, f"AUC {auc:.3f}"
    assert sum(genuine) / n > sum(tampered) / n


def test_pipeline_reports_stage_availability():
    pytest.importorskip("torch")
    import models.pipeline as p
    assert set(p.AVAILABLE) == {"authenticity", "ocr", "face_match", "liveness"}
    assert p.AVAILABLE["authenticity"] == "ok"   # torch is installed, so this stage must load
