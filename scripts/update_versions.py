import json, urllib.request, os, sys

GITHUB_API = "https://api.github.com/repos"

def debug(msg):
    print(f"[DEBUG] {msg}", file=sys.stderr)

def gh_get(url):
    debug(f"Requesting {url}")
    headers = {
        "User-Agent": "github-actions",
        "Accept": "application/vnd.github+json"
    }
    token = os.environ.get("AUTH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        debug("Using AUTH_TOKEN for authentication")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        text = resp.read()
        debug(f"Response status: {resp.status}, length: {len(text)} bytes")
        return json.loads(text)

# ----- Xenia Manager tags -----
def fetch_latest_tag_string(repo_url):
    try:
        debug(f"Fetching latest tag from {repo_url}")
        data = gh_get(repo_url)
        tag = data.get("tag_name")
        debug(f"Tag found: {tag}")
        return tag
    except Exception as e:
        print(f"Error fetching {repo_url}: {e}", file=sys.stderr)
        return None

# ----- Canary (sort releases explicitly) -----
def fetch_all_releases(repo, per_page=100):
    """Fetch all releases for a repository with pagination."""
    releases = []
    page = 1
    while True:
        url = f"{GITHUB_API}/{repo}/releases?per_page={per_page}&page={page}"
        batch = gh_get(url)
        if not batch:
            break
        releases.extend(batch)
        if len(batch) < per_page:
            break  # no more pages
        page += 1
    return releases

def fetch_latest_canary():
    repo = "xenia-canary/xenia-canary-releases"

    # --- Step 1: try latest endpoint ---
    debug(f"Fetching latest release for {repo}")
    try:
        latest = gh_get(f"{GITHUB_API}/{repo}/releases/latest")
        assets = [a for a in latest.get("assets", []) if "windows" in a["name"].lower()]
        if assets:
            asset = assets[0]
            debug(f"Found Windows asset in latest release: {latest['tag_name']} / {asset['name']}")
            return {
                "tag_name": latest.get("tag_name"),
                "url": asset.get("browser_download_url"),
            }
        else:
            debug("Latest release has no Windows asset, falling back to all releases")
    except Exception as e:
        debug(f"Error fetching latest release: {e}, falling back to all releases")

    # --- Step 2: fallback to fetching all releases---
    releases = fetch_all_releases(repo)
    debug(f"Fetched {len(releases)} total releases")

    if not releases:
        return {"tag_name": None, "url": None}

    # sort newest first
    releases.sort(
        key=lambda r: r.get("published_at") or r.get("created_at") or "",
        reverse=True,
    )

    for rel in releases:
        assets = [a for a in rel.get("assets", []) if "windows" in a["name"].lower()]
        if assets:
            asset = assets[0]
            debug(f"Chosen Canary release: {rel['tag_name']} / {asset['name']}")
            return {
                "tag_name": rel.get("tag_name"),
                "url": asset.get("browser_download_url"),
            }

    debug("No Windows assets found in any Canary releases")
    return {"tag_name": None, "url": None}

# ----- Netplay stable -----
def fetch_netplay_stable():
    debug("Fetching Netplay stable latest release")
    rel = gh_get(f"{GITHUB_API}/AdrianCassar/xenia-canary/releases/latest")
    assets = [a for a in rel.get("assets", []) if "windows" in a["name"].lower()]
    asset = assets[0]["name"] if assets else "none"
    debug(f"Stable tag={rel.get('tag_name')} asset={asset}")
    return {
        "tag_name": rel.get("tag_name"),
        "url": assets[0].get("browser_download_url") if assets else None
    }

# ----- Netplay nightly -----
def fetch_netplay_nightly():
    branch = "netplay_canary_experimental"
    debug(f"Fetching commit SHA for branch {branch}")
    commit_data = gh_get(f"{GITHUB_API}/AdrianCassar/xenia-canary/commits/{branch}")
    sha = commit_data.get("sha", "")[:7]
    parents = commit_data.get("parents", [])
    parent_sha = parents[0]["sha"][:7] if parents else None
    debug(f"Commit sha={sha}, parent_sha={parent_sha}")

    return {
        "tag_name": sha or parent_sha or None,
        "url": "https://nightly.link/AdrianCassar/xenia-canary/workflows/"
               "Windows_build/netplay_canary_experimental/xenia_canary_netplay_windows.zip"
    }

# ----- Mousehook versions -----
def fetch_mousehook_versions():
    debug("Fetching Mousehook releases")
    releases = gh_get(f"{GITHUB_API}/marinesciencedude/xenia-canary-mousehook/releases")
    debug(f"Found {len(releases)} mousehook releases")

    def fmt(rel):
        if not rel:
            return {"tag_name": None, "url": None}
        url = rel["assets"][0].get("browser_download_url") if rel.get("assets") else None
        debug(f"Mousehook release {rel.get('tag_name')} url={url}")
        return {"tag_name": rel.get("tag_name"), "url": url}

    standard_rel = next((r for r in releases if "netplay" not in r["tag_name"].lower()), None)
    netplay_rel = next((r for r in releases if "netplay" in r["tag_name"].lower()), None)
    return {"standard": fmt(standard_rel), "netplay": fmt(netplay_rel)}

# ----- MAIN -----
debug("=== Starting version fetch process ===")

fetched_data = {
    "stable": fetch_latest_tag_string(f"{GITHUB_API}/xenia-manager/xenia-manager/releases/latest"),
    "experimental": fetch_latest_tag_string(f"{GITHUB_API}/xenia-manager/experimental-builds/releases/latest"),
    "xenia": {
        "canary": fetch_latest_canary(),
        "netplay": {
            "stable": fetch_netplay_stable(),
            "nightly": fetch_netplay_nightly()
        },
        "mousehook": fetch_mousehook_versions()
    }
}

debug("Writing updated version.json")
os.makedirs("data", exist_ok=True)
with open("data/version.json", "w", encoding="utf-8") as f:
    json.dump(fetched_data, f, indent=2)

debug("Final fetched_data JSON:")
print(json.dumps(fetched_data, indent=2))

print("✅ version.json updated with latest releases")