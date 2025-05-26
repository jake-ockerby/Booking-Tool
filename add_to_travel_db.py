import pandas as pd
import asyncio
import sqlite3
import time
from booking_tools import Booker

cities = pd.read_csv('citynames.csv')
cities_list = list(cities['Full Name'])


try:
    with sqlite3.connect("travel.db") as conn:
        print(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully.")

except sqlite3.OperationalError as e:
    print("Failed to open database:", e)
    
cursor = conn.cursor()
# cursor.execute("DELETE FROM hotels")
booker = Booker(location='Manchester, United Kingdom', from_='2025-06-11', to_='2025-07-21', adults=2, children=0,
                rooms=1, sort='Price & Rating', holiday_length=7)

start_time = time.time()
hotels_df = asyncio.run(booker.booking_search())
hotels_df['city'] = 'Manchester, United Kingdom'
hotels_df = hotels_df.set_index('city')
hotels_df['total_price'] = hotels_df['total_price']/14
hotels_df = hotels_df.rename(columns={'total_price': 'approx_price'})
end_time = time.time()
print('Execution Time: '+ str(round(end_time - start_time)) + 's')

start_time = time.time()
hotels_df.to_sql(name='hotels', con=conn, if_exists='replace')
end_time = time.time()
print('Added to DB in '+ str(round(end_time - start_time)) + 's')

df = pd.read_sql("SELECT * FROM hotels", conn)
conn.commit()

cursor.close()
conn.close()