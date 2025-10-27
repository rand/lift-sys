#!/usr/bin/env python3
"""Audit planning documents and create inventory for synthesis plan.

This script catalogs all planning documents in docs/planning/ and categorizes them
by date, status, topic, and relevance for the synthesis plan.

Usage:
    python scripts/docs/audit_planning_docs.py

Outputs:
    - validation/DOC_INVENTORY.csv - Structured inventory
    - validation/DOC_INVENTORY.md - Human-readable report
"""

import csv
import re
from datetime import datetime
from pathlib import Path


def extract_date_from_filename(filename: str) -> datetime | None:
    """Extract date from filename if present (format: YYYYMMDD or YYYY-MM-DD)."""
    # Try YYYYMMDD format
    match = re.search(r"(\d{8})", filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d")
        except ValueError:
            pass

    # Try YYYY-MM-DD format
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            pass

    return None


def extract_date_from_content(content: str) -> datetime | None:
    """Extract 'Last Updated' or 'Date' from document content."""
    # Look for patterns like "Date: 2025-10-27" or "Last Updated: 2025-10-27"
    patterns = [
        r"\*\*Date\*\*:\s*(\d{4}-\d{2}-\d{2})",
        r"\*\*Last Updated\*\*:\s*(\d{4}-\d{2}-\d{2})",
        r"Date:\s*(\d{4}-\d{2}-\d{2})",
        r"Last Updated:\s*(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, content[:2000])  # Check first 2000 chars
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                pass

    return None


def categorize_topic(filename: str, content: str) -> str:
    """Categorize document by topic."""
    fname_lower = filename.lower()
    content_lower = content[:500].lower()

    # Check filename patterns first
    if "dspy" in fname_lower:
        return "DSPy Architecture"
    elif "ics" in fname_lower or "phase1" in fname_lower or "phase2" in fname_lower:
        return "ICS Frontend"
    elif "hole" in fname_lower or "typed" in fname_lower:
        return "Typed Holes"
    elif "supabase" in fname_lower or "infrastructure" in fname_lower:
        return "Infrastructure"
    elif "robustness" in fname_lower or "tokdrift" in fname_lower:
        return "Robustness Testing"
    elif "roadmap" in fname_lower or "beads" in fname_lower:
        return "Planning/Roadmap"
    elif "modal" in fname_lower:
        return "Modal Deployment"
    elif "honeycomb" in fname_lower:
        return "Observability"
    elif "dowhy" in fname_lower or "causal" in fname_lower:
        return "Causal Analysis"
    elif "integration" in fname_lower:
        return "Integration"
    elif "session" in fname_lower or "summary" in fname_lower:
        return "Session Summary"

    # Check content patterns
    if "dspy" in content_lower or "pydantic ai" in content_lower:
        return "DSPy Architecture"
    elif "integrated context studio" in content_lower or "ics" in content_lower:
        return "ICS Frontend"
    elif "typed hole" in content_lower:
        return "Typed Holes"

    return "Other"


def determine_status(filename: str, content: str, doc_date: datetime | None) -> str:
    """Determine document status: Active, Stale, Complete, or Superseded."""
    fname_lower = filename.lower()
    content_lower = content[:1000].lower()

    # Check for completion markers
    if "complete" in fname_lower or "completion" in fname_lower or "✅ complete" in content_lower:
        return "Complete"

    # Check for status markers in content
    if "status**: complete" in content_lower or "status: complete" in content_lower:
        return "Complete"
    elif "superseded" in content_lower or "deprecated" in content_lower:
        return "Superseded"

    # Check date staleness (>30 days = stale)
    if doc_date:
        days_old = (datetime.now() - doc_date).days
        if days_old > 30:
            return "Stale"
        elif days_old > 7:
            return "Recent"
        else:
            return "Active"

    # No date, check for active markers
    if "in progress" in content_lower or "active" in content_lower:
        return "Active"

    return "Unknown"


def analyze_documents() -> list[dict]:
    """Analyze all documents in docs/planning/."""
    planning_dir = Path("docs/planning")
    if not planning_dir.exists():
        print(f"Error: {planning_dir} not found")
        return []

    docs = []
    for filepath in sorted(planning_dir.glob("*.md")):
        # Read content
        try:
            content = filepath.read_text()
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}")
            continue

        # Extract metadata
        filename = filepath.name
        file_date = extract_date_from_filename(filename)
        content_date = extract_date_from_content(content)
        doc_date = content_date or file_date

        topic = categorize_topic(filename, content)
        status = determine_status(filename, content, doc_date)

        # Calculate age
        age_days = (datetime.now() - doc_date).days if doc_date else None

        # Extract file size
        size_kb = filepath.stat().st_size / 1024

        docs.append(
            {
                "filename": filename,
                "path": str(filepath),
                "topic": topic,
                "status": status,
                "date": doc_date.strftime("%Y-%m-%d") if doc_date else "Unknown",
                "age_days": age_days if age_days is not None else "Unknown",
                "size_kb": f"{size_kb:.1f}",
                "lines": len(content.splitlines()),
            }
        )

    return docs


def generate_csv_report(docs: list[dict], output_path: Path):
    """Generate CSV inventory report."""
    fieldnames = ["filename", "topic", "status", "date", "age_days", "size_kb", "lines", "path"]

    with open(output_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for doc in docs:
            writer.writerow(doc)

    print(f"✅ CSV inventory written to {output_path}")


def generate_markdown_report(docs: list[dict], output_path: Path):
    """Generate human-readable markdown report."""
    lines = [
        "# Planning Documents Inventory",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Documents**: {len(docs)}",
        "",
        "---",
        "",
        "## Summary by Status",
        "",
    ]

    # Count by status
    status_counts = {}
    for doc in docs:
        status = doc["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        lines.append(f"- **{status}**: {count} documents")

    lines.extend(["", "---", "", "## Summary by Topic", ""])

    # Count by topic
    topic_counts = {}
    for doc in docs:
        topic = doc["topic"]
        topic_counts[topic] = topic_counts.get(topic, 0) + 1

    for topic, count in sorted(topic_counts.items()):
        lines.append(f"- **{topic}**: {count} documents")

    lines.extend(["", "---", "", "## Documents by Status", ""])

    # Group by status
    by_status = {}
    for doc in docs:
        status = doc["status"]
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(doc)

    for status in ["Active", "Recent", "Complete", "Stale", "Superseded", "Unknown"]:
        if status not in by_status:
            continue

        lines.append(f"### {status} ({len(by_status[status])} documents)")
        lines.append("")
        lines.append("| Filename | Topic | Date | Age (days) |")
        lines.append("|----------|-------|------|------------|")

        for doc in sorted(by_status[status], key=lambda d: d["filename"]):
            lines.append(
                f"| {doc['filename']} | {doc['topic']} | {doc['date']} | {doc['age_days']} |"
            )

        lines.append("")

    lines.extend(["---", "", "## Recommendations", ""])

    # Generate recommendations
    stale_count = status_counts.get("Stale", 0)
    complete_count = status_counts.get("Complete", 0)
    superseded_count = status_counts.get("Superseded", 0)

    if stale_count > 0:
        lines.append(
            f"- **Archive {stale_count} stale documents** (>30 days old) to `docs/archive/2025_q4/`"
        )
    if complete_count > 0:
        lines.append(
            f"- **Archive {complete_count} completed documents** to `docs/archive/2025_q4/`"
        )
    if superseded_count > 0:
        lines.append(
            f"- **Archive {superseded_count} superseded documents** to `docs/archive/2025_q4/`"
        )

    active_count = status_counts.get("Active", 0) + status_counts.get("Recent", 0)
    lines.append(f"- **Keep {active_count} active/recent documents** in `docs/planning/`")
    lines.append(
        f"- **Target**: Reduce from {len(docs)} to ~20 active planning documents after synthesis"
    )

    # Write report
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"✅ Markdown inventory written to {output_path}")


def main():
    """Main entry point."""
    print("📊 Auditing planning documents...")
    print()

    docs = analyze_documents()

    if not docs:
        print("❌ No documents found or error reading documents")
        return 1

    print(f"Found {len(docs)} planning documents")
    print()

    # Generate reports
    validation_dir = Path("validation")
    validation_dir.mkdir(exist_ok=True)

    csv_path = validation_dir / "DOC_INVENTORY.csv"
    md_path = validation_dir / "DOC_INVENTORY.md"

    generate_csv_report(docs, csv_path)
    generate_markdown_report(docs, md_path)

    print()
    print("✅ Document inventory complete!")
    print()
    print("Next steps:")
    print("1. Review validation/DOC_INVENTORY.md")
    print("2. Identify canonical documents for each topic")
    print("3. Archive stale/complete/superseded documents")
    print("4. Update unified roadmap with active documents only")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
