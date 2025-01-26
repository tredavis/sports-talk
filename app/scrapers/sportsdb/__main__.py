import chromadb
import os
from .crawler import SportsDBCrawler


def main():
    # Initialize ChromaDB client
    chroma_client = chromadb.Client()

    # Create crawler instance
    crawler = SportsDBCrawler()

    # Start crawling from NFL league page
    print("Starting to crawl NFL data")
    crawler.run()


if __name__ == "__main__":
    main()
