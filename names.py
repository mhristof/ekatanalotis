import pandas as pd
from rapidfuzz import process

# Load your datasets
kritikos_df = pd.read_csv('sm-kritikos.csv')
marketin_df = pd.read_csv('sm-marketin.csv')

# Function to perform fuzzy matching
def rapidfuzz_match_names(kritikos_names, marketin_names, threshold=80):
    matches = []
    for name in kritikos_names:
        match = process.extractOne(name, marketin_names)
        if match and match[1] >= threshold:
            matches.append((name, match[0], match[1]))
    return matches

kritikos_names = kritikos_df['name'].tolist()
marketin_names = marketin_df['name'].tolist()

# Get fuzzy matches
fuzzy_matches = rapidfuzz_match_names(kritikos_names, marketin_names)

# Create DataFrame for the matches
fuzzy_matches_df = pd.DataFrame(fuzzy_matches, columns=['name_kritikos', 'name_marketin', 'score'])

# Merge the matched data with original dataframes to get barcodes
matched_df = pd.merge(fuzzy_matches_df, kritikos_df, left_on='name_kritikos', right_on='name', how='left')
matched_df = pd.merge(matched_df, marketin_df, left_on='name_marketin', right_on='name', how='left', suffixes=('_kritikos', '_marketin'))

# Select relevant columns
result_df = matched_df[['name_kritikos', 'barcode_kritikos', 'name_marketin', 'barcode_marketin', 'score']]
print(result_df)
