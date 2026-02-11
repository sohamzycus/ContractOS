#!/usr/bin/env python3
"""Download LegalBench contract_nli datasets from GitHub.

Downloads train.tsv and base_prompt.txt for all 14 contract_nli tasks
from the HazyResearch/legalbench repository.

Usage:
    python tests/fixtures/legalbench/download_legalbench.py
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from urllib.request import urlopen

BASE_URL = "https://raw.githubusercontent.com/HazyResearch/legalbench/main/tasks"

# All 14 contract_nli tasks
CONTRACT_NLI_TASKS = [
    "contract_nli_confidentiality_of_agreement",
    "contract_nli_explicit_identification",
    "contract_nli_inclusion_of_verbally_conveyed_information",
    "contract_nli_limited_use",
    "contract_nli_no_licensing",
    "contract_nli_notice_on_compelled_disclosure",
    "contract_nli_permissible_acquirement_of_similar_information",
    "contract_nli_permissible_copy",
    "contract_nli_permissible_development_of_similar_information",
    "contract_nli_permissible_post-agreement_possession",
    "contract_nli_return_of_confidential_information",
    "contract_nli_sharing_with_employees",
    "contract_nli_sharing_with_third-parties",
    "contract_nli_survival_of_obligations",
]

# Additional relevant tasks
EXTRA_TASKS = [
    "definition_extraction",
    "contract_qa",
]


def download_file(url: str) -> str:
    """Download a file and return its content as string."""
    print(f"  Downloading {url.split('/')[-1]}...")
    with urlopen(url) as resp:
        return resp.read().decode("utf-8")


def download_task(task_name: str, output_dir: Path) -> dict:
    """Download a single task's files and return stats."""
    task_dir = output_dir / task_name
    task_dir.mkdir(parents=True, exist_ok=True)

    stats = {"task": task_name, "train_rows": 0, "test_rows": 0}

    # Download train.tsv
    try:
        train_url = f"{BASE_URL}/{task_name}/train.tsv"
        train_content = download_file(train_url)
        (task_dir / "train.tsv").write_text(train_content)

        # Count rows
        reader = csv.DictReader(io.StringIO(train_content), delimiter="\t")
        rows = list(reader)
        stats["train_rows"] = len(rows)

        # Extract unique documents
        docs = {r.get("document_name", "") for r in rows if r.get("document_name")}
        stats["unique_documents"] = len(docs)

        # Count yes/no distribution
        yes_count = sum(1 for r in rows if r.get("answer", "").strip().lower() == "yes")
        no_count = sum(1 for r in rows if r.get("answer", "").strip().lower() == "no")
        stats["yes_count"] = yes_count
        stats["no_count"] = no_count

    except Exception as e:
        print(f"  WARNING: Failed to download train.tsv for {task_name}: {e}")

    # Download base_prompt.txt
    try:
        prompt_url = f"{BASE_URL}/{task_name}/base_prompt.txt"
        prompt_content = download_file(prompt_url)
        (task_dir / "base_prompt.txt").write_text(prompt_content)
    except Exception as e:
        print(f"  WARNING: Failed to download base_prompt.txt for {task_name}: {e}")

    return stats


def main() -> None:
    output_dir = Path(__file__).parent
    print("=" * 60)
    print("LegalBench Dataset Downloader")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print()

    all_stats = []

    # Download contract_nli tasks
    print(f"Downloading {len(CONTRACT_NLI_TASKS)} contract_nli tasks...")
    print("-" * 40)
    for task in CONTRACT_NLI_TASKS:
        print(f"\n[{task}]")
        stats = download_task(task, output_dir)
        all_stats.append(stats)
        print(f"  → {stats['train_rows']} train rows, {stats.get('unique_documents', 0)} unique docs")

    # Download extra tasks
    print(f"\n\nDownloading {len(EXTRA_TASKS)} additional tasks...")
    print("-" * 40)
    for task in EXTRA_TASKS:
        print(f"\n[{task}]")
        stats = download_task(task, output_dir)
        all_stats.append(stats)
        print(f"  → {stats['train_rows']} train rows")

    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    total_rows = sum(s["train_rows"] for s in all_stats)
    total_tasks = len(all_stats)
    print(f"Tasks downloaded: {total_tasks}")
    print(f"Total train rows: {total_rows}")
    print()

    # Write summary file
    summary_lines = ["# LegalBench Dataset Summary\n"]
    summary_lines.append(f"Total tasks: {total_tasks}\n")
    summary_lines.append(f"Total train rows: {total_rows}\n\n")
    summary_lines.append("| Task | Train Rows | Yes | No | Docs |\n")
    summary_lines.append("|------|-----------|-----|-----|------|\n")
    for s in all_stats:
        summary_lines.append(
            f"| {s['task']} | {s['train_rows']} | "
            f"{s.get('yes_count', '-')} | {s.get('no_count', '-')} | "
            f"{s.get('unique_documents', '-')} |\n"
        )
    (output_dir / "SUMMARY.md").write_text("".join(summary_lines))
    print("Summary written to SUMMARY.md")


if __name__ == "__main__":
    main()
