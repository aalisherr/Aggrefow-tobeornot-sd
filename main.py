import asyncio
from loguru import logger
from app.config.loader import AppConfig
from app.utils.logger import setup_logging
from app.orchestrator import Orchestrator


async def main():
    """Main entry point"""
    setup_logging()
    logger.info("🚀 Starting Crypto Announcements Aggregator V2")

    # Load configuration from YAML files
    config = AppConfig.load("config")

    # Create and run orchestrator
    orchestrator = Orchestrator(config)

    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        await orchestrator.cleanup()
        logger.info("✅ Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())