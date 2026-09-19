"""
Phase 2 Tests: Historical Memory Storage Component.

Tests:
1. SQLite database initialization (in-memory and file-based).
2. Schema and index creation.
3. Insertion of unified telemetry snapshots (ACID transactions).
4. Time-series querying for system memory history.
5. Time-series querying for specific process history.
6. Foreign key integrity and cascading deletes.
7. Filtering by timestamp ranges and limits.
8. History retention pruning.
9. Periodic sampling service integration.
"""

from pathlib import Path
import time
import pytest

from src.collector.monitor import SystemMetrics, ProcessMetrics, SystemSnapshot
from src.storage.database import MetricsDatabase
from src.storage.service import record_current_snapshot, collect_and_store_samples


def make_dummy_snapshot(timestamp: float, pid_offset: int = 0) -> SystemSnapshot:
    """Helper to generate consistent synthetic snapshots for testing."""
    sys_metric = SystemMetrics(
        timestamp=timestamp,
        total_ram_mb=16384.0,
        available_ram_mb=8192.0,
        used_ram_mb=8192.0,
        percent_used=50.0,
        swap_total_mb=4096.0,
        swap_used_mb=512.0,
        swap_percent=12.5,
    )
    p1 = ProcessMetrics(
        pid=100 + pid_offset,
        name="test_worker.exe",
        rss_mb=256.0,
        vms_mb=512.0,
        memory_percent=1.56,
        cpu_percent=2.0,
        num_threads=4,
        create_time=1700000000.0,
        status="running",
    )
    p2 = ProcessMetrics(
        pid=200 + pid_offset,
        name="test_service.exe",
        rss_mb=512.0,
        vms_mb=1024.0,
        memory_percent=3.12,
        cpu_percent=0.5,
        num_threads=8,
        create_time=1700000050.0,
        status="running",
    )
    return SystemSnapshot(
        timestamp=timestamp,
        system=sys_metric,
        processes=[p1, p2],
    )


def test_db_init_and_schema():
    """Verify that tables and indexes are created successfully."""
    with MetricsDatabase(":memory:") as db:
        cursor = db.connection.cursor()

        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "system_snapshots" in tables
        assert "process_snapshots" in tables

        # Verify indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = [row[0] for row in cursor.fetchall()]
        assert "idx_system_snapshots_ts" in indexes
        assert "idx_process_snapshots_pid_ts" in indexes
        assert "idx_process_snapshots_sys_id" in indexes


def test_insert_and_retrieve_snapshot():
    """Verify inserting and querying a complete snapshot."""
    t0 = 1700001000.0
    snapshot = make_dummy_snapshot(timestamp=t0)

    with MetricsDatabase(":memory:") as db:
        sys_id = db.insert_snapshot(snapshot)
        assert sys_id > 0

        # Retrieve latest snapshot
        latest = db.get_latest_snapshot()
        assert latest is not None
        assert latest["system"]["id"] == sys_id
        assert latest["system"]["timestamp"] == t0
        assert latest["system"]["total_ram_mb"] == 16384.0
        assert len(latest["processes"]) == 2

        # Verify process details
        proc_names = [p["name"] for p in latest["processes"]]
        assert "test_worker.exe" in proc_names
        assert "test_service.exe" in proc_names


def test_system_history_query():
    """Verify querying system history with time boundaries and limits."""
    with MetricsDatabase(":memory:") as db:
        base_t = 1000.0
        # Insert 5 consecutive snapshots
        for i in range(5):
            snap = make_dummy_snapshot(timestamp=base_t + (i * 10))
            db.insert_snapshot(snap)

        # Retrieve all
        all_records = db.get_system_history()
        assert len(all_records) == 5
        assert all_records[0]["timestamp"] == 1000.0
        assert all_records[4]["timestamp"] == 1040.0

        # Range query
        subset = db.get_system_history(start_time=1010.0, end_time=1030.0)
        assert len(subset) == 3
        assert [r["timestamp"] for r in subset] == [1010.0, 1020.0, 1030.0]

        # Limit query
        limited = db.get_system_history(limit=2)
        assert len(limited) == 2


def test_process_history_query():
    """Verify querying process time-series history for a specific PID."""
    with MetricsDatabase(":memory:") as db:
        for i in range(4):
            # Same PID 100 with increasing RSS memory
            snap = SystemSnapshot(
                timestamp=100.0 + i,
                system=SystemMetrics(
                    timestamp=100.0 + i,
                    total_ram_mb=16000.0,
                    available_ram_mb=8000.0,
                    used_ram_mb=8000.0,
                    percent_used=50.0,
                    swap_total_mb=4000.0,
                    swap_used_mb=0.0,
                    swap_percent=0.0,
                ),
                processes=[
                    ProcessMetrics(
                        pid=100,
                        name="growing_proc.exe",
                        rss_mb=100.0 + (i * 10),
                        vms_mb=200.0,
                        memory_percent=1.0,
                        cpu_percent=1.0,
                        num_threads=2,
                        create_time=50.0,
                        status="running",
                    )
                ],
            )
            db.insert_snapshot(snap)

        history = db.get_process_history(pid=100)
        assert len(history) == 4
        assert [r["rss_mb"] for r in history] == [100.0, 110.0, 120.0, 130.0]

        # Non-existent PID returns empty list
        empty_history = db.get_process_history(pid=9999)
        assert empty_history == []


def test_foreign_key_cascading_delete():
    """Verify that deleting a system snapshot automatically deletes associated process snapshots."""
    with MetricsDatabase(":memory:") as db:
        snap = make_dummy_snapshot(timestamp=500.0)
        sys_id = db.insert_snapshot(snap)

        # Confirm process rows exist
        cursor = db.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM process_snapshots WHERE system_snapshot_id = ?", (sys_id,))
        assert cursor.fetchone()[0] == 2

        # Delete system snapshot
        with db.connection:
            db.connection.execute("DELETE FROM system_snapshots WHERE id = ?", (sys_id,))

        # Associated process rows must be deleted by cascade
        cursor.execute("SELECT COUNT(*) FROM process_snapshots WHERE system_snapshot_id = ?", (sys_id,))
        assert cursor.fetchone()[0] == 0


def test_prune_history():
    """Verify rolling retention pruning removes older records."""
    with MetricsDatabase(":memory:") as db:
        now = time.time()
        # Old snapshot (1000 seconds ago)
        old_snap = make_dummy_snapshot(timestamp=now - 1000)
        db.insert_snapshot(old_snap)

        # Recent snapshot (10 seconds ago)
        recent_snap = make_dummy_snapshot(timestamp=now - 10)
        db.insert_snapshot(recent_snap)

        assert len(db.get_system_history()) == 2

        # Prune older than 300 seconds
        pruned_count = db.prune_history(retention_seconds=300)
        assert pruned_count == 1

        remaining = db.get_system_history()
        assert len(remaining) == 1
        assert remaining[0]["timestamp"] == recent_snap.timestamp


def test_file_based_db(tmp_path: Path):
    """Verify persistence on a physical disk file."""
    db_file = tmp_path / "test_metrics.db"
    assert not db_file.exists()

    with MetricsDatabase(db_file) as db:
        snap = make_dummy_snapshot(timestamp=2000.0)
        db.insert_snapshot(snap)

    assert db_file.exists()

    # Re-open the database and verify data persists
    with MetricsDatabase(db_file) as db2:
        records = db2.get_system_history()
        assert len(records) == 1
        assert records[0]["timestamp"] == 2000.0


def test_record_current_snapshot_live():
    """Verify recording a real live snapshot from the OS collector."""
    with MetricsDatabase(":memory:") as db:
        sys_id = record_current_snapshot(db, top_n=5)
        assert sys_id > 0

        latest = db.get_latest_snapshot()
        assert latest is not None
        assert latest["system"]["total_ram_mb"] > 0
        assert len(latest["processes"]) <= 5
