import rookiepy
from curl_cffi import requests
from bs4 import BeautifulSoup 
from urllib.parse import urljoin

import tjx

# Home menu
url = "https://tjmaxx.tjx.com/store/index.jsp"


# My personal path where my cookies are stored. Must add a place for the user's ones too'
cookie_path = "/home/diego/.config/mozilla/firefox/rj3cbqz5.default-release/cookies.sqlite"
raw_cookies = rookiepy.any_browser(cookie_path, domains=["tjx.com"])
session = requests.Session(impersonate="firefox")

for c in raw_cookies:
    session.cookies.set(c["name"], c["value"], domain=c["domain"])

response = session.get(url)

print("Status: ", "Connection succesful" if response.status_code == 200 else "Connection failed")

soup = BeautifulSoup(response.text, "html.parser")

options = soup.find('div', class_="navigation-bar-wrap")

# main options
# Only gets the first 11 categories
top_links = options.select("nav > ul > li > a[href], div > ul > li > a[href]")

options = {
    f"{i}. {a.get_text(strip=True)}": urljoin(url, a['href'])
    for i, a in enumerate([link for link in top_links if link.get_text(strip=True)], start=1)
}

user_options = list(options.keys())

print(*user_options, sep="\n")

user_option = (int(input(f"Pick an option from 1-{len(user_options)}: ")) - 1)
selected = user_options[user_option]
user_link = options[selected]

category_response = session.get(user_link)
category_soup = BeautifulSoup(category_response.text, "html.parser")

tjx.scrape_page(category_soup, selected)