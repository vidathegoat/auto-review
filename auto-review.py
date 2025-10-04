#!/usr/bin/env python3
"""
KoG Auto Manual Review Tool
Automates player account verification for kog.tw
"""

import json
import os
import sys
import time
import ipaddress
import re
from urllib.parse import quote_plus
from dataclasses import dataclass
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Configuration
COOKIES_FILE = "cookies.json"
BASE_URL = "https://kog.tw"
MIN_REQUEST_INTERVAL = 1.2


@dataclass
class PlayerData:
    """Holds player information"""
    name: str
    finishes: str
    status: str = ""
    migration_status: str = ""
    match_percentage: Optional[int] = None


class KoGSession:
    """Manages authenticated session with kog.tw"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "KoGTool/1.0"})
        self._mount_retries()
        self._last_request_time = 0.0

    def _mount_retries(self, total=5, backoff=1.5):
        """Configure automatic retries"""
        retry = Retry(
            total=total,
            connect=total,
            read=total,
            status=total,
            backoff_factor=backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["HEAD", "GET", "OPTIONS", "POST"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def load_cookies(self, filename=COOKIES_FILE):
        """Load cookies from file"""
        if os.path.exists(filename):
            with open(filename, "r") as f:
                cookies = json.load(f)
                self.session.cookies.update(cookies)
                return True
        return False

    def save_cookies(self, cookies, filename=COOKIES_FILE):
        """Save cookies to file"""
        with open(filename, "w") as f:
            json.dump(cookies, f)

    def is_valid(self):
        """Check if current session is authenticated"""
        try:
            resp = self._get(f"{BASE_URL}/player_edit.php?player=")
            return resp.status_code == 200 and "inputEmail" in resp.text
        except Exception:
            return False

    def authenticate(self):
        """Acquire valid cookies via browser login"""
        if self.load_cookies() and self.is_valid():
            print("Session valid from saved cookies")
            return True

        print("Saved cookies invalid or missing. Opening browser for login...")
        cookies = self._browser_login()

        if cookies:
            self.session.cookies.update(cookies)
            self.save_cookies(cookies)
            print("Login successful, cookies saved")
            return True

        print("ERROR: Failed to authenticate")
        return False

    def _browser_login(self):
        """Open browser for manual login and capture cookies"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(BASE_URL)
        print("Browser opened. Please log in...")

        max_checks = 200
        checks = 0
        cookies = None

        try:
            while checks < max_checks:
                time.sleep(3)
                checks += 1

                selenium_cookies = driver.get_cookies()
                session_cookies = {
                    c['name']: c['value']
                    for c in selenium_cookies
                    if c['name'] in ('PHPSESSID', 'cf_clearance')
                }

                if session_cookies:
                    test_session = requests.Session()
                    test_session.cookies.update(session_cookies)
                    try:
                        resp = test_session.get(f"{BASE_URL}/player_edit.php?player=", timeout=10)
                        if resp.status_code == 200 and "inputEmail" in resp.text:
                            cookies = session_cookies
                            break
                    except Exception:
                        pass
            else:
                print("Timeout waiting for login")
        finally:
            driver.quit()

        return cookies

    def _get(self, url, timeout=20):
        """Rate-limited GET request"""
        now = time.time()
        wait = (self._last_request_time + MIN_REQUEST_INTERVAL) - now
        if wait > 0:
            time.sleep(wait)

        resp = self.session.get(url, timeout=timeout)
        self._last_request_time = time.time()

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 5
            time.sleep(delay)
            resp = self.session.get(url, timeout=timeout)
            self._last_request_time = time.time()

        resp.raise_for_status()
        return resp

    def _post(self, url, json_data=None, headers=None, timeout=20):
        """Rate-limited POST request"""
        now = time.time()
        wait = (self._last_request_time + MIN_REQUEST_INTERVAL) - now
        if wait > 0:
            time.sleep(wait)

        resp = self.session.post(url, json=json_data, headers=headers or {}, timeout=timeout)
        self._last_request_time = time.time()

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 5
            time.sleep(delay)
            resp = self.session.post(url, json=json_data, headers=headers or {}, timeout=timeout)
            self._last_request_time = time.time()

        resp.raise_for_status()
        return resp

    def scrape_player_data(self, ref_number):
        """Scrape player migration data by reference number"""
        url = f"{BASE_URL}/player_migration.php?ref={quote_plus(str(ref_number))}"
        resp = self._get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        headers = soup.find_all("h1")
        if len(headers) < 2:
            raise ValueError("Invalid page structure - not enough headers")

        # First table (Hard facts)
        first_table_data = self._parse_first_table(soup, headers)

        # Second table (Finished on names)
        player_rows = self._parse_second_table(soup, headers)

        return first_table_data, player_rows

    def _parse_first_table(self, soup, headers):
        """Parse the 'Hard facts' table"""
        hardfacts_h1 = soup.find(lambda tag: tag.name == "h1" and "hard facts" in tag.get_text(strip=True).lower())
        first_table = hardfacts_h1.find_next("table") if hardfacts_h1 else headers[0].find_next("table")

        if not first_table:
            return {"total_finishes": None, "same_user_with": None}

        kv = self._parse_key_value_table(first_table)

        # Total finishes
        raw_finishes = kv.get("Total finishes", "")
        digits = "".join(ch for ch in raw_finishes if ch.isdigit())
        total_finishes = int(digits) if digits else None

        # Shared with
        raw_shared = kv.get("Same user or shared computer as/with", "")
        same_user_with = None
        if raw_shared and not self._is_na(raw_shared):
            parts = re.split(r",|\band\b", raw_shared, flags=re.IGNORECASE)
            same_user_with = [p.strip().strip('"\'') for p in parts if p.strip()]

        return {
            "total_finishes": total_finishes,
            "same_user_with": same_user_with or []
        }

    def _parse_second_table(self, soup, headers):
        """Parse the 'Finished on names' table"""
        if len(headers) < 2:
            return []

        second_table = headers[1].find_next("table")
        if not second_table:
            return []

        rows = []
        seen = set()

        for row in second_table.find_all("tr")[1:]:
            tds = row.find_all("td")
            if len(tds) == 2:
                name = tds[0].get_text(strip=True)
                finishes = tds[1].get_text(strip=True)

                # Deduplicate (handles malformed nested <tr> bug)
                key = (name, finishes)
                if key not in seen:
                    seen.add(key)
                    rows.append({"name": name, "finishes": finishes})

        return rows

    def _parse_key_value_table(self, table):
        """Parse two-column key-value tables"""
        kv = {}
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) >= 2:
                key = self._clean_text(cells[0].get_text(" ", strip=True))
                val = self._clean_text(cells[1].get_text(" ", strip=True))
                if key:
                    kv[key] = val
        return kv

    def _clean_text(self, text):
        """Clean and normalize text"""
        text = (text or "").replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return re.sub(r":\s*$", "", text)

    def _is_na(self, text):
        """Check if text represents N/A"""
        text = (text or "").replace("\xa0", " ").strip().lower()
        return text in {"n/a", "na", "none", "-", ""}

    def check_registration(self, player_name):
        """Check if player is registered"""
        try:
            url = f"{BASE_URL}/player_edit.php?player={quote_plus(player_name)}"
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            email_input = soup.find("input", {"name": "inputEmail"})
            if not email_input:
                return "UNREGISTERED (NO EMAIL FIELD)"

            email = (email_input.get("value") or "").strip()
            return "REGISTERED" if email else "UNREGISTERED"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def check_migration_status(self, player_name):
        """Check migration/ban status"""
        try:
            url = f"{BASE_URL}/player_edit.php?player={quote_plus(player_name)}"
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            migration_label = soup.find("label", string="Migration Status")
            if migration_label:
                status_div = migration_label.find_next("div")
                migration_status = (status_div.get_text(strip=True) or "").strip('"')
                if migration_status == "Banned":
                    return "BANNED"
                return ""
            return "NOT MIGRATED"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def check_ip_match(self, player_name, ip_address):
        """Check IP match percentage via API"""
        try:
            url = f"{BASE_URL}/api.php?automated=1"
            payload = {
                "type": "user/admin/check_player",
                "data": {"playername": player_name, "playerip": ip_address}
            }
            headers = {"Content-Type": "application/json"}
            resp = self._post(url, json_data=payload, headers=headers)
            data = resp.json()

            # Extract percentage from various possible response structures
            pct = (
                    data.get("match_percentage")
                    or (data.get("result") or {}).get("percentage")
                    or ((data.get("data") or {}).get("match") or {}).get("percent")
            )

            if isinstance(pct, str) and pct.strip().isdigit():
                pct = int(pct.strip())

            return pct
        except Exception as e:
            print(f"ERROR checking IP for {player_name}: {str(e)}")
            return None


