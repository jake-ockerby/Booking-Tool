#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 23 14:38:54 2025

@author: jake_ockerby
"""

import pandas as pd

df = pd.read_csv('geonames.csv', sep=';', on_bad_lines='skip')
df_list = []
for country in df['Country Code'].unique():
    if country not in ['RU', 'UA']:
        df_country = df[df['Country Code'] == country].copy()
        
        if country == 'GB':
            df_country = df_country.sort_values('Population', ascending=False).head(10)
        else:
            df_country = df_country.sort_values('Population', ascending=False).head(3)
            
        df_country['Full Name'] = df_country['Name'] + ', ' + df_country['Country name EN']
        df_country = df_country[['Full Name', 'Population']].copy().dropna()
        df_list.append(df_country)
        
df_filtered = pd.concat(df_list, ignore_index=True)
df_filtered.to_csv('citynames.csv')