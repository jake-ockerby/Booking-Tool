# Code Author: Jake Ockerby

import streamlit as st
import pandas as pd
from scipy import stats
from datetime import date, timedelta
import sqlite3
import io
today = date.today()

# Cache to prevent computation on every rerun
@st.cache_data
def convert_df(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter",
                            engine_kwargs={'options': {'strings_to_urls': False}})
    
    df = df.copy()
    if "hotel_link" in df.columns:
        df["hotel_link"] = df["hotel_link"].astype(str)
    
    df.to_excel(writer, index=False)
    writer.close()
    data_bytes = output.getvalue()
    return data_bytes

cities = pd.read_csv('citynames.csv')
cities_tuple = tuple(cities['Full Name'])

st.set_page_config(page_title="Cheeky Booker", layout="centered")

st.title("Cheeky Booker")
st.markdown("Use this tool to search for the best hotels within a given period.")

# ------------ Instructions -------------
with st.expander("Instructions"):
    st.markdown("## How To Use This Tool")
    
    st.markdown("## IMPORTANT")
    st.write("""
    - This tool is not meant to be used as a simple search for hotels between two
    exact dates, but rather as a search for the best hotels in a given window.
    
    - **Example**: You are travelling to Madrid for a week but don't know the best dates to go over the summer.
    In the Travel Window section, you enter from 1st July to 31st August and hit search. The tool
    will then search from 1st - 8th July, 2nd - 9th July, 3rd - 10th July, ... all the way up until the 31st
    August. The long list of results can then be downloaded to excel.
    
    - Some filters (such as Price Range) may limit available results.
    - Price & Rating will sort using the VM (Value for Money) Score. Here, the best possible score is 100
      and the worst possible score is 0.
    """)
    
    st.markdown("### 1. Enter a Hotel Location")
    st.write("""
    **Hotel Location**: Type the name of the city where you want to find a hotel.
    - **Note**: There are 115 cities to select from across Europe (including Turkey).
    More cities may be included in future.
    """)

    st.markdown("### 2. Choose Your Travel Window")
    st.write("""
    - Select your **start date** & **end date** for the search window — this window must span 2 days at minimum,
      and 182 at maximum.
    """)


    st.markdown("### 3. Set Holiday Duration")
    st.write("""
    - Use the slider to pick how many days you want the holiday to last (up to 30 days).
    """)

    st.markdown("### 4. (Optional) Add Filters")
    st.write("""
    Expand the 'Additional Filters' section to refine your search:
    - **Price Range**: Minimum and maximum nightly hotel price
    - **Rating**: Choose hotels rated between 6 & 10
    - **Reviews**: Choose hotels that have over a certain number of reviews
    - **Sort Results**: By Price, Rating, or Price & Rating
    """)

    st.markdown("### 5. Search")
    st.write("""
    - Click the **Search** button.
    - The app will search for hotels over the selected window and holiday duration.
    - If no location is provided, a warning will be shown.
    """)

    st.markdown("### 6. View and Download Results")
    st.write("""
    - After the search completes, you’ll see a table of results with links to **hotel pages** (Booking.com)
    - Prices shown are per person per night, and are approximates only.
    - Click **Download Results** to save the data as an Excel spreadsheet.
    """)
    
    st.markdown("### Feedback")
    st.write(""" I would be grateful for any feedback on this tool, and would like to be made
             aware of any issues you encounter. Please contact me via email at jakeockerby@gmail.com""")

st.divider()

# ----------- Location & Airports ------------
st.markdown("### Location & Airports")
# location = st.text_input("Hotel Location:", None)
location = st.selectbox("Hotel Location:", cities_tuple, index=None)

st.divider()

# ----------- Date Selection ------------
st.markdown("### Travel Window")
col4, col5 = st.columns(2)
with col4:
    from_ = st.date_input("From:", today, min_value=today, max_value=today + timedelta(days=180))
with col5:
    to_ = st.date_input("To:", from_ + timedelta(days=2), min_value=from_ + timedelta(days=2),
                        max_value=today + timedelta(days=182))

# ----------- Holiday Length ------------
st.markdown("### Holiday Duration")
holiday_length = st.slider("Holiday Duration (Days):", 1, min((to_ - from_).days, 30))

# ----------- Advanced Filters ------------
st.markdown("### Additional Filters")
with st.expander("Click to add filters"):
    st.markdown("#### Price Range (£ per person per night)")
    col9, col10 = st.columns(2)
    with col9:
        min_price = st.number_input("Min. Price:", min_value=0, max_value=4999)
    with col10:
        max_price = st.number_input("Max. Price:", value=5000, min_value=min_price, max_value=5000)

    st.markdown("#### Rating")
    col11, col12 = st.columns(2)
    with col11:
        min_review_score = st.number_input("Min. Rating:", min_value=6, max_value=9.9)
    with col12:
        max_review_score = st.number_input("Max. Rating:", value=9.9, min_value=min_review_score, max_value=9.9)
        
    st.markdown("#### Reviews")
    min_reviews = st.number_input("Min. # of reviews:", min_value=0, max_value=100000)

    st.markdown("#### Sort Options")
    sort = st.selectbox("Sort By:", ("Price", "Rating", "Price & Rating"))


st.divider()

