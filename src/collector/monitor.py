"""
Phase 1: Process and Memory Monitoring Component.

Provides lightweight, robust telemetry collection for:
1. System-wide memory (RAM, Swap, percentage utilization).
2. Process-level metrics (PID, Name, RSS, VMS, CPU %, Threads, Creation time).
Handles transient processes (NoSuchProcess) and permission boundaries (AccessDenied).
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import time
from typing import List, Optional
import psutil

BYTES_IN_MB = 1024 * 1024


@dataclass(frozen=True)
class SystemMetrics:
    """System-level memory counters at a specific instant."""
    timestamp: float
    total_ram_mb: float
    available_ram_mb: float
    used_ram_mb: float
    percent_used: float
    swap_total_mb: float
    swap_used_mb: float
    swap_percent: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProcessMetrics:
    """Process-level resource utilization attributes."""
    pid: int
    name: str
    rss_mb: float
    vms_mb: float
    memory_percent: float
    cpu_percent: float
    num_threads: int
    create_time: float
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SystemSnapshot:
    """A combined snapshot of system memory and active processes."""
    timestamp: float
    system: SystemMetrics
    processes: List[ProcessMetrics]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "system": self.system.to_dict(),
            "processes": [p.to_dict() for p in self.processes],
        }


def get_system_metrics() -> SystemMetrics:
    """
    Collect instantaneous system-wide memory metrics.
    
    Returns:
        SystemMetrics: Normalized system memory counters in Megabytes.
    """
    now = time.time()
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return SystemMetrics(
        timestamp=now,
        total_ram_mb=round(vm.total / BYTES_IN_MB, 2),
        available_ram_mb=round(vm.available / BYTES_IN_MB, 2),
        used_ram_mb=round(vm.used / BYTES_IN_MB, 2),
        percent_used=round(vm.percent, 2),
        swap_total_mb=round(swap.total / BYTES_IN_MB, 2),
        swap_used_mb=round(swap.used / BYTES_IN_MB, 2),
        swap_percent=round(swap.percent, 2),
    )


def get_process_metrics(filter_accessible_only: bool = True) -> List[ProcessMetrics]:
    """
    Query all active processes and collect resource utilization attributes.
    
    Robustly catches NoSuchProcess, AccessDenied, and ZombieProcess exceptions
    which naturally occur during concurrency and OS security checks.

    Args:
        filter_accessible_only: If True, skips processes that couldn't be read.

    Returns:
        List[ProcessMetrics]: List of active process records.
    """
    process_records: List[ProcessMetrics] = []
    
    # Using process_iter with pre-selected attributes significantly reduces
    # overhead compared to repeated individual system calls.
    attributes = [
        "pid",
        "name",
        "memory_info",
        "memory_percent",
        "cpu_percent",
        "num_threads",
        "create_time",
        "status",
    ]

    for proc in psutil.process_iter(attrs=attributes):
        try:
            info = proc.info
            mem_info = info.get("memory_info")
            if mem_info is None:
                continue

            rss_mb = round(mem_info.rss / BYTES_IN_MB, 2)
            vms_mb = round(mem_info.vms / BYTES_IN_MB, 2)

            record = ProcessMetrics(
                pid=int(info.get("pid") or 0),
                name=str(info.get("name") or "unknown"),
                rss_mb=rss_mb,
                vms_mb=vms_mb,
                memory_percent=round(float(info.get("memory_percent") or 0.0), 2),
                cpu_percent=round(float(info.get("cpu_percent") or 0.0), 2),
                num_threads=int(info.get("num_threads") or 0),
                create_time=float(info.get("create_time") or 0.0),
                status=str(info.get("status") or "running"),
            )
            process_records.append(record)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Process terminated or protected by OS kernel security
            if not filter_accessible_only:
                pass
            continue

    return process_records


def collect_snapshot(top_n_processes: Optional[int] = None) -> SystemSnapshot:
    """
    Capture a unified telemetry snapshot of system and process memory.
    
    Args:
        top_n_processes: Optional limit to keep only top N processes by RSS.
                         If None, keeps all accessible processes.

    Returns:
        SystemSnapshot: Contains system counters and process list.
    """
    now = time.time()
    sys_metrics = get_system_metrics()
    processes = get_process_metrics()

    # Sort processes descending by physical memory (RSS)
    processes.sort(key=lambda p: p.rss_mb, reverse=True)

    if top_n_processes is not None and top_n_processes > 0:
        processes = processes[:top_n_processes]

    return SystemSnapshot(
        timestamp=now,
        system=sys_metrics,
        processes=processes,
    )


def format_snapshot(snapshot: SystemSnapshot, top_n: int = 10) -> str:
    """
    Format a snapshot into a readable text table suitable for console display.
    """
    ts_str = datetime.fromtimestamp(snapshot.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    sys_info = snapshot.system

    lines = [
        "=" * 80,
        f" SYSTEM & PROCESS RESOURCE SNAPSHOT - {ts_str}",
        "=" * 80,
        f"RAM Total     : {sys_info.total_ram_mb:>10.2f} MB",
        f"RAM Used      : {sys_info.used_ram_mb:>10.2f} MB ({sys_info.percent_used:.1f}%)",
        f"RAM Available : {sys_info.available_ram_mb:>10.2f} MB",
        f"Swap Total    : {sys_info.swap_total_mb:>10.2f} MB",
        f"Swap Used     : {sys_info.swap_used_mb:>10.2f} MB ({sys_info.swap_percent:.1f}%)",
        "-" * 80,
        f"Top {top_n} Processes by Physical Memory (RSS):",
        f"{'PID':<8} {'Name':<28} {'RSS (MB)':<12} {'VMS (MB)':<12} {'Mem %':<8} {'Threads':<8}",
        "-" * 80,
    ]

    for p in snapshot.processes[:top_n]:
        # Truncate long process names for aligned terminal display
        name_display = (p.name[:25] + "...") if len(p.name) > 28 else p.name
        lines.append(
            f"{p.pid:<8} {name_display:<28} {p.rss_mb:>10.2f}  {p.vms_mb:>10.2f}  "
            f"{p.memory_percent:>6.1f}% {p.num_threads:>7}"
        )

    lines.append("=" * 80)
    return "\n".join(lines)


if __name__ == "__main__":
    # Self-test / direct execution display
    snapshot = collect_snapshot(top_n_processes=15)
    print(format_snapshot(snapshot, top_n=15))
