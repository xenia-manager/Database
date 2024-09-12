# Libraries
import json
import requests
from bs4 import BeautifulSoup
import os

# URL template
base_url = "https://gamesdb.launchbox-app.com"
url_template = "https://gamesdb.launchbox-app.com/platforms/games/19-microsoft-xbox-360/page/{}"
games = []

# Function to extract content of the games
def getgamecontent(gamelinks):
    for url in gamelinks:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Game Title
        title = ""
        titleparse = soup.find('h1')
        if titleparse:
            title = titleparse.text.strip().replace(':',' -')

        # Artwork
        artwork = {
            "Front Image": None,
            "Disc": None,
            "Logo": None
        }
        artworkcontainer = soup.findAll('div', class_='imageContainerColumn')
        if artworkcontainer:
            for container in artworkcontainer:
                imgelementsparse = container.find_all('img')
                if imgelementsparse:
                    for img in imgelementsparse:
                        img_src = img.get('src')
                        img_alt = img.get('alt', '')
                        if "Box - Front Image" in img_alt and "Fanart" not in img_alt:
                            artwork['Front Image'] = img_src
                        if "Disc" in img_alt:
                            artwork['Disc'] = img_src
                        if "Clear Logo Image" in img_alt:
                            artwork['Logo'] = img_src
                    
        # Parsed Game
        parsed_game = {
            'Title': title,
            'URL': url.replace('images', 'details')
        }

        if artwork and artwork['Front Image']:
            # Check if artwork as disc image
            if artwork.get('Disc') is None:
                artwork['Disc'] = "https://raw.githubusercontent.com/xenia-manager/xenia-manager-database/main/Assets/disc.png"
            parsed_game['Artwork'] = artwork
            print(parsed_game)
            games.append(parsed_game)

# Function to extract all games per pages
def getgameurl():
    last_page = getNumberOfPages()
    for page_number in range(1, last_page):
        all_hrefs = []
        url = url_template.format(page_number)
        print("Currently processing this url: " + url)   

        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        hrefs = soup.select('#cardsContainer div a')
        for href in hrefs:
            href_url = href.get('href')
            full_url = base_url + href_url if href_url.startswith('/') else href_url
            full_url = full_url.replace('details', 'images')
            all_hrefs.append(full_url)
            
        print(f'Page {page_number}: Found {len(hrefs)} links.') 
        print(f'Parsing games from page {page_number}')
        getgamecontent(all_hrefs)

# Check how many pages there is
def getNumberOfPages():
    page_number = 1
    while True:
        url = url_template.format(page_number)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        empty_list = soup.find('h1', class_='empty-games-list')
        if empty_list:
            print(f"Empty list found on page {page_number}.")
            break
            
        print(f"Checked page {page_number}.")
        page_number += 1
    
    return page_number

getgameurl()

with open('Database/launchbox_games.json', 'w') as json_file:
    json.dump(games, json_file, indent=4)