# ----------- Search Button ------------
if st.button("Search", type="primary"):
    # If hotel location is non-empty, run the full booking search
    if location:
        with st.spinner("Bear with me ...", show_time=True):
            try:
                with sqlite3.connect("travel.db") as conn:
                    print(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully.")

            except:
                st.write("Failed to open database")
                
            query = f"""SELECT *
                        FROM hotels
                        WHERE city = '{location}'
                        AND checkin_date >= '{from_}'
                        AND checkin_date <= '{to_}'
                        AND approx_price BETWEEN {min_price} AND {max_price}
                        AND rating >= {min_review_score}
                        AND rating <= {max_review_score}
                        AND reviews >= {min_reviews}
                        
                        ORDER BY name, checkin_date
                        """
            result_df = pd.read_sql(query, con=conn)
            result_df['checkin_date'] = pd.to_datetime(result_df['checkin_date']).dt.date
            result_df['checkout_date'] = pd.to_datetime(result_df['checkout_date']).dt.date
            conn.close()
            
            hotel_names = list(result_df['name'].unique())
            final_results = []
            for name in hotel_names:
                hotel_df = result_df[result_df['name'] == name].copy()
                first_day = list(hotel_df['checkin_date'])[0]
                last_day = list(hotel_df['checkin_date'])[-1]
                window = (last_day - first_day).days - holiday_length + 1
                if window >= 1:
                    for i in range(window):
                        checkin = first_day + timedelta(days=i)
                        checkout = checkin + timedelta(days=holiday_length)
                        holiday = hotel_df[(hotel_df['checkin_date'] >= checkin) & (hotel_df['checkin_date'] <= checkout)].copy()
                        weeks = int(holiday_length/7) + 1
                        weekly_results = []
                        for j in range(weeks):
                            week_end = checkin + timedelta(days=(j+1)*7)
                            week_result = holiday[holiday['checkout_date'] == week_end].copy()
                            if weeks != 1:
                                if week_end > checkout:
                                    days_over = (week_end - checkout).days
                                    week_result['approx_price'] = week_result['approx_price']*((7-days_over)/holiday_length)
                                else:
                                    week_result['approx_price'] = week_result['approx_price']*(7/holiday_length)
                                
                            weekly_results.append(week_result)
                       
                        check_missing = [len(x) for x in weekly_results]
                        if len(check_missing) == 1:
                            check_missing.append(0)
                            
                        if 0 not in check_missing[:-1]:
                            weekly_df = pd.concat(weekly_results)

                            avg_price = round(sum(weekly_df['approx_price']), 2)
                            holiday_result = weekly_df.iloc[[0]].copy()
                            
                            checkin_orig = holiday_result['checkin_date'].values[0].strftime("%Y-%m-%d")
                            checkout_orig = holiday_result['checkout_date'].values[0].strftime("%Y-%m-%d")
                            checkin_str = checkin.strftime("%Y-%m-%d")
                            checkout_str = checkout.strftime("%Y-%m-%d")
                            
                            holiday_result['checkin_date'] = checkin_str
                            holiday_result['checkout_date'] = checkout_str
                            holiday_result['hotel_link'] = holiday_result['hotel_link'].apply(lambda x:\
                            x.replace("checkin={0}&checkout={1}".format(checkin_orig, checkout_orig),
                                    "checkin={0}&checkout={1}".format(checkin_str, checkout_str)
                                    ))
                            holiday_result['approx_price'] = avg_price
                            final_results.append(holiday_result)
                    
            final_result_df = pd.concat(final_results)
            
            # Scale columns to be within a range of 0 and 1 - price is represented as the percentile value over all prices
            final_result_df['price_percentile'] = stats.percentileofscore(final_result_df['approx_price'], final_result_df['approx_price'])*0.01
            final_result_df['rating_scaled'] = final_result_df['rating']*0.1
            
            # Build VM (Value for Money) score
            final_result_df['vm_score_unrounded'] = 100*(((1-final_result_df['price_percentile'])+final_result_df['rating_scaled'])/2)
            
            # Sort final results based on user input
            if sort == 'Price & Rating':
                final_result_df = final_result_df.sort_values(by='vm_score_unrounded', ascending=False)
                
            elif sort == 'Price':
                final_result_df = final_result_df.sort_values(by='approx_price', ascending=True)
            
            else:
                final_result_df = final_result_df.sort_values(by='rating', ascending=False)
        
            # Apply rounding to VM score
            final_result_df['vm_score'] = round(final_result_df['vm_score_unrounded'])
            final_result_df['vm_score'] = final_result_df['vm_score'].astype(int)
        
            # Drop scaled columns
            final_result_df.drop('price_percentile', axis=1, inplace=True)
            final_result_df.drop('rating_scaled', axis=1, inplace=True)
            final_result_df.drop('vm_score_unrounded', axis=1, inplace=True)
                    
                    
        st.success("Search complete!")

        column_config = {
        "hotel_link": st.column_config.LinkColumn("hotel_link", display_text="Hotel Link")
        }
        st.dataframe(final_result_df, column_config=column_config, hide_index=True)

        excel = convert_df(final_result_df)
        st.download_button("Download Results", data=excel, file_name="search_results.xlsx", type="primary")

    # Else display a warning
    else:
        st.warning("Please enter a destination")
            
