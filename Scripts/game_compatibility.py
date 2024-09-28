import requests
import time
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
OWNER = 'xenia-canary'
REPO = 'game-compatibility'
STATE = 'open'
PER_PAGE = 100  # Maximum allowed per page

# Headers for authentication
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Function to parse title
def parse_title(issue_title):
    try:
        parts = issue_title.split(' - ', 1)  # Split at first occurrence of ' - '
        return {"id": parts[0], "title": parts[1]} if len(parts) == 2 else {"id": None, "title": issue_title}
    except Exception as e:
        print(f"Error parsing title: {e}")
        return {"id": None, "title": issue_title}

# Function to parse labels
def parse_labels(labels):
    try:
        for label in labels:
            if label["name"].startswith("state-"):
                if label["name"] in ["state-nothing", "state-crash", "state-crash-guest", "state-crash-host", "state-crash-xna-WONTFIX"]:
                    return "Unplayable"
                elif label["name"] in ["state-intro", "state-hang", "state-load", "state-title", "state-menus"]:
                    return "Loads"
                elif label["name"] in ["state-gameplay"]:
                    return "Gameplay"
                elif label["name"] in ["state-playable"]:
                    return "Playable"
        return "Unknown"
    except Exception as e:
        print(f"Error parsing labels: {e}")
        return "Unknown"

# Function to parse API response
def parse_request(data):
    try:
        parsed_response = []
        for game in data:
            # Parse game ID and title
            gameid_title = parse_title(game["title"])
            state = parse_labels(game["labels"])
            parsed_game = {
                "id": gameid_title["id"],
                "title": gameid_title["title"],
                "state": state,
                "url": game["html_url"]
            }
            print(parsed_game)
            parsed_response.append(parsed_game)
        return parsed_response
    except Exception as e:
        print(f"Error processing request data: {e}")
        return []

# Function to fetch issues
def fetch_issues(owner, repo, state='all', per_page=100):
    try:
        issues = []
        page = 1
        while True:
            url = f'https://api.github.com/repos/{owner}/{repo}/issues'
            params = {
                'state': state,
                'per_page': per_page,
                'page': page
            }
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f'Error fetching issues: {response.status_code}')
                print(response.json())
                break
            
            data = response.json()
            if not data:
                break  # No more issues
            
            issues.extend(parse_request(data))
            print(f'Fetched page {page} with {len(data)} issues')
            page += 1
            
            # To respect rate limits
            time.sleep(1)  # Sleep for 1 second between requests
        
        return issues
    except Exception as e:
        print(f"Error fetching issues: {e}")
        return []

# Function to save issues to file
def save_issues_to_file(issues, filename='Database/game_compatibility.json'):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(issues, f, ensure_ascii=False, indent=4)
        print(f'Saved {len(issues)} issues to {filename}')
    except Exception as e:
        print(f"Error saving issues to file: {e}")

# Main function
if __name__ == '__main__':
    all_issues = fetch_issues(OWNER, REPO, STATE, PER_PAGE)
    if all_issues:
        save_issues_to_file(all_issues)
    else:
        print("No issues fetched or error occurred.")