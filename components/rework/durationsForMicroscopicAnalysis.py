import os

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")


"""
Counts for each different specimen type and the different rework events
"""

df = pd.read_csv('MicroscopicAnalysis-1744105034034.csv')
df = df[df['event_name'].isin([99, 91, 92, 93])]

df = df.drop_duplicates(subset=['case_id', 'happened_at'])

df = df[['specimen_typ', 'event_name']]

counts = df.groupby(['specimen_typ', 'event_name']).size().reset_index(name='count')

counts_pivot = df.pivot_table(
    index='specimen_typ',
    columns='event_name',
    aggfunc='size',
    fill_value=0
)

if counts_pivot.index.name != 'specimen_typ':
        counts_pivot.set_index('specimen_typ', inplace=True)


counts_pivot.to_csv('counts_pivot.csv', index ='specimen_typ')