def generate_review_message(review_name, players):
    """Generate formatted review message"""
    # Filter out the review name itself
    filtered = [p for p in players if p.name.strip().lower() != review_name.strip().lower()]

    msg = f"## Manual review is for: `{review_name}`\n"
    msg += "Have you registered or completed a map with one or more of the following names?\n\n"

    if filtered:
        msg += "\n".join(f"- `{p.name}`" for p in filtered)
    else:
        msg += "_(no other names found)_"

    msg += "\n\n### Please elaborate your case:\n"
    msg += "- If you already registered one of these names, why are you trying to register a new name?\n"
    msg += "- If you just finished with one of these names, please do not finish maps for other names besides the one associated with your account.\n"
    msg += "- If you did not register or finish maps for any of these names, please confirm that you did not register or finish any maps for these names.\n\n"
    msg += "*While you are waiting for us, make sure to familiarize yourself with our [#kog-rulebook](https://discord.com/channels/342003344476471296/978628693389885490)*"

    return msg


def print_table(players):
    """Print player data as a formatted table"""
    if not players:
        print("No players to display")
        return

    # Calculate column widths
    name_width = max(len(p.name) for p in players) + 2
    status_width = max(len(p.status) for p in players) + 2
    mig_width = max(len(p.migration_status) for p in players) + 2 if any(p.migration_status for p in players) else 0
    fin_width = max(len(p.finishes) for p in players) + 2

    # Header
    print("\n" + "=" * 80)
    header = f"{'Name':<{name_width}} {'Status':<{status_width}}"
    if mig_width:
        header += f" {'Migration':<{mig_width}}"
    header += f" {'Finishes':<{fin_width}}"
    if any(p.match_percentage is not None for p in players):
        header += " IP Match %"
    print(header)
    print("-" * 80)

    # Rows
    for p in players:
        row = f"{p.name:<{name_width}} {p.status:<{status_width}}"
        if mig_width:
            row += f" {p.migration_status:<{mig_width}}"
        row += f" {p.finishes:<{fin_width}}"
        if p.match_percentage is not None:
            row += f" {p.match_percentage}%"
        print(row)

    print("=" * 80 + "\n")


