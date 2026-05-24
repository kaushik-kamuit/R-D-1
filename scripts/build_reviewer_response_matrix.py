from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
RESULTS = ROOT / "results"


def _evidence_type(action: str, response: str) -> str:
    text = f"{action} {response}".lower()
    if "reran" in text or "diagnostic" in text or "ablation" in text or "sensitivity" in text or "baseline" in text:
        return "new_experiment_or_diagnostic"
    if "table" in text or "artifact" in text or "csv" in text or "script" in text:
        return "new_table_or_reproducibility_artifact"
    if "moderated" in text or "reframed" in text or "clarified" in text or "renamed" in text:
        return "manuscript_reframing_or_limitation"
    if "verified" in text:
        return "verification"
    return "manuscript_revision"


def _extract_refs(action: str) -> str:
    refs = []
    refs.extend(re.findall(r"`([^`]+)`", action))
    refs.extend(re.findall(r"(results/[A-Za-z0-9_\-./]+\.csv)", action))
    refs.extend(re.findall(r"(scripts/[A-Za-z0-9_\-./]+\.py)", action))
    cleaned: list[str] = []
    for ref in refs:
        if ref not in cleaned:
            cleaned.append(ref)
    return "; ".join(cleaned)


def main() -> None:
    draft = (PAPER / "response_to_reviewers_draft.md").read_text(encoding="utf-8")
    reviewer = ""
    rows: list[dict[str, str]] = []
    blocks = re.split(r"(?=^## Reviewer |\n### Comment )", draft, flags=re.MULTILINE)
    for block in blocks:
        reviewer_match = re.match(r"## Reviewer (\d+)", block.strip())
        if reviewer_match:
            reviewer = reviewer_match.group(1)
            continue
        comment_match = re.match(r"### Comment (\d+)\n", block.strip())
        if not comment_match or not reviewer:
            continue
        comment_id = comment_match.group(1)
        concern = re.search(r"Concern:\s*(.*?)(?:\n\nResponse:)", block, flags=re.DOTALL)
        response = re.search(r"Response:\s*(.*?)(?:\n\nAction:)", block, flags=re.DOTALL)
        action = re.search(r"Action:\s*(.*?)(?:\n\n###|\Z)", block, flags=re.DOTALL)
        concern_text = " ".join((concern.group(1) if concern else "").split())
        response_text = " ".join((response.group(1) if response else "").split())
        action_text = " ".join((action.group(1) if action else "").split())
        rows.append(
            {
                "reviewer": reviewer,
                "comment": comment_id,
                "concern": concern_text,
                "evidence_type": _evidence_type(action_text, response_text),
                "response_summary": response_text,
                "action_taken": action_text,
                "referenced_artifacts": _extract_refs(action_text),
                "status": "addressed",
            }
        )

    out = RESULTS / "reviewer_response_matrix.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Wrote {out.relative_to(ROOT)} with {len(rows)} reviewer-comment rows")


if __name__ == "__main__":
    main()
