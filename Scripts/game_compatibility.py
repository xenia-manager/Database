import json
import os
import sys
import time
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# Configuration defaults (overridden in main)
DEFAULT_OWNER = 'xenia-canary'
DEFAULT_REPO = 'game-compatibility'
DEFAULT_OUTPUT_FILE = 'Database/Game Compatibility/canary.json'

STATE = 'open'
PER_PAGE = 100
BASE_URL = 'https://api.github.com'

# Rate limiting
RATE_LIMIT_DELAY = 0.1
MAX_RETRIES = 3
RETRY_DELAY = 5

GITHUB_TOKEN = os.getenv('TOKEN')


def get_headers() -> Dict[str, str]:
    headers = {
        'Accept': 'application/vnd.github+json',  # Updated to newer API version
        'X-GitHub-Api-Version': '2022-11-28',    # Specify API version
        'User-Agent': 'xenia-data-sync/1.0'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'  # Use Bearer instead of token
    return headers


def parse_title(issue_title: str, debug: bool = False) -> Dict[str, Optional[str]]:
    try:
        title = issue_title.strip()
        if debug:
            print(f"🔍 Parsing title: '{title}'")

        if ' - ' in title:
            parts = title.split(' - ', 1)
            return {"id": parts[0].strip().upper(), "title": parts[1].strip()}

        if '-' in title:
            dash_index = title.find('-')
            if dash_index > 0:
                potential_id = title[:dash_index].strip()
                potential_title = title[dash_index + 1:].strip()
                if len(potential_id) == 8 and potential_id.isalnum():
                    return {"id": potential_id.upper(), "title": potential_title}

        return {"id": None, "title": title}
    except Exception as e:
        print(f"❌ Error parsing title '{issue_title}': {e}", file=sys.stderr)
        return {"id": None, "title": issue_title}


def parse_labels(labels: List[Dict], debug: bool = False) -> str:
    try:
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
        print(f"❌ Error parsing labels: {e}", file=sys.stderr)
        return "Unknown"


def validate_repo_exists(owner: str, repo: str, debug: bool = False) -> bool:
    """Check if the repository exists before trying to fetch issues"""
    url = f"{BASE_URL}/repos/{owner}/{repo}"
    
    if debug:
        print(f"🔍 Checking if repository {owner}/{repo} exists...")
    
    try:
        request = Request(url, headers=get_headers())
        with urlopen(request, timeout=30) as response:
            if response.status == 200:
                if debug:
                    print(f"✅ Repository {owner}/{repo} exists and is accessible")
                return True
    except HTTPError as e:
        if e.code == 404:
            print(f"❌ Repository {owner}/{repo} not found (404)", file=sys.stderr)
        elif e.code == 403:
            print(f"❌ Access denied to {owner}/{repo} (403). Check permissions/token.", file=sys.stderr)
        else:
            print(f"❌ HTTP Error {e.code} when checking repository: {e.reason}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error checking repository: {e}", file=sys.stderr)
        return False
    
    return False


def make_request(url: str, params: Optional[Dict] = None, debug: bool = False) -> Optional[Dict]:
    # Validate parameters
    if params:
        # Ensure all values are strings or numbers
        clean_params = {}
        for k, v in params.items():
            if isinstance(v, (str, int)):
                clean_params[k] = str(v)
            else:
                print(f"⚠️ Skipping invalid parameter {k}={v}", file=sys.stderr)
        params = clean_params
        
        if params:
            url = f"{url}?{urlencode(params)}"

    if debug:
        print(f"🌐 Making request to: {url}")

    for attempt in range(MAX_RETRIES):
        try:
            request = Request(url, headers=get_headers())
            with urlopen(request, timeout=30) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if debug:
                        print(f"✅ Request successful, got {len(data) if isinstance(data, list) else 1} item(s)")
                    return data
                else:
                    print(f"❌ Unexpected status code: {response.status}", file=sys.stderr)
        except HTTPError as e:
            if e.code == 403:
                print(f"Rate limited (403). Waiting {RETRY_DELAY * (attempt + 1)} seconds...", file=sys.stderr)
                time.sleep(RETRY_DELAY * (attempt + 1))
            elif e.code == 422:
                print(f"❌ Unprocessable Entity (422). Likely reached end of available pages.", file=sys.stderr)
                if debug:
                    print(f"   URL: {url}", file=sys.stderr)
                    if params:
                        print(f"   Params: {params}", file=sys.stderr)
                # Return empty list to indicate no more data instead of None
                return []
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


def process_issues(issues_data: List[Dict], debug: bool = False, owner: str = '', repo: str = '') -> List[Dict]:
    processed = []
    for issue in issues_data:
        try:
            issue_number = issue.get("number", 0)
            issue_url = issue.get("html_url", "")
            
            # Skip pull requests
            if "pull_request" in issue:
                if debug:
                    print(f"⏭️ Skipping pull request #{issue_number}")
                continue

            # Skip specific issues depending on repo
            if owner == 'xenia-canary' and issue_number == 1:
                if debug:
                    print(f"⏭️ Skipping Canary repo issue #{issue_number}")
                continue
            elif owner == 'xenia-project' and issue_number == 2247:
                if debug:
                    print(f"⏭️ Skipping Stable repo issue #{issue_number}")
                continue

            title_data = parse_title(issue.get("title", ""), debug)
            state = parse_labels(issue.get("labels", []), debug)

            game_data = {
                "id": title_data["id"],
                "title": title_data["title"],
                "state": state,
                "url": issue_url
            }

            processed.append(game_data)
        except Exception as e:
            print(f"❌ Error processing issue {issue.get('number', 'unknown')}: {e}", file=sys.stderr)
            continue
    return processed

def get_repo_stats(owner: str, repo: str, debug: bool = False) -> Dict[str, int]:
    """Get repository statistics to understand total issue counts"""
    url = f"{BASE_URL}/repos/{owner}/{repo}"
    data = make_request(url, debug=debug)
    
    if data and isinstance(data, dict):
        return {
            'open_issues': data.get('open_issues_count', 0),
            'total_issues': data.get('open_issues_count', 0)  # This includes PRs
        }
    return {'open_issues': 0, 'total_issues': 0}


def fetch_issues_by_date_ranges(owner: str, repo: str, debug: bool = False) -> List[Dict]:
    """Fetch all issues by breaking them into date ranges to bypass pagination limits"""
    from datetime import datetime, timedelta
    import calendar
    
    all_issues = []
    
    # Start from 2013 (when Xenia project likely started) to now
    start_year = 2013
    current_year = datetime.now().year
    
    print(f"🗓️  Fetching issues by year ranges from {start_year} to {current_year}...")
    
    for year in range(start_year, current_year + 1):
        # Create date range for this year
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        print(f"📅 Fetching issues from {year}...")
        
        page = 1
        year_issues = []
        
        while True:
            params = {
                'q': f'repo:{owner}/{repo} is:issue is:open created:{start_date}..{end_date}',
                'sort': 'created',
                'order': 'desc',
                'per_page': PER_PAGE,
                'page': page
            }
            
            url = f"{BASE_URL}/search/issues"
            data = make_request(url, params, debug)
            
            if not data or not isinstance(data, dict):
                break
                
            items = data.get('items', [])
            if not items:
                break
            
            if debug:
                print(f"  📄 {year} Page {page}: {len(items)} issues")
            
            processed_issues = process_issues(items, debug, owner, repo)
            year_issues.extend(processed_issues)
            
            if len(items) < PER_PAGE:
                break
                
            page += 1
            time.sleep(RATE_LIMIT_DELAY * 2)  # Be more conservative with search API
            
            if page > 10:  # Safety valve
                break
        
        print(f"✅ {year}: Found {len(year_issues)} issues")
        all_issues.extend(year_issues)
    
    # Remove duplicates (just in case)
    seen_urls = set()
    unique_issues = []
    for issue in all_issues:
        if issue['url'] not in seen_urls:
            seen_urls.add(issue['url'])
            unique_issues.append(issue)
    
    if len(all_issues) != len(unique_issues):
        print(f"🔄 Removed {len(all_issues) - len(unique_issues)} duplicate issues")
    
    return unique_issues


def fetch_issues_via_search(owner: str, repo: str, debug: bool = False) -> List[Dict]:
    """Alternative method using GitHub Search API with single query"""
    all_issues = []
    page = 1
    
    while True:
        # Search API allows different queries and may have higher limits
        params = {
            'q': f'repo:{owner}/{repo} is:issue is:open',
            'sort': 'created',
            'order': 'desc',
            'per_page': PER_PAGE,
            'page': page
        }
        
        url = f"{BASE_URL}/search/issues"
        data = make_request(url, params, debug)
        
        if not data or not isinstance(data, dict):
            break
            
        items = data.get('items', [])
        if not items:
            break
            
        if debug:
            print(f"🔍 Search API - Page {page}: {len(items)} issues (total: {data.get('total_count', 'unknown')})")
        
        processed_issues = process_issues(items, debug, owner, repo)
        all_issues.extend(processed_issues)
        
        if len(items) < PER_PAGE:
            break
            
        page += 1
        time.sleep(RATE_LIMIT_DELAY * 2)  # Search API needs more conservative rate limiting
        
        # Search API has stricter rate limits, so be more conservative
        if page > 10:  # 1000 results max for search API too
            print("⚠️  Reached Search API pagination limit")
            break
    
    return all_issues


def fetch_all_issues(owner: str, repo: str, debug: bool = False) -> List[Dict]:
    # First, validate that the repository exists
    if not validate_repo_exists(owner, repo, debug):
        return []
    
    # Get repository stats for comparison
    repo_stats = get_repo_stats(owner, repo, debug)
    if debug:
        print(f"📊 Repository stats: {repo_stats['open_issues']} open issues (includes PRs)")
    
    all_issues = []
    page = 1
    max_pages = 100  # Safety limit to prevent infinite loops

    while page <= max_pages:
        params = {
            'state': STATE,
            'per_page': PER_PAGE,
            'page': page,
            'sort': 'created',
            'direction': 'desc'
        }
        
        url = f"{BASE_URL}/repos/{owner}/{repo}/issues"
        data = make_request(url, params, debug)

        # Handle different return cases
        if data is None:
            print("❌ Failed to fetch data (connection error)")
            break
        elif isinstance(data, list) and len(data) == 0:
            if page == 1:
                print("✅ No issues found in repository")
            else:
                if debug:
                    print(f"✅ No more issues (reached end of available data at page {page})")
                else:
                    print("✅ Reached end of available data")
            break

        if not isinstance(data, list):
            print(f"❌ Expected list, got {type(data)}", file=sys.stderr)
            if isinstance(data, dict) and 'message' in data:
                print(f"   API message: {data['message']}", file=sys.stderr)
            break

        if debug:
            print(f"📄 Processing page {page} with {len(data)} issues (total so far: {len(all_issues)})")

        processed_issues = process_issues(data, debug, owner, repo)
        all_issues.extend(processed_issues)

        # Check if we've reached the last page
        if len(data) < PER_PAGE:
            if debug:
                print(f"📄 Last page reached (got {len(data)} < {PER_PAGE})")
            break

        page += 1
        time.sleep(RATE_LIMIT_DELAY)

    # Warn if we hit the GitHub API pagination limit
    if len(all_issues) >= 999 and page > 10:
        print("⚠️  Note: You may have hit GitHub's ~1000 result pagination limit.", file=sys.stderr)
        print("   This is a known limitation of the GitHub API.", file=sys.stderr)

    return all_issues


def save_compatibility_data(issues: List[Dict], output_file: str) -> bool:
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        def extract_issue_number(url: str) -> int:
            try:
                return int(url.split('/')[-1])
            except (ValueError, IndexError):
                return 0

        issues.sort(key=lambda x: extract_issue_number(x.get("url", "")), reverse=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved {len(issues)} games to {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error saving to {output_file}: {e}", file=sys.stderr)
        return False


def main():
    debug_mode = '--debug' in sys.argv or '-d' in sys.argv
    complete_fetch = '--complete' in sys.argv or '-c' in sys.argv

    if '--stable' in sys.argv:
        owner = 'xenia-project'
        repo = 'game-compatibility'
        output_file = 'Database/Game Compatibility/stable.json'
    else:
        owner = DEFAULT_OWNER
        repo = DEFAULT_REPO
        output_file = DEFAULT_OUTPUT_FILE

    if debug_mode:
        print("🐛 Debug mode enabled")
        
    if complete_fetch:
        print("🔄 Complete fetch mode enabled - will attempt to get all issues")

    if not GITHUB_TOKEN:
        print("⚠️  Warning: GITHUB_TOKEN not set. API requests may be rate-limited.", file=sys.stderr)

    print(f"Fetching compatibility data from {owner}/{repo}")

    # Choose strategy based on flags
    if complete_fetch:
        print("🗓️  Using date-based chunking for complete fetch...")
        issues = fetch_issues_by_date_ranges(owner, repo, debug_mode)
    else:
        print("📡 Using standard API fetch (limited to ~1000 results)...")
        issues = fetch_all_issues(owner, repo, debug_mode)
        
        if len(issues) >= 999:
            print("⚠️  Hit API pagination limit. Use --complete flag to fetch all issues.")

    if not issues:
        print("❌ No issues fetched or error occurred", file=sys.stderr)
        sys.exit(1)

    if not save_compatibility_data(issues, output_file):
        sys.exit(1)

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
        for i, game in enumerate(issues[:3]):
            print(f"  {i+1}. ID={game['id']}, Title='{game['title']}', State={game['state']}")
        if len(issues) > 3:
            print(f"  ... and {len(issues) - 3} more")


if __name__ == '__main__':
    main()