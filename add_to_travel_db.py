import pandas as pd
import asyncio
import sqlite3
import time
from datetime import date, timedelta
from booking_tools import Booker

cities = pd.read_csv('citynames.csv')
cities_list = sorted(list(cities['Full Name']))
exclude = ['Andorra', 'San Marino', 'Monaco', 'Jersey', 'Guernsey', 'Isle of Man',
           'Liechtenstein', 'Sector 3', 'Syria', 'Luxembourg', 'Cyprus']
for item in exclude:
    cities_list = [city for city in cities_list if item not in city ]

try:
    with sqlite3.connect("travel.db") as conn:
        print(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully.")

except sqlite3.OperationalError as e:
    print("Failed to open database:", e)
    
cursor = conn.cursor()
# cursor.execute("DELETE FROM hotels")

today = date.today().strftime("%Y-%m-%d")
end_date = (date.today() + timedelta(days=212)).strftime("%Y-%m-%d")
for city in [cities_list[4]]:
    start_time = time.time()
    print(city)
    booker = Booker(location=city, from_=today, to_=end_date, adults=2, children=0,
                    rooms=1, sort='Price & Rating', holiday_length=7)
    
    
    hotels_df = asyncio.run(booker.booking_search())
    hotels_df['city'] = city
    hotels_df = hotels_df.set_index('city')
    if 'Athens' in city:
        athenian_spirit = hotels_df[hotels_df['name'] == 'Athenian Spirit']
        helpme = athenian_spirit[['total_price', 'url']].copy().head(25)
        print(helpme['url'].values[0])
        helpme.to_csv('helpme.csv')
        print(helpme)
        
    hotels_df['total_price'] = hotels_df['total_price']/14
    hotels_df = hotels_df.rename(columns={'total_price': 'approx_price'})
    hotels_df.to_sql(name='hotels', con=conn, if_exists='append')
    end_time = time.time()
    print('Execution Time: '+ str(round(end_time - start_time)) + 's\n')


# df = pd.read_sql("SELECT * FROM hotels", conn)
conn.commit()
cursor.close()
conn.close()