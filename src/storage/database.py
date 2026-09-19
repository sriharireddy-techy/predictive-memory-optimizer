"""
Phase 2: Historical Memory Storage Component.

Manages persistent relational storage for system and process telemetry using SQLite.
Supports:
- Schema initialization with indexing for rapid time-series querying.
- Atomic ACID transaction writes for system and batch process snapshots.
- Time-range queries for system and individual process histories.
- Rolling history retention pruning.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Union

from src.collector.monitor import SystemSnapshot, SystemMetrics, ProcessMetrics


class MetricsDatabase:
    """
    SQLite-backed relational storage for system and process telemetry time-series.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the database connection.
        
        Args:
            db_path: Filepath to SQLite database. If None or ':memory:',
                     an in-memory database is used (ideal for tests).
        """
        if db_path is None or db_path == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = str(db_path)
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_connection()
        self.init_schema()

    def _initialize_connection(self) -> None:
        """Establish SQLite connection with WAL mode and foreign keys enabled."""
        self._conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        
        # Pragmas for reliability and concurrency
        with self._conn:
            self._conn.execute("PRAGMA foreign_keys = ON;")
            if self.db_path != ":memory:":
                # Write-Ahead Logging (WAL) significantly improves concurrent read/write performance
                self._conn.execute("PRAGMA journal_mode = WAL;")
                self._conn.execute("PRAGMA synchronous = NORMAL;")

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._initialize_connection()
        return self._conn

    def init_schema(self) -> None:
        """Create tables and performance indexes if they do not exist."""
        with self.connection:
            # 1. System-level snapshots
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS system_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    total_ram_mb REAL NOT NULL,
                    available_ram_mb REAL NOT NULL,
                    used_ram_mb REAL NOT NULL,
                    percent_used REAL NOT NULL,
                    swap_total_mb REAL NOT NULL,
                    swap_used_mb REAL NOT NULL,
                    swap_percent REAL NOT NULL
                );
            """)

            # 2. Process-level snapshots
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS process_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_snapshot_id INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    pid INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    rss_mb REAL NOT NULL,
                    vms_mb REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    cpu_percent REAL NOT NULL,
                    num_threads INTEGER NOT NULL,
                    create_time REAL NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (system_snapshot_id) REFERENCES system_snapshots (id) ON DELETE CASCADE
                );
            """)

            # 3. Performance indexes for time-series queries
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_snapshots_ts
                ON system_snapshots (timestamp);
            """)
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_process_snapshots_pid_ts
                ON process_snapshots (pid, timestamp);
            """)
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_process_snapshots_sys_id
                ON process_snapshots (system_snapshot_id);
            """)

    def insert_snapshot(self, snapshot: SystemSnapshot) -> int:
        """
        Atomically persist a unified telemetry snapshot into SQLite.
        
        Args:
            snapshot: SystemSnapshot containing system and process records.

        Returns:
            int: The primary key ID of the inserted system snapshot.
        """
        sys = snapshot.system
        conn = self.connection

        with conn:
            cursor = conn.cursor()
            # 1. Insert system snapshot
            cursor.execute("""
                INSERT INTO system_snapshots (
                    timestamp, total_ram_mb, available_ram_mb, used_ram_mb,
                    percent_used, swap_total_mb, swap_used_mb, swap_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                sys.timestamp,
                sys.total_ram_mb,
                sys.available_ram_mb,
                sys.used_ram_mb,
                sys.percent_used,
                sys.swap_total_mb,
                sys.swap_used_mb,
                sys.swap_percent,
            ))
            system_id = cursor.lastrowid

            # 2. Batch insert process snapshots using executemany
            if snapshot.processes:
                process_rows = [
                    (
                        system_id,
                        snapshot.timestamp,
                        p.pid,
                        p.name,
                        p.rss_mb,
                        p.vms_mb,
                        p.memory_percent,
                        p.cpu_percent,
                        p.num_threads,
                        p.create_time,
                        p.status,
                    )
                    for p in snapshot.processes
                ]
                cursor.executemany("""
                    INSERT INTO process_snapshots (
                        system_snapshot_id, timestamp, pid, name,
                        rss_mb, vms_mb, memory_percent, cpu_percent,
                        num_threads, create_time, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, process_rows)

            return system_id

    def get_system_history(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve time-series system memory records within a time range.
        
        Returns records sorted chronologically (ascending).
        """
        query = "SELECT * FROM system_snapshots WHERE 1=1"
        params: List[Any] = []

        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp ASC"

        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_process_history(
        self,
        pid: int,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve historical samples for a specific PID, ordered chronologically.
        """
        query = "SELECT * FROM process_snapshots WHERE pid = ?"
        params: List[Any] = [pid]

        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp ASC"

        if limit is not None and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_active_pids_in_window(
        self,
        window_seconds: float,
        anchor_time: Optional[float] = None,
    ) -> List[int]:
        """
        Return all unique PIDs recorded within the window [anchor_time - window_seconds, anchor_time].
        If anchor_time is None, defaults to the latest recorded timestamp in the database (or current time).
        """
        cursor = self.connection.cursor()
        if anchor_time is None:
            cursor.execute("SELECT MAX(timestamp) FROM process_snapshots;")
            row = cursor.fetchone()
            anchor_time = float(row[0]) if (row and row[0] is not None) else time.time()

        cutoff = anchor_time - window_seconds
        cursor.execute("""
            SELECT DISTINCT pid FROM process_snapshots
            WHERE timestamp >= ? AND timestamp <= ? ORDER BY pid ASC;
        """, (cutoff, anchor_time))
        return [row[0] for row in cursor.fetchall()]

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the most recently inserted system snapshot with its processes.
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM system_snapshots ORDER BY timestamp DESC LIMIT 1;
        """)
        latest_sys = cursor.fetchone()
        if not latest_sys:
            return None

        sys_dict = dict(latest_sys)
        sys_id = sys_dict["id"]

        cursor.execute("""
            SELECT * FROM process_snapshots
            WHERE system_snapshot_id = ?
            ORDER BY rss_mb DESC;
        """, (sys_id,))
        proc_list = [dict(row) for row in cursor.fetchall()]

        return {
            "system": sys_dict,
            "processes": proc_list,
        }

    def prune_history(self, retention_seconds: float) -> int:
        """
        Delete snapshots older than `retention_seconds` to constrain database size.
        
        Args:
            retention_seconds: Data older than (now - retention_seconds) is purged.

        Returns:
            int: Number of system snapshot records pruned.
        """
        cutoff = time.time() - retention_seconds
        with self.connection:
            cursor = self.connection.cursor()
            cursor.execute("""
                DELETE FROM system_snapshots WHERE timestamp < ?;
            """, (cutoff,))
            pruned_count = cursor.rowcount
            return pruned_count

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "MetricsDatabase":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
