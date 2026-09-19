"""
Manifest Audit Script

Compares original and new sampling manifests by source root IDs (not CONV_001 labels).
Reports added, removed, and shared source root IDs across candidate brands.
Saves audit report to results/brand_review/manifest_audit_report.json.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Set

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V1_PATH = REPO_ROOT / "results" / "brand_review" / "sampling_manifest_v1.json"
MANIFEST_V2_PATH = REPO_ROOT / "results" / "brand_review" / "sampling_manifest.json"
OUTPUT_REPORT_PATH = REPO_ROOT / "results" / "brand_review" / "manifest_audit_report.json"


def audit_manifests(
    v1_path: Path = MANIFEST_V1_PATH,
    v2_path: Path = MANIFEST_V2_PATH,
    output_path: Path = OUTPUT_REPORT_PATH
) -> Dict[str, Any]:
    """
    Compares source root IDs between original (v1) and new (v2) sampling manifests.
    """
    if not v1_path.exists():
        raise FileNotFoundError(f"Original manifest not found at: '{v1_path}'")
    if not v2_path.exists():
        raise FileNotFoundError(f"New manifest not found at: '{v2_path}'")

    with open(v1_path, "r", encoding="utf-8") as f:
        v1_data = json.load(f)

    with open(v2_path, "r", encoding="utf-8") as f:
        v2_data = json.load(f)

    v1_convs = v1_data.get("conversations", [])
    v2_convs = v2_data.get("conversations", [])

    brands = sorted(list({c["brand"] for c in v1_convs + v2_convs}))

    brand_audit: Dict[str, Any] = {}
    total_added = 0
    total_removed = 0
    total_shared = 0

    print("================ MANIFEST COMPARISON AUDIT ================", flush=True)
    print(f"Original Manifest (v1) : {v1_path.relative_to(REPO_ROOT)}")
    print(f"New Manifest (v2)      : {v2_path.relative_to(REPO_ROOT)}")
    print("Note: Comparison is based strictly on source root_tweet_id (ignoring index labels).\n")

    for brand in brands:
        v1_roots: Set[str] = {c["root_tweet_id"] for c in v1_convs if c["brand"] == brand}
        v2_roots: Set[str] = {c["root_tweet_id"] for c in v2_convs if c["brand"] == brand}

        shared_ids = sorted(list(v1_roots & v2_roots))
        added_ids = sorted(list(v2_roots - v1_roots))
        removed_ids = sorted(list(v1_roots - v2_roots))

        total_shared += len(shared_ids)
        total_added += len(added_ids)
        total_removed += len(removed_ids)

        brand_audit[brand] = {
            "v1_count": len(v1_roots),
            "v2_count": len(v2_roots),
            "shared_count": len(shared_ids),
            "added_count": len(added_ids),
            "removed_count": len(removed_ids),
            "shared_root_tweet_ids": shared_ids,
            "added_root_tweet_ids": added_ids,
            "removed_root_tweet_ids": removed_ids,
        }

        print(f"Brand: {brand}")
        print(f"  - v1 Root Count : {len(v1_roots)}")
        print(f"  - v2 Root Count : {len(v2_roots)}")
        print(f"  - Shared Roots  : {len(shared_ids)}")
        print(f"  - Added Roots   : {len(added_ids)}")
        print(f"  - Removed Roots : {len(removed_ids)}")
        print()

    report = {
        "v1_manifest_file": str(v1_path.relative_to(REPO_ROOT)),
        "v2_manifest_file": str(v2_path.relative_to(REPO_ROOT)),
        "provenance_note": (
            "V1 manifest contains 30 Spotify records. brand_profile.md references 31 "
            "review records from the original inspection. V1 is a post-normalization "
            "artifact (target_complete_per_brand=30); the authentic pre-normalization "
            "31-record sample is not preserved in the repository."
        ),
        "summary": {
            "total_shared_roots": total_shared,
            "total_added_roots": total_added,
            "total_removed_roots": total_removed,
        },
        "brand_breakdown": brand_audit,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Saved audit report to: '{output_path.relative_to(REPO_ROOT)}'")
    print("=============================================================", flush=True)

    return report


if __name__ == "__main__":
    try:
        audit_manifests()
    except Exception as err:
        print(f"Error auditing manifests: {err}", file=sys.stderr)
        sys.exit(1)
