#!/usr/bin/env python3
"""Run the indexing worker."""

import asyncio
import signal
import sys
from src.workers.indexing_worker import IndexingWorker
from src.utils.logging import get_logger

logger = get_logger(__name__)

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    logger.info("shutdown_signal_received", signal=sig)
    sys.exit(0)

async def main():
    """Main entry point for worker."""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run worker
    worker = IndexingWorker()
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("worker_interrupted")
        worker.stop()
    except Exception as e:
        logger.error("worker_error", error=str(e))
        raise

if __name__ == "__main__":
    asyncio.run(main())