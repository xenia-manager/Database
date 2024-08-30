import json
import requests
from lxml import etree
import re
import time

# URL of the JSON data
json_url = "https://gist.githubusercontent.com/shazzaam7/f50b225d0e423b2e7da9ab2918beeb4c/raw/d22657de5dbcfdc658450bfbe76856b3f580c04b/filtered_xbox360_marketplace.json"

# Fetch JSON data from the provided URL
response = requests.get(json_url)
if response.status_code == 200:
    initial_json = response.json()
else:
    print(f"Failed to fetch JSON data from the URL, status code: {response.status_code}")
    initial_json = []

# URL template
url_template = "http://marketplace-xb.xboxlive.com/marketplacecatalog/v1/product/en-US/66ACD000-77FE-1000-9115-D802{id}?bodytypes=1.3&detailview=detaillevel5&pagenum=1&pagesize=1&stores=1&tiers=2.3&offerfilter=1&producttypes=1.5.18.19.20.21.22.23.30.34.37.46.47.61"

# Function to extract the required data from the XML
def extract_game_data(xml_content, titleid):
    ns = {
        'a': 'http://www.w3.org/2005/Atom',
        '': 'http://marketplace.xboxlive.com/resource/product/v1'
    }
    tree = etree.fromstring(xml_content)
    entry = tree.find('.//a:entry', namespaces=ns)
    if entry is None:
        print(f"No entry found for titleid: {titleid}")
        return None
    
    title_element = entry.find('.//fullTitle', namespaces=ns)
    title = title_element.text if title_element is not None else None

    # Remove the "Full Game - " prefix from the title if it exists
    if title and title.startswith("Full Game - "):
        title = title.replace("Full Game - ", "", 1)

    if title:
        title = re.sub(r'[^\w\s-]', '', title)  # Keep alphanumeric characters, spaces, underscores, and hyphens

    game_data = {
        'ID': titleid,
        'Title': title,
        'Banner': None,
        'Background': None,
        'Box art': None,
        'Icon': None
    }

    images = entry.findall('.//image', namespaces=ns)
    for image in images:
        fileUrl = image.find('fileUrl', namespaces=ns).text
        imageMediaType = image.find('imageMediaType', namespaces=ns).text
        if imageMediaType == '14':
            relationshipType = image.find('size', namespaces=ns).text
            if relationshipType == '15':
                game_data['Banner'] = fileUrl
            elif relationshipType == '22':
                game_data['Background'] = fileUrl
            elif relationshipType == '23':
                game_data['Box art'] = fileUrl
            elif relationshipType == '14':
                game_data['Icon'] = fileUrl

    return game_data

# Retry mechanism parameters
max_retries = 5
retry_delay = 5  # seconds

output_data = []
for game in initial_json:
    titleid = game['titleid']
    url = url_template.format(id=titleid)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                game_data = extract_game_data(response.content, titleid)
                if game_data and game_data['Box art'] is not None:
                    output_data.append(game_data)
                    print(game_data)
                break  # Exit retry loop if successful
            else:
                print(f"Failed to fetch data for titleid: {titleid}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed for titleid: {titleid}. Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)  # Wait before retrying
            else:
                print(f"Failed to fetch data for titleid: {titleid} after {max_retries} attempts.")

# Save the output data to a JSON file
with open('Database/xbox_marketplace_games.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=4)
