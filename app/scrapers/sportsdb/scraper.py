import requests
from bs4 import BeautifulSoup
import json
import os
from time import sleep
import hashlib
from datetime import datetime
from typing import Dict, Optional


class SportsDBScraper:
    def __init__(self):
        print("Initializing SportsDBScraper...")
        self.base_url = "https://www.thesportsdb.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # Set up data directory in the app root
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        self.players_file = os.path.join(self.data_dir, "players.json")
        os.makedirs(self.data_dir, exist_ok=True)
        print(f"Data directory created at: {self.data_dir}")

    def fetch_player_page(self, url: str) -> Optional[str]:
        """Fetch the HTML content of a player's page"""
        print(f"\nFetching page: {url}")
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_player_info(self, html: str) -> Dict:
        """Parse player information from HTML"""
        print("\nParsing player information...")
        soup = BeautifulSoup(html, "html.parser")

        # Get player name and description
        name = soup.find("font", size="5")
        name = name.text.strip() if name else "Unknown Player"

        description = soup.find("div", {"class": "col-sm-9"})
        if description:
            desc_text = description.find("p")
            description = desc_text.text.strip() if desc_text else ""
        else:
            description = ""

        # Get basic info
        bio_section = soup.find("div", {"class": "col-sm-3"})
        bio_info = {}
        if bio_section:
            for b in bio_section.find_all("b"):
                key = b.text.strip()
                value = b.next_sibling.text.strip() if b.next_sibling else ""
                if key and value:
                    bio_info[key] = value

        player_data = {
            "name": name,
            "description": description,
            "biographical_info": bio_info,
        }

        print(f"Successfully parsed data for: {name}")
        return player_data

    def save_players_json(self, player_data: Dict):
        """Save or update players.json file"""
        print("\nSaving to players.json...")
        existing_data = []

        # Read existing data if file exists
        if os.path.exists(self.players_file):
            with open(self.players_file, "r") as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    print("Error reading existing JSON file, starting fresh")
                    existing_data = []

        # Check if player already exists
        player_exists = False
        for i, player in enumerate(existing_data):
            if player.get("name") == player_data["name"]:
                existing_data[i] = player_data
                player_exists = True
                print(f"Updated existing player: {player_data['name']}")
                break

        # Add new player if doesn't exist
        if not player_exists:
            existing_data.append(player_data)
            print(f"Added new player: {player_data['name']}")

        # Write back to file
        with open(self.players_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
        print(f"Successfully saved to: {self.players_file}")

    def process_player(self, url: str):
        """Process a single player's page"""
        html = self.fetch_player_page(url)
        if html:
            player_data = self.parse_player_info(html)
            self.save_players_json(player_data)
            return True
        return False
