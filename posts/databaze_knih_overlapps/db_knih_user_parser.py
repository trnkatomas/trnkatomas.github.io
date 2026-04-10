import requests
from bs4 import BeautifulSoup
import re
import json
import time

def extract_user_reviews(soup, author, title):
    # 2. Extract User Ratings
    # Ratings are typically listed within a container with class 'komentare_vypis'
    reviews = []
    review_containers = soup.find_all("div", class_="ubox")
    
    if not review_containers:
        print("Could not find the review container. The page structure might have changed.")
        return

    # Each rating is usually in a div (often with no specific class, or 'komentar_item')
    # We look for user links and rating images inside
    for review_container in review_containers:
        user_tag = review_container.find("a")
        if user_tag:
            user_name = user_tag.get_text(strip=True)
            
            # Stars are represented by <img> tags with alt text like "5 hvězdiček"
            star_img = review_container.find("div", {"class" : ['rating-svg', 'rating-svg-novice']})
            stars = 0
            if star_img and 'style' in star_img.attrs:
                # Use regex to find the first digit in the alt text
                match = star_img['style'].split(":")
                if match and len(match) > 1:
                    stars = float(match[1])

            reviews.append({
                "author": author,
                "book_title": title,
                "user_name": user_name,
                "stars": stars
            })
    return reviews



def scrape_databaze_knih_reviews(url):
    # Set headers to mimic a real browser to avoid blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # 1. Extract Book Title and Author
        # Usually found in h1 and h2 tags at the top of the page
        title_raw = soup.find("h1")
        for child in title_raw.find_all("em"): child.decompose()
        title = title_raw.get_text(strip=True)
        author_tag = soup.find("span", class_="author")
        author = author_tag.get_text(strip=True) if author_tag else "N/A"

        print(f"Scraping: {title} by {author}\n" + "-"*50)
        pages_to_parse = True

        reviews = []
        while pages_to_parse:
            current_reviews = extract_user_reviews(soup, author, title)
            reviews += current_reviews

            next_page = soup.find('span', class_='next')
            if not next_page:
                pages_to_parse = False
            else:
                next_page_link = next_page.find('a')
                time.sleep(1.5) # Polite delay to avoid getting blocked
                response = requests.get('https://www.databazeknih.cz' + next_page_link['href'], headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")

        return reviews

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# URL from your request
base_url = "https://www.databazeknih.cz/hodnoceni-knihy/" 

book_ids = [
    "maly-zivot-332368", "naivni-super-8767", "ctyricet-dnu-28894", 
    "kamen-a-bolest-11774", "lisky-na-vinici-278", "middlemarch-46538", 
    "nadejne-vyhlidky-8285", "pravda-o-zkaze-sodomy-41699", "pilire-zeme-12524", 
    "katedrala-more-15423", "noeticka-trilogie-povetron-26613", "egyptan-sinuhet-310526", 
    "navzdory-basnik-zpiva-295", "quo-vadis-285", "vanoce-na-manhattanu-574391"
]
book_ids_2 = [
    "harry-potter-harry-potter-a-kamen-mudrcu-501766",
    "mluviti-pravdu-107",
    "vrac-49004",
    "stoparuv-pruvodce-galaxii-stoparuv-pruvodce-galaxii-3996",
    "pan-prstenu-spolecenstvo-prstenu-2",
    "nekonecny-pribeh-679",
    "odkaz-dracich-jezdcu-odkaz-dracich-jazdcov-eragon-1108",
    "pipi-dlouha-puncocha-4-pribehy-2527",
    "letopisy-kralovske-komory-dablova-cisla-484501",
    "jmeno-ruze-607",
    "don-quijote-i-226118",
    "robert-langdon-sifra-mistra-leonarda-6",
]

all_data = []

for book_id in book_ids_2:
    url = f"https://www.databazeknih.cz/hodnoceni-knihy/{book_id}"
    book_reviews = scrape_databaze_knih_reviews(url) # Using the spider function from previous response
    if book_reviews:
        for entry in book_reviews:
            print(json.dumps(entry))
        all_data.extend(book_reviews)
    time.sleep(3) # Extra delay between different books to be safe

