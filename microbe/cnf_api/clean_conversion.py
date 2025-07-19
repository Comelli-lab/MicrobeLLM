import pandas as pd
import os

# Paths
base_dir = r"/api_data/CNF"
conversion_file = os.path.join(base_dir, "CONVERSION FACTOR.csv")
measure_file = os.path.join(base_dir, "MEASURE NAME.csv")

# Read both files
conversion_df = pd.read_csv(conversion_file, dtype=str, encoding="latin-1")
measure_df = pd.read_csv(measure_file, dtype=str, encoding="latin-1")

# Get list of valid MeasureIDs
valid_measure_ids = set(measure_df["MeasureID"].dropna())

# Filter out rows with invalid MeasureIDs
before = len(conversion_df)
conversion_df_cleaned = conversion_df[conversion_df["MeasureID"].isin(valid_measure_ids)]
after = len(conversion_df_cleaned)

# Save the cleaned file (overwrite)
conversion_df_cleaned.to_csv(conversion_file, index=False, encoding="latin-1")

print(f"Removed {before - after} invalid MeasureID rows from CONVERSION FACTOR.csv")
