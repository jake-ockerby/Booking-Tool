# Code Author: Jake Ockerby

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from booking_tools import Booker
import io
import asyncio
import nest_asyncio
from concurrent.futures import ThreadPoolExecutor
today = date.today()
nest_asyncio.apply()

# Cache to prevent computation on every rerun
@st.cache_data
def convert_df(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    
    df = df.copy()
    if "hotel_link" in df.columns:
        df["hotel_link"] = df["hotel_link"].astype(str)
    if "flight_link" in df.columns:
        df["flight_link"] = df["flight_link"].astype(str)
    
    df.to_excel(writer, index=False)
    writer.close()
    data_bytes = output.getvalue()
    return data_bytes

# Needed to use async properly in streamlit
def run_async_in_thread(async_func, *args, **kwargs):
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(async_func(*args, **kwargs))

    with ThreadPoolExecutor() as executor:
        return executor.submit(_run).result()


# Read airport names
iata_table = pd.read_csv('airports.csv')
iata_table = iata_table.rename(columns={'Airport name': 'name', 'IATA': 'code'})
iata_table = iata_table[['name']].copy()

city_codes = pd.read_csv('citycodes.csv')
city_codes = city_codes[['name']].copy()
city_codes['name'] = city_codes['name'].apply(lambda x: x.split(' Metropolitan Area')[0])

# Combine the two dataframes
code_table = pd.concat([iata_table, city_codes])
airports_tuple = tuple(code_table['name'])


st.set_page_config(page_title="Hotels & Flights Search Tool", layout="centered")

st.title("Hotels & Flights Search Tool")
st.markdown("Use this tool to search for the best hotels and flights within a given period.")

# ------------ Instructions -------------
with st.expander("Instructions"):
    st.markdown("## How To Use This Tool")
    
    st.markdown("## IMPORTANT")
    st.write("""
    - This tool is not meant to be used as a simple search for hotels and flights between two
    exact dates, but rather as a search for the best hotels and flights in a given window.
    
    - **Example**: You are travelling to Madrid for a week but don't know the best dates to go over the summer.
    In the Travel Window section, you enter from 1st July to 31st August and hit search. The tool
    will then search from 1st - 8th July, 2nd - 9th July, 3rd - 10th July, ... all the way up until the 31st
    August. The long list of results can then be downloaded to excel.
    
    - Searches may take a few minutes and will take longer for larger windows — so please be patient.
    - Some filters (like review scores or stars) may limit available results.
    - The flight search is a bit temperamental and sometimes fails to gather flight data. Trying again should
    fix this.
    - Selecting Price & Rating in the sort options will result in a deeper, longer search, and will sort using
    the VM (Value for Money) Score. Here, the best possible score is 100 and the worst possible score is 0.
    """)
    
    st.markdown("### 1. Enter a Hotel Location or Airport Information")
    st.write("""
    - **Hotel Location**: Type the name of the city or area where you want to find a hotel.
    - **From Airport**: Select your departure airport.
    - **To Airport**: Select your destination airport.
    
    **Note**: Only return flights are searched.""")

    st.markdown("### 2. Choose Your Travel Window")
    st.write("""
    - Select your **start date** & **end date** for the search window — this window must span 2 days at minimum,
    and 90 days at maximum.
    """)

    st.markdown("### 3. Specify Group and Accommodation")
    st.write("""
    - Number of **adults** (1–8)
    - Number of **children** (0–8)
    - Number of **rooms** (1–8)
    """)

    st.markdown("### 4. Set Holiday Duration")
    st.write("""
    - Use the slider to pick how many days you want the holiday to last (up to 30 days).
    """)

    st.markdown("### 5. (Optional) Add Filters")
    st.write("""
    Expand the 'Additional Filters' section to refine your search:
    - **Price Range**: Minimum and maximum nightly hotel price
    - **Sort Results**: By Price, Rating, or Price & Rating
    - **Minimum Review Rating**: (6–9)
    - **Star Rating**: (0–5, 0 is set by default and disables this filter)
    - **Meal Options**: e.g. Breakfast or All-Inclusive
    - **Bed Type**: e.g. Twin or Double
    - **Distance from Centre**: Within 0.5 to 2 miles
    """)

    st.markdown("### 6. Search")
    st.write("""
    - Click the **Search** button.
    - The app will either:
        - Search **hotels & flights** if hotel & flight locations are entered.
        - Search **hotels only** if only a hotel location is entered.
        - Search **flights only** if both departure and arrival airports are entered,
        but no hotel location.
        - Show a **warning** if neither is provided.
    """)

    st.markdown("### 7. View and Download Results")
    st.write("""
    - After the search completes, you’ll see a table of results with links to:
        - **Hotel pages** (Booking.com)
        - **Flight bookings** (Kayak)
    - Click **Download Results** to save the data as an Excel spreadsheet.
    """)
    
    st.markdown("### Feedback")
    st.write(""" I would be grateful for any feedback on this tool, and would like to be made
             aware of any issues you encounter. Please contact me via email at jakeockerby@gmail.com""")

st.divider()

# ----------- Location & Airports ------------
st.markdown("### Location & Airports")
col1, col2, col3 = st.columns([2, 1.5, 1.5])
with col1:
    location = st.text_input("Hotel Location:", None)
with col2:
    airport_from = st.selectbox("From Airport:", airports_tuple, index=None)
with col3:
    airport_to = st.selectbox("To Airport:", airports_tuple, index=None)

st.divider()

# ----------- Date Selection ------------
st.markdown("### Travel Window")
col4, col5 = st.columns(2)
with col4:
    from_ = st.date_input("From:", today, min_value=today, max_value=today + timedelta(days=540))
with col5:
    to_ = st.date_input("To:", from_ + timedelta(days=2),
                        min_value=from_ + timedelta(days=2), max_value=from_ + timedelta(days=90))

# ----------- People & Rooms ------------
st.markdown("### People & Rooms")
col6, col7, col8 = st.columns(3)
with col6:
    adults = st.number_input("Adults:", min_value=1, max_value=8)
with col7:
    children = st.number_input("Children:", min_value=0, max_value=8)
with col8:
    rooms = st.number_input("Rooms:", min_value=1, max_value=8)

# ----------- Holiday Length ------------
st.markdown("### Holiday Duration")
holiday_length = st.slider("Holiday Duration (Days):", 1, min((to_ - from_).days, 30))

# ----------- Advanced Filters ------------
st.markdown("### Additional Filters")
with st.expander("Click to add filters"):
    st.markdown("#### Price Range (£ per night)")
    col9, col10 = st.columns(2)
    with col9:
        min_price = st.number_input("Min. Price:", min_value=0, max_value=9999)
    with col10:
        max_price = st.number_input("Max. Price:", value=10000, min_value=min_price, max_value=10000)

    st.markdown("#### Sort Options")
    sort = st.selectbox("Sort By:", ("Price", "Rating", "Price & Rating"))

    col11, col12 = st.columns(2)
    with col11:
        review_score = st.number_input("Min. Review Rating:", min_value=6, max_value=9)
    with col12:
        stars = st.number_input("Star Rating:", min_value=0, max_value=5)

    st.markdown("#### Meal & Bed Options")
    mealplan = st.selectbox("Meals Included:", ("Not Arsed", "Breakfast", "Breakfast & Dinner", "All-Inclusive"))
    twin_beds = st.selectbox("Beds:", ("Not Arsed", "Twin Beds", "Double Bed"))

    st.markdown("#### Distance From Centre")
    distance = st.selectbox("Distance:", ("Not Arsed", "Half-Mile", "1 Mile", "2 Miles"))

st.divider()

# ----------- Search Button ------------
if st.button("Search", type="primary"):
    # Pass variables to class
    booker = Booker(location, from_, to_, adults, children, rooms, sort, holiday_length,
                    airport_from, airport_to, review_score, mealplan, twin_beds, stars,
                    distance, price_range=[min_price, max_price], clean_airport_names=False)
    
    # If hotel location is non-empty, run the full booking search
    if location:
        with st.spinner("Bear with me ...", show_time=True):
            result_df = run_async_in_thread(booker.booking_search)
        st.success("Search complete!")
        st.write(result_df)

    #     column_config = {
    #         "hotel_link": st.column_config.LinkColumn("hotel_link", display_text="Hotel Link"),
    #         "flight_link": st.column_config.LinkColumn("flight_link", display_text="Flight Link")
    #     }
    #     st.dataframe(result_df, column_config=column_config, hide_index=True)

    #     excel = convert_df(result_df)
    #     st.download_button("Download Results", data=excel, file_name="search_results.xlsx", type="primary")

    # # If both airport destinations are non-empty, run the flights search
    # elif airport_from and airport_to:
    #     with st.spinner("Bear with me ...", show_time=True):
    #         result_df = run_async_in_thread(booker.kayak_flights_search)
    #     if result_df.empty:
    #         st.error("Failed to gather flight information - please try again.")
    #     else:
    #         st.success("Flight search complete!")
    #         column_config = {
    #             "hotel_link": st.column_config.LinkColumn("hotel_link", display_text="Hotel Link"),
    #             "flight_link": st.column_config.LinkColumn("flight_link", display_text="Flight Link")
    #         }
    #         st.dataframe(result_df, column_config=column_config, hide_index=True)

    #         excel = convert_df(result_df)
    #         st.download_button("Download Results", data=excel, file_name="search_results.xlsx", type="primary")

    # # Else display a warning
    # else:
    #     st.warning("Please enter a hotel location or a valid pair of airports.")
            
