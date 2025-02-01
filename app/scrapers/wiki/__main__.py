import chromadb
import os
from .crawler import WikipediaCrawler


def main():
    # Initialize ChromaDB client
    chroma_client = chromadb.Client()

    # Create crawler instance
    crawler = WikipediaCrawler()
    # Start crawling from NFL league page
    print("Starting to crawl Wikipedia data")
    #print(crawler.players_data)
    crawler.run(crawler.players_names)


if __name__ == "__main__":
    main()
