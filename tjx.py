import rookiepy
from curl_cffi import requests
from bs4 import BeautifulSoup 
from rich.table import Table
from rich.console import Console
from price_parser import Price

# ==========================================
# TJX SCRAPER ROADMAP
# ==========================================
# [ ] 1. Extra Product Fields (same HTML card, zero extra requests)
#       - Brand name: <span class="product-brand"> (ignore if "reveal designer")
#       - Product URL: <a class="product-link">["href"] -> prepend "https://tjmaxx.tjx.com"
#       - Clickable terminal title: f"[link={url}]{name}[/link]" in rich table
#       - Low-stock alert: <div class="invLvlInd"> (e.g., "only 1 left!")
#       - Product ID: <a class="moveToFavlist">["data-itemid"] (unique key for tracking)
#       - Retail discount %: compare "retail compare" vs "price" alongside TJX markdown %
#
# [ ] 2. Pagination (scrape beyond the first 180 items)
#       - Find <div data-nextlink="..."> at the bottom of the product grid
#       - Wrap request/parse logic in a `while url:` loop
#       - Add `sleep(uniform(2.5, 5.0))` between pages to protect Akamai cookies
#       - Break early if page title switches to "Something went wrong."
#       - Deduplicate items using a `seen_ids = set()`
#
# [ ] 3. CLI Filters (argparse)
#       - --min-discount <int>   (only show deals >= X% off)
#       - --max-price <float>    (filter by budget)
#       - --search <keyword>     (match product name or brand)
#       - --pages <int>          (limit max pages fetched per run)
#       - --top <int>            (limit rows printed in terminal)
#
# [ ] 4. Persistence & Price Drop Tracking (CSV / SQLite)
#       - Export cleaned items to CSV (csv.DictWriter or pandas)
#       - Store runs in SQLite keyed by product ID + timestamp
#       - Flag "NEW" items and "PRICE DROP" second-markdowns compared to last run
# ==========================================

# There must be some delay so we are not rate-limtied

url = "https://tjmaxx.tjx.com/store/shop/clearance/_/N-3951437597?Nr=AND(OR(product.catalogId%3Atjmaxx)%2Cproduct.siteId%3Atjmaxx)&tn=10"

# Make sure to have a browser installed

# My personal path where my cookies are stored. Must add a place for the user's ones too'
cookie_path = "/home/diego/.config/mozilla/firefox/rj3cbqz5.default-release/cookies.sqlite"
raw_cookies = rookiepy.any_browser(cookie_path, domains=["tjx.com"])
session = requests.Session(impersonate="firefox")

for c in raw_cookies:
    session.cookies.set(c["name"], c["value"], domain=c["domain"])

response = session.get(url)

print("Status: ", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")
title = soup.title.string if soup.title else "No title"

# Use dictionary comprehension
# Will get the item name (the key), its price and what the product is supposed to retail for
cards = soup.find_all("div", class_="product")


items = [
    {
        "name": card.find("span", class_="product-title").get_text(strip=True) if card.find("span", class_="product-title") else None,
        "price": (price := Price.fromstring(card.find("span", class_="discounted-price").get_text(strip=True).split("new price:")[-1]).amount_float if card.find("span", class_="discounted-price") else None),
        "brand": (b if (b := card.find("span", class_="product-brand").get_text(strip=True)) and b.lower() != "reveal designer" else None) if card.find("span", class_="product-brand") else None,
        "original price": (orig := Price.fromstring(card.find("span", class_="strike").get_text(strip=True)).amount_float if card.find("span", class_="strike") else None),
        "retail compare": Price.fromstring(card.find("span", class_="price-comparison").get_text(strip=True)).amount_float if card.find("span", class_="price-comparison") else None,
        "discount": round(((orig - price) / orig) * 100, 1) if price and orig else None,
        "low stock": card.find("div", class_="invLvlInd").get_text(strip=True) if card.find("div", class_="invLvlInd") else None,
        "link": ("https://tjmaxx.tjx.com" + a["href"].split("?")[0] if (a := card.find("a", class_="product-link")) and a.get("href") else None),
    }
    for card in cards
]



# Sorts from lowest to greatest (finds max discounts)
items = sorted(items, key=lambda x: x["discount"] or 0, reverse=True )


table = Table(*[k.title() for k in items[0].keys() if k != "link"], title=title)

for item in items:
    name_display = f"[underline cyan][link={item['link']}]{item['name']}[/link][/underline cyan]" if item["link"] and item["name"] else (item["name"] or "-")
    table.add_row(
    name_display,
    item["name"] or "-",
    f"${item['price']:.2f}" if item["price"] is not None else "-",
    item['brand'] or "-",
    f"${item['original price']:.2f}" if item["original price"] is not None else "-",
    f"${item['retail compare']:.2f}" if item["retail compare"] is not None else "-",
    f"{item['discount']:.0f}%" if item["discount"] is not None else "-",
    item['low stock'] or "-",
    )

Console().print(table)
