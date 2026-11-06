"""
Master ETL Pipeline CLI & Automation Runner.

Usage:
  # 1. Run pipeline on the latest dump in database/
  python scripts/run_etl_pipeline.py

  # 2. Run pipeline on a specific dump file
  python scripts/run_etl_pipeline.py --dump database/my_new_backup.dump

  # 3. Target specific pipelines (all | graph | vector)
  python scripts/run_etl_pipeline.py --target graph
  python scripts/run_etl_pipeline.py --target vector

  # 4. Watch database directory for new .dump files and auto-run
  python scripts/run_etl_pipeline.py --watch
"""

import sys
import time
import os
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.pipeline import ETLPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("run_etl_pipeline")


def run_single(dump_path=None, target="all", force_restore=False, visualize=True):
    print("=" * 70)
    print("          GROUPWARE AI CHATBOT - AUTOMATED ETL PIPELINE           ")
    print("=" * 70)
    
    pipeline = ETLPipeline(
        dump_path=Path(dump_path) if dump_path else None,
        force_restore=force_restore
    )
    
    print(f"Target Mode       : {target.upper()}")
    print(f"Dump Source File  : {pipeline.staging.dump_path}")
    print(f"SQL Cache File    : {pipeline.staging.dump_sql_path}")
    print(f"Auto-Restore Dump : {'Forced' if force_restore else 'Smart timestamp detection'}")
    print("-" * 70)

    result = pipeline.run(target=target, generate_visualizer=visualize)

    print("\n" + "=" * 70)
    print("                    PIPELINE EXECUTION SUMMARY                    ")
    print("=" * 70)
    print(f"Status            : SUCCESS")
    print(f"Execution Time    : {result['elapsed_seconds']}s")
    
    if result.get("graph"):
        g = result["graph"]
        print("\n--- GRAPH ONTOLOGY (Architecture B) ---")
        print(f"  Nodes Loaded    : {g.get('nodes_loaded', 0):,}")
        print(f"  Rels Loaded     : {g.get('relationships_loaded', 0):,}")
        print(f"  Live Neo4j      : {'Connected & Ingested' if g.get('live_neo4j') else 'Offline (Exported locally)'}")
        print(f"  Snapshot JSON   : {g.get('export_file')}")
        print(f"  Cypher Script   : {g.get('cypher_script')}")
        if visualize:
            print(f"  HTML Visualizer : {ROOT / 'data' / 'graph_export' / 'visualize_graph.html'}")

    if result.get("vector"):
        v = result["vector"]
        print("\n--- VECTOR DB (Qdrant Multi-Tenant) ---")
        print(f"  Collection Name : {v.get('collection_name')}")
        print(f"  Docs Indexed    : {v.get('documents_indexed', 0):,}")
        if "breakdown" in v:
            for k, val in v["breakdown"].items():
                print(f"    - {k:18}: {val:,}")

    print("=" * 70)
    return result


def watch_directory(interval_seconds=10, target="all"):
    db_dir = ROOT / "database"
    db_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("         WATCHER MODE STARTED - WAITING FOR NEW .DUMP FILES         ")
    print("=" * 70)
    print(f"Monitoring Directory : {db_dir}")
    print(f"Check Interval       : {interval_seconds}s")
    print("Press Ctrl+C to stop watching.\n")

    last_seen_mtimes = {}

    def get_dump_files():
        return {f: f.stat().st_mtime for f in db_dir.glob("*.dump")}

    last_seen_mtimes = get_dump_files()

    try:
        while True:
            time.sleep(interval_seconds)
            current_files = get_dump_files()
            
            # Check for newly added or modified dump files
            new_or_modified = []
            for f, mtime in current_files.items():
                if f not in last_seen_mtimes or mtime > last_seen_mtimes[f]:
                    new_or_modified.append(f)

            if new_or_modified:
                new_or_modified.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_dump = new_or_modified[0]
                logger.info(f"Detected new/modified database dump: {latest_dump.name}")
                logger.info("Auto-triggering ETL Pipeline...")
                try:
                    run_single(dump_path=latest_dump, target=target, force_restore=True, visualize=True)
                except Exception as e:
                    logger.error(f"Error during automated ETL run: {e}", exc_info=True)
                last_seen_mtimes = current_files

    except KeyboardInterrupt:
        print("\nWatcher mode terminated by user.")


def main():
    parser = argparse.ArgumentParser(description="Groupware ETL Pipeline Automation Runner")
    parser.add_argument("--dump", type=str, default=None, help="Path to input .dump file")
    parser.add_argument("--target", choices=["all", "graph", "vector"], default="all", help="Target pipeline to run")
    parser.add_argument("--force-restore", action="store_true", help="Force pg_restore dump to SQL cache")
    parser.add_argument("--no-visualize", action="store_true", help="Skip HTML graph visualizer generation")
    parser.add_argument("--watch", action="store_true", help="Run in continuous background watcher mode")
    parser.add_argument("--interval", type=int, default=10, help="Watcher check interval in seconds (default: 10)")
    args = parser.parse_args()

    if args.watch:
        watch_directory(interval_seconds=args.interval, target=args.target)
    else:
        run_single(
            dump_path=args.dump,
            target=args.target,
            force_restore=args.force_restore,
            visualize=not args.no_visualize
        )


if __name__ == "__main__":
    main()
