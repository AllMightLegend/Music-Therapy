import pandas as pd
df = pd.read_csv('muse_v3.csv')
print('Total columns:', len(df.columns))
print('\nAll columns:')
for col in df.columns:
    print(f'  - {col}')
print(f'\nDataset shape: {df.shape}')
print(f'\nSample statistics:')
print(df[['valence_tags', 'arousal_tags', 'dominance_tags']].describe())
