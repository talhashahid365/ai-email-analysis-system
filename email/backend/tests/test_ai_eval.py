import json
import os
import pytest
from app.services import ai_engine

CAT_MAP = {
    "sales": "Sales Inquiry",
    "sales inquiry": "Sales Inquiry",
    "customer complaint": "Customer Complaint",
    "complaint": "Customer Complaint",
    "support": "Support Request",
    "support request": "Support Request",
    "meeting": "Meeting Request",
    "meeting request": "Meeting Request",
    "invoice": "Invoice / Payment",
    "invoice / payment": "Invoice / Payment",
    "finance": "Invoice / Payment",
    "payment": "Invoice / Payment",
    "hr": "Job Application",
    "job application": "Job Application",
    "general": "General Information",
    "general information": "General Information",
    "project update": "General Information",
    "internal": "General Information",
    "legal": "General Information",
    "reports": "General Information",
    "newsletter": "General Information",
    "customer feedback": "Customer Complaint",
    "security": "Urgent",
    "urgent": "Urgent",
    "spam": "Spam",
    "other": "Other",
}


def test_ai_benchmark_evaluation():
    """Evaluate AI Engine performance on the benchmark dataset."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets", "sample_100_emails.json")
    with open(json_path, "r", encoding="utf-8") as f:
        sample_emails = json.load(f)

    assert len(sample_emails) >= 90, f"Expected benchmark emails, found {len(sample_emails)}"

    correct_cat = 0
    correct_prio = 0
    total = len(sample_emails)

    for item in sample_emails:
        res, meta = ai_engine.analyze_email(
            item["subject"],
            item["body_plain"],
            item["sender_email"],
            item["sender_name"],
        )

        expected_cat_raw = (item.get("expected_category") or item.get("expected_cat") or "").strip().lower()
        expected_cat = CAT_MAP.get(expected_cat_raw, expected_cat_raw)
        actual_cat = CAT_MAP.get(res["category"].lower(), res["category"])

        if expected_cat and actual_cat.lower() == expected_cat.lower():
            correct_cat += 1

        expected_prio = item.get("expected_priority")
        if expected_prio and res["priority"] == expected_prio:
            correct_prio += 1

        # Basic assertion for pipeline contract
        assert "short_summary" in res and len(res["short_summary"]) > 0
        assert "detailed_summary" in res and len(res["detailed_summary"]) > 0
        assert "extracted_info" in res

    cat_accuracy = (correct_cat / total) * 100
    prio_accuracy = (correct_prio / total) * 100

    print(f"\nAI Category Classification Accuracy: {cat_accuracy:.2f}% ({correct_cat}/{total})")
    print(f"AI Priority Detection Accuracy: {prio_accuracy:.2f}% ({correct_prio}/{total})")

    assert cat_accuracy >= 30.0, f"Category accuracy dropped below 30%: {cat_accuracy:.2f}%"
    assert prio_accuracy >= 40.0, f"Priority accuracy dropped below 40%: {prio_accuracy:.2f}%"

