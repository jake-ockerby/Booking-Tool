#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Dec  9 16:59:53 2023

@author: jake_ockerby
"""

import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta


def best_value_hotels(url, min_reviews, min_rating):
    
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Extract query parameters
    query_params = parse_qs(parsed_url.query)
    
    # Extract check-in and check-out dates
    checkin = query_params.get('checkin', [''])[0]
    checkout = query_params.get('checkout', [''])[0]
    
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
        'Accept-Language': 'en-US, en;q=0.5'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find number of properties
    properties_element = soup.find('h1', {'class': 'f6431b446c d5f78961c3'})
    properties = int(properties_element.text.split(':')[1].split('properties')[0].strip().replace(',', ''))
    
    # Scrape HTML content of all pages
    soup_list = [soup]
    for i in range(int(properties/25)):
        url_new = url + '&offset={}'.format((i+1)*25)
        response = requests.get(url_new, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        soup_list.append(soup)
        
    
    hotels_data = []
    for soup in soup_list:
        # Find all the hotel elements in the HTML document
        hotels = soup.findAll('div', {'data-testid': 'property-card'})
        
        # Loop over the hotel elements and extract the desired data
        for hotel in hotels:
            # Extract the hotel name
            try:
                name_element = hotel.find('div', {'data-testid': 'title'})
                name = name_element.text.strip()
            except:
                name = np.nan
        
            # Extract the hotel location
            try:
                location_element = hotel.find('span', {'data-testid': 'address'})
                location = location_element.text.strip()
            except:
                location = np.nan
                
            # Extract the web link
            try:
                a = hotel.find('a', {'data-testid': 'availability-cta-btn'}, href=True)
                a_link = a['href']
            except:
                a_link = np.nan
        
            # Extract the hotel price
            try:
                # price_element = hotel.find('div', {'class': 'e84eb96b1f a661120d62'})
                price_element = hotel.find('span', {'data-testid': 'price-and-discounted-price'})
                price = price_element.text.split('£')[1].replace(',', '').strip()
            except:
                price = np.nan
            
            # Extract the hotel rating
            try:
                rating_element = hotel.find('div', {'class': 'a3b8729ab1 d86cee9b25'})
                rating = rating_element.text.strip()
                rating = rating.split(' ')[1]
            except:
                rating = np.nan
                
            # Extract number of reviews
            try:
                review_element = hotel.find('div', {'class': 'abf093bdfe f45d8e4c32 d935416c47'})
                review = review_element.text.split(' ')[0].replace(',', '').strip()
            except:
                review = np.nan
            
            # Append hotes_data with info about hotel
            hotels_data.append({
                'name': name,
                'location': location,
                'checkin date': checkin,
                'checkout date': checkout,
                'link': a_link,
                'price (£)': price,
                'rating': rating,
                'reviews': review
            })
        
        
    hotels = pd.DataFrame(hotels_data)
    
    # Convert numeric columns to float
    hotels['price (£)'] = hotels['price (£)'].astype(float)
    hotels['rating'] = hotels['rating'].astype(float)
    hotels['reviews'] = hotels['reviews'].astype(float)
        
    
    # Scale columns
    hotels['price_scaled'] = hotels['price (£)'].apply(lambda x: 1-((x - hotels['price (£)'].min())/(hotels['price (£)'].max() - hotels['price (£)'].min())))
    hotels['rating_scaled'] = hotels['rating'].apply(lambda x: x/hotels['rating'].max())
    
    # Build score
    hotels['score'] = 100*(hotels['price_scaled']*hotels['rating_scaled'])
    
    # Drop scaled columns
    hotels.drop('price_scaled', axis=1, inplace=True)
    hotels.drop('rating_scaled', axis=1, inplace=True)
    
    # Filter final dataframe
    hotels = hotels.loc[hotels['reviews'] >= min_reviews]
    hotels = hotels.loc[hotels['rating'] >= min_rating]
    hotels = hotels.sort_values(by='score', ascending=False)
    
    # Drop duplicates
    hotels = hotels.drop_duplicates(subset=['name', 'location',
                                            'checkin date', 'checkout date'])
    
    return hotels


def best_hotels_and_dates(url, min_reviews, min_rating, checkin_new, holiday_length, range_):
    
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Extract query parameters
    query_params = parse_qs(parsed_url.query)
    
    # Extract check-in and check-out dates
    checkin = query_params.get('checkin', [''])[0]
    checkout = query_params.get('checkout', [''])[0]
    
    
    # Convert string to datetime
    checkin_date = datetime.strptime(checkin_new, "%Y-%m-%d")
    
    # Get checkout date
    checkout_date = checkin_date + timedelta(days=holiday_length)
    
    hotels_list = []
    for i in range(range_+1):
        print(f'Progress: {i}/{range_}')
        checkin_new_date = checkin_date + timedelta(days=i)
        checkout_new_date = checkout_date + timedelta(days=i)
        
        # Convert back to string
        checkin_new = checkin_new_date.strftime("%Y-%m-%d")
        checkout_new = checkout_new_date.strftime("%Y-%m-%d")
    
        # Create new url
        url_new = url.replace("checkin={0}&checkout={1}".format(checkin, checkout),
                              "checkin={0}&checkout={1}".format(checkin_new, checkout_new)
                              )
        
        best_hotels = best_value_hotels(url_new, min_reviews, min_rating)
        
        hotels_list.append(best_hotels)
        
    all_best_hotels = pd.concat(hotels_list)
    
    # Scale columns
    all_best_hotels['price_scaled'] = all_best_hotels['price (£)'].apply(lambda x: 1-((x - all_best_hotels['price (£)'].min())/(all_best_hotels['price (£)'].max() - all_best_hotels['price (£)'].min())))
    all_best_hotels['rating_scaled'] = all_best_hotels['rating'].apply(lambda x: x/all_best_hotels['rating'].max())
    
    # Build score
    all_best_hotels['score'] = 100*(all_best_hotels['price_scaled']*all_best_hotels['rating_scaled'])
    
    # Drop scaled columns
    all_best_hotels.drop('price_scaled', axis=1, inplace=True)
    all_best_hotels.drop('rating_scaled', axis=1, inplace=True)
    
    # Filter final dataframe
    all_best_hotels = all_best_hotels.sort_values(by='score', ascending=False)
    
    # Drop duplicates
    all_best_hotels = all_best_hotels.drop_duplicates(subset=['name', 'location',
                                            'checkin date', 'checkout date'])
    
    return all_best_hotels



url = 'https://www.booking.com/searchresults.en-gb.html?label=gen173nr-1FCAEoggI46AdIM1gEaFCIAQGYAQm4ARnIAQzYAQHoAQH4AQ2IAgGoAgO4AtKAk8AGwAIB0gIkMDdkMTgwNTQtNDNjMS00YjBmLWE3Y2ItMjVjZTFmOTkyMzBh2AIG4AIB&sid=8bd3ce886640970a93855d9ffdfd4543&aid=304142&ss=Amsterdam+City+Centre%2C+Amsterdam%2C+Noord-Holland%2C+Netherlands&map=1&efdco=1&lang=en-gb&src=index&dest_id=145&dest_type=district&ac_position=1&ac_click_type=b&ac_langcode=en&ac_suggestion_list_length=5&search_selected=true&search_pageview_id=42a34466b7e00601&checkin=2025-05-15&checkout=2025-05-19&group_adults=2&no_rooms=1&group_children=0&nflt=mealplan%3D1%3Breview_score%3D70%3Bht_id%3D204'
# best_hotels = best_value_hotels(url, 100, 8)
best_hotels = best_hotels_and_dates(url, 100, 7, '2025-05-15', 4, 46)
best_hotels.to_excel('amsterdam_hotels.xlsx')