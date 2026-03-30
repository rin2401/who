import argparse
import asyncio
import sys

sys.path.insert(0, ".")

from src.database import connect_db, close_db
from src.crawler.crawler import crawl_company


def main():
    parser = argparse.ArgumentParser(description="Crawl LinkedIn company profiles")
    parser.add_argument("--company", required=True, help="Company slug (e.g., zalo)")
    args = parser.parse_args()
    
    async def run():
        await connect_db()
        try:
            await crawl_company(args.company)
        finally:
            await close_db()
    
    asyncio.run(run())


if __name__ == "__main__":
    main()
