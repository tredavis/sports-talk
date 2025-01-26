from bs4 import BeautifulSoup
from time import sleep
from typing import Set, Dict, List
import json
import os
import requests
from datetime import datetime
from urllib.parse import urljoin
import re
import traceback


class SportsDBCrawler:
    def __init__(self):
        self.base_url = "https://www.thesportsdb.com"
        self.processed_urls = set()
        self.teams_data = {}
        self.players_data = []
        self.save_frequency = 10  # Save after every 10 players
        self.backup_frequency = 50  # Create backup every 50 players
        self.player_count = 0

        # Create necessary directories
        os.makedirs("app/data/backups", exist_ok=True)
        os.makedirs("app/data", exist_ok=True)

        # Initialize players.json if it doesn't exist
        players_file = "app/data/players.json"
        if not os.path.exists(players_file):
            with open(players_file, "w", encoding="utf-8") as f:
                json.dump({"players": []}, f, indent=2, ensure_ascii=False)
            print("Created new players.json file")

        # Load existing players at initialization
        self.load_existing_players()

    def fetch_page(self, url: str) -> str:
        """Fetch the content of a web page"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {str(e)}")
            return ""

    def extract_team_data(self, html: str, team_url: str) -> Dict:
        """Extract team information from team page"""
        soup = BeautifulSoup(html, "html.parser")
        team_data = {"url": team_url, "name": "", "players": []}

        try:
            # Extract team name from the breadcrumb navigation (5th anchor)
            breadcrumbs = soup.select("section#feature div.col-sm-12 a")
            if len(breadcrumbs) >= 5:
                team_name = breadcrumbs[4].text.strip()  # 5th anchor (index 4)
                team_data["name"] = team_name
                print(f"Found team name from breadcrumb: {team_name}")
            else:
                print(
                    f"Warning: Not enough breadcrumbs to extract team name for {team_url}"
                )

            # Find all player links in the team roster section
            player_links = soup.select("div.col-sm-9 table a[href^='/player/']")
            seen_urls = set()

            for link in player_links:
                player_url = urljoin("https://www.thesportsdb.com", link["href"])
                if player_url not in seen_urls:
                    team_data["players"].append(player_url)
                    seen_urls.add(player_url)

        except Exception as e:
            print(f"Error processing team {team_url}: {str(e)}")

        return team_data

    def extract_player_data(self, html: str, player_url: str):
        """Extract player data from the HTML content of a player page"""
        player_data = {
            "url": player_url,
            "name": "",
            "number": "",
            "position": "",
            "birth_year": None,
            "birth_place": "",
            "height": "",
            "weight": "",
            "team": "",
            "status": "",
            "nationality": "",
            "description": "",
            "honors": [],
        }

        try:
            soup = BeautifulSoup(html, "html.parser")

            # 1. Extract Player Name
            name_tag = soup.find("b", text=re.compile(r"^Name$", re.I))
            if name_tag:
                # Navigate to the <font> tag containing the <a> tag with the name
                # Handle possible malformed <a> tags
                font_tag = name_tag.find_next_sibling("br")
                if font_tag:
                    font_tag = font_tag.find_next_sibling("font")
                if font_tag:
                    # Extract text directly from the font tag
                    # Handle cases where <a> tag is self-closed improperly
                    name_text = font_tag.get_text(separator=" ", strip=True)
                    name_text = re.sub(r"^/[^/]+-/", "", name_text).strip()
                    player_data["name"] = name_text
                    print(f"Extracted player name: {player_data['name']}")
                else:
                    print(
                        f"Warning: <font> tag not found after <b>Name</b> for {player_url}"
                    )
            else:
                print(f"Warning: <b>Name</b> tag not found for {player_url}")

            # 2. Extract Other Fields
            fields = {
                "Born": "birth_year",
                "Birth Place": "birth_place",
                "Position": "position",
                "Status": "status",
                "Ethnicity": "nationality",
                "Team Number": "number",
                "Height": "height",
                "Weight": "weight",
                "Team": "team",
            }

            for field_label, field_key in fields.items():
                field_tag = soup.find("b", text=re.compile(rf"^{field_label}$", re.I))
                if field_tag:
                    field_value_tag = field_tag.find_next_sibling("br")
                    if field_value_tag:
                        # Extract the text following the <br> tag
                        next_element = field_value_tag.next_sibling
                        # Handle cases where next_element is NavigableString or a Tag
                        if next_element:
                            if isinstance(next_element, str):
                                value = next_element.strip()
                            else:
                                value = next_element.get_text(separator=" ", strip=True)
                            if field_key == "birth_year":
                                # Extract year using regex
                                year_match = re.search(r"\d{4}", value)
                                if year_match:
                                    player_data[field_key] = int(year_match.group())
                                    print(
                                        f"Extracted {field_label}: {player_data[field_key]}"
                                    )
                            else:
                                player_data[field_key] = value
                                print(
                                    f"Extracted {field_label}: {player_data[field_key]}"
                                )
                        else:
                            print(
                                f"Warning: No value found for {field_label} in {player_url}"
                            )
                    else:
                        print(
                            f"Warning: <br> tag not found after <b>{field_label}</b> for {player_url}"
                        )
                else:
                    print(
                        f"Warning: <b>{field_label}</b> tag not found for {player_url}"
                    )

            # 3. Extract Description
            description_tag = soup.find("b", text=re.compile(r"^Description$", re.I))
            if description_tag:
                # The description seems to be within the next <p> tag after some <br> and <a> tags
                # Navigate to the <p> tag
                # Start by finding the next sibling after <b>Description</b>
                next_sibling = description_tag.find_next_sibling()
                while next_sibling and next_sibling.name != "p":
                    next_sibling = next_sibling.find_next_sibling()
                if next_sibling and next_sibling.name == "p":
                    description_text = next_sibling.get_text(separator=" ", strip=True)
                    player_data["description"] = description_text
                    print(f"Extracted description for {player_data['name']}")
                else:
                    print(
                        f"Warning: <p> tag with description not found for {player_url}"
                    )
            else:
                print(f"Warning: <b>Description</b> tag not found for {player_url}")

            # 4. Extract Honors
            honors_tag = soup.find("b", text=re.compile(r"^Career Honours$", re.I))
            if honors_tag:
                honors_table = honors_tag.find_next("table")
                if honors_table:
                    honor_rows = honors_table.find_all("tr")
                    for row in honor_rows:
                        honor_cells = row.find_all("td")
                        if len(honor_cells) >= 2:
                            honor_name = honor_cells[0].get_text(strip=True)
                            honor_year = honor_cells[1].get_text(strip=True)
                            player_data["honors"].append(
                                {"honor": honor_name, "year": honor_year}
                            )
                            print(
                                f"Added honor: {honor_name} ({honor_year}) for {player_data['name']}"
                            )
                else:
                    print(f"Warning: Honors table not found for {player_url}")

            # 5. Skip Players with Placeholder Description
            if player_data["description"] == "--- add one?":
                print(
                    f"Skipping player '{player_data.get('name', 'Unknown')}' due to placeholder description."
                )
                return  # Skip adding to players_data

            # 6. Append Player Data if Name Exists
            if player_data["name"]:
                self.players_data.append(player_data)
                self.player_count += 1
                print(
                    f"Added player {player_data['name']} to memory. Total players in memory: {len(self.players_data)}"
                )

                # Regular save
                if self.player_count % self.save_frequency == 0:
                    print(f"Triggering save at player count: {self.player_count}")
                    self.save_players()

                # Backup save
                if self.player_count % self.backup_frequency == 0:
                    print(f"Triggering backup at player count: {self.player_count}")
                    self.save_players(is_backup=True)
            else:
                print(
                    f"Warning: Player name not extracted for {player_url}. Skipping entry."
                )

        except Exception as e:
            print(f"Error extracting player data from {player_url}: {str(e)}")
            traceback.print_exc()
            # Try to save what we have if there's an error
            if self.players_data:
                self.save_players(is_backup=True)

        return player_data

    def crawl_nfl_teams(self):
        """Crawl NFL teams and their players"""
        try:
            print("Starting NFL teams crawl...")
            # Fetch the NFL teams URL
            nfl_teams_url = urljoin(self.base_url, "/league/4391-NFL")
            nfl_html = self.fetch_page(nfl_teams_url)
            if not nfl_html:
                print(f"Failed to fetch NFL teams page: {nfl_teams_url}")
                return

            # Extract team URLs
            team_links = self.extract_team_links(nfl_html)
            print(f"Found {len(team_links)} teams to process.")

            start_time = datetime.now()
            for team_url in team_links:
                if team_url in self.processed_urls:
                    print(f"Skipping already processed team: {team_url}")
                    continue

                print(f"Processing team: {team_url}")
                team_html = self.fetch_page(team_url)
                if not team_html:
                    print(f"Failed to fetch team page: {team_url}")
                    continue

                # Extract players from the team page
                player_urls = self.extract_player_links(team_html)
                print(f"Extracted {len(player_urls)} player URLs from {team_url}")

                for player_url in player_urls:
                    if player_url in self.processed_urls:
                        print(f"Skipping already processed player: {player_url}")
                        continue

                    print(f"Processing player: {player_url}")
                    player_html = self.fetch_page(player_url)
                    if not player_html:
                        print(f"Failed to fetch player page: {player_url}")
                        continue

                    # Extract and store player data
                    self.extract_player_data(player_html, player_url)
                    self.processed_urls.add(player_url)
                    sleep(1)  # Be polite to the server

                self.processed_urls.add(team_url)
                sleep(1)  # Be polite to the server

            # Final save if any players remain
            if self.players_data:
                print(f"Saving final batch of {len(self.players_data)} players...")
                self.save_players()

            end_time = datetime.now()
            duration = end_time - start_time
            print(f"Crawl completed at {end_time}")
            print(f"Total duration: {duration}")
            print(f"Total players collected: {len(self.players_data)}")

        except KeyboardInterrupt:
            print("Crawl interrupted by user. Saving any remaining players...")
            if self.players_data:
                self.save_players()
            print("Crawl terminated gracefully.")
        except Exception as e:
            print(f"Error during crawl: {e}")
            if self.players_data:
                print("Saving collected data before exit...")
                self.save_players()
            traceback.print_exc()

    def save_data(self):
        """Save the crawled data to JSON files"""
        try:
            # Save teams data
            with open("app/data/teams.json", "w", encoding="utf-8") as f:
                json.dump(
                    {"teams": list(self.teams_data.values())},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            # Save players data
            with open("app/data/players.json", "w", encoding="utf-8") as f:
                json.dump(
                    {"players": self.players_data}, f, indent=2, ensure_ascii=False
                )

            print(
                f"Saved {len(self.teams_data)} teams and {len(self.players_data)} players"
            )
        except Exception as e:
            print(f"Error saving data: {e}")

    def save_players(self, is_backup: bool = False):
        """Save players data to JSON file"""
        players_file = "app/data/players.json"
        backup_dir = "app/data/backups"
        backup_file = os.path.join(
            backup_dir, f"players_backup_{self.player_count}.json"
        )

        try:
            if is_backup:
                # Create a backup copy
                with open(players_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(backup_file, "w", encoding="utf-8") as bf:
                    json.dump(data, bf, indent=2, ensure_ascii=False)
                print(f"Backup saved at {backup_file}")
            else:
                # Load existing data
                if os.path.exists(players_file):
                    with open(players_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {"players": []}
                    print("Created new players.json file")

                # Append new players
                data["players"].extend(self.players_data)
                total_players = len(data["players"])
                with open(players_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(
                    f"Successfully saved {len(self.players_data)} players to {players_file} (Total players: {total_players})"
                )

                # Clear the in-memory players_data
                self.players_data = []
        except Exception as e:
            print(f"Error saving players to {players_file}: {str(e)}")
            traceback.print_exc()

    def cleanup_old_backups(self, keep_last_n=5):
        """Clean up old backup files, keeping only the n most recent ones"""
        try:
            backup_dir = "app/data/backups"
            backup_files = sorted(
                [f for f in os.listdir(backup_dir) if f.startswith("players_")],
                reverse=True,
            )

            # Remove old backup files
            for old_file in backup_files[keep_last_n:]:
                os.remove(os.path.join(backup_dir, old_file))
        except Exception as e:
            print(f"Error cleaning up backups: {e}")

    def load_existing_players(self):
        """Load existing players data from JSON file"""
        try:
            players_file = "app/data/players.json"
            with open(players_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            self.players_data = existing_data.get("players", [])
            self.player_count = len(self.players_data)
            print(f"Loaded {self.player_count} existing players")
        except Exception as e:
            print(f"Error loading existing players: {str(e)}")
            traceback.print_exc()

    def extract_team_links(self, html: str) -> List[str]:
        """Extract team URLs from the NFL teams page"""
        soup = BeautifulSoup(html, "html.parser")
        team_links = []
        # Adjust the selector based on the actual HTML structure
        # Example: <a href="/team/134946-Arizona-Cardinals">Arizona Cardinals</a>
        for a_tag in soup.find_all("a", href=re.compile(r"^/team/\d+-")):
            href = a_tag.get("href")
            if href:
                full_url = urljoin(self.base_url, href)
                team_links.append(full_url)
        return list(set(team_links))  # Remove duplicates

    def extract_player_links(self, html: str) -> List[str]:
        """Extract player URLs from a team page"""
        soup = BeautifulSoup(html, "html.parser")
        player_links = []
        # Adjust the selector based on the actual HTML structure
        # Example: <a href="/player/34164780-Budda-Baker">Budda Baker</a>
        for a_tag in soup.find_all("a", href=re.compile(r"^/player/\d+-")):
            href = a_tag.get("href")
            if href:
                full_url = urljoin(self.base_url, href)
                player_links.append(full_url)
        return list(set(player_links))  # Remove duplicates

    def run(self):
        """Run the crawler"""
        print("Starting NFL teams crawl...")
        self.crawl_nfl_teams()
        print("Crawl finished.")


if __name__ == "__main__":
    crawler = SportsDBCrawler()
    crawler.run()
