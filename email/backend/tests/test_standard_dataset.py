"""Regression floors for the standard 90-email benchmark (tests/eval_standard.py).

These floors sit a few points below the rule-based engine's measured baseline (see tests/standard_results.md) so a
regression fails CI. They are NOT targets: raise them as the engine (or an LLM provider) improves. Do not tune the
engine to this dataset - it is the shared yardstick every intern is scored on."""
import json
import os
from collections import Counter

import pytest

import eval_standard  # tests/ is on sys.path (pytest prepend import mode)

FLOORS = {
    "category": 60.0, "priority_within_one_level": 85.0, "sentiment": 40.0, "reply_required": 80.0,
    "action_required": 70.0, "summary_present": 100.0, "extraction_fields": 78.0, "deadlines": 70.0,
    "action_items_found": 80.0,
}


def test_dataset_shape():
    with open(eval_standard.DATASET, encoding="utf-8") as fh:
        data = json.load(fh)
    counts = Counter(d["expected"]["category"] for d in data)
    assert len(data) == 90 and set(counts.values()) == {10} and len(counts) == 9
    for d in data:
        assert {"category", "priority", "sentiment", "reply_required", "action_required", "extracted", "deadlines",
                "action_items", "reply_keywords"} <= set(d["expected"])


@pytest.mark.skipif(os.getenv("SKIP_STANDARD_EVAL") == "1", reason="explicitly skipped")
def test_standard_dataset_regression_floors():
    result = eval_standard.evaluate()
    for metric, floor in FLOORS.items():
        pct = result["metrics"][metric]["pct"]
        assert pct is not None and pct >= floor, f"{metric} fell to {pct}% (floor {floor}%)"
