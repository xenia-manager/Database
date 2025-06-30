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

def parse_title(issue_title: str, debug: bool = False) -> Dict[str, Optional[str]]:
    """Parse game ID and title from issue title."""
    try:
        title = issue_title.strip()
        if debug:
            print(f"🔍 Parsing title: '{title}'")
        
        # Try standard format first: "12345678 - Game Title"
        if ' - ' in title:
            parts = title.split(' - ', 1)
            result = {"id": parts[0].strip(), "title": parts[1].strip()}
            if debug:
                print(f"  ✅ Standard format found: ID='{result['id']}', Title='{result['title']}'")
            return result
        
        # Handle missing space before dash: "12345678- Game Title" or "12345678-Game Title"
        if '-' in title:
            if debug:
                print(f"  🔧 Trying dash fallback...")
            # Find the first dash
            dash_index = title.find('-')
            if dash_index > 0:
                # Extract potential ID (everything before the dash)
                potential_id = title[:dash_index].strip()
                # Extract title (everything after the dash)
                potential_title = title[dash_index + 1:].strip()
                
                if debug:
                    print(f"    Potential ID: '{potential_id}' (len={len(potential_id)})")
                    print(f"    Potential Title: '{potential_title}'")
                
                # Validate that the ID part looks like a game ID (8 hex characters)
                if len(potential_id) == 8 and all(c in '0123456789ABCDEFabcdef' for c in potential_id):
                    result = {"id": potential_id.upper(), "title": potential_title}
                    if debug:
                        print(f"  ✅ Dash format parsed: ID='{result['id']}', Title='{result['title']}'")
                    return result
                elif debug:
                    print(f"    ❌ Invalid ID format (not 8 hex chars)")
        
        # If no valid ID-title split found, return as title only
        result = {"id": None, "title": title}
        if debug:
            print(f"  ⚠️  No ID found, using as title only: '{result['title']}'")
        return result
        
    except Exception as e:
        print(f"❌ Error parsing title '{issue_title}': {e}", file=sys.stderr)
        return {"id": None, "title": issue_title}

def parse_labels(labels: List[Dict], debug: bool = False) -> str:
    """Parse game state from labels."""
    try:
        if debug:
            label_names = [label.get("name", "") for label in labels]
            print(f"🏷️  Labels found: {label_names}")
        
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
                result = state_mappings[label_name]
                if debug:
                    print(f"  ✅ State label found: '{label_name}' → '{result}'")
                return result
        
        if debug:
            print(f"  ⚠️  No state labels found, defaulting to 'Unknown'")
        return "Unknown"
    except Exception as e:
        print(f"❌ Error parsing labels: {e}", file=sys.stderr)
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

def process_issues(issues_data: List[Dict], debug: bool = False) -> List[Dict]:
    """Process raw issue data into game compatibility format."""
    processed = []
    
    if debug:
        print(f"\n📦 Processing {len(issues_data)} issues...")
    
    for i, issue in enumerate(issues_data):
        try:
            issue_number = issue.get("number", "unknown")
            issue_url = issue.get("html_url", "")
            
            if debug:
                print(f"\n🎮 Issue #{issue_number} ({i+1}/{len(issues_data)})")
                print(f"   URL: {issue_url}")
            
            # Skip the main repository issue
            if issue_url == "https://github.com/xenia-canary/game-compatibility/issues/1":
                if debug:
                    print(f"   ⏭️  Skipping main repository issue")
                continue
            
            # Parse title for game ID and name
            title_data = parse_title(issue.get("title", ""), debug)
            
            # Parse labels for compatibility state
            state = parse_labels(issue.get("labels", []), debug)
            
            game_data = {
                "id": title_data["id"],
                "title": title_data["title"],
                "state": state,
                "url": issue_url
            }
            
            if debug:
                print(f"   📊 Final result: ID='{game_data['id']}', Title='{game_data['title']}', State='{game_data['state']}'")
            
            processed.append(game_data)
            
        except Exception as e:
            print(f"❌ Error processing issue {issue.get('number', 'unknown')}: {e}", file=sys.stderr)
            continue
    
    if debug:
        print(f"\n✅ Processed {len(processed)} games successfully")
    
    return processed

def fetch_all_issues(debug: bool = False) -> List[Dict]:
    """Fetch all issues from the repository."""
    all_issues = []
    page = 1
    
    print("Fetching game compatibility issues...")
    
    while True:
        print(f"📄 Fetching page {page}...", end=" ")
        
        params = {
            'state': STATE,
            'per_page': PER_PAGE,
            'page': page
        }
        
        url = f"{BASE_URL}/repos/{OWNER}/{REPO}/issues"
        data = make_request(url, params)
        
        if not data:
            print("❌ Failed to fetch data")
            break
            
        if not isinstance(data, list) or len(data) == 0:
            print("✅ No more issues")
            break
        
        processed_issues = process_issues(data, debug)
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
        
        # Sort by URL (which contains issue number) in descending order
        def extract_issue_number(url: str) -> int:
            try:
                # Extract issue number from URL like "https://github.com/xenia-canary/game-compatibility/issues/533"
                return int(url.split('/')[-1])
            except (ValueError, IndexError):
                return 0  # Fallback for malformed URLs
        
        issues.sort(key=lambda x: extract_issue_number(x.get("url", "")), reverse=True)
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Saved {len(issues)} games to {OUTPUT_FILE}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving to {OUTPUT_FILE}: {e}", file=sys.stderr)
        return False

def main():
    """Main function."""
    # Check for debug mode
    debug_mode = '--debug' in sys.argv or '-d' in sys.argv
    
    if debug_mode:
        print("🐛 Debug mode enabled")
    
    if not GITHUB_TOKEN:
        print("⚠️  Warning: GITHUB_TOKEN not set. API requests may be rate-limited.", file=sys.stderr)
    
    print(f"Fetching compatibility data from {OWNER}/{REPO}")
    
    # Fetch all issues
    issues = fetch_all_issues(debug_mode)
    
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
    
    if debug_mode:
        print(f"\n🔍 Debug Summary:")
        print(f"  - First 3 games:")
        for i, game in enumerate(issues[:3]):
            print(f"    {i+1}. ID={game['id']}, Title='{game['title']}', State={game['state']}")
        if len(issues) > 3:
            print(f"    ... and {len(issues) - 3} more")

if __name__ == '__main__':
    main()
