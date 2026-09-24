from src.storage.database import MetricsDatabase
from src.storage.service import collect_and_store_samples

def main():
    db = MetricsDatabase("data/memory_monitor.db")

    print("Starting Phase 2 live test...")
    print("Collecting 5 snapshots, 2 seconds apart...\n")

    ids = collect_and_store_samples(
        db=db,
        sample_count=5,
        interval_seconds=2,
        top_n=10,
    )

    print("\nSaved snapshot IDs:")
    print(ids)

    print("\nLatest stored snapshot:")
    latest = db.get_latest_snapshot()

    if latest:
        system = latest["system"]

        print(f"RAM Used      : {system['used_ram_mb']:.2f} MB")
        print(f"RAM Available : {system['available_ram_mb']:.2f} MB")
        print(f"RAM Usage     : {system['percent_used']:.1f}%")

        print("\nTop stored processes:")

        for process in latest["processes"][:10]:
            print(
                f"{process['pid']:<8}"
                f"{process['name'][:25]:<25}"
                f"{process['rss_mb']:>10.2f} MB"
            )

    db.close()


if __name__ == "__main__":
    main()