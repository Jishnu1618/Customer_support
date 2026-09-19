"""
Unit and regression tests for SQLite provenance and build integrity (Correction 6).

Covers:
1. Stale checksum is detected before extraction.
2. An interrupted build cannot be reused.
3. Unknown inbound values fail clearly.
4. Conflicting duplicate IDs are rejected or quarantined (and identical duplicate rows deduplicated).
5. A valid completed index is reused.
6. A failed rebuild preserves the previous database.
7. Every exported record's source checksum describes the database actually used.
"""

import json
import sqlite3
from pathlib import Path
import pytest

from src.sample_brand_conversations import (
    build_sqlite_index,
    validate_sqlite_index,
    compute_file_sha256,
    CURRENT_SCHEMA_VERSION,
)
from src.prepare_phase2_dataset import (
    validate_or_rebuild_index,
    export_phase2_outputs,
)


class TestSQLiteProvenanceAndBuildIntegrity:

    def test_stale_checksum_detected_before_extraction(self, tmp_path):
        """Before extraction, compare current CSV checksum with DB stored checksum; detect stale checksum."""
        csv_path = tmp_path / "data.csv"
        db_path = tmp_path / "index.sqlite"

        # 1. Build initial index
        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,True,Mon Oct 16 10:00:00 +0000 2017,hello,,\n"
        )
        build_sqlite_index(csv_path, db_path)

        # 2. Modify CSV to alter its checksum
        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,True,Mon Oct 16 10:00:00 +0000 2017,hello modified,,\n"
        )
        new_checksum = compute_file_sha256(csv_path)

        # 3. validate_sqlite_index detects stale checksum
        is_valid, reason, meta = validate_sqlite_index(db_path, expected_csv_checksum=new_checksum)
        assert is_valid is False
        assert "Stale source CSV checksum" in reason

        # 4. validate_or_rebuild_index with rebuild_if_invalid=False rejects the stale index
        with pytest.raises(ValueError, match="SQLite index validation failed: Stale source CSV checksum"):
            validate_or_rebuild_index(db_path, csv_path, rebuild_if_invalid=False)

    def test_interrupted_build_cannot_be_reused(self, tmp_path):
        """An index missing build_completed or with build_completed != '1' cannot be reused."""
        csv_path = tmp_path / "data.csv"
        db_path = tmp_path / "index.sqlite"

        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,True,Mon Oct 16 10:00:00 +0000 2017,hello,,\n"
        )
        build_sqlite_index(csv_path, db_path)

        # Case A: build_completed deleted
        conn = sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM index_metadata WHERE key = 'build_completed'")
        conn.commit()
        conn.close()

        is_valid, reason, _ = validate_sqlite_index(db_path)
        assert is_valid is False
        assert "interrupted or not completed" in reason

        with pytest.raises(ValueError, match="interrupted or not completed"):
            validate_or_rebuild_index(db_path, csv_path, rebuild_if_invalid=False)

        # Case B: build_completed = '0'
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT OR REPLACE INTO index_metadata (key, value) VALUES ('build_completed', '0')")
        conn.commit()
        conn.close()

        is_valid, reason, _ = validate_sqlite_index(db_path)
        assert is_valid is False
        assert "interrupted or not completed" in reason

    def test_unknown_inbound_values_fail_clearly(self, tmp_path):
        """Reusing shared strict inbound parser: unexpected values raise clear ValueError."""
        csv_path = tmp_path / "bad_inbound.csv"
        db_path = tmp_path / "index.sqlite"

        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,maybe,Mon Oct 16 10:00:00 +0000 2017,hello,,\n"
        )

        with pytest.raises(ValueError, match="Unexpected non-boolean value found in 'inbound' column: 'maybe'"):
            build_sqlite_index(csv_path, db_path)

    def test_conflicting_duplicate_ids_quarantined_and_identical_deduplicated(self, tmp_path, capsys):
        """Conflicting duplicates are quarantined (no last-write-wins), and identical rows deduplicated."""
        csv_path = tmp_path / "duplicates.csv"
        db_path = tmp_path / "index.sqlite"

        # Tweet 100 has conflicting version; Tweet 200 has identical duplicate
        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "100,customer_v1,True,Mon Oct 16 10:00:00 +0000 2017,original inquiry,,\n"
            "100,customer_v2,False,Mon Oct 16 10:05:00 +0000 2017,conflicting inquiry,,\n"
            "200,customer_v3,True,Mon Oct 16 10:10:00 +0000 2017,another inquiry,,\n"
            "200,customer_v3,True,Mon Oct 16 10:10:00 +0000 2017,another inquiry,,\n"
        )

        meta = build_sqlite_index(csv_path, db_path)
        captured = capsys.readouterr()

        assert "conflicting duplicate tweet IDs detected" in captured.out
        assert "Deduplicated 1 identical duplicate rows" in captured.out

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Primary table has exactly 2 unique tweets
        cursor.execute("SELECT count(*) FROM tweets")
        assert cursor.fetchone()[0] == 2

        # 2. Tweet 100 retains original first-write data (no last-write-wins)
        cursor.execute("SELECT author_id, text, inbound FROM tweets WHERE tweet_id = '100'")
        row_100 = cursor.fetchone()
        assert row_100["author_id"] == "customer_v1"
        assert row_100["text"] == "original inquiry"
        assert row_100["inbound"] == 1

        # 3. Tweet 100 conflicting version is quarantined
        cursor.execute("SELECT author_id, text, inbound, quarantine_reason FROM quarantined_tweets WHERE tweet_id = '100'")
        q_row = cursor.fetchone()
        assert q_row is not None
        assert q_row["author_id"] == "customer_v2"
        assert q_row["text"] == "conflicting inquiry"
        assert q_row["inbound"] == 0
        assert q_row["quarantine_reason"] == "CONFLICTING_DUPLICATE_TWEET_ID"

        # 4. Metadata stores duplicate and conflict counts
        cursor.execute("SELECT key, value FROM index_metadata")
        meta_dict = {r["key"]: r["value"] for r in cursor.fetchall()}
        assert meta_dict["row_count"] == "2"
        assert meta_dict["identical_duplicates_count"] == "1"
        assert meta_dict["conflicting_duplicates_count"] == "1"
        assert meta_dict["schema_version"] == CURRENT_SCHEMA_VERSION
        assert meta_dict["build_completed"] == "1"
        conn.close()

    def test_conflicting_duplicate_ids_rejected_when_configured(self, tmp_path):
        """When reject_conflicts=True, conflicting duplicate IDs raise ValueError."""
        csv_path = tmp_path / "reject_dup.csv"
        db_path = tmp_path / "index.sqlite"

        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "100,customer_v1,True,Mon Oct 16 10:00:00 +0000 2017,original inquiry,,\n"
            "100,customer_v2,False,Mon Oct 16 10:05:00 +0000 2017,conflicting inquiry,,\n"
        )

        with pytest.raises(ValueError, match="Conflicting duplicate tweet ID detected in CSV: 100"):
            build_sqlite_index(csv_path, db_path, reject_conflicts=True)

    def test_valid_completed_index_is_reused(self, tmp_path, capsys):
        """A valid completed index matching checksum, schema, and row count is reused without rebuilding."""
        csv_path = tmp_path / "data.csv"
        db_path = tmp_path / "index.sqlite"

        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,True,Mon Oct 16 10:00:00 +0000 2017,hello,,\n"
        )
        # First build
        build_sqlite_index(csv_path, db_path)
        capsys.readouterr()

        # Second build call with unchanged CSV
        meta = build_sqlite_index(csv_path, db_path)
        captured = capsys.readouterr()

        assert "Using existing SQLite index" in captured.out
        assert "checksum verified" in captured.out
        assert meta["build_completed"] == "1"
        assert meta["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_failed_rebuild_preserves_previous_database(self, tmp_path):
        """A failed rebuild preserves the previous database intact."""
        valid_csv_path = tmp_path / "valid.csv"
        bad_csv_path = tmp_path / "bad.csv"
        db_path = tmp_path / "index.sqlite"

        # 1. Build initial valid index with 2 rows
        valid_csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,True,Mon Oct 16 10:00:00 +0000 2017,hello,,\n"
            "2,user2,False,Mon Oct 16 10:05:00 +0000 2017,hi,,1\n"
        )
        build_sqlite_index(valid_csv_path, db_path)
        orig_checksum = compute_file_sha256(valid_csv_path)

        # 2. Attempt rebuild with invalid CSV
        bad_csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "10,userX,bad_inbound_value,Mon Oct 16 10:00:00 +0000 2017,crash,,\n"
        )

        with pytest.raises(ValueError, match="Unexpected non-boolean value"):
            build_sqlite_index(bad_csv_path, db_path, force_rebuild=True)

        # 3. Verify original database was preserved intact
        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM tweets")
        assert cursor.fetchone()[0] == 2
        cursor.execute("SELECT value FROM index_metadata WHERE key = 'source_csv_sha256'")
        assert cursor.fetchone()[0] == orig_checksum
        cursor.execute("SELECT value FROM index_metadata WHERE key = 'build_completed'")
        assert cursor.fetchone()[0] == "1"
        conn.close()

    def test_stored_row_count_mismatch_detected(self, tmp_path):
        """Stored row count mismatch against actual database count fails validation."""
        csv_path = tmp_path / "data.csv"
        db_path = tmp_path / "index.sqlite"

        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,True,Mon Oct 16 10:00:00 +0000 2017,hello,,\n"
        )
        build_sqlite_index(csv_path, db_path)

        # Corrupt stored row count
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE index_metadata SET value = '999' WHERE key = 'row_count'")
        conn.commit()
        conn.close()

        is_valid, reason, _ = validate_sqlite_index(db_path)
        assert is_valid is False
        assert "Stored row count (999) does not match actual database count (1)" in reason

    def test_incompatible_schema_version_detected(self, tmp_path):
        """Incompatible schema version fails validation."""
        csv_path = tmp_path / "data.csv"
        db_path = tmp_path / "index.sqlite"

        csv_path.write_text(
            "tweet_id,author_id,inbound,created_at,text,response_tweet_id,in_response_to_tweet_id\n"
            "1,user1,True,Mon Oct 16 10:00:00 +0000 2017,hello,,\n"
        )
        build_sqlite_index(csv_path, db_path)

        # Change schema version
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE index_metadata SET value = '1.0' WHERE key = 'schema_version'")
        conn.commit()
        conn.close()

        is_valid, reason, _ = validate_sqlite_index(db_path)
        assert is_valid is False
        assert "Incompatible schema version" in reason

    def test_every_exported_record_has_source_checksum_describing_db_used(self, tmp_path, monkeypatch):
        """Done when: Every exported record's source checksum describes the database actually used."""
        test_data_dir = tmp_path / "data"
        test_manifest_dir = tmp_path / "manifests"
        test_report_dir = tmp_path / "reports"

        monkeypatch.setattr("src.prepare_phase2_dataset.OUTPUT_DATA_DIR", test_data_dir)
        monkeypatch.setattr("src.prepare_phase2_dataset.OUTPUT_MANIFEST_DIR", test_manifest_dir)
        monkeypatch.setattr("src.prepare_phase2_dataset.OUTPUT_REPORT_DIR", test_report_dir)

        test_item = {
            "example_id": "SpotifyCares:1001:C1:R1",
            "group_id": "1001",
            "target_customer_tweet_id": "C1",
            "selected_brand_reply_tweet_id": "R1",
            "customer_text": "Need help with login",
            "brand_reply_text": "We are here to help!",
            "model_input_text": "[Customer_1] (TARGET CUSTOMER INQUIRY): Need help with login",
            "ancestor_turns": [
                {
                    "tweet_id": "C1",
                    "author_id": "Customer_1",
                    "inbound": 1,
                    "created_at": "Mon Oct 16 10:00:00 +0000 2017",
                    "text": "Need help with login"
                }
            ],
            "input_quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
            "reply_quality_flags": {"has_url": False, "private_handoff": False, "external_context_required": False, "suspected_multipart": False, "partial_text": False},
            "created_at": "Mon Oct 16 10:00:00 +0000 2017",
        }

        db_actual_checksum = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        export_phase2_outputs(
            dev_set=[test_item],
            eval_pool=[test_item],
            historical_corpus=[test_item],
            all_partitioned=[{**test_item, "partition": "dev"}],
            exclusion_summary={},
            leakage_report={},
            source_checksum=db_actual_checksum,
        )

        files_to_check = [
            test_data_dir / "spotify_knowledge.jsonl",
            test_data_dir / "dev_inputs.jsonl",
            test_data_dir / "eval_pool_inputs.jsonl",
            test_manifest_dir / "split_manifest.jsonl",
        ]

        for filepath in files_to_check:
            assert filepath.exists()
            with open(filepath, "r", encoding="utf-8") as f:
                lines = [json.loads(line) for line in f]
            assert len(lines) > 0
            for record in lines:
                assert "source_csv_sha256" in record
                assert record["source_csv_sha256"] == db_actual_checksum
