# crawler.py
from bs4 import BeautifulSoup
from time import sleep
import json
import os
import requests
from datetime import datetime
import re
import traceback


class WikipediaCrawler:
    def __init__(self):
        """
        Initializes the Wikipedia crawler.

        - We parse top-level <h2> headings inside .mw-parser-output, ignoring typical 'References', 'External links', etc.
        - We skip loading old JSON; each run overwrites players_wiki.json with fresh data.
        """
        self.base_wiki_url = "https://en.wikipedia.org/wiki/"
        self.players_data = []       # holds new players data for this run
        self.processed_players = set()

        self.save_frequency = 5
        self.backup_frequency = 10
        self.player_count = 0

        os.makedirs("app/data/backups", exist_ok=True)
        os.makedirs("app/data", exist_ok=True)

        self.players_file = "app/data/players_wiki.json"
        self.players_orig = "app/data/players.json"

        # Load your original players, turning their 'name' into wiki slugs
        with open(self.players_orig, "r", encoding="utf-8") as f:
            players_json = json.load(f)
            # For each player, we convert e.g. "Zach Thomas" to "Zach_Thomas"
            self.players_names = [
                player['name'].replace(' ', '_') for player in players_json['players']
            ]

        # Some headings we might skip because we usually don't care about them
        # or they are typically empty:
        self.headings_to_skip = {
            "Contents",
            "References",
            "External_links",
            "Further_reading",
            "See_also",
            "Notes"
        }

    def fetch_page(self, wiki_slug: str) -> str:
        """Fetch the Wikipedia HTML for a player's page."""
        full_url = self.base_wiki_url + wiki_slug
        try:
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {full_url}: {str(e)}")
            return ""

    def parse_player_page(self, html: str, wiki_slug: str):
        """
        Parse the Wikipedia page for a single NFL player:
          - Grab <h2> sections from the main content.
          - Return data with "sections": { title: text }
          - We keep "tables": [] if you want to remove them or comment out to ignore them.
        """
        soup = BeautifulSoup(html, "html.parser")
        player_data = {
            "name": wiki_slug,
            "sections": {},
            "tables": []
        }

        # 1) main content
        main_content = soup.find("div", class_="mw-parser-output")
        if not main_content:
            print("Warning: no .mw-parser-output found, skipping parse.")
            return player_data

        # 2) find all <h2> headings in main_content (NOT restricting with recursive=False)
        all_h2 = main_content.find_all("h2")
        # parse each heading's text
        for h2 in all_h2:
            section_title = self._get_section_title(h2)
            # skip if heading is empty or in headings_to_skip
            if not section_title or section_title in self.headings_to_skip:
                continue

            # gather paragraphs from this h2 until next h2
            paragraphs = []
            sibling = h2.find_next_sibling()
            while sibling and sibling.name != "h2":
                if sibling.name in ("p", "ul", "ol"):
                    paragraphs.append(sibling.get_text(" ", strip=True))
                sibling = sibling.find_next_sibling()

            joined = "\n\n".join(paragraphs).strip()
            if joined:
                player_data["sections"][section_title] = joined

        # 3) OPTIONAL: parse wikitable data
        # If you don't want tables at all, comment out this entire block:
        # --------------------------------------------------------------
        tables = main_content.find_all("table", class_="wikitable")
        for tbl in tables:
            caption_tag = tbl.find("caption")
            if caption_tag:
                table_title = caption_tag.get_text(strip=True)
            else:
                table_title = self._guess_table_title(tbl)

            table_data = self._parse_html_table(tbl)
            if table_data:
                player_data["tables"].append({
                    "title": table_title,
                    "data": table_data
                })
        # --------------------------------------------------------------

        return player_data

    def _parse_html_table(self, table_soup):
        """Parse a 'wikitable' into a list of row dicts."""
        rows = table_soup.find_all("tr")
        if not rows:
            return []

        headers = []
        data_rows = []

        # find first <tr> that has multiple <th> for column headers
        for row in rows:
            ths = row.find_all("th")
            if len(ths) >= 2:  # or > 1
                headers = [th.get_text(strip=True) for th in ths]
                break

        for row in rows:
            tds = row.find_all("td")
            # Only parse if # of tds matches # of headers
            if len(tds) == len(headers) and len(tds) > 1:
                row_dict = {}
                for i, cell in enumerate(tds):
                    col_name = headers[i]
                    val = cell.get_text(" ", strip=True)
                    row_dict[col_name] = val
                data_rows.append(row_dict)

        return data_rows

    def _guess_table_title(self, tbl_soup):
        """If table lacks <caption>, guess from preceding heading."""
        prev = tbl_soup.find_previous_sibling(
            lambda x: x.name in ("h2","h3","h4","h5")
        )
        if prev:
            return self._get_section_title(prev)
        return "Unknown Table"

    def _get_section_title(self, heading_tag):
        """
        Extract text from the heading. If <span class="mw-headline"> is present, use that.
        Then remove trailing '[edit]' if present.
        """
        if not heading_tag:
            return None

        # e.g. <span class="mw-headline" id="Early_life">Early life</span>
        span = heading_tag.find("span", class_="mw-headline")
        if span:
            txt = span.get_text(strip=True)
        else:
            # fallback
            txt = heading_tag.get_text(" ", strip=True)

        txt = re.sub(r"\[edit\]$", "", txt).strip()
        # replace spaces with underscore if you like
        return txt.replace(" ", "_") if txt else None

    def crawl_player(self, wiki_slug: str):
        """Crawl one player wiki page. Skip if we already did it."""
        if wiki_slug in self.processed_players:
            print(f"Skipping already processed: {wiki_slug}")
            return

        print(f"Fetching: {wiki_slug}")
        html = self.fetch_page(wiki_slug)
        if not html:
            print(f"Failed to fetch: {wiki_slug}")
            return

        try:
            data = self.parse_player_page(html, wiki_slug)
            self.players_data.append(data)
            self.processed_players.add(wiki_slug)
            self.player_count += 1

            if self.player_count % self.save_frequency == 0:
                self.save_players()

            if self.player_count % self.backup_frequency == 0:
                self.save_players(backup=True)

        except Exception as e:
            print(f"Error crawling {wiki_slug}: {e}")
            traceback.print_exc()
            self.save_players(backup=True)

    def save_players(self, backup=False):
        """Save players to the main JSON or create a backup if backup=True."""
        data_out = {"players": self.players_data}
        try:
            if backup:
                fname = f"app/data/backups/wiki_players_backup_{self.player_count}.json"
                with open(fname, "w", encoding="utf-8") as bf:
                    json.dump(data_out, bf, indent=2, ensure_ascii=False)
                print(f"[Backup] wrote: {fname}")
            else:
                with open(self.players_file, "w", encoding="utf-8") as f:
                    json.dump(data_out, f, indent=2, ensure_ascii=False)
                print(f"[Save] wrote {len(self.players_data)} players to {self.players_file}")
        except Exception as e:
            print(f"Error saving players: {e}")
            traceback.print_exc()

    def run(self, list_of_player_slugs):
        """Crawl them all, then do a final save."""
        start = datetime.now()
        print("=== Starting Wikipedia Crawler ===")

        for slug in list_of_player_slugs:
            self.crawl_player(slug)
            sleep(1.0)  # rate limit

        if self.players_data:
            self.save_players()

        dur = datetime.now() - start
        print(f"Done crawling. Duration: {dur}")
        print(f"Total players: {len(self.players_data)}")


if __name__ == "__main__":
    crawler = WikipediaCrawler()
    # We can just run with all players from players.json
    # or a subset. For example:
    # crawler.run(["Zach_Thomas", "Patrick_Mahomes"])

    # If you want to crawl everything from self.players_names:
    crawler.run(crawler.players_names)