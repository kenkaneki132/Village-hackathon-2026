"""
Local pre-screening stages (no API cost). Each stage is optional: if its dependencies or
weights are missing, it is skipped and reported instead of breaking the whole pipeline.
"""

import importlib


def _optional(module: str, fn: str):
    try:
        return getattr(importlib.import_module(module), fn), None
    except Exception as e:  # ImportError, missing weights, etc.
        return None, f"{type(e).__name__}: {e}"


score_authenticity, AUTH_ERR = _optional("models.authenticity", "score_authenticity")
extract_id_fields, OCR_ERR = _optional("models.ocr_extractor", "extract_id_fields")
match_faces, FACE_ERR = _optional("models.face_match", "match_faces")
passive_liveness, LIVE_ERR = _optional("models.liveness", "passive_liveness")

AVAILABLE = {
    "authenticity": AUTH_ERR or "ok",
    "ocr": OCR_ERR or "ok",
    "face_match": FACE_ERR or "ok",
    "liveness": LIVE_ERR or "ok",
}

if all(f is None for f in (score_authenticity, extract_id_fields, match_faces, passive_liveness)):
    raise ImportError(f"No local model stages available: {AVAILABLE}")


def _run(fn, *args):
    if fn is None:
        return None
    try:
        return fn(*args)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


async def run_local_pipeline(id_bytes: bytes, selfie_bytes: bytes | None = None) -> dict:
    """Runs stages 1-4 locally."""
    return {
        "local": {
            "authenticity": _run(score_authenticity, id_bytes),
            "ocr_fields": _run(extract_id_fields, id_bytes),
            "face_match": _run(match_faces, id_bytes, selfie_bytes) if selfie_bytes else None,
            "liveness": _run(passive_liveness, selfie_bytes) if selfie_bytes else None,
            "stages": AVAILABLE,
        }
    }
