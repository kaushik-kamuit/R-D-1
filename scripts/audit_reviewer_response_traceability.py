from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
RESULTS = ROOT / "results"


def _resolve_ref(ref: str, manuscript: str) -> tuple[str, bool, str]:
    ref = ref.strip()
    if not ref:
        return "", True, "empty"
    if ref.startswith(("tab:", "fig:", "alg:")):
        return "manuscript_label", f"\\label{{{ref}}}" in manuscript, ref
    if ref.startswith(("results/", "scripts/", "paper/")):
        path = ROOT / ref
        return "file", path.exists(), ref
    if ref.endswith((".csv", ".json", ".py", ".md", ".tex", ".pdf")):
        path = ROOT / ref
        return "file", path.exists(), ref
    return "text_reference", True, ref


def main() -> None:
    matrix_path = RESULTS / "reviewer_response_matrix.csv"
    if not matrix_path.exists():
        raise SystemExit(f"Missing {matrix_path.relative_to(ROOT)}")
    matrix = pd.read_csv(matrix_path).fillna("")
    manuscript = (PAPER / "ieee_submission.tex").read_text(encoding="utf-8")

    rows: list[dict[str, object]] = []
    for _, row in matrix.iterrows():
        refs = [part.strip() for part in str(row["referenced_artifacts"]).split(";") if part.strip()]
        if not refs:
            rows.append(
                {
                    "reviewer": row["reviewer"],
                    "comment": row["comment"],
                    "reference": "",
                    "reference_type": "none",
                    "exists_or_resolves": True,
                    "resolved_target": "",
                    "note": "No explicit artifact reference; action is manuscript-only or prose-only.",
                }
            )
            continue
        for ref in refs:
            ref_type, ok, target = _resolve_ref(ref, manuscript)
            rows.append(
                {
                    "reviewer": row["reviewer"],
                    "comment": row["comment"],
                    "reference": ref,
                    "reference_type": ref_type,
                    "exists_or_resolves": ok,
                    "resolved_target": target,
                    "note": "OK" if ok else "Missing referenced response artifact or manuscript label.",
                }
            )

    out = RESULTS / "reviewer_response_traceability.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    missing = [r for r in rows if not bool(r["exists_or_resolves"])]
    print(f"Wrote {out.relative_to(ROOT)} with {len(rows)} traceability rows")
    if missing:
        for item in missing:
            print(f"Missing: R{item['reviewer']} C{item['comment']} -> {item['reference']}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
