#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 18 17:47:25 2023

@author: jake_ockerby
"""

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta


def best_value_hotels(url, min_reviews, min_rating):
    
    # # Parse the URL
    # parsed_url = urlparse(url)
    
    # # Extract query parameters
    # query_params = parse_qs(parsed_url.query)
    
    # # Extract check-in and check-out dates
    # checkin = query_params.get('checkin', [''])[0]
    # checkout = query_params.get('checkout', [''])[0]
    
    
    headers = {"User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 12871.102.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    print('here')
    # # Find number of properties
    # properties_element = soup.find('h1', {'class': 'f6431b446c d5f78961c3'})
    # properties = int(properties_element.text.split(':')[1].split('properties')[0].strip())
    
    # # Scrape HTML content of all pages
    # soup_list = [soup]
    # for i in range(int(properties/25)):
    #     url_new = url + '&offset={}'.format((i+1)*25)
    #     response = requests.get(url_new, headers=headers)
    #     soup = BeautifulSoup(response.text, 'html.parser')
    #     soup_list.append(soup)
        
    
    hotels_data = []
    # for soup in soup_list:
        # Find all the hotel elements in the HTML document
    hotels = soup.findAll('h1', {'class': 'detailed-card-header__title'})
    #     # Loop over the hotel elements and extract the desired data
    #     for hotel in hotels:
    #         # Extract the hotel name
    #         try:
    #             name_element = hotel.find('div', {'data-testid': 'title'})
    #             name = name_element.text.strip()
    #         except:
    #             name = np.nan
        
    #         # Extract the hotel location
    #         try:
    #             location_element = hotel.find('span', {'data-testid': 'address'})
    #             location = location_element.text.strip()
    #         except:
    #             location = np.nan
                
    #         # Extract the web link
    #         try:
    #             a = hotel.find('a', {'data-testid': 'availability-cta-btn'}, href=True)
    #             a_link = a['href']
    #         except:
    #             a_link = np.nan
        
    #         # Extract the hotel price
    #         try:
    #             # price_element = hotel.find('div', {'class': 'e84eb96b1f a661120d62'})
    #             price_element = hotel.find('span', {'data-testid': 'price-and-discounted-price'})
    #             price = price_element.text.split('£')[1].replace(',', '').strip()
    #         except:
    #             price = np.nan
            
    #         # Extract the hotel rating
    #         try:
    #             rating_element = hotel.find('div', {'class': 'a3b8729ab1 d86cee9b25'})
    #             rating = rating_element.text.strip()
    #         except:
    #             rating = np.nan
                
    #         # Extract number of reviews
    #         try:
    #             review_element = hotel.find('div', {'class': 'abf093bdfe f45d8e4c32 d935416c47'})
    #             review = review_element.text.split(' ')[0].replace(',', '').strip()
    #         except:
    #             review = np.nan
            
    #         # Append hotes_data with info about hotel
    #         hotels_data.append({
    #             'name': name,
    #             'location': location,
    #             'checkin date': checkin,
    #             'checkout date': checkout,
    #             'link': a_link,
    #             'price (£)': price,
    #             'rating': rating,
    #             'reviews': review
    #         })
        
        
    # hotels = pd.DataFrame(hotels_data)
    
    # # Convert numeric columns to float
    # hotels['price (£)'] = hotels['price (£)'].astype(float)
    # hotels['rating'] = hotels['rating'].astype(float)
    # hotels['reviews'] = hotels['reviews'].astype(float)
    
    # # Scale columns
    # hotels['price_scaled'] = hotels['price (£)'].apply(lambda x: 1-((x - hotels['price (£)'].min())/(hotels['price (£)'].max() - hotels['price (£)'].min())))
    # hotels['rating_scaled'] = hotels['rating'].apply(lambda x: x/hotels['rating'].max())
    
    # # Build score
    # hotels['score'] = 100*(hotels['price_scaled']*hotels['rating_scaled'])
    
    # # Drop scaled columns
    # hotels.drop('price_scaled', axis=1, inplace=True)
    # hotels.drop('rating_scaled', axis=1, inplace=True)
    
    # # Filter final dataframe
    # hotels = hotels.loc[hotels['reviews'] >= min_reviews]
    # hotels = hotels.loc[hotels['rating'] >= min_rating]
    # hotels = hotels.sort_values(by='score', ascending=False)
    
    return hotels
    
    
url = 'https://www.jet2holidays.com/beach/canary-islands/tenerife?airport=3&date=03-06-2024&duration=10&occupancy=r3c&sortorder=5&page=1&boardbasis=5'
best_hotels = best_value_hotels(url, 200, 8.5)