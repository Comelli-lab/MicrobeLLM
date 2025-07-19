import os
import pandas as pd
from glob import glob

# Paths
base_dir = r"/api_data/CNF"
update_dir = r"C:\Users\mario\Downloads\cnf-fcen-csv-update-miseajour"
output_dir = base_dir  # Change if you want to save to a different folder

# Mapping table base names to primary key column
table_primary_keys = {
    "YIELD NAME": "YieldID",
    "REFUSE NAME": "RefuseID",
    "MEASURE NAME": "MeasureID",
    "FOOD NAME": "FoodID",
    "FOOD GROUP": "FoodGroupID",
    "FOOD SOURCE": "FoodSourceID",
    "NUTRIENT NAME": "NutrientID",
    "NUTRIENT SOURCE": "NutrientSourceID",
}


def apply_updates(base_file, update_files, primary_key):
    print(f"\nProcessing base file: {os.path.basename(base_file)} (primary key: {primary_key})")

    # Read the base CSV
    base_df = pd.read_csv(base_file, dtype=str, encoding="latin1")

    # Map update type to suffix
    updates = {'ADD': None, 'CHANGED': None, 'DELETE': None}
    for suffix in updates.keys():
        matched = [f for f in update_files if suffix in os.path.basename(f)]
        if matched:
            updates[suffix] = matched[0]

    # Apply DELETE
    if updates['DELETE']:
        delete_df = pd.read_csv(updates['DELETE'], dtype=str, encoding="latin1")
        print(f" - Deleting {len(delete_df)} rows")
        base_df = base_df[~base_df[primary_key].isin(delete_df[primary_key])]

    # Apply CHANGED
    if updates['CHANGED']:
        changed_df = pd.read_csv(updates['CHANGED'], dtype=str, encoding="latin1")
        print(f" - Changing {len(changed_df)} rows")
        base_df = base_df[~base_df[primary_key].isin(changed_df[primary_key])]
        base_df = pd.concat([base_df, changed_df], ignore_index=True)

    # Apply ADD
    if updates['ADD']:
        add_df = pd.read_csv(updates['ADD'], dtype=str, encoding="latin1")
        print(f" - Adding {len(add_df)} rows")
        base_df = pd.concat([base_df, add_df], ignore_index=True)

    # Save updated file
    output_path = os.path.join(output_dir, os.path.basename(base_file))
    base_df.to_csv(output_path, index=False)
    print(f" - Saved updated file to: {output_path}")


def deduplicate_all_files():
    print("\n--- Deduplicating all updated files ---")

    base_files = glob(os.path.join(output_dir, "*.csv"))

    for base_file in base_files:
        base_name = os.path.splitext(os.path.basename(base_file))[0]
        primary_key = table_primary_keys.get(base_name)

        if not primary_key:
            continue  # Skip files without a known primary key

        df = pd.read_csv(base_file, dtype=str, encoding="latin-1")
        before = len(df)
        df = df.drop_duplicates(subset=[primary_key])
        after = len(df)

        if before != after:
            print(f" - {base_name}: removed {before - after} duplicate rows based on {primary_key}")
            df.to_csv(base_file, index=False, encoding="latin-1")
        else:
            print(f" - {base_name}: no duplicates found.")


def main():
    # First apply updates
    base_files = glob(os.path.join(base_dir, "*.csv"))

    for base_file in base_files:
        base_name = os.path.splitext(os.path.basename(base_file))[0]

        # Find matching update files
        update_files = glob(os.path.join(update_dir, f"{base_name}*.csv"))

        if not update_files:
            print(f"\nNo updates found for: {base_name}")
            continue

        # Determine primary key
        primary_key = table_primary_keys.get(base_name)
        if not primary_key:
            print(f"\nWarning: No primary key mapping found for {base_name}, skipping...")
            continue

        apply_updates(base_file, update_files, primary_key)

    # Then deduplicate
    deduplicate_all_files()


if __name__ == "__main__":
    main()
