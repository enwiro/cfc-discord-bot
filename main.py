#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

import discord
from dotenv import load_dotenv
import os
from string import Template
import math


def scrape_croisieres():
    driver = webdriver.Chrome()
    driver.get("https://www.cfc-croisieres.fr/croisieres/")

    # Scroll for load all page
    for _ in range(10):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(1)
    resp = driver.page_source
    driver.quit()

    # Extract data from HTML
    soup = BeautifulSoup(resp, "html.parser")
    cruises = []
    for card in soup.select("div.home-cruise-card__text-container"):
        # Title
        title = card.select_one("h3.home-cruise-card__title a").get_text(strip=True)
        m = re.match(r"(\d+)\s*Nuits?\s*-\s*(.+)", title, re.IGNORECASE)
        nights = int(m.group(1)) if m else None
        nom   = m.group(2).strip() if m else title

        # Price
        price_elem = card.select_one(".home-cruise-card__price__figure")
        price = int(price_elem.get_text(strip=True).replace(' ','').replace('€','')) if price_elem else None

        # Taxe
        taxe_elem = card.select_one(".home-cruise-card__price__service-charge")
        taxe = None
        if taxe_elem:
            mt = re.search(r"([\d\s]+€)", taxe_elem.get_text())
            taxe = int(mt.group(1).strip().replace(' ','').replace('€','')) if mt else None
        
        # Link
        link_elem = soup.select_one("h3.home-cruise-card__title a")
        link = link_elem["href"] if link_elem else None

        # Date
        start_elem = soup.select_one(".home-cruise-card__dates-depart .home-cruise-card__text")
        end_elem = soup.select_one(".home-cruise-card__dates-arrive .home-cruise-card__text")

        startDate = start_elem.get_text().strip() if start_elem else None
        endDate = end_elem.get_text().strip() if end_elem else None

        if (price and taxe and nights and link):
            pricePerDay = (price + taxe) / nights
            cruises.append({
                "title": nom,
                "nights": nights,
                "price": price,
                "startDate": startDate,
                "endDate": endDate,
                "taxe": taxe,
                "pricePerDay" : pricePerDay,
                "link" : link
            })
            cruises = sorted(cruises, key=lambda x: x["pricePerDay"])

    return cruises

def filter_cruise_under(price_per_day, cruises):
    cruises_under_price_per_day = []
    for cruise in cruises:
        if cruise["pricePerDay"] <= price_per_day :
            cruises_under_price_per_day.append(cruise)

    return cruises_under_price_per_day

if __name__ == "__main__":
    load_dotenv()

    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    CruiseAlert = Template("""
@here 🚢
**Croisière : $title**
Nuits : $nights
Date : $startDate - $endDate
Prix par jour : $pricePerDay €
*Lien : https://www.cfc-croisieres.fr$link*
    """)


    @client.event
    async def on_ready():
        # Recherche du canal nommé "general"
        channel = client.get_channel(1382335792273166357)
        if channel:
            cruises = scrape_croisieres()
            cruises = filter_cruise_under(81, cruises)
            for cruise in cruises :
                await channel.send(
                    CruiseAlert.substitute(
                        title=cruise["title"], 
                        nights=cruise["nights"], 
                        startDate=cruise["startDate"], 
                        endDate=cruise["endDate"],
                        pricePerDay=math.ceil(cruise["pricePerDay"]),
                        link=cruise["link"]
                        )
                    )
        await client.close()

    client.run(os.getenv('DISCORD_TOKEN'))