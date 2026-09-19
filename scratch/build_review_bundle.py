"""
Builds annotation_review_bundle.zip preserving repository-relative paths.
Includes all human-review workbooks, final dev/gold labels, taxonomy, guidelines,
inputs, manifests, cluster membership, exclusions, scripts, helpers, and reports.
Strictly excludes secrets, .env, .venv, twcs.csv, and SQLite databases.
"""

import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path("E:/Reply_agent")
OUTPUT_ZIP_PATH = REPO_ROOT / "annotation_review_bundle.zip"

EXCLUDED_FILENAMES = {
    "twcs.csv",
    ".env",
    ".env.example",
    "twcs_index.sqlite",
    "annotation_review_bundle.zip",
    "test_dv.xlsx",
}

EXCLUDED_DIR_NAMES = {
    ".venv",
    ".pytest_cache",
    "__pycache__",
    ".git",
}

EXCLUDED_EXTENSIONS = {
    ".sqlite",
    ".sqlite-journal",
    ".pyc",
}

# Explicit list of files to include
FILES_TO_INCLUDE = [
    # Top-level documents and indices
    "FILE_INDEX.md",
    "README.md",
    "scope.md",
    "decision_log.md",
    "sampling_notes.md",
    "final_report.md",
    "report.md",
    "intents.yaml",
    "annotation_guidelines.md",
    "dev_labels.csv",
    "dev_gold.jsonl",
    "gold_labels.csv",
    "golden_eval.jsonl",
    "gold_human_review.xlsx",
    "gold_selection_manifest.jsonl",
    "human_ratings.csv",
    "reply_human_review_task_v2_annonated.xlsx",
    "metrics.json",
    "judge_agreement.json",
    "results_table.csv",
    "evaluate.py",
    "judge.py",
    "reproduce.py",
    "validate_annotations.py",
    "requirements.txt",

    # Configs
    "configs/__init__.py",
    "configs/brand_config.json",
    "configs/intent_taxonomy.json",
    "configs/settings.py",

    # Source code & helper modules
    "src/__init__.py",
    "src/context_builder.py",
    "src/duplicate_detector.py",
    "src/language_filter.py",
    "src/sample_brand_conversations.py",
    "src/prepare_phase2_dataset.py",
    "src/audit_manifests.py",
    "src/audit_correction2.py",
    "src/baselines.py",
    "src/pipeline.py",
    "src/retriever.py",
    "src/run_baselines.py",
    "src/run_phase5_dev.py",
    "src/run_phase5_eval.py",
    "src/evaluate_phase6.py",
    "src/agent.py",
    "src/inspect_dataset.py",
    "src/judge.py",
    "src/llm.py",

    # Data processed
    "data/processed/spotify_knowledge.jsonl",
    "data/processed/dev_inputs.jsonl",
    "data/processed/eval_pool_inputs.jsonl",
    "data/processed/v2/spotify_knowledge.jsonl",
    "data/processed/v2/knowledge.jsonl",
    "data/processed/v2/dev_inputs.jsonl",
    "data/processed/v2/dev_labels.csv",
    "data/processed/v2/eval_pool.jsonl",
    "data/processed/v2/eval_pool_inputs.jsonl",
    "data/processed/v2/gold_labels.csv",

    # Data manifests
    "data/manifests/split_manifest.jsonl",
    "data/manifests/v2/cluster_membership.json",
    "data/manifests/v2/gold_selection_manifest.jsonl",
    "data/manifests/v2/split_manifest.jsonl",

    # Scratch scripts
    "scratch/create_reply_review_task_workbook.py",
    "scratch/create_gold_human_review_workbook.py",
    "scratch/verify_gold_workbook.py",
    "scratch/build_gold_annotations.py",
    "scratch/build_phase3_artifacts.py",
    "scratch/generate_dev_labels.py",
    "scratch/select_gold_evaluation.py",
    "scratch/inspect_all_gold_records.py",
    "scratch/inspect_dev_50.py",
    "scratch/verify_phase3_deliverables.py",
    "scratch/verify_phase4_deliverables.py",
    "scratch/verify_phase5_deliverables.py",
    "scratch/verify_phase6_deliverables.py",
    "scratch/audit_user_annotations.py",
    "scratch/analyze_evaluation_subsets.py",
    "scratch/dev_50_summary.txt",
    "scratch/dump_gold_200.py",
    "scratch/enrich_knowledge_and_aliases.py",
    "scratch/gold_200_inspection.txt",
    "scratch/test_correction4_outputs.py",
    "scratch/test_outcome_classification.py",
    "scratch/test_redaction_regex.py",
    "scratch/verify_20_source_conversations.py",
    "scratch/regenerate_human_review_artifacts.py",

    # Results & reports
    "results/data_profile.json",
    "results/brand_review/review_scores.csv",
    "results/brand_review/original_sampling_manifest.json",
    "results/brand_review/sampling_manifest_original_uploaded.json",
    "results/brand_review/sampling_manifest_v1.json",
    "results/brand_review/sampling_manifest.json",
    "results/brand_review/AppleSupport.md",
    "results/brand_review/AskPlayStation.md",
    "results/brand_review/SpotifyCares.md",
    "results/brand_review/manifest_audit_report.json",
    "results/phase2/correction2/correction2_audit_report.json",
    "results/phase2/correction2/correction2_audit_summary.md",
    "results/phase2/correction2/duplicate_clusters.json",
    "results/phase2/correction2/exclusion_history.json",
    "results/phase2/correction2/exported_4050_audit.json",
    "results/phase2/data_summary.md",
    "results/phase2/dev_preview.md",
    "results/phase2/exclusion_summary.json",
    "results/phase2/language_human_review_sheet.csv",
    "results/phase2/language_review_queue.json",
    "results/phase2/leakage_report.json",
    "results/phase2_v2/cluster_membership.json",
    "results/phase2_v2/data_summary.md",
    "results/phase2_v2/dev_labels.csv",
    "results/phase2_v2/dev_preview.md",
    "results/phase2_v2/development_review_notes.md",
    "results/phase2_v2/exclusion_summary.json",
    "results/phase2_v2/exclusions.json",
    "results/phase2_v2/gold_annotations_summary.md",
    "results/phase2_v2/gold_human_review.xlsx",
    "results/phase2_v2/gold_labels.csv",
    "results/phase2_v2/gold_selection_manifest.jsonl",
    "results/phase2_v2/language_human_review_sheet.csv",
    "results/phase2_v2/language_review_queue.json",
    "results/phase2_v2/leakage_report.json",
    "results/phase2_v2/manual_source_verification_20.md",
    "results/phase4/baseline_0_dev_predictions.jsonl",
    "results/phase4/baseline_1_dev_predictions.jsonl",
    "results/phase4/baseline_evaluation_report.md",
    "results/phase5/frozen_config.json",
    "results/phase5/phase5_final_report.md",
    "results/phase5/retrieval_inspection_20.md",
    "results/phase5/tuning_log.md",
    "results/phase5/dev_predictions_baseline_0.jsonl",
    "results/phase5/dev_predictions_baseline_1.jsonl",
    "results/phase5/dev_predictions_main_agent.jsonl",
    "results/phase5/eval_predictions_baseline_0.jsonl",
    "results/phase5/eval_predictions_baseline_1.jsonl",
    "results/phase5/eval_predictions_main_agent.jsonl",
    "results/phase6/human_ratings_90.jsonl",
    "results/phase6/human_ratings_90_v2.jsonl",
    "results/phase6/reply_human_review_task.xlsx",
    "results/phase6/reply_human_review_task_v2.xlsx",
    "results/phase6/system_identity_mapping.csv",
    "results/phase6/system_identity_mapping.json",
    "results/phase6/judge_predictions_600.jsonl",
    "results/phase6/judge_rubric.md",
    "results/phase6/judge_validation_agreement.md",
    "results/phase6/phase6_evaluation_report.md",
    "results/phase6/fixtures/README.md",
    "results/phase6/fixtures/synthetic_ratings_fixture.csv",
    "results/phase6/fixtures/synthetic_ratings_90_fixture.jsonl",

    # Tests
    "tests/fixtures/README.md",
    "tests/fixtures/synthetic_ratings_fixture.csv",
    "tests/test_baselines.py",
    "tests/test_context_builder.py",
    "tests/test_context_validation_and_regression.py",
    "tests/test_customer_target_selection.py",
    "tests/test_duplicate_detection.py",
    "tests/test_environment.py",
    "tests/test_extraction_fixes.py",
    "tests/test_inspect_dataset.py",
    "tests/test_language_filter.py",
    "tests/test_phase2_preparation.py",
    "tests/test_phase6.py",
    "tests/test_pipeline.py",
    "tests/test_redaction_consistency.py",
    "tests/test_sample_brand_conversations.py",
    "tests/test_sqlite_provenance.py",
]

def main():
    print(f"Building {OUTPUT_ZIP_PATH.name}...")
    
    missing_files = []
    added_files = []

    with zipfile.ZipFile(OUTPUT_ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel_path_str in FILES_TO_INCLUDE:
            p = REPO_ROOT / rel_path_str
            
            # Security & exclusion filter
            if any(part in EXCLUDED_DIR_NAMES for part in p.parts):
                print(f"SKIPPING EXCLUDED DIR: {rel_path_str}")
                continue
            if p.name in EXCLUDED_FILENAMES or p.suffix in EXCLUDED_EXTENSIONS:
                print(f"SKIPPING EXCLUDED FILE: {rel_path_str}")
                continue
            
            if not p.exists():
                missing_files.append(rel_path_str)
                print(f"WARNING: File not found: {rel_path_str}")
                continue

            # Add to zip with normalized POSIX relative path
            posix_rel = p.relative_to(REPO_ROOT).as_posix()
            zf.write(p, arcname=posix_rel)
            added_files.append(posix_rel)

    zip_size_bytes = OUTPUT_ZIP_PATH.stat().st_size
    zip_size_mb = zip_size_bytes / (1024 * 1024)

    print("\n================================================================================")
    print(f"Successfully generated {OUTPUT_ZIP_PATH.name}!")
    print(f"  - Total files packaged: {len(added_files)}")
    print(f"  - Missing files: {len(missing_files)}")
    print(f"  - Bundle archive size: {zip_size_mb:.2f} MB ({zip_size_bytes:,} bytes)")
    print("================================================================================\n")

    if missing_files:
        print("Missing files report:")
        for mf in missing_files:
            print(f"  - {mf}")

    # Audit the generated zip
    print("Auditing generated ZIP contents...")
    with zipfile.ZipFile(OUTPUT_ZIP_PATH, "r") as zf:
        infolist = zf.infolist()
        names = zf.namelist()
        
        # Verify no forbidden items
        for n in names:
            assert not any(n.endswith(ext) for ext in EXCLUDED_EXTENSIONS), f"Forbidden extension in zip: {n}"
            assert not any(part in EXCLUDED_DIR_NAMES for part in Path(n).parts), f"Forbidden directory in zip: {n}"
            assert Path(n).name not in EXCLUDED_FILENAMES, f"Forbidden filename in zip: {n}"
            assert not Path(n).is_absolute(), f"Path is not relative: {n}"

        assert "FILE_INDEX.md" in names, "FILE_INDEX.md missing from zip"
        assert "gold_human_review.xlsx" in names, "gold_human_review.xlsx missing from zip"
        assert "golden_eval.jsonl" in names, "golden_eval.jsonl missing from zip"
        assert "gold_labels.csv" in names, "gold_labels.csv missing from zip"
        assert "dev_labels.csv" in names, "dev_labels.csv missing from zip"
        assert "dev_gold.jsonl" in names, "dev_gold.jsonl missing from zip"
        assert "intents.yaml" in names, "intents.yaml missing from zip"
        assert "annotation_guidelines.md" in names, "annotation_guidelines.md missing from zip"
        assert "validate_annotations.py" in names, "validate_annotations.py missing from zip"
        assert "data/processed/v2/spotify_knowledge.jsonl" in names, "data/processed/v2/spotify_knowledge.jsonl missing from zip"
        assert "data/processed/spotify_knowledge.jsonl" in names, "data/processed/spotify_knowledge.jsonl missing from zip"
        assert "results/phase6/reply_human_review_task.xlsx" in names, "results/phase6/reply_human_review_task.xlsx missing from zip"
        assert "tests/fixtures/synthetic_ratings_fixture.csv" in names, "tests/fixtures/synthetic_ratings_fixture.csv missing from zip"

    print("Audit passed: 100% relative paths, zero secrets/SQLite/twcs.csv, all key assets verified!")

if __name__ == "__main__":
    main()
