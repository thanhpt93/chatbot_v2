"""
Master ETL Pipeline Orchestrator.
Coordinates:
1. Staging Data Extraction
2. Graph Transformation & Loading (Neo4j Architecture B)
3. Vector Embedding & Indexing (Qdrant ChatMessage Option A)
4. Interactive Graph Visualization Generation
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from etl.staging import StagingExtractor
from etl.graph.transformer import GraphTransformer
from etl.graph.loader import GraphLoader
from etl.vector.loader import VectorLoader

logger = logging.getLogger("etl.pipeline")

class ETLPipeline:
    def __init__(self, dump_path: Optional[Path] = None, force_restore: bool = False):
        self.staging = StagingExtractor(dump_path=dump_path, force_restore=force_restore)
        self.graph_transformer = GraphTransformer()
        self.graph_loader = GraphLoader()
        self._vector_loader = None  # Lazy load vector dependencies if needed
        self.force_restore = force_restore

    @property
    def vector_loader(self):
        if self._vector_loader is None:
            self._vector_loader = VectorLoader()
        return self._vector_loader

    def run(self, target: str = "all", generate_visualizer: bool = True) -> Dict[str, Any]:
        """
        Runs the ETL pipeline.
        target: 'all' | 'graph' | 'vector'
        """
        start_time = time.time()
        logger.info(f"=== Starting Groupware ETL Pipeline (target={target}) ===")

        # 1. Staging Extraction
        logger.info("[Step 1/3] Extracting staging data...")
        staging_data = self.staging.extract_all()
        table_counts = {k: len(v) for k, v in staging_data.items()}
        logger.info(f"Staging tables extracted: {table_counts}")

        graph_result = None
        vector_result = None

        # 2. Graph Pipeline
        if target in ("all", "graph"):
            logger.info("[Step 2/3] Processing Graph Pipeline (Architecture B)...")
            graph_data = self.graph_transformer.transform(staging_data)
            graph_result = self.graph_loader.load(graph_data)
            logger.info(f"Graph Pipeline completed: {graph_result['nodes_loaded']} nodes, {graph_result['relationships_loaded']} rels")

            if generate_visualizer:
                try:
                    from scripts.visualize_graph import generate_html
                    logger.info("Generating interactive graph visualizer (visualize_graph.html)...")
                    generate_html()
                except Exception as e:
                    logger.warning(f"Could not generate visualizer HTML: {e}")

        # 3. Vector Pipeline
        if target in ("all", "vector"):
            logger.info("[Step 3/3] Processing Vector Pipeline (ChatMessage Option A)...")
            vector_result = self.vector_loader.load_texts(staging_data)
            logger.info(f"Vector Pipeline completed: {vector_result['documents_indexed']} docs indexed")

        elapsed = round(time.time() - start_time, 2)
        logger.info(f"=== ETL Pipeline finished in {elapsed}s ===")

        return {
            "target": target,
            "elapsed_seconds": elapsed,
            "staging_tables": table_counts,
            "graph": graph_result,
            "vector": vector_result
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Groupware ETL Pipeline")
    parser.add_argument("--dump", type=str, default=None, help="Path to .dump file")
    parser.add_argument("--target", choices=["all", "graph", "vector"], default="all", help="Pipeline target")
    parser.add_argument("--force-restore", action="store_true", help="Force pg_restore rebuild of SQL dump")
    parser.add_argument("--no-visualize", action="store_true", help="Skip HTML visualizer generation")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    pipeline = ETLPipeline(dump_path=Path(args.dump) if args.dump else None, force_restore=args.force_restore)
    res = pipeline.run(target=args.target, generate_visualizer=not args.no_visualize)
    print("\nETL Pipeline Result Summary:")
    print(res)
