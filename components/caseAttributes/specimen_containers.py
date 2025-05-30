import pandas as pd

"""
Creating weights for specimen containers, using empirical values 
"""

df = pd.read_csv('../../extraFiles/compressed_output.csv')

df = df[df['activity'] == 'accessioning']

df = df[['specimen_typ', 'specimen_containers']]

counts = (df.groupby(['specimen_typ','specimen_containers'])
                    .size()
                    .reset_index(name = 'count'))


counts['weight'] = counts.groupby('specimen_typ')['count'].transform(lambda x: x / x.sum())

weighted_containers = counts.sort_values(['specimen_typ', 'weight'], ascending=[True, False])

weighted_containers.to_csv('specimen_containers_empirical_distribution.csv')