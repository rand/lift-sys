#!/usr/bin/env python3
"""Classify planning documents as CANONICAL, ARCHIVE, SUPERSEDED, or STALE.

This script analyzes the documentation inventory and identifies:
- CANONICAL: Most current, authoritative version (keep in planning/)
- ARCHIVE: Complete, stale, or superseded (move to archive/)
- SUPERSEDED: Explicitly replaced by newer document
- STALE: >30 days old without completion markers

Usage:
    python scripts/docs/classify_docs.py

Inputs:
    - validation/DOC_INVENTORY.csv - Structured inventory from audit

Outputs:
    - validation/DOC_CLASSIFICATION.md - Human-readable classification
    - validation/DOC_CLASSIFICATION.csv - Structured classification
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_inventory(csv_path: Path) -> list[dict]:
    """Load document inventory from CSV."""
    docs = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            docs.append(row)
    return docs


def parse_date(date_str: str) -> datetime | None:
    """Parse date string to datetime."""
    if date_str == "Unknown":
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def calculate_staleness_days(date_str: str) -> int | None:
    """Calculate days since document date."""
    doc_date = parse_date(date_str)
    if not doc_date:
        return None
    return (datetime.now() - doc_date).days


def group_by_topic(docs: list[dict]) -> dict[str, list[dict]]:
    """Group documents by topic."""
    by_topic = defaultdict(list)
    for doc in docs:
        topic = doc["topic"]
        by_topic[topic].append(doc)
    return by_topic


def identify_canonical_for_topic(docs: list[dict], topic: str) -> list[str]:
    """Identify canonical documents for a topic.

    Returns list of filenames that should be canonical.
    """
    # Sort by date (newest first), with Unknown dates last
    sorted_docs = sorted(
        docs,
        key=lambda d: (
            d["date"] == "Unknown",  # Unknown dates go last
            d["date"] if d["date"] != "Unknown" else "0000-00-00",
        ),
        reverse=True,
    )

    canonical = []

    # Special handling for different topic types
    if topic == "Session Summary":
        # Session summaries are archival by nature
        # Only keep most recent 3 as reference
        for doc in sorted_docs[:3]:
            if doc["status"] != "Complete":
                canonical.append(doc["filename"])
    elif topic == "Planning/Roadmap":
        # Keep all active roadmap docs
        for doc in sorted_docs:
            if doc["status"] == "Active":
                canonical.append(doc["filename"])
    elif topic == "ICS Frontend":
        # Keep phase completion reports and current planning
        for doc in sorted_docs:
            fname = doc["filename"].lower()
            status = doc["status"]
            # Keep completion reports
            if "completion" in fname or "phase" in fname:
                if status in ["Active", "Complete"]:
                    canonical.append(doc["filename"])
            # Keep current planning docs
            elif status == "Active":
                canonical.append(doc["filename"])
    elif topic == "DSPy Architecture":
        # Keep current architecture docs and completion summaries
        for doc in sorted_docs:
            fname = doc["filename"].lower()
            status = doc["status"]
            if status == "Active" and "completion" not in fname:
                canonical.append(doc["filename"])
            elif status == "Complete" and "results" in fname:
                # Keep integration results as reference
                canonical.append(doc["filename"])
    else:
        # For other topics, keep active docs and newest complete doc
        active_count = 0
        complete_count = 0
        for doc in sorted_docs:
            status = doc["status"]
            if status == "Active":
                canonical.append(doc["filename"])
                active_count += 1
            elif status == "Complete" and complete_count == 0:
                # Keep one complete doc as historical reference
                canonical.append(doc["filename"])
                complete_count += 1

    return canonical


def classify_documents(docs: list[dict]) -> list[dict]:
    """Classify each document.

    Returns list of dicts with classification field added.
    """
    classified = []
    by_topic = group_by_topic(docs)

    # Identify canonical docs per topic
    canonical_files = set()
    for topic, topic_docs in by_topic.items():
        canonical_for_topic = identify_canonical_for_topic(topic_docs, topic)
        canonical_files.update(canonical_for_topic)

    # Classify each document
    for doc in docs:
        filename = doc["filename"]
        status = doc["status"]
        staleness = calculate_staleness_days(doc["date"])

        classification = None
        reason = ""

        # Determine classification
        if filename in canonical_files:
            classification = "CANONICAL"
            reason = "Current authoritative document for topic"
        elif status == "Complete":
            classification = "ARCHIVE"
            reason = "Marked complete, archive for reference"
        elif status == "Superseded":
            classification = "SUPERSEDED"
            reason = "Explicitly superseded by newer document"
        elif status == "Stale":
            classification = "ARCHIVE"
            reason = ">30 days old (status: stale)"
        elif status == "Unknown":
            if staleness and staleness > 30:
                classification = "ARCHIVE"
                reason = f"{staleness} days old, no clear status"
            else:
                classification = "REVIEW"
                reason = "Unknown status, needs manual review"
        else:
            # Active or Recent, but not canonical
            classification = "REVIEW"
            reason = "Not canonical but active/recent, needs manual review"

        classified.append(
            {
                **doc,
                "classification": classification,
                "reason": reason,
            }
        )

    return classified


def generate_classification_report(classified: list[dict], output_path: Path):
    """Generate human-readable classification report."""
    lines = [
        "# Documentation Classification",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Documents**: {len(classified)}",
        "",
        "---",
        "",
        "## Summary by Classification",
        "",
    ]

    # Count by classification
    classification_counts = defaultdict(int)
    for doc in classified:
        classification_counts[doc["classification"]] += 1

    for classification, count in sorted(classification_counts.items()):
        lines.append(f"- **{classification}**: {count} documents")

    lines.extend(["", "---", "", "## Classification Details", ""])

    # Group by classification
    by_classification = defaultdict(list)
    for doc in classified:
        by_classification[doc["classification"]].append(doc)

    # Output each classification group
    for classification in ["CANONICAL", "ARCHIVE", "SUPERSEDED", "REVIEW"]:
        if classification not in by_classification:
            continue

        docs = by_classification[classification]
        lines.append(f"### {classification} ({len(docs)} documents)")
        lines.append("")

        if classification == "CANONICAL":
            lines.append("**Keep these documents in `docs/planning/`**")
            lines.append("")

        lines.append("| Filename | Topic | Status | Date | Reason |")
        lines.append("|----------|-------|--------|------|--------|")

        for doc in sorted(docs, key=lambda d: (d["topic"], d["filename"])):
            lines.append(
                f"| {doc['filename']} | {doc['topic']} | {doc['status']} | {doc['date']} | {doc['reason']} |"
            )

        lines.append("")

    # Add action plan
    lines.extend(["---", "", "## Action Plan", ""])

    canonical_count = classification_counts["CANONICAL"]
    archive_count = classification_counts.get("ARCHIVE", 0)
    superseded_count = classification_counts.get("SUPERSEDED", 0)
    review_count = classification_counts.get("REVIEW", 0)

    lines.append("### Phase 4: Documentation Consolidation")
    lines.append("")
    lines.append(f"1. **Keep {canonical_count} CANONICAL documents** in `docs/planning/`")
    lines.append(f"2. **Archive {archive_count} documents** to `docs/archive/2025_q4/`")
    if superseded_count > 0:
        lines.append(
            f"3. **Archive {superseded_count} SUPERSEDED documents** to `docs/archive/2025_q4/`"
        )
    if review_count > 0:
        lines.append(f"4. **Manually review {review_count} documents** for classification")
    lines.append("")
    lines.append(
        f"**Target**: Reduce from {len(classified)} to ~{canonical_count} active planning docs"
    )
    lines.append("")

    # Write report
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"✅ Classification report written to {output_path}")


def generate_classification_csv(classified: list[dict], output_path: Path):
    """Generate CSV classification report."""
    fieldnames = [
        "filename",
        "topic",
        "status",
        "date",
        "classification",
        "reason",
        "path",
    ]

    with open(output_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for doc in classified:
            writer.writerow(
                {
                    "filename": doc["filename"],
                    "topic": doc["topic"],
                    "status": doc["status"],
                    "date": doc["date"],
                    "classification": doc["classification"],
                    "reason": doc["reason"],
                    "path": doc["path"],
                }
            )

    print(f"✅ Classification CSV written to {output_path}")


def main():
    """Main entry point."""
    print("📋 Classifying planning documents...")
    print()

    # Load inventory
    inventory_path = Path("validation/DOC_INVENTORY.csv")
    if not inventory_path.exists():
        print(f"❌ Inventory not found: {inventory_path}")
        print("   Run scripts/docs/audit_planning_docs.py first")
        return 1

    docs = load_inventory(inventory_path)
    print(f"Loaded {len(docs)} documents from inventory")
    print()

    # Classify documents
    classified = classify_documents(docs)
    print(f"Classified {len(classified)} documents")
    print()

    # Generate reports
    md_path = Path("validation/DOC_CLASSIFICATION.md")
    csv_path = Path("validation/DOC_CLASSIFICATION.csv")

    generate_classification_report(classified, md_path)
    generate_classification_csv(classified, csv_path)

    print()
    print("✅ Document classification complete!")
    print()
    print("Next steps:")
    print("1. Review validation/DOC_CLASSIFICATION.md")
    print("2. Manually review documents marked REVIEW")
    print("3. Begin Phase 4: Documentation Consolidation")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
