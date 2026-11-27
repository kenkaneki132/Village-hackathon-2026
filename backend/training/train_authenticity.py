"""
Fine-tune an ImageNet-pretrained MobileNetV3-Small to classify synthetic ID images as
genuine vs. tampered. Produces the weights used by models/authenticity.py.

  python training/make_tamper_dataset.py --n 800
  python training/train_authenticity.py --epochs 6

Outputs:
  weights/authenticity_mobilenetv3.pt      state_dict + metadata (~6 MB)
  weights/authenticity_metrics.json        validation metrics per tamper type

Caveat: trained only on synthetic cards. It demonstrates the pre-screening stage of the
pipeline; it is NOT a production fraud detector for real government IDs.
"""

import argparse
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms

ROOT = Path(__file__).resolve().parents[1]
INPUT_SIZE = (270, 428)   # H, W (keeps the card aspect ratio and fine text detail)
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def build_model(pretrained: bool = True) -> nn.Module:
    weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    m = models.mobilenet_v3_small(weights=weights)
    m.classifier[3] = nn.Linear(m.classifier[3].in_features, 2)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(Path(__file__).parent / "data"))
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "weights" / "authenticity_mobilenetv3.pt"))
    args = ap.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(max(1, os.cpu_count() or 1))

    train_tf = transforms.Compose([
        transforms.Resize(INPUT_SIZE),
        transforms.RandomApply([transforms.ColorJitter(0.15, 0.15, 0.1, 0.02)], p=0.5),
        transforms.RandomAffine(degrees=2, translate=(0.02, 0.02), scale=(0.97, 1.03)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    eval_tf = transforms.Compose([transforms.Resize(INPUT_SIZE), transforms.ToTensor(), transforms.Normalize(MEAN, STD)])

    full_train = datasets.ImageFolder(args.data, transform=train_tf)
    full_eval = datasets.ImageFolder(args.data, transform=eval_tf)
    assert full_train.classes == ["genuine", "tampered"], full_train.classes

    idx = list(range(len(full_train)))
    random.shuffle(idx)
    n_val = int(len(idx) * 0.2)
    val_idx, train_idx = idx[:n_val], idx[n_val:]
    train_dl = DataLoader(Subset(full_train, train_idx), batch_size=args.batch, shuffle=True, num_workers=0)
    val_dl = DataLoader(Subset(full_eval, val_idx), batch_size=64, shuffle=False, num_workers=0)

    model = build_model(pretrained=True)
    head = list(model.classifier.parameters())
    head_ids = {id(p) for p in head}
    body = [p for p in model.parameters() if id(p) not in head_ids]
    opt = torch.optim.AdamW([{"params": body, "lr": args.lr * 0.3}, {"params": head, "lr": args.lr}], weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[args.lr * 0.3, args.lr],
                                                steps_per_epoch=len(train_dl), epochs=args.epochs)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)

    def evaluate():
        model.eval()
        correct = total = 0
        per_type = defaultdict(lambda: [0, 0])
        conf = [[0, 0], [0, 0]]
        with torch.no_grad():
            pos = 0
            for x, y in val_dl:
                pred = model(x).argmax(1)
                for i in range(len(y)):
                    path = full_eval.samples[val_idx[pos + i]][0]
                    t = "genuine" if y[i] == 0 else Path(path).stem.split("_", 2)[-1]
                    per_type[t][0] += int(pred[i] == y[i])
                    per_type[t][1] += 1
                    conf[int(y[i])][int(pred[i])] += 1
                pos += len(y)
                correct += (pred == y).sum().item()
                total += len(y)
        return correct / total, {k: round(a / b, 3) for k, (a, b) in sorted(per_type.items())}, conf

    print(f"train {len(train_idx)}  val {len(val_idx)}  device cpu  threads {torch.get_num_threads()}")
    best, history = 0.0, []
    for ep in range(1, args.epochs + 1):
        model.train()
        t0, run_loss, n = time.time(), 0.0, 0
        for x, y in train_dl:
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            sched.step()
            run_loss += loss.item() * len(y)
            n += len(y)
        acc, per_type, conf = evaluate()
        history.append({"epoch": ep, "train_loss": round(run_loss / n, 4), "val_acc": round(acc, 4)})
        print(f"epoch {ep}/{args.epochs}  loss {run_loss / n:.4f}  val_acc {acc:.3f}  {per_type}  ({time.time() - t0:.0f}s)")
        if acc >= best:
            best = acc
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            torch.save({"arch": "mobilenet_v3_small", "classes": ["genuine", "tampered"], "input_size": list(INPUT_SIZE),
                        "mean": MEAN, "std": STD, "state_dict": model.state_dict(),
                        "val_acc": round(acc, 4), "trained_on": "synthetic IDs (training/make_tamper_dataset.py)"}, args.out)
            metrics = {"val_accuracy": round(acc, 4), "per_type_accuracy": per_type,
                       "confusion_matrix": {"rows=true [genuine, tampered]": conf}, "history": history,
                       "train_size": len(train_idx), "val_size": len(val_idx)}
            Path(args.out).with_name("authenticity_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"Done: best val_acc {best:.3f} -> {args.out}")


if __name__ == "__main__":
    main()
