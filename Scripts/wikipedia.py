# Libraries
import requests
from bs4 import BeautifulSoup
import json
import re
import unicodedata

# Function to extract image URL from the title's Wikipedia page
def extract_image_url(title_link):
    response = requests.get("https://en.wikipedia.org" + title_link)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        infobox_image = soup.find('td', {'class': 'infobox-image'})
        if infobox_image:
            image = infobox_image.find('img')
            if image:
                image_url = image.get('src')
                # Prepend "https://" to the image URL if it doesn't start with it already
                if not image_url.startswith("https://"):
                    image_url = "https:" + image_url
                return image_url
    return None

def clean_title(cell):
    title = cell.text.strip()
    # Remove footnotes like [note 9], [note 10], etc.
    title = re.sub(r'\[\w+\s*\d+\]', '', title)
    title = unicodedata.normalize('NFKD', title)
    title = title.replace(':', ' -')
    return title


# List of Wikipedia URLs
urls = [
    "https://en.wikipedia.org/wiki/List_of_Xbox_360_games_(A%E2%80%93L)",
    "https://en.wikipedia.org/wiki/List_of_Xbox_360_games_(M%E2%80%93Z)"
]

# Initialize an empty list to store all Xbox 360 titles data
xbox_360_titles = []

# Iterate over each URL
for url in urls:
    # Send a GET request to the URL
    response = requests.get(url)
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find the table containing Xbox 360 titles
        table = soup.find('table', {'class': 'wikitable sortable'})
        # Extract table rows
        rows = table.find_all('tr')
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            title = clean_title(cells[0])
            # Extract the hyperlink and its URL
            link = cells[0].find('a')
            if link:
                game_link = link.get('href')
                image_url = extract_image_url(game_link)
            else:
                game_link = None
                image_url = None
            
            if title and (game_link or image_url):
                game_data = {
                    "title": title,
                    "url": game_link,
                    "boxart": image_url
                }
                # Append the dictionary to the list
                print(game_data)
                xbox_360_titles.append(game_data)

with open('Database/wikipedia_games.json', 'w') as json_file:
    json.dump(xbox_360_titles, json_file, indent=4)

print("Data scraped and saved successfully!")
