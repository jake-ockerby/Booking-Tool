# Code Author: Jake Ockerby

import asyncio
import nest_asyncio
import aiohttp
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from scipy import stats
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from urllib.parse import urlparse, urlencode, parse_qs, quote
from datetime import date, datetime, timedelta
import time
import re
import json
import random
from fuzzywuzzy import fuzz, process

nest_asyncio.apply()  # Allows nested async loops (for Jupyter)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}
# HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36',
#        'Accept-Language': 'en-US, en;q=0.5'
#       }
API_KEY = "1ecc066a30605371c68cb8f985a830c4"
# API_URL = "https://async.scraperapi.com/jobs"
# proxies = {
#   "https": "scraperapi.country_code=uk:1ecc066a30605371c68cb8f985a830c4@proxy-server.scraperapi.com:8001"
# }
semaphore = asyncio.Semaphore(5)

class Booker:
    def __init__(self, location, from_, to_, adults, children, rooms, sort, holiday_length, airport_from=None,
                 airport_to=None, review_score=6, mealplan="Not Arsed", twin_beds="Not Arsed", stars=0,
                 distance="Not Arsed", price_range=[0, 10000], clean_airport_names=True):

        self.location = location
        
        if isinstance(from_, date):
            self.from_ = from_.strftime("%Y-%m-%d")
        else:
            self.from_ = from_
            
        if isinstance(to_, date):
            self.to_ = to_.strftime("%Y-%m-%d")
        else:
            self.to_ = to_

        self.adults = adults
        self.children = children
        self.rooms = rooms
        self.sort = sort
        self.holiday_length = holiday_length
        self.airport_from = airport_from
        self.airport_to = airport_to
        self.review_score = review_score * 10
        self.mealplan = mealplan
        self.twin_beds = twin_beds
        self.stars = stars
        self.distance = distance
        self.price_min = price_range[0]
        self.price_max = price_range[1]
        self.clean_airport_names = clean_airport_names
        self.batch_size = 20
      
    # https://www.booking.com/searchresults.en-gb.html?ss=Antalya&checkin=2025-06-02&checkout=2025-06-03&group_adults=2&group_children=0&no_rooms=1&order=price&nflt=ht_id%3D204%3Breview_score%3D60%3BGBP-0-10000-1
    def build_scraperapi_url(self, target_url, country_code="uk"):
        return f"http://api.scraperapi.com?api_key={API_KEY}&url={quote(target_url)}&premium=true&keep_headers=true&country_code={country_code}"

    # Asynchronous fetch
    async def fetch(self, session, url):
        scraperapi_url = self.build_scraperapi_url(url)
        async with semaphore:
            try:
                async with session.get(scraperapi_url, timeout=60) as response:
                    return await response.text()
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return None
    

    # Builds the booking.com URL
    async def build_url(self):
        # Build additional URL settings based on user input
        if self.mealplan != "Not Arsed":
            mealplan_dict = {'Breakfast': 1, 'Breakfast & Dinner': 9, 'All-Inclusive': 4}
            mealplan_str = f';mealplan={mealplan_dict[self.mealplan]}'
        else:
            mealplan_str = ''
    
        if self.twin_beds != "Not Arsed":
            twin_dict = {'Twin Beds': 2, 'Double Bed': 3}
            twin_str = f';tdb={twin_dict[self.twin_beds]}'
        else:
            twin_str = ''
    
        if self.stars != 0:
            stars_str = f';class={self.stars}'
        else:
            stars_str = ''
    
        if self.distance != "Not Arsed":
            distance_dict = {'Half-Mile': 805, '1 Mile': 1610, '2 Miles': 3220}
            distance_str = f';distance={distance_dict[self.distance]}'
        else:
            distance_str = ''
            
        pricerange_str = f';GBP-{self.price_min}-{self.price_max}-1'
        
        # Convert checkin string to datetime
        checkin_date = datetime.strptime(self.from_, "%Y-%m-%d")
        
        # Get initial checkout date
        checkout_date = checkin_date + timedelta(days=self.holiday_length)
        
        # Get datetime for end of window
        end_date = datetime.strptime(self.to_, "%Y-%m-%d")
        
        # Calculate window range
        window = (end_date - checkin_date).days
        range_ = window + 1 - self.holiday_length

        # Create order mapping - two options for price & rating to gather more search results
        order_map = {'Price': ['price'], 'Rating': ['bayesian_review_score'],
                     'Price & Rating': ['price', 'bayesian_review_score']}
    
        urls = []
        dates = []

        # For each date in the range, build a specific URL and add to list
        for map_ in range(len(order_map[self.sort])):
            for i in range(range_):
                # Add a day per iteration to checkin and checkout
                checkin_new_date = checkin_date + timedelta(days=i)
                checkout_new_date = checkout_date + timedelta(days=i)
                
                # Convert back to string
                checkin_new = checkin_new_date.strftime("%Y-%m-%d")
                checkout_new = checkout_new_date.strftime("%Y-%m-%d")
    
                # Create url
                base_url = "https://www.booking.com/searchresults.en-gb.html"
                query = {
                    "ss": self.location,
                    "checkin": checkin_new,
                    "checkout": checkout_new,
                    "group_adults": self.adults,
                    "group_children": self.children,
                    "no_rooms": self.rooms,
                    "order": order_map[self.sort][map_],
                    "nflt": f"ht_id=204;review_score={self.review_score}" + mealplan_str + twin_str + stars_str + distance_str + pricerange_str
                }
                url = f"{base_url}?{urlencode(query)}"
                print(url)

                # Append each URL and set of dates to lists
                urls.append(url)
                dates.append([checkin_new, checkout_new])

        # Return all URLs, which are unique for each set of dates
        return urls, dates

    # Extracts the text from each hotel card displayed on the webpage
    async def extract_hotels_from_page(self, html, date):
        # Store information gathered in a dictionary
        hotels_data = {'name': [], 'location': [], 'date_from': [], 'date_to': [],
                       'hotel_price': [], 'rating': [], 'reviews': [], 'hotel_link': []}

        # Using BeautifulSoup to extract all hotel cards
        page = BeautifulSoup(html, 'lxml') 
        print(page.text)
        hotels = page.findAll('div', {'data-testid': 'property-card'})
        links = page.findAll('a', {'data-testid': 'availability-cta-btn'}, href=True)
        locations = page.findAll('span', {'data-testid': 'address'})
        hotels = [h.text.strip() for h in hotels]
    
        # Loop over the hotel cards and extract information
        for hotel, a, loc in zip(hotels, links, locations):
            try:
                name = hotel.split('Opens in new window')[0].strip()
                link = a['href']
                location = ', '.join(loc)
                rating = float(hotel.split('Scored')[1][:4].strip())
                review = int(re.sub(r'[^0-9]', '', hotel.split('reviews')[0][-8:]))
                try:
                    price = int(re.sub(r'[^0-9]', '', hotel.split('Price')[1][:8]))
                except:
                    price = int(re.sub(r'[^0-9]', '', hotel.split('Current price')[1][:8]))

                # Add to dictionary
                hotels_data['name'].append(name)
                hotels_data['location'].append(location)
                hotels_data['date_from'].append(date[0])
                hotels_data['date_to'].append(date[1])
                hotels_data['hotel_link'].append(link)
                hotels_data['hotel_price'].append(price)
                hotels_data['rating'].append(rating)
                hotels_data['reviews'].append(review)
            except:
                continue

        # Convert dictionary to dataframe and return
        hotels_df = pd.DataFrame(hotels_data)
        
        return hotels_df
    
    
    async def extract_hotels_from_page_playwright(self, url, date):
        scraperapi_url = self.build_scraperapi_url(url)
        hotels_data = {'name': [], 'location': [], 'date_from': [], 'date_to': [],
                       'hotel_price': [], 'rating': [], 'reviews': [], 'hotel_link': []}
    
        async with async_playwright() as p:
            await asyncio.sleep(random.uniform(1, 3))
    
            browser_context = await p.chromium.launch_persistent_context(
                user_data_dir="./tmp-user-data",
                headless=True,
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
    
            page = await browser_context.new_page()
    
            await page.set_extra_http_headers({
                "Accept-Language": "en-GB,en;q=0.9",
            })
    
            # Optional: Use stealth-like evasion
            await page.evaluate("""() => {
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', { get: () => ['en-GB', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            }""")
    
            # try:
            await page.goto(scraperapi_url, wait_until="networkidle")
            print(await page.inner_text('body'))
            # except Exception as e:
            #     print(f"Failed to load page: {e}")
            #     await browser_context.close()
            #     return pd.DataFrame(hotels_data)
    
            hotel_cards = await page.locator('[data-testid="property-card"]').all()
    
            for card in hotel_cards:
                try:
                    name = await card.locator('[data-testid="title"]').inner_text()
                    location = await card.locator('[data-testid="address"]').inner_text()
                    link = await card.locator('[data-testid="availability-cta-btn"]').get_attribute('href')
    
                    try:
                        rating = await card.locator('[data-testid="review-score"] >> text=/[0-9]+\\.?[0-9]*/').inner_text()
                        rating = float(rating.strip())
                    except:
                        rating = 9999
    
                    try:
                        review_text = await card.locator('[data-testid="review-score"] span').all_inner_texts()
                        review = int(re.sub(r'[^0-9]', '', review_text[-1])) if review_text else None
                    except:
                        review = 9999
    
                    try:
                        price_text = await card.locator('[data-testid="price-and-discounted-price"]').inner_text()
                        price = int(re.sub(r'[^0-9]', '', price_text))
                    except:
                        price = 9999
    
                    hotels_data['name'].append(name)
                    hotels_data['location'].append(location)
                    hotels_data['date_from'].append(date[0])
                    hotels_data['date_to'].append(date[1])
                    hotels_data['hotel_link'].append(link)
                    hotels_data['hotel_price'].append(price)
                    hotels_data['rating'].append(rating)
                    hotels_data['reviews'].append(review)
                except Exception as e:
                    print(f"Error extracting a hotel card: {e}")
                    continue
    
            await browser_context.close()
            return pd.DataFrame(hotels_data)


    # Builds Kayak URL for flights
    async def build_kayak_flight_url(self):
        # Read IATA codes for all commercial airports - needed for Kayak URLs
        iata_table = pd.read_csv('airports.csv')
        iata_table = iata_table.rename(columns={'Airport name': 'name', 'IATA': 'code'})
        iata_table = iata_table[['name', 'code']].copy()

        # Read IATA city codes for cities with more than one commercial airport
        city_codes = pd.read_csv('citycodes.csv')
        city_codes = city_codes[['name', 'code']].copy()
        city_codes['name'] = city_codes['name'].apply(lambda x: x.split(' Metropolitan Area')[0])

        # Combine the two dataframes
        code_table = pd.concat([iata_table, city_codes])

        # Clean user input using fuzzywuzzy package and match cleaned names to their corresponding IATA codes
        if self.clean_airport_names == True:
            airport_from_clean = process.extractOne(self.airport_from, code_table['name'])[0]
            airport_to_clean = process.extractOne(self.airport_to, code_table['name'])[0]
        else:
            airport_from_clean = self.airport_from
            airport_to_clean = self.airport_to
            
        from_code = code_table['code'][code_table['name'] == airport_from_clean].values[0]
        to_code = code_table['code'][code_table['name'] == airport_to_clean].values[0]

        # Build additional strings for number of adults and children
        adults_str = f'{self.adults}adults/'
        
        if self.children == 0:
            children_str = ''
        else:
            add_list = ['11' for i in range(self.children)]
            add_str = '-'.join(add_list)
            children_str = 'children-' + add_str
    
        sort_str = '?sort=bestflight_a'
    
        # Convert checkin string to datetime
        depart_date = datetime.strptime(self.from_, "%Y-%m-%d") + timedelta(days=-1)
    
        # Get datetime for end of window
        end_date = datetime.strptime(self.to_, "%Y-%m-%d") + timedelta(days=1)
        
        # Calculate window range
        window = (end_date - depart_date).days

        # Flight prices are read from a calander layout, which shows ~ 1 month of data
        # If daterange the user has entered is longer than 1 month, we need to build mulitple URLs
        holiday_length = self.holiday_length
        num_searches = int((window - holiday_length)/32) + 1
    
        urls = []
        dates = []

        # Cycle through dates and build unique URLs
        for n in range(num_searches):
            # Add ~ 1 month each iteration, and convert to string type
            depart_new_dt = depart_date + timedelta(days=n*32)
            month_later_dt = depart_new_dt + timedelta(days=32)
            depart_new = depart_new_dt.strftime("%Y-%m-%d")
            month_later = month_later_dt.strftime("%Y-%m-%d")
        
            base_url = f'https://www.kayak.co.uk/flights/{from_code}-{to_code}/{depart_new}/{month_later}-flexible-calendar-{self.holiday_length}/'
            url = base_url + adults_str + children_str + sort_str

            # Append URLs and dateranges to lists
            urls.append(url)
            dates.append([depart_new, month_later])

        # Return URLs and dateranges, along with other important info
        return urls, dates, airport_from_clean, airport_to_clean, end_date
    

    # Extracts approximate flight prices from each calendar URL
    async def get_kayak_flight_prices(self, url, daterange, end_date):
        async with async_playwright() as p:
            # Load page, extract content, and close page
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
    
            page = await context.new_page()
            await stealth_async(page)
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            dates_text = await page.locator('[class="nSfL-date"]').all_inner_texts()
            prices_text = await page.locator('[class="nSfL-price"]').all_inner_texts()
            await browser.close()

            # Get actual flight search page for user to navigate to, to be added to final result dataframe
            flight_page_url = url.replace(f'-flexible-calendar-{self.holiday_length}', '')

            # We are only interested in the start of our dateranges, not where the webpage dates start
            depart_date = datetime.strptime(daterange[0], "%Y-%m-%d")
            day_start = str(int(daterange[0].split('-')[-1]))
            start_from_index = dates_text.index(day_start)
            dates_text = dates_text[start_from_index:]
            prices_text = prices_text[start_from_index:]
            
            # Store information gathered in a dictionary
            flights_data = {'date_from': [], 'date_to': [], 'approx_flight_price': [], 'flight_link': []}
            for i in range(len(dates_text)):
                # Add one day per iteration to the depart and return dates
                depart_update_dt = depart_date + timedelta(days=i)
                return_update_dt = depart_date + timedelta(days=i+self.holiday_length)
                depart_update = depart_update_dt.strftime("%Y-%m-%d")
                return_update = return_update_dt.strftime("%Y-%m-%d")
                date_url = flight_page_url.replace(daterange[0], depart_update)
                date_url = date_url.replace(daterange[1], return_update)

                # Get the price for each date, if missing then fill with dummy integer value
                if prices_text[i] != '':
                    price = int(re.sub(r'[^0-9]', '', prices_text[i]))
                else:
                    price = 9999

                # Add all information to the dictionary
                flights_data['date_from'].append(depart_update)
                flights_data['date_to'].append(return_update)
                flights_data['approx_flight_price'].append(price)
                flights_data['flight_link'].append(date_url)

            # Convert the dictionary to a dataframe
            flights_df = pd.DataFrame(flights_data)

            # When the end of our daterange is earlier than the end of the webpage calendar,
            # limit the dataframe to exclude anything beyond the end of our daterange
            if end_date < return_update_dt:
                end = end_date.strftime("%Y-%m-%d")
                last_date = list(flights_df.index[flights_df['date_to'] == end])[0]
                flights_df = flights_df.iloc[:last_date + 1].copy()
                
            return flights_df

    # Gathers all flight information and returns one large result dataframe
    async def kayak_flights_search(self):
        # Call the function that builds the flight URLs and extract the prices
        urls, dates, airport_from_clean, airport_to_clean, end_date = await self.build_kayak_flight_url()
        # Sometimes fails to load webpage on first try
        try:
            tasks = [self.get_kayak_flight_prices(url, daterange, end_date) for url, daterange in zip(urls, dates)]
            flights_list = await asyncio.gather(*tasks)
    
            # Concatenate into one large dataframe
            all_flight_info = pd.concat(flights_list)
            all_flight_info['airport_from'] = airport_from_clean
            all_flight_info['airport_to'] = airport_to_clean
            all_flight_info = all_flight_info[['airport_from', 'airport_to', 'date_from', 'date_to', 'approx_flight_price', 'flight_link']].copy()
    
            # Edit the prices so that it reflects the total price for all passengers
            all_flight_info['approx_flight_price'] = all_flight_info['approx_flight_price']*(self.adults + self.children)
            all_flight_info = all_flight_info.sort_values(by='approx_flight_price', ascending=True)
    
            # Convert the dummy integer value to 'Missing'
            all_flight_info = all_flight_info.replace(9999*(self.adults + self.children), 'Missing')
        except:
            print('Failed to gather flight information - please try again.')
            all_flight_info = pd.DataFrame()

        # Return the results
        return all_flight_info
    
    
    # Gathers all hotel information (and flight informtion if specified) and returns one large result dataframe
    async def booking_search(self):
        batch_size = self.batch_size
        hotels_list = []
    
        # Build URLs and dates
        urls, dates = await self.build_url()
    
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i+batch_size]
            batch_dates = dates[i:i+batch_size]
    
            tasks = [self.extract_hotels_from_page_playwright(url, date)
                     for url, date in zip(batch_urls, batch_dates)]
            batch_results = await asyncio.gather(*tasks)
            hotels_list.extend(batch_results)
    
        # Combine all into one dataframe
        all_best_hotels = pd.concat(hotels_list)
        
        # batch_size = self.batch_size
        # hotels_list = []
        
        # # Using aiohttp wih a session vastly improves execution time
        # connector = aiohttp.TCPConnector(limit=90)
        # async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        #     # Call the function that builds the hotel webpage URLs and extract information
        #     urls, dates = await self.build_url()
            
        #     for i in range(0, len(urls), batch_size):
        #         batch_urls = urls[i:i+batch_size]
        #         batch_dates = dates[i:i+batch_size]
                
        #         tasks = [self.fetch(session, url) for url in batch_urls]
        #         html_pages = await asyncio.gather(*tasks)
        
        #         tasks = [self.extract_hotels_from_page(html, date) for html, date in zip(html_pages, batch_dates)]
        #         batch_results = await asyncio.gather(*tasks)
        #         hotels_list.extend(batch_results)
    
        # Concatenate into one large dataframe
        all_best_hotels = pd.concat(hotels_list)
        
        # Drop duplicates
        all_best_hotels = all_best_hotels.drop_duplicates(subset=['name', 'rating', 'reviews',
                                                          'date_from', 'date_to'])

        # If user inputs airport information, execute the flights search and calculate a total price
        if (self.airport_from != None) & (self.airport_to != None):
            flights_df = asyncio.run(self.kayak_flights_search())
            if len(flights_df) > 0:    
                all_best_hotels = all_best_hotels.merge(flights_df, on=['date_from', 'date_to'], how='left')
                # Use dummy integer value in place of 'Missing' - needed for further calculations
                all_best_hotels = all_best_hotels.replace('Missing', 99999)
                all_best_hotels['approx_flight_price'] = all_best_hotels['approx_flight_price'].astype(int)
                all_best_hotels['total_price'] = all_best_hotels['hotel_price'] + all_best_hotels['approx_flight_price']
            else:
                all_best_hotels = all_best_hotels.rename(columns={'date_from': 'checkin_date', 'date_to': 'checkout_date',
                                                              'hotel_price': 'total_price'})
        else:
            all_best_hotels = all_best_hotels.rename(columns={'date_from': 'checkin_date', 'date_to': 'checkout_date',
                                                              'hotel_price': 'total_price'})
    
        # Scale columns to be within a range of 0 and 1 - price is represented as the percentile value over all prices
        all_best_hotels['price_percentile'] = stats.percentileofscore(all_best_hotels['total_price'], all_best_hotels['total_price'])*0.01
        all_best_hotels['rating_scaled'] = all_best_hotels['rating']*0.1
        
        # Build VM (Value for Money) score
        all_best_hotels['vm_score_unrounded'] = 100*(((1-all_best_hotels['price_percentile'])+all_best_hotels['rating_scaled'])/2)
        
        # Sort final results based on user input
        if self.sort == 'Price & Rating':
            all_best_hotels = all_best_hotels.sort_values(by='vm_score_unrounded', ascending=False)
            
        elif self.sort == 'Price':
            all_best_hotels = all_best_hotels.sort_values(by='total_price', ascending=True)
        
        else:
            all_best_hotels = all_best_hotels.sort_values(by='rating', ascending=False)
    
        # Apply rounding to VM score
        all_best_hotels['vm_score'] = round(all_best_hotels['vm_score_unrounded'])
        all_best_hotels['vm_score'] = all_best_hotels['vm_score'].astype(int)
    
        # Drop scaled columns
        all_best_hotels.drop('price_percentile', axis=1, inplace=True)
        all_best_hotels.drop('rating_scaled', axis=1, inplace=True)
        all_best_hotels.drop('vm_score_unrounded', axis=1, inplace=True)

        # If user inputs airport information, revert the dummy integer values implemented earlier,
        # and rename and return appropriate columns
        if (self.airport_from != None) & (self.airport_to != None):
            if len(flights_df) > 0:
                all_best_hotels['total_price'] = np.where(all_best_hotels['approx_flight_price'] == 99999,
                                                          'Missing', all_best_hotels['total_price'])
                all_best_hotels['approx_flight_price'] = np.where(all_best_hotels['approx_flight_price'] == 99999,
                                                           'Missing', all_best_hotels['approx_flight_price'])
                
                all_best_hotels = all_best_hotels.rename(columns={'date_from': 'depart', 'date_to': 'return'})
                all_best_hotels = all_best_hotels[['name', 'location', 'airport_from', 'airport_to', 'depart', 'return',
                                                   'rating', 'reviews', 'hotel_price', 'approx_flight_price', 'total_price',
                                                   'vm_score', 'hotel_link', 'flight_link']].copy()

        # Return final results
        return all_best_hotels
    
    