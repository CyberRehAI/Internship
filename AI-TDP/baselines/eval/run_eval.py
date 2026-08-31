"""
Evaluate baseline embeddings with coarse-label protocol.

Usage (from AI-TDP root):
  python -m baselines.eval.run_eval --model-id lstm_ae_net
  python -m baselines.eval.run_eval --compare-all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.eval.metrics import evaluate_embeddings
from baselines.train.common import DEFAULT_OUTPUTS

EVAL_DIR = DEFAULT_OUTPUTS / "evaluation"


def _write_comparison(rows: List[Dict], out_path: Path) -> None:
    lines = [
        "# Baseline comparison",
        "",
        "Coarse labels: Val = normal, Test = attack-period. "
        "Threshold = Val score quantile. ROC/PR on Val∪Test.",
        "",
        "| model_id | quantile | threshold | Val FPR | Test detection | F1 (V∪T) | ROC-AUC | PR-AUC |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        vu = r["val_union_test"]
        lines.append(
            f"| {r.get('model_id')} | {r['quantile']} | {r['threshold']:.6g} | "
            f"{r['val_fpr']:.4f} | {r['test_detection_rate']:.4f} | "
            f"{vu['f1']:.4f} | {vu['roc_auc']:.4f} | {vu['pr_auc']:.4f} |"
        )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate baseline window scores")
    p.add_argument("--model-id", type=str, default=None, help="e.g. lstm_ae_net")
    p.add_argument(
        "--embeddings-dir",
        type=Path,
        default=None,
        help="Override path to embeddings/ (contains val.npz, test.npz)",
    )
    p.add_argument("--outputs-root", type=Path, default=DEFAULT_OUTPUTS)
    p.add_argument("--eval-dir", type=Path, default=EVAL_DIR)
    p.add_argument("--quantile", type=float, default=0.95)
    p.add_argument(
        "--compare-all",
        action="store_true",
        help="Evaluate every subdirectory of outputs-root that has embeddings/",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    eval_dir = Path(args.eval_dir)
    eval_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Dict] = []

    if args.compare_all:
        root = Path(args.outputs_root)
        model_dirs = sorted(
            d for d in root.iterdir() if d.is_dir() and (d / "embeddings" / "val.npz").is_file()
        )
        if not model_dirs:
            print(f"ERROR: no model embeddings under {root}", file=sys.stderr)
            return 1
        for d in model_dirs:
            mid = d.name
            result = evaluate_embeddings(
                d / "embeddings", quantile=args.quantile, model_id=mid
            )
            out = eval_dir / f"{mid}.json"
            out.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"Wrote {out}")
            rows.append(result)
    else:
        if args.embeddings_dir is not None:
            emb = Path(args.embeddings_dir)
            mid = args.model_id or emb.parent.name
        elif args.model_id:
            mid = args.model_id
            emb = Path(args.outputs_root) / mid / "embeddings"
        else:
            print("ERROR: pass --model-id, --embeddings-dir, or --compare-all", file=sys.stderr)
            return 1
        result = evaluate_embeddings(emb, quantile=args.quantile, model_id=mid)
        out = eval_dir / f"{mid}.json"
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        print(f"Wrote {out}")
        rows.append(result)

    comparison = eval_dir / "comparison.md"
    # Merge with existing JSON rows if compare-all or single
    if args.compare_all:
        _write_comparison(rows, comparison)
    else:
        # Rebuild table from all json files in eval_dir
        all_rows = []
        for jp in sorted(eval_dir.glob("*.json")):
            all_rows.append(json.loads(jp.read_text(encoding="utf-8")))
        if all_rows:
            _write_comparison(all_rows, comparison)
    print(f"Wrote {comparison}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
