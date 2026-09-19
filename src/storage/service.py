"""
Phase 2 Service: Periodic Sampling and Historical Ingestion Engine.

Provides helper routines to sample OS telemetry and persist records into SQLite.
"""

import time
from typing import List, Optional
from src.collector.monitor import collect_snapshot, SystemSnapshot
from src.storage.database import MetricsDatabase


def record_current_snapshot(
    db: MetricsDatabase,
    top_n: Optional[int] = None,
) -> int:
    """
    Capture a live snapshot from the OS and persist it into the historical database.

    Args:
        db: Active MetricsDatabase instance.
        top_n: Optional filter to keep top N processes by RSS.

    Returns:
        int: The inserted system snapshot ID.
    """
    snapshot = collect_snapshot(top_n_processes=top_n)
    return db.insert_snapshot(snapshot)


def collect_and_store_samples(
    db: MetricsDatabase,
    sample_count: int,
    interval_seconds: float = 1.0,
    top_n: Optional[int] = 20,
) -> List[int]:
    """
    Perform periodic sampling of system and process memory over time.

    Args:
        db: Active MetricsDatabase instance.
        sample_count: Total number of iterations to collect.
        interval_seconds: Delay in seconds between consecutive samples.
        top_n: Limit top N processes per snapshot.

    Returns:
        List[int]: List of inserted system snapshot IDs.
    """
    inserted_ids: List[int] = []
    for i in range(sample_count):
        sys_id = record_current_snapshot(db, top_n=top_n)
        inserted_ids.append(sys_id)
        if i < sample_count - 1:
            time.sleep(interval_seconds)
    return inserted_ids