def main():
    print("=" * 80)
    print("KoG Auto Manual Review Tool")
    print("=" * 80 + "\n")

    # Get reference number
    ref_number = input("Enter reference number (e.g., ref284118): ").strip()
    if not ref_number:
        print("ERROR: Reference number is required")
        return 1

    # Get IP address (optional)
    ip_address = input("Enter IP address to check (or press Enter to skip): ").strip()
    if ip_address:
        try:
            ip_address = str(ipaddress.ip_address(ip_address))
        except ValueError:
            print(f"ERROR: Invalid IP address: {ip_address}")
            return 1
    else:
        ip_address = None

    # Ask for registered-only filter
    registered_only_input = input("Show only registered players in message? (y/n): ").strip().lower()
    registered_only = registered_only_input in ('y', 'yes')

    print()

    # Initialize session
    print("Initializing session...")
    session = KoGSession()

    if not session.authenticate():
        return 1

    # Scrape player data
    print(f"\nFetching data for {ref_number}...")
    try:
        first_table, player_rows = session.scrape_player_data(ref_number)
    except Exception as e:
        print(f"ERROR: Failed to scrape data: {str(e)}")
        return 1

    if not player_rows:
        print("No player data found")
        return 1

    print(f"Found {len(player_rows)} player(s)")
    print(f"Total finishes: {first_table['total_finishes']}")
    if first_table['same_user_with']:
        print(f"Shared with: {', '.join(first_table['same_user_with'])}")

    # Check each player
    players = []
    print("\nChecking players...")
    for row in player_rows:
        print(f"  Checking {row['name']}...", end=" ")
        status = session.check_registration(row['name'])
        mig_status = session.check_migration_status(row['name'])

        player = PlayerData(
            name=row['name'],
            finishes=row['finishes'],
            status=status,
            migration_status=mig_status
        )

        # Check IP if requested and player is registered
        if ip_address and status == "REGISTERED":
            pct = session.check_ip_match(row['name'], ip_address)
            player.match_percentage = pct
            print(f"{status} (IP: {pct}%)" if pct is not None else status)
        else:
            print(status)

        players.append(player)

    # Display results
    print_table(players)

    # Generate message
    review_name = players[0].name if players else "Unknown"

    if registered_only:
        registered = [p for p in players if p.status == "REGISTERED"]
        message = generate_review_message(review_name, registered)
    else:
        message = generate_review_message(review_name, players)

    print("\n" + "=" * 80)
    print("REVIEW MESSAGE:")
    print("=" * 80)
    print(message)
    print("=" * 80 + "\n")

    # Copy to clipboard
    try:
        import pyclip
        pyclip.copy(message)
        print("Message copied to clipboard\n")
    except Exception:
        print("(Could not copy to clipboard - install pyclip if needed)\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())