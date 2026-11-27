"""
Local authenticity pre-screen: a small CNN that scores how likely an ID image is untampered.

Default weights: weights/authenticity_mobilenetv3.pt, trained by training/train_authenticity.py
on synthetic genuine/tampered cards. A legacy ResNet-50 checkpoint (weights/kid34k_resnet50.pth,
a raw state_dict) is still supported if you have one. Override with AUTH_WEIGHTS=/path/to/file.
"""

import io
import os
from pathlib import Path

import torch
from PIL import Image
from torchvision import models, transforms

WEIGHTS_DIR = Path(__file__).resolve().parents[1] / "weights"
DEFAULT_WEIGHTS = WEIGHTS_DIR / "authenticity_mobilenetv3.pt"
LEGACY_WEIGHTS = WEIGHTS_DIR / "kid34k_resnet50.pth"

_model = None
_transform = None
_meta = {}


def _load():
    global _model, _transform, _meta
    if _model is not None:
        return _model
    path = Path(os.getenv("AUTH_WEIGHTS", DEFAULT_WEIGHTS if DEFAULT_WEIGHTS.exists() else LEGACY_WEIGHTS))
    if not path.exists():
        raise FileNotFoundError(f"No authenticity weights at {path}. Run training/train_authenticity.py first.")
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    if isinstance(ckpt, dict) and "arch" in ckpt:
        if ckpt["arch"] != "mobilenet_v3_small":
            raise ValueError(f"Unsupported arch {ckpt['arch']}")
        m = models.mobilenet_v3_small()
        m.classifier[3] = torch.nn.Linear(m.classifier[3].in_features, 2)
        m.load_state_dict(ckpt["state_dict"])
        size, mean, std = tuple(ckpt["input_size"]), ckpt["mean"], ckpt["std"]
        _meta = {"arch": ckpt["arch"], "weights": path.name, "val_acc": ckpt.get("val_acc")}
    else:  # legacy raw ResNet-50 state_dict
        m = models.resnet50()
        m.fc = torch.nn.Linear(2048, 2)
        m.load_state_dict(ckpt)
        size, mean, std = (224, 224), [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
        _meta = {"arch": "resnet50", "weights": path.name}
    m.eval()
    _transform = transforms.Compose([transforms.Resize(size), transforms.ToTensor(), transforms.Normalize(mean, std)])
    _model = m
    return _model


def score_authenticity(img_bytes: bytes) -> dict:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    model = _load()
    with torch.no_grad():
        prob = torch.softmax(model(_transform(img).unsqueeze(0)), dim=1)[0][0].item()  # class 0 = genuine
    verdict = "PASS" if prob > 0.7 else "WARN" if prob > 0.4 else "FAIL"
    return {"score": round(prob, 3), "verdict": verdict, "model": _meta}
