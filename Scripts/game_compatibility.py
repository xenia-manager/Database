import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
OWNER = 'xenia-canary'
REPO = 'game-compatibility'
STATE = 'open'
PER_PAGE = 100
BASE_URL = 'https://api.github.com'
OUTPUT_FILE = 'Database/game_compatibility.json'

# Rate limiting
RATE_LIMIT_DELAY = 0.1  # Reduced from 1 second
MAX_RETRIES = 3
RETRY_DELAY = 5

def get_headers() -> Dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'xenia-data-sync/1.0'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers

def parse_title(issue_title: str) -> Dict[str, Optional[str]]:
    """Parse game ID and title from issue title."""
    try:
        title = issue_title.strip()
        
        # Try standard format first: "12345678 - Game Title"
        if ' - ' in title:
            parts = title.split(' - ', 1)
            return {"id": parts[0].strip(), "title": parts[1].strip()}
        
        # Handle missing space before dash: "12345678- Game Title" or "12345678-Game Title"
        if '-' in title:
            # Find the first dash
            dash_index = title.find('-')
            if dash_index > 0:
                # Extract potential ID (everything before the dash)
                potential_id = title[:dash_index].strip()
                # Extract title (everything after the dash)
                potential_title = title[dash_index + 1:].strip()
                
                # Validate that the ID part looks like a game ID (8 hex characters)
                if len(potential_id) == 8 and all(c in '0123456789ABCDEFabcdef' for c in potential_id):
                    return {"id": potential_id.upper(), "title": potential_title}
        
        # If no valid ID-title split found, return as title only
        return {"id": None, "title": title}
        
    except Exception as e:
        print(f"Error parsing title '{issue_title}': {e}", file=sys.stderr)
        return {"id": None, "title": issue_title}

def parse_labels(labels: List[Dict]) -> str:
    """Parse game state from labels."""
    try:
        # Define state mappings for better maintainability
        state_mappings = {
            "state-nothing": "Unplayable",
            "state-crash": "Unplayable", 
            "state-crash-guest": "Unplayable",
            "state-crash-host": "Unplayable",
            "state-crash-xna-WONTFIX": "Unplayable",
            "state-intro": "Loads",
            "state-hang": "Loads",
            "state-load": "Loads", 
            "state-title": "Loads",
            "state-menus": "Loads",
            "state-gameplay": "Gameplay",
            "state-playable": "Playable"
        }
        
        for label in labels:
            label_name = label.get("name", "")
            if label_name in state_mappings:
                return state_mappings[label_name]
        
        return "Unknown"
    except Exception as e:
        print(f"Error parsing labels: {e}", file=sys.stderr)
        return "Unknown"

def make_request(url: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """Make HTTP request with retry logic."""
    if params:
        url = f"{url}?{urlencode(params)}"
    
    for attempt in range(MAX_RETRIES):
        try:
            request = Request(url, headers=get_headers())
            with urlopen(request, timeout=30) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                else:
                    print(f"HTTP {response.status} for {url}", file=sys.stderr)
                    
        except HTTPError as e:
            if e.code == 403:
                # Rate limited or forbidden
                print(f"Rate limited (403). Waiting {RETRY_DELAY * (attempt + 1)} seconds...", file=sys.stderr)
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
                
        except URLError as e:
            print(f"URL Error: {e.reason}", file=sys.stderr)
            
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
        
        if attempt < MAX_RETRIES - 1:
            print(f"Retrying in {RETRY_DELAY} seconds... (attempt {attempt + 1}/{MAX_RETRIES})", file=sys.stderr)
            time.sleep(RETRY_DELAY)
    
    return None

def process_issues(issues_data: List[Dict]) -> List[Dict]:
    """Process raw issue data into game compatibility format."""
    processed = []
    
    for issue in issues_data:
        try:
            # Skip the main repository issue
            if issue.get("html_url") == "https://github.com/xenia-canary/game-compatibility/issues/1":
                continue
            
            # Parse title for game ID and name
            title_data = parse_title(issue.get("title", ""))
            
            # Parse labels for compatibility state
            state = parse_labels(issue.get("labels", []))
            
            game_data = {
                "id": title_data["id"],
                "title": title_data["title"],
                "state": state,
                "url": issue.get("html_url")
            }
            
            processed.append(game_data)
            
        except Exception as e:
            print(f"Error processing issue {issue.get('number', 'unknown')}: {e}", file=sys.stderr)
            continue
    
    return processed

def fetch_all_issues() -> List[Dict]:
    """Fetch all issues from the repository."""
    all_issues = []
    page = 1
    
    print("Fetching game compatibility issues...")
    
    while True:
        print(f"Fetching page {page}...", end=" ")
        
        params = {
            'state': STATE,
            'per_page': PER_PAGE,
            'page': page
        }
        
        url = f"{BASE_URL}/repos/{OWNER}/{REPO}/issues"
        data = make_request(url, params)
        
        if not data:
            print("Failed to fetch data")
            break
            
        if not isinstance(data, list) or len(data) == 0:
            print("No more issues")
            break
        
        processed_issues = process_issues(data)
        all_issues.extend(processed_issues)
        
        print(f"Got {len(data)} issues, processed {len(processed_issues)}")
        
        # If we got fewer than requested, we've reached the end
        if len(data) < PER_PAGE:
            break
            
        page += 1
        time.sleep(RATE_LIMIT_DELAY)
    
    return all_issues

def save_compatibility_data(issues: List[Dict]) -> bool:
    """Save issues to JSON file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        # Sort by game ID for consistent output
        issues.sort(key=lambda x: (x["id"] or "", x["title"] or ""))
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Saved {len(issues)} games to {OUTPUT_FILE}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving to {OUTPUT_FILE}: {e}", file=sys.stderr)
        return False

def main():
    """Main function."""
    if not GITHUB_TOKEN:
        print("⚠️  Warning: GITHUB_TOKEN not set. API requests may be rate-limited.", file=sys.stderr)
    
    print(f"Fetching compatibility data from {OWNER}/{REPO}")
    
    # Fetch all issues
    issues = fetch_all_issues()
    
    if not issues:
        print("❌ No issues fetched or error occurred", file=sys.stderr)
        sys.exit(1)
    
    # Save to file
    if not save_compatibility_data(issues):
        sys.exit(1)
    
    # Print summary
    states = {}
    for issue in issues:
        state = issue["state"]
        states[state] = states.get(state, 0) + 1
    
    print("\n📊 Compatibility Summary:")
    for state, count in sorted(states.items()):
        print(f"  {state}: {count}")
    
    print(f"\n🎮 Total games: {len(issues)}")

if __name__ == '__main__':
    main()
