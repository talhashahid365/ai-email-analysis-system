"""Scores the AI engine against datasets/standard_test_dataset.json (90 emails, spec §26/§27).

    cd backend && python tests/eval_standard.py          # prints a report, writes tests/standard_results.{json,md}

Uses whatever provider is configured (LLM if a key is set, otherwise the rule-based engine), so run it once per
provider and keep the numbers honest. The dataset is never used to tune the engine."""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
DATASET = os.path.join(os.path.dirname(HERE), "datasets", "standard_test_dataset.json")
PRIORITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _norm(v) -> str:
    return re.sub(r"[\s#,]", "", str(v or "")).lower()


def _match(expected, actual) -> bool:
    e, a = _norm(expected), _norm(actual)
    return bool(e and a and (e in a or a in e))


def evaluate(dataset_path: str = DATASET) -> dict:
    from app.services import ai_engine, smart_reply
    with open(dataset_path, encoding="utf-8") as fh:
        data = json.load(fh)

    tally = defaultdict(lambda: [0, 0])  # metric -> [correct, total]
    per_category = defaultdict(lambda: [0, 0])
    confusion = defaultdict(int)
    failures = []

    def score(metric, ok):
        tally[metric][1] += 1
        tally[metric][0] += 1 if ok else 0
        return ok

    for item in data:
        exp = item["expected"]
        ref = datetime.fromisoformat(item["received_at"])
        res, _meta = ai_engine.analyze_email(item["subject"], item["body_plain"], item["sender_email"],
                                             item["sender_name"], reference=ref)
        ok_cat = score("category", res["category"] == exp["category"])
        per_category[exp["category"]][1] += 1
        per_category[exp["category"]][0] += 1 if ok_cat else 0
        if not ok_cat:
            confusion[(exp["category"], res["category"])] += 1
            failures.append(f"#{item['id']} category: expected {exp['category']}, got {res['category']} - {item['subject']}")
        score("priority_exact", res["priority"] == exp["priority"])
        score("priority_within_one_level", abs(PRIORITY_RANK[res["priority"]] - PRIORITY_RANK[exp["priority"]]) <= 1)
        score("sentiment", res["sentiment"] == exp["sentiment"])
        score("reply_required", bool(res["reply_required"]) == exp["reply_required"])
        score("action_required", bool(res["action_required"]) == exp["action_required"])
        score("summary_present", bool(res.get("short_summary")) and bool(res.get("detailed_summary")))

        info = res.get("extracted_info") or {}
        for field, value in exp["extracted"].items():
            score("extraction_fields", _match(value, info.get(field)))

        found_dates = {d["due_date"] for d in res.get("deadlines", [])} | {a.get("due_date") for a in res.get("action_items", [])}
        for d in exp["deadlines"]:
            score("deadlines", d["due_date"] in found_dates)

        if exp["action_required"]:
            score("action_items_found", len(res.get("action_items", [])) > 0)

        if exp["reply_keywords"]:
            reply = smart_reply.generate_heuristic_reply("Professional", res["category"], item["sender_name"],
                                                         item["subject"], info).lower()
            score("reply_mentions_key_terms", all(k.lower() in reply for k in exp["reply_keywords"]))

    metrics = {k: {"correct": c, "total": t, "pct": round(100.0 * c / t, 1) if t else None} for k, (c, t) in tally.items()}
    return {"emails": len(data), "metrics": metrics,
            "category_by_class": {k: {"correct": c, "total": t} for k, (c, t) in per_category.items()},
            "top_confusions": sorted(({"expected": e, "got": g, "count": n} for (e, g), n in confusion.items()),
                                     key=lambda x: -x["count"])[:10],
            "failures_sample": failures[:25]}


def to_markdown(r: dict) -> str:
    lines = [f"# Standard dataset results ({r['emails']} emails)", "", "| Metric | Correct | Total | % |", "|---|---|---|---|"]
    for k, v in r["metrics"].items():
        lines.append(f"| {k} | {v['correct']} | {v['total']} | {v['pct']} |")
    lines += ["", "## Category accuracy by class", "", "| Category | Correct | Total |", "|---|---|---|"]
    lines += [f"| {k} | {v['correct']} | {v['total']} |" for k, v in r["category_by_class"].items()]
    lines += ["", "## Most common confusions", ""] + [f"- {c['expected']} -> {c['got']}: {c['count']}" for c in r["top_confusions"]]
    lines += ["", "## Sample of category misses", ""] + [f"- {f}" for f in r["failures_sample"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    result = evaluate()
    with open(os.path.join(HERE, "standard_results.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    md = to_markdown(result)
    with open(os.path.join(HERE, "standard_results.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)
