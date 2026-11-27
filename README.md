# 🔐 ID Verify AI

> **Notary Everyday × VillageHacks 2026 (ASU)**, built in 24 hours, then hardened afterwards.
> A four-level identity-document verification pipeline: **authenticity → extraction → cross-document matching → compliance**.

**Live demo:** https://kenkaneki132.github.io/Village-hackathon-2026/ (static demo mode with three synthetic scenarios)

![Python](https://img.shields.io/badge/FastAPI-Python-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-Vite-61DAFB?logo=react&logoColor=black)
![Claude](https://img.shields.io/badge/LLM-Claude%20Vision-D97757)
![PyTorch](https://img.shields.io/badge/local%20model-PyTorch-EE4C2C?logo=pytorch&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest%20%2B%20vitest-success)

## Why

Remote notarization and KYC depend on trusting an uploaded photo of an ID. Manual review is slow and inconsistent, and plain OCR misses tampering. ID Verify AI layers checks from *"can we read it?"* to *"does it look forged, does it match the other documents, and is it compliant?"* It shows reviewers **why** a document passed or failed, citing the relevant rules (NIST IAL2, MISMO, state notary law).

## Pipeline

| Stage | What runs | Output |
|---|---|---|
| **Local pre-screen** (optional) | MobileNetV3 tamper classifier (+ optional OCR, face match, liveness) | authenticity score; early-reject obvious forgeries before paying for an LLM call |
| **L1 Authenticity** | Claude Vision | font, format, security-feature, layout and barcode checks |
| **L2 Extraction** | Claude Vision | structured fields with per-field confidence |
| **L3 Cross-document** | Claude Vision | name/DOB/address comparison against a supporting document |
| **L4 Compliance** | Claude + server rules | expiration math done server-side with the real date, NIST IAL2 / MISMO / in-state flags, PROCEED / HOLD / REJECT |

## Run it on a new machine

**Requirements:** **Python 3.12** (what CI uses; 3.10+ should work) and **Node.js 20.19+ or 22.12+** (the frontend uses Vite 8). An `ANTHROPIC_API_KEY` is only needed for live `/verify` calls; everything else, including the tests, runs without it.

```bash
git clone https://github.com/kenkaneki132/Village-hackathon-2026.git
cd Village-hackathon-2026

# backend
cd backend
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # add ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000                   # GET /health shows what's configured

# frontend
cd frontend && npm ci && npm run dev                    # http://localhost:5173
```

No key? The server still boots: `/synthetic-test` works and `/verify` returns a clear 503. To run the frontend with no backend at all, use `VITE_DEMO_MODE=true npm run dev` (PowerShell: `$env:VITE_DEMO_MODE='true'; npm run dev`).

Tests: `cd backend && pip install -r requirements-dev.txt && python -m pytest -q` (the 3 model tests skip unless PyTorch and the trained weights are present), and `cd frontend && npm test`.

### Optional local models

```bash
pip install -r requirements-local.txt                    # torch, torchvision (+ OCR/face libs if you want them)
python training/make_tamper_dataset.py --n 800          # 1,600 synthetic genuine/tampered cards
python training/train_authenticity.py --epochs 14 --lr 5e-4
```

Each local stage loads independently. Missing dependencies or weights skip that stage (reported in `/health`) instead of crashing the API.

## The tamper detector (new)

The original code expected a ResNet-50 trained on KID34K, a research ID-card dataset that isn't freely downloadable, and the weights were never committed. I replaced it with a reproducible pipeline:

1. **Data:** `training/make_tamper_dataset.py` renders synthetic licenses (Faker + Pillow, with a synthetic portrait) and applies five realistic forgeries: **font swap**, **splice** from another card, **photo swap** with double-JPEG artifacts, **misaligned retyping** and **copy-move clone**. Both classes get the same augmentations (JPEG recompression, rotation, blur, lighting, glare), so the model can't shortcut on capture conditions.
2. **Model:** ImageNet-pretrained **MobileNetV3-Small** (6 MB) fine-tuned at 270×428 to keep text detail, with label smoothing and OneCycle LR.
3. **Results** (held-out 20% split, 320 images, 14 epochs on CPU): **73.8% accuracy**. Genuine cards are recognized 85% of the time; detection by tamper type: photo swap 87%, clone 59%, splice 58%, misalign 56%, font swap 54%. Subtle text edits are the hard cases, and higher input resolution or text-region crops are the obvious next step. Full numbers and the confusion matrix are in `weights/authenticity_metrics.json`.

> Trained only on synthetic cards, this is a **pre-screen demo, not a production fraud detector**. Real deployments need real (consented) data.

## Tests

```bash
cd backend  && pip install -r requirements-dev.txt && pytest -q   # API + generator + dataset; model tests run if torch + weights exist
cd frontend && npm test                                             # demo scenarios + API client (Vitest)
```

- **API:** health/config reporting, `/synthetic-test` without a key, 503 instead of a crash when the key is missing, 415/413/400 for bad uploads, mocked Claude happy path, expired IDs forced to REJECT, malformed model JSON → 502, a failing local stage doesn't break the request, low authenticity + spoof is rejected **before** calling Claude, expiry math, JSON fence parsing.
- **Training:** cross-platform fonts (regression), every tamper type changes the card, portraits stay inside the photo box, balanced dataset CLI, no import side effects, model output contract, and a held-out separation check.
- **Frontend:** scenario completeness, dates relative to today (the demo never goes stale), demo mode never touches the network, fallback when the backend is down, and server error details surfaced.

## Changelog (portfolio-upgrade)

- 🐛 **`/verify` crashed on every request:** `run_local_pipeline` was called but never imported, and `models/pipeline.py` imported a non-existent `compliance` module. Local stages are now optional and isolated.
- 🐛 The server **crashed at startup without an API key** (the Anthropic client was built at import). It's now created lazily.
- 🐛 Declared upload limits (types, 10 MB) were never enforced. Now 415 / 413 / 400.
- 🐛 `generate_test_ids.py` only looked for Linux font paths, so the "font_mismatch" fraud type was invisible on Windows and macOS. It created `synthetic_data/` on import, which is also fixed.
- ✨ Trained the missing authenticity model (above) with a reproducible data and training pipeline.
- ✨ Static demo mode with pass / warn / fail scenarios, so the app deploys to GitHub Pages with no backend.
- ✨ Configurable model and CORS via env, `.env.example`, `requirements-local.txt`, CI and a Pages workflow.

## Team & role

Built at VillageHacks '26. **My role:** <!-- e.g. backend pipeline, prompt design, synthetic data + tamper model -->
