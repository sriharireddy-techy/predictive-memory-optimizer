"""
Phase 1 Tests: Process and Memory Monitoring Component.

Tests:
1. System memory metrics collection and range validation.
2. Process metrics collection and data integrity.
3. Handling of transient/vanished processes (NoSuchProcess).
4. Handling of protected kernel/system processes (AccessDenied).
5. Handling of zombie processes (ZombieProcess).
6. Snapshot aggregation, sorting by RSS, and top_n truncation.
7. Output format rendering.
"""

from unittest.mock import MagicMock, patch
import psutil
import pytest

from src.collector.monitor import (
    SystemMetrics,
    ProcessMetrics,
    SystemSnapshot,
    get_system_metrics,
    get_process_metrics,
    collect_snapshot,
    format_snapshot,
)


def test_get_system_metrics_real():
    """Verify live system metrics collection returns sensible values."""
    metrics = get_system_metrics()

    assert isinstance(metrics, SystemMetrics)
    assert metrics.timestamp > 0
    assert metrics.total_ram_mb > 0
    assert metrics.available_ram_mb > 0
    assert metrics.used_ram_mb > 0
    assert 0.0 <= metrics.percent_used <= 100.0
    assert metrics.swap_total_mb >= 0
    assert metrics.swap_used_mb >= 0
    assert 0.0 <= metrics.swap_percent <= 100.0


def test_system_metrics_serialization():
    """Verify SystemMetrics can be serialized to a dictionary."""
    metrics = get_system_metrics()
    d = metrics.to_dict()
    assert isinstance(d, dict)
    assert "total_ram_mb" in d
    assert "available_ram_mb" in d
    assert "percent_used" in d


def test_get_process_metrics_real():
    """Verify live process metrics collection returns active processes."""
    processes = get_process_metrics()

    assert isinstance(processes, list)
    assert len(processes) > 0, "There should be at least one running process on the host"

    # Inspect the first process record
    p = processes[0]
    assert isinstance(p, ProcessMetrics)
    assert isinstance(p.pid, int)
    assert isinstance(p.name, str)
    assert p.rss_mb >= 0.0
    assert p.vms_mb >= 0.0
    assert p.num_threads >= 0
    assert p.create_time >= 0.0


def test_collect_snapshot_structure_and_sorting():
    """Verify collect_snapshot aggregates system and sorted processes."""
    snapshot = collect_snapshot(top_n_processes=5)

    assert isinstance(snapshot, SystemSnapshot)
    assert isinstance(snapshot.system, SystemMetrics)
    assert len(snapshot.processes) <= 5

    # Check sorting: RSS should be descending
    rss_values = [p.rss_mb for p in snapshot.processes]
    assert rss_values == sorted(rss_values, reverse=True), "Processes must be sorted descending by RSS"


def test_format_snapshot():
    """Verify format_snapshot produces a formatted report string."""
    snapshot = collect_snapshot(top_n_processes=3)
    output = format_snapshot(snapshot, top_n=3)

    assert isinstance(output, str)
    assert "SYSTEM & PROCESS RESOURCE SNAPSHOT" in output
    assert "RAM Total" in output
    assert "Top 3 Processes" in output


def test_handle_nosuchprocess_and_accessdenied():
    """
    Simulate processes raising NoSuchProcess, AccessDenied, and ZombieProcess during iteration.
    Verify that the collector gracefully catches them and continues without crashing.
    """
    class DummyProc:
        def __init__(self, info_dict=None, exc=None):
            self._info = info_dict
            self._exc = exc

        @property
        def info(self):
            if self._exc:
                raise self._exc
            return self._info

    # 1: Valid process
    p1 = DummyProc(info_dict={
        "pid": 1001,
        "name": "valid_worker.exe",
        "memory_info": MagicMock(rss=104857600, vms=209715200),  # 100MB RSS, 200MB VMS
        "memory_percent": 2.5,
        "cpu_percent": 1.2,
        "num_threads": 4,
        "create_time": 1700000000.0,
        "status": "running",
    })

    # 2: Process that terminates between enumeration and inspection (NoSuchProcess)
    p2 = DummyProc(exc=psutil.NoSuchProcess(pid=1002))

    # 3: Protected OS system process (AccessDenied)
    p3 = DummyProc(exc=psutil.AccessDenied(pid=4))

    # 4: Dead/zombie process (ZombieProcess)
    p4 = DummyProc(exc=psutil.ZombieProcess(pid=1004))

    # 5: Another valid process
    p5 = DummyProc(info_dict={
        "pid": 1005,
        "name": "browser.exe",
        "memory_info": MagicMock(rss=524288000, vms=1048576000),  # 500MB RSS
        "memory_percent": 8.0,
        "cpu_percent": 4.5,
        "num_threads": 12,
        "create_time": 1700000100.0,
        "status": "running",
    })

    with patch("psutil.process_iter", return_value=[p1, p2, p3, p4, p5]):
        results = get_process_metrics()

    # Only p1 and p5 should be collected; p2, p3, and p4 must be safely ignored
    assert len(results) == 2
    assert results[0].pid == 1001
    assert results[0].name == "valid_worker.exe"
    assert results[0].rss_mb == 100.0
    assert results[1].pid == 1005
    assert results[1].name == "browser.exe"
    assert results[1].rss_mb == 500.0
