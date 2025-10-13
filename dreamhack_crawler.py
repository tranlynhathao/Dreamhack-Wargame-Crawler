#!/usr/bin/env python3
"""
DreamHack Wargame Crawler v2
Automatically crawls and maps all DreamHack wargame challenges with proper query parameter support
and comprehensive local tracking system.
"""

import json
import os
import hashlib
import time
import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from urllib.parse import urljoin, urlparse, parse_qs
import html

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class DreamHackCrawler:
    """Main crawler class for DreamHack wargame challenges."""

    CATEGORIES = [
        "",  # all
        "misc",
        "crypto",
        "web",
        "web3",
        "pwnable",
        "forensics",
        "reversing",
        "cloud",
    ]
    DIFFICULTIES = [
        "",  # all
        "0",
        "beginner",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
    ]
    STATUSES = ["", "todo", "attempted", "solved"]

    def __init__(
        self,
        base_url: str = "https://dreamhack.io/wargame",
        cookie: Optional[str] = None,
        delay: float = 1.0,
        output_path: str = "manifest.json",
        verbose: bool = True,
        sort_by: str = "id",
        sort_order: str = "desc",
    ):
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.output_path = output_path
        self.verbose = verbose
        self.sort_by = sort_by
        self.sort_order = sort_order

        # Setup session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            }
        )

        if cookie:
            self.session.headers.update({"Cookie": cookie})

        # Playwright setup
        self.playwright = None
        self.browser = None
        self.page = None

        # Load existing manifest
        self.manifest = self.load_manifest()

    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}")

    def log_always(self, message: str):
        """Log message regardless of verbose mode."""
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}")

    def load_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create empty one."""
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.log(f"Warning: Could not load existing manifest: {e}")
        return {}

    def save_manifest(self):
        """Save manifest to disk with configurable sorting."""
        try:
            # Apply sorting based on configuration
            if self.sort_by == "none":
                sorted_manifest = self.manifest
            else:
                sorted_manifest = self._sort_manifest()

            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(sorted_manifest, f, indent=2, ensure_ascii=False)

            # Update internal manifest to maintain sorted order
            self.manifest = sorted_manifest
        except IOError as e:
            self.log(f"Error saving manifest: {e}")
        except (ValueError, KeyError) as e:
            self.log(f"Error sorting manifest: {e}")
            # Fallback to unsorted save if sorting fails
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(self.manifest, f, indent=2, ensure_ascii=False)

    def _sort_manifest(self) -> Dict[str, Any]:
        """Sort manifest based on configured sort_by and sort_order."""
        reverse_order = self.sort_order == "desc"

        if self.sort_by == "id":
            # Sort by challenge ID
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: int(x[0]),
                    reverse=reverse_order,
                )
            )
        elif self.sort_by == "title":
            # Sort by challenge title
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: x[1].get("title", "").lower(),
                    reverse=reverse_order,
                )
            )
        elif self.sort_by == "category":
            # Sort by category, then by ID
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: (x[1].get("category", "").lower(), int(x[0])),
                    reverse=reverse_order,
                )
            )
        elif self.sort_by == "difficulty":
            # Sort by difficulty (as number), then by ID
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: (
                        self._difficulty_to_number(x[1].get("difficulty", "0")),
                        int(x[0]),
                    ),
                    reverse=reverse_order,
                )
            )
        elif self.sort_by == "first_seen":
            # Sort by first seen date
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: x[1].get("first_seen", ""),
                    reverse=reverse_order,
                )
            )
        elif self.sort_by == "last_seen":
            # Sort by last seen date
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: x[1].get("last_seen", ""),
                    reverse=reverse_order,
                )
            )
        elif self.sort_by == "has_download":
            # Sort by download status, then by ID
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: (x[1].get("has_download", False), int(x[0])),
                    reverse=reverse_order,
                )
            )
        else:
            # Default to ID sorting if unknown sort_by
            self.log(
                f"Unknown sort_by value '{self.sort_by}', defaulting to ID sorting"
            )
            return dict(
                sorted(
                    self.manifest.items(),
                    key=lambda x: int(x[0]),
                    reverse=reverse_order,
                )
            )

    def _difficulty_to_number(self, difficulty: str) -> int:
        """Convert difficulty string to number for sorting."""
        try:
            # Handle numeric difficulties
            if difficulty.isdigit():
                return int(difficulty)
            # Handle named difficulties
            difficulty_map = {
                "beginner": 0,
                "easy": 1,
                "medium": 5,
                "hard": 8,
                "expert": 10,
            }
            return difficulty_map.get(difficulty.lower(), 0)
        except:
            return 0

    def init_playwright(self):
        """Initialize Playwright for JS-heavy pages."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright not available. Install with: pip install playwright"
            )

        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=True)
            context = self.browser.new_context()

            # Set cookie if provided
            if "Cookie" in self.session.headers:
                cookie_str = self.session.headers["Cookie"]
                cookies = []
                for cookie_part in cookie_str.split(";"):
                    if "=" in cookie_part:
                        name, value = cookie_part.strip().split("=", 1)
                        cookies.append(
                            {
                                "name": name,
                                "value": value,
                                "domain": "dreamhack.io",
                                "path": "/",
                            }
                        )
                context.add_cookies(cookies)

            self.page = context.new_page()

    def cleanup_playwright(self):
        """Clean up Playwright resources."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def fetch_with_fallback(
        self, url: str, use_playwright: bool = False
    ) -> Tuple[str, bool]:
        """Fetch page content with fallback to Playwright if needed."""
        if use_playwright or not self._simple_fetch_works(url):
            return self._fetch_with_playwright(url), True
        else:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text, False

    def _simple_fetch_works(self, url: str) -> bool:
        """Test if simple requests fetch works for the URL."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # Check if we got meaningful content (not just JS loader)
                soup = BeautifulSoup(response.text, "html.parser")
                return len(soup.find_all(["div", "span", "p"])) > 5
        except:
            pass
        return False

    def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page using Playwright."""
        if not self.page:
            self.init_playwright()

        self.page.goto(url, wait_until="networkidle")
        time.sleep(2)  # Extra wait for dynamic content
        return self.page.content()

    def extract_challenge_id_from_url(self, url: str) -> Optional[str]:
        """Extract challenge ID from various URL formats."""
        patterns = [r"/wargame/challenges/(\d+)", r"challenge_id=(\d+)", r"id=(\d+)"]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def parse_challenges_from_listing(
        self, html_content: str, category: str, difficulty: str, status: str
    ) -> List[Dict[str, Any]]:
        """Parse challenges from a wargame listing page."""
        soup = BeautifulSoup(html_content, "html.parser")
        challenges = []

        # Look for challenge entries using multiple strategies
        challenge_elements = []

        # Strategy 1: Look for challenge cards/items with various class names
        selectors = [
            ".challenge-item",
            ".wargame-item",
            ".challenge-card",
            "[data-challenge-id]",
            "tr[data-id]",
            ".challenge-row",
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                challenge_elements = elements
                break

        # Strategy 2: Look for links to challenges directly
        if not challenge_elements:
            challenge_elements = soup.find_all(
                "a", href=re.compile(r"/wargame/challenges/\d+")
            )

        # Strategy 3: Look for table rows or list items containing challenge links
        if not challenge_elements:
            # Find all elements that contain challenge links
            for element in soup.find_all(["tr", "li", "div"]):
                if element.find("a", href=re.compile(r"/wargame/challenges/\d+")):
                    challenge_elements.append(element)

        # Strategy 4: Parse from script tags containing challenge data (if any)
        if not challenge_elements:
            script_tags = soup.find_all("script", string=re.compile(r"challenge"))
            for script in script_tags:
                # Try to extract JSON data from script tags
                try:
                    json_matches = re.findall(r'({.*"id".*?})', script.string or "")
                    for json_str in json_matches:
                        try:
                            data = json.loads(json_str)
                            if "id" in data:
                                challenges.append(
                                    {
                                        "id": str(data["id"]),
                                        "title": data.get(
                                            "title", data.get("name", "")
                                        ),
                                        "challenge_url": f"https://dreamhack.io/wargame/challenges/{data['id']}",
                                        "category": category
                                        or data.get("category", ""),
                                        "difficulty": difficulty
                                        or data.get("difficulty", ""),
                                    }
                                )
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    continue

        # Parse HTML elements for challenge data
        for element in challenge_elements:
            try:
                # Extract challenge ID
                challenge_id = None

                # Method 1: from data attributes
                if element.get("data-challenge-id"):
                    challenge_id = element.get("data-challenge-id")
                elif element.get("data-id"):
                    challenge_id = element.get("data-id")

                # Method 2: from href links
                if not challenge_id:
                    challenge_links = element.find_all(
                        "a", href=re.compile(r"/wargame/challenges/\d+")
                    )
                    if not challenge_links and element.get("href"):
                        challenge_links = [element]  # Element itself is a link

                    for link in challenge_links:
                        href = link.get("href", "")
                        challenge_id = self.extract_challenge_id_from_url(href)
                        if challenge_id:
                            break

                if not challenge_id:
                    continue

                # Extract title
                title = ""
                title_selectors = [
                    ".title",
                    ".challenge-title",
                    ".name",
                    "h3",
                    "h4",
                    "h5",
                    "[data-title]",
                    ".challenge-name",
                    ".problem-title",
                ]

                for sel in title_selectors:
                    title_elem = element.select_one(sel)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break

                # If no title found, try to extract from link text
                if not title:
                    challenge_links = element.find_all(
                        "a", href=re.compile(r"/wargame/challenges/\d+")
                    )
                    for link in challenge_links:
                        link_text = link.get_text(strip=True)
                        if link_text and len(link_text) > 0:
                            title = link_text
                            break

                # Fallback: use element text, clean it up
                if not title and element.get_text():
                    title = re.sub(r"\s+", " ", element.get_text(strip=True))
                    # Take first reasonable part as title
                    parts = title.split()
                    if parts:
                        title = " ".join(parts[:5])  # Take first 5 words max

                # Build challenge URL
                challenge_url = (
                    f"https://dreamhack.io/wargame/challenges/{challenge_id}"
                )

                # Extract category and difficulty from the current context or element
                elem_category = category
                elem_difficulty = difficulty

                # Try to extract category from element if not provided
                if not elem_category:
                    category_indicators = element.find_all(
                        string=re.compile(
                            r"(pwnable|web|crypto|forensics|reversing|misc|cloud|web3)",
                            re.IGNORECASE,
                        )
                    )
                    if category_indicators:
                        elem_category = category_indicators[0].lower().strip()

                # Try to extract difficulty from element if not provided
                if not elem_difficulty:
                    difficulty_indicators = element.find_all(
                        string=re.compile(r"(level\s*\d+|beginner|\d+)", re.IGNORECASE)
                    )
                    for indicator in difficulty_indicators:
                        match = re.search(
                            r"(level\s*)?([\d]+|beginner)", indicator.lower()
                        )
                        if match:
                            elem_difficulty = match.group(2)
                            break

                challenges.append(
                    {
                        "id": challenge_id,
                        "title": title,
                        "challenge_url": challenge_url,
                        "category": elem_category,
                        "difficulty": elem_difficulty,
                        "status": status,
                    }
                )

            except Exception as e:
                self.log(f"Error parsing challenge element: {e}")
                continue

        return challenges

    def fetch_challenge_details(self, challenge_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific challenge."""
        url = f"https://dreamhack.io/wargame/challenges/{challenge_id}"

        if self.verbose:
            self.log(f"      Fetching details for challenge {challenge_id}...")

        try:
            html_content, used_playwright = self.fetch_with_fallback(url)
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract description
            description = ""
            desc_selectors = [
                ".challenge-description",
                ".description",
                ".problem-content",
                ".challenge-detail",
                "[data-description]",
                ".problem-description",
                ".problem-text",
                ".challenge-text",
            ]

            for sel in desc_selectors:
                desc_elem = soup.select_one(sel)
                if desc_elem:
                    description = html.unescape(desc_elem.get_text(strip=True))
                    break

            return {"description": description}

        except Exception as e:
            self.log(f"Error fetching challenge {challenge_id} details: {e}")
            return {"description": f"Error fetching details: {str(e)}"}

    def update_manifest_entry(self, challenge_data: Dict[str, Any]):
        """Update or create manifest entry for a challenge."""
        challenge_id = challenge_data["id"]
        current_time = datetime.now(timezone.utc).isoformat()

        if challenge_id in self.manifest:
            # Update existing entry - preserve has_download flag
            existing = self.manifest[challenge_id]
            existing["title"] = challenge_data.get("title", existing.get("title", ""))
            existing["challenge_url"] = challenge_data.get(
                "challenge_url", existing.get("challenge_url", "")
            )
            existing["category"] = challenge_data.get(
                "category", existing.get("category", "")
            )
            existing["difficulty"] = challenge_data.get(
                "difficulty", existing.get("difficulty", "")
            )
            existing["last_seen"] = current_time

            # Update description if provided
            if "description" in challenge_data:
                existing["description"] = challenge_data["description"]

            # NEVER automatically set has_download during crawling - only preserve existing value
            if "has_download" not in existing:
                existing["has_download"] = False

        else:
            # Create new entry - has_download defaults to False
            self.manifest[challenge_id] = {
                "id": challenge_id,
                "title": challenge_data.get("title", ""),
                "challenge_url": challenge_data.get("challenge_url", ""),
                "category": challenge_data.get("category", ""),
                "difficulty": challenge_data.get("difficulty", ""),
                "has_download": False,  # Always start as False
                "description": challenge_data.get("description", ""),
                "first_seen": current_time,
                "last_seen": current_time,
            }

            title = challenge_data.get("title", "Unknown")
            category = challenge_data.get("category", "unknown")
            difficulty = challenge_data.get("difficulty", "?")
            self.log(f"NEW: {challenge_id} '{title}' [{category}] (diff: {difficulty})")

    def build_query_url(
        self, category: str, difficulty: str, status: str, page: int
    ) -> str:
        """Build URL with proper query parameters."""
        url = self.base_url
        params = []

        if category:
            params.append(f"category={category}")
        if difficulty:
            params.append(f"difficulty={difficulty}")
        if status:
            params.append(f"status={status}")
        if page > 1:
            params.append(f"page={page}")

        if params:
            url += "?" + "&".join(params)

        return url

    def crawl_mapping_mode(self):
        """Main crawling logic for mapping mode with proper query parameter iteration."""
        self.log_always("Starting comprehensive mapping mode crawl...")

        # Calculate total combinations for progress tracking
        total_combinations = (
            len(self.CATEGORIES) * len(self.DIFFICULTIES) * len(self.STATUSES)
        )
        self.log_always(f"Will crawl {total_combinations} parameter combinations")

        combination_count = 0
        total_new_challenges = 0
        total_updated_challenges = 0
        total_pages_crawled = 0

        for category in self.CATEGORIES:
            for difficulty in self.DIFFICULTIES:
                for status in self.STATUSES:
                    combination_count += 1
                    consecutive_failures = 0
                    page = 1

                    category_display = category or "all"
                    difficulty_display = difficulty or "all"
                    status_display = status or "all"

                    self.log(
                        f"Progress: {combination_count}/{total_combinations} combinations - Starting [{category_display}:{difficulty_display}:{status_display}]"
                    )

                    while consecutive_failures < 5:
                        try:
                            # Build URL with proper query parameters
                            url = self.build_query_url(
                                category, difficulty, status, page
                            )

                            self.log(f"  Fetching page {page}...")

                            # Fetch page
                            html_content, _ = self.fetch_with_fallback(url)

                            # Parse challenges
                            challenges = self.parse_challenges_from_listing(
                                html_content, category, difficulty, status
                            )

                            total_pages_crawled += 1

                            if not challenges:
                                self.log(
                                    f"  Page {page}: No challenges found - stopping pagination for this combination"
                                )
                                break

                            self.log(
                                f"  Page {page}: Found {len(challenges)} challenges"
                            )

                            # Process each challenge
                            new_in_this_batch = 0
                            updated_in_this_batch = 0
                            for i, challenge in enumerate(challenges, 1):
                                challenge_id = challenge["id"]
                                challenge_title = challenge.get("title", "Unknown")

                                # Check if this is a new challenge or needs detail fetching
                                is_new = challenge_id not in self.manifest

                                if is_new:
                                    self.log(
                                        f"    Processing new challenge {i}/{len(challenges)}: {challenge_id} '{challenge_title}'"
                                    )
                                    # Fetch detailed information for new challenges
                                    details = self.fetch_challenge_details(challenge_id)
                                    challenge.update(details)
                                    total_new_challenges += 1
                                    new_in_this_batch += 1
                                    time.sleep(self.delay)  # Rate limiting
                                else:
                                    # Only log for first few existing challenges to avoid spam
                                    if i <= 3:
                                        self.log(
                                            f"    Updating existing challenge {i}/{len(challenges)}: {challenge_id}"
                                        )
                                    elif i == 4 and len(challenges) > 4:
                                        self.log(
                                            f"    ... updating {len(challenges)-3} more existing challenges"
                                        )
                                    total_updated_challenges += 1
                                    updated_in_this_batch += 1

                                self.update_manifest_entry(challenge)

                            if new_in_this_batch > 0 or updated_in_this_batch > 0:
                                self.log(
                                    f"  Batch complete: {new_in_this_batch} new, {updated_in_this_batch} updated"
                                )

                            # Save progress periodically
                            self.save_manifest()

                            page += 1
                            consecutive_failures = 0
                            time.sleep(self.delay)

                        except Exception as e:
                            consecutive_failures += 1
                            self.log(
                                f"Error on [{category_display}:{difficulty_display}:{status_display}] page {page}: {e}"
                            )

                            if consecutive_failures >= 5:
                                self.log(
                                    f"Too many failures for [{category_display}:{difficulty_display}:{status_display}], skipping"
                                )
                                break

                            time.sleep(
                                self.delay * consecutive_failures
                            )  # Exponential backoff

        # Final statistics
        self.log_always("\n" + "=" * 60)
        self.log_always("CRAWLING COMPLETED!")
        self.log_always("=" * 60)
        self.log_always(
            f"Total parameter combinations processed: {combination_count}/{total_combinations}"
        )
        self.log_always(f"Total pages crawled: {total_pages_crawled}")
        self.log_always(f"New challenges discovered: {total_new_challenges}")
        self.log_always(f"Existing challenges updated: {total_updated_challenges}")
        self.log_always(f"Total challenges in manifest: {len(self.manifest)}")
        self.log_always(f"Manifest saved to: {self.output_path}")

        # Category breakdown
        if self.manifest:
            from collections import Counter

            categories = Counter(
                c.get("category", "unknown") for c in self.manifest.values()
            )
            self.log_always(f"\nChallenges by category:")
            for cat, count in sorted(categories.items()):
                if cat:  # Skip empty categories
                    self.log_always(f"  {cat}: {count}")

    def update_local_tracking(self):
        """Update manifest based on local downloaded files."""
        self.log_always("Updating local tracking based on downloaded files...")

        challenges_dir = Path("challenges")
        if not challenges_dir.exists():
            self.log_always("No challenges directory found")
            # Still save manifest to apply sorting even if no directory found
            self.save_manifest()
            self.log_always(f"Manifest sorted and saved to {self.output_path}")
            return

        # Get all downloaded challenge IDs
        downloaded_ids = set()
        for category_dir in challenges_dir.iterdir():
            if category_dir.is_dir():
                for challenge_dir in category_dir.iterdir():
                    if challenge_dir.is_dir():
                        # Extract ID from directory name (format: id-title)
                        dir_name = challenge_dir.name
                        id_match = re.match(r"^(\d+)-", dir_name)
                        if id_match:
                            challenge_id = id_match.group(1)
                            # Check if meta.json exists (indicates successful download)
                            meta_file = challenge_dir / "meta.json"
                            if meta_file.exists():
                                downloaded_ids.add(challenge_id)

        self.log_always(f"Found {len(downloaded_ids)} locally downloaded challenges")

        # Update manifest entries
        updated_count = 0
        for challenge_id, challenge_info in self.manifest.items():
            current_has_download = challenge_info.get("has_download", False)
            should_have_download = challenge_id in downloaded_ids

            if current_has_download != should_have_download:
                challenge_info["has_download"] = should_have_download
                updated_count += 1

                if should_have_download:
                    self.log(
                        f"Set has_download=true for {challenge_id}: {challenge_info.get('title', 'Unknown')}"
                    )
                else:
                    self.log(
                        f"Set has_download=false for {challenge_id}: {challenge_info.get('title', 'Unknown')}"
                    )

        if updated_count > 0:
            self.log_always(f"Updated {updated_count} entries in manifest")
        else:
            self.log_always("No updates needed")

        # Always save to apply sorting
        self.save_manifest()
        self.log_always(f"Manifest sorted and saved to {self.output_path}")

    def download_challenge(self, challenge_id: str) -> bool:
        """Download files for a specific challenge."""
        if challenge_id not in self.manifest:
            self.log_always(
                f"Challenge {challenge_id} not found in manifest. Run mapping first."
            )
            return False

        challenge_info = self.manifest[challenge_id]

        # Check if already downloaded
        if challenge_info.get("has_download", False):
            self.log_always(
                f"Challenge {challenge_id} already downloaded. Use --update to refresh local tracking."
            )
            return False

        category = challenge_info.get("category", "unknown")
        title_slug = re.sub(r"[^\w\-_]", "_", challenge_info.get("title", "challenge"))[
            :50
        ]

        # Create download directory
        download_dir = Path(f"challenges/{category}/{challenge_id}-{title_slug}")
        download_dir.mkdir(parents=True, exist_ok=True)

        self.log_always(f"Downloading challenge {challenge_id} to {download_dir}")

        # Fetch fresh challenge page to get presigned URLs
        url = f"https://dreamhack.io/wargame/challenges/{challenge_id}"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                html_content, _ = self.fetch_with_fallback(url)

                # Extract download URLs
                download_urls = self._extract_download_urls(html_content)

                if not download_urls:
                    self.log(f"No download URLs found for challenge {challenge_id}")
                    return False

                downloaded_files = []

                for file_url in download_urls:
                    try:
                        filename = self._extract_filename_from_url(file_url)
                        file_path = download_dir / filename

                        self.log(f"Downloading {filename}...")

                        # Download file
                        response = requests.get(file_url, timeout=60)
                        response.raise_for_status()

                        # Save file
                        with open(file_path, "wb") as f:
                            f.write(response.content)

                        # Compute checksum
                        sha256_hash = hashlib.sha256(response.content).hexdigest()

                        downloaded_files.append(
                            {
                                "filename": filename,
                                "url_fetched": file_url.split("?")[
                                    0
                                ],  # Remove query params for security
                                "checksum": sha256_hash,
                                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                            }
                        )

                    except requests.RequestException as e:
                        if (
                            hasattr(e, "response")
                            and e.response
                            and e.response.status_code == 403
                        ):
                            self.log(
                                f"403 error downloading {file_url}, retry {attempt + 1}/{max_retries}"
                            )
                            if attempt < max_retries - 1:
                                time.sleep(1)
                                break
                        raise e

                # Save metadata
                meta_data = {"id": int(challenge_id), "files": downloaded_files}

                with open(download_dir / "meta.json", "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, indent=2, ensure_ascii=False)

                # Update manifest to reflect download
                self.manifest[challenge_id]["has_download"] = True
                self.save_manifest()

                self.log_always(
                    f"Successfully downloaded {len(downloaded_files)} files for challenge {challenge_id}"
                )
                return True

            except Exception as e:
                self.log_always(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        self.log_always(
            f"Failed to download challenge {challenge_id} after {max_retries} attempts"
        )
        return False

    def _extract_download_urls(self, html_content: str) -> List[str]:
        """Extract download URLs from challenge page HTML."""
        urls = []

        # S3 presigned URL pattern
        s3_pattern = r'https://[^"\']*.s3.amazonaws.com[^"\'].*'
        s3_urls = re.findall(s3_pattern, html_content)
        urls.extend(s3_urls)

        # Other download URL patterns
        soup = BeautifulSoup(html_content, "html.parser")

        # Look for download links
        download_links = soup.find_all(
            "a", href=re.compile(r"download|attachment", re.IGNORECASE)
        )
        for link in download_links:
            href = link.get("href")
            if href and not href.startswith("#"):
                if not href.startswith("http"):
                    href = urljoin("https://dreamhack.io", href)
                urls.append(href)

        return list(set(urls))  # Remove duplicates

    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL."""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)

        if not filename or "." not in filename:
            # Try to get filename from query params
            params = parse_qs(parsed.query)
            if "filename" in params:
                filename = params["filename"][0]
            else:
                filename = "attachment.bin"

        return filename


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="DreamHack Wargame Crawler v2")
    parser.add_argument(
        "--base", default="https://dreamhack.io/wargame", help="Base URL"
    )
    parser.add_argument("--cookie", help="Session cookie string")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests"
    )
    parser.add_argument("--download", help="Download specific challenge ID")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update local tracking based on downloaded files",
    )
    parser.add_argument(
        "--output", default="manifest.json", help="Output manifest path"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--sort-by",
        default="id",
        choices=[
            "none",
            "id",
            "title",
            "category",
            "difficulty",
            "first_seen",
            "last_seen",
            "has_download",
        ],
        help="Sort manifest by (default: id)",
    )
    parser.add_argument(
        "--sort-order",
        default="desc",
        choices=["asc", "desc"],
        help="Sort order: asc (ascending) or desc (descending) (default: desc)",
    )

    args = parser.parse_args()

    try:
        crawler = DreamHackCrawler(
            base_url=args.base,
            cookie=args.cookie,
            delay=args.delay,
            output_path=args.output,
            verbose=args.verbose,
            sort_by=args.sort_by,
            sort_order=args.sort_order,
        )

        if args.download:
            # Download mode
            success = crawler.download_challenge(args.download)
            sys.exit(0 if success else 1)
        elif args.update:
            # Update local tracking mode
            crawler.update_local_tracking()
        else:
            # Mapping mode
            crawler.crawl_mapping_mode()
            crawler.save_manifest()

            # Show preview
            if crawler.manifest:
                print("\n" + "=" * 60)
                print("MANIFEST PREVIEW (first 10 entries):")
                print("=" * 60)

                for i, (challenge_id, data) in enumerate(
                    list(crawler.manifest.items())[:10]
                ):
                    print(f"{i+1:2d}. ID: {challenge_id}")
                    print(f"    Title: {data.get('title', 'N/A')}")
                    print(f"    Category: {data.get('category', 'N/A')}")
                    print(f"    Difficulty: {data.get('difficulty', 'N/A')}")
                    print(f"    Has Download: {data.get('has_download', False)}")
                    print(f"    First Seen: {data.get('first_seen', 'N/A')}")
                    print()

                print(f"Total challenges in manifest: {len(crawler.manifest)}")
                print(f"Manifest saved to: {args.output}")

    except KeyboardInterrupt:
        print("\nCrawling interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if "crawler" in locals():
            crawler.cleanup_playwright()


if __name__ == "__main__":
    main()
