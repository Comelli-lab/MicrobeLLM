import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from cnf_sqlalchemy_postgres import (
    Base, Food, FoodGroup, FoodSource, NutrientName, NutrientSource,
    NutrientAmount, MeasureName, ConversionFactor,
    RefuseName, RefuseAmount, YieldName, YieldAmount
)
from datetime import datetime

# --- CONFIG ---
DATA_DIR = "../../api_data/CNF/"
engine = create_engine("postgresql://postgres:postgres@localhost:5432/cnf")
Session = sessionmaker(bind=engine)
session = Session()


# --- HELPER ---
def safe_parse_date(date_str):
    try:
        if pd.isna(date_str) or str(date_str).lower() in ['nat', 'nan']:
            return None
        return pd.to_datetime(date_str).date()
    except:
        return None


def ensure_and_reset_sequence(table_name, column_name, sequence_name):
    # Ensure the sequence exists and is linked
    create_sequence_query = text(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = :sequence_name) THEN
                CREATE SEQUENCE {sequence_name}
                START WITH 1
                INCREMENT BY 1
                NO MINVALUE
                NO MAXVALUE
                CACHE 1;
                ALTER TABLE {table_name} ALTER COLUMN {column_name} SET DEFAULT nextval('{sequence_name}');
            END IF;
        END $$;
    """)
    session.execute(create_sequence_query, {'sequence_name': sequence_name})
    session.commit()

    # Reset the sequence
    reset_query = text(f"""
        SELECT setval(
            '{sequence_name}',
            COALESCE((SELECT MAX({column_name}) FROM {table_name}), 1),
            false
        );
    """)
    session.execute(reset_query)
    session.commit()


def clear_all_tables():
    session.query(NutrientAmount).delete()
    session.query(ConversionFactor).delete()
    session.query(RefuseAmount).delete()
    session.query(YieldAmount).delete()
    session.query(Food).delete()
    session.query(FoodGroup).delete()
    session.query(FoodSource).delete()
    session.query(NutrientName).delete()
    session.query(NutrientSource).delete()
    session.query(MeasureName).delete()
    session.query(RefuseName).delete()
    session.query(YieldName).delete()
    session.commit()


# --- INGESTION FUNCTIONS ---
def load_food():
    df = pd.read_csv(f"{DATA_DIR}FOOD NAME.csv", encoding="latin1")
    df.columns = df.columns.str.strip().str.replace(" ", "")
    for _, row in df.iterrows():
        session.add(Food(
            food_id=int(row['FoodID']),
            food_code=str(row['FoodCode']),
            food_group_id=int(row['FoodGroupID']) if pd.notna(row['FoodGroupID']) else None,
            food_source_id=int(row['FoodSourceID']) if pd.notna(row['FoodSourceID']) else None,
            description=row['FoodDescription'],
            description_fr=row['FoodDescriptionF'],
            country_code=str(row['CountryCode']) if pd.notna(row['CountryCode']) else None,
            date_of_entry=safe_parse_date(row['FoodDateOfEntry']),
            date_of_publication=safe_parse_date(row['FoodDateOfPublication']),
            scientific_name=row['ScientificName'] if pd.notna(row['ScientificName']) else None
        ))
    session.commit()


def load_support_table(model, filename, col_map, dtypes=None):
    if dtypes:
        df = pd.read_csv(f"{DATA_DIR}{filename}", encoding="latin1", dtype=dtypes)
    else:
        df = pd.read_csv(f"{DATA_DIR}{filename}", encoding="latin1")
    df.columns = df.columns.str.strip().str.replace(" ", "")
    for _, row in df.iterrows():
        session.add(model(**{k: row[v] if pd.notna(row[v]) else None for k, v in col_map.items()}))
    session.commit()


def load_nutrient_amount():
    df = pd.read_csv(f"{DATA_DIR}NUTRIENT AMOUNT.csv", encoding="latin1")
    df.columns = df.columns.str.strip().str.replace(" ", "")
    for _, row in df.iterrows():
        session.add(NutrientAmount(
            food_id=int(row['FoodID']),
            nutrient_name_id=int(row['NutrientID']),
            nutrient_source_id=int(row['NutrientSourceID']),
            value=row['NutrientValue'] if pd.notna(row['NutrientValue']) else None,
            standard_error=row['StandardError'] if pd.notna(row['StandardError']) else None,
            num_observations=int(row['NumberofObservations']) if pd.notna(row['NumberofObservations']) else None,
            date_of_entry=safe_parse_date(row['NutrientDateOfEntry'])
        ))
    session.commit()


def load_conversion_factor():
    df = pd.read_csv(f"{DATA_DIR}CONVERSION FACTOR.csv", encoding="latin1")
    df.columns = df.columns.str.strip().str.replace(" ", "")
    for _, row in df.iterrows():
        session.add(ConversionFactor(
            food_id=int(row['FoodID']),
            measure_id=int(row['MeasureID']),
            value=row['ConversionFactorValue'] if pd.notna(row['ConversionFactorValue']) else None,
            date_of_entry=safe_parse_date(row['ConvFactorDateOfEntry'])
        ))
    session.commit()


def load_refuse_amount():
    df = pd.read_csv(f"{DATA_DIR}REFUSE AMOUNT.csv", encoding="latin1")
    df.columns = df.columns.str.strip().str.replace(" ", "")
    for _, row in df.iterrows():
        session.add(RefuseAmount(
            food_id=int(row['FoodID']),
            refuse_id=int(row['RefuseID']),
            amount=row['RefuseAmount'] if pd.notna(row['RefuseAmount']) else None,
            date_of_entry=safe_parse_date(row['RefuseDateOfEntry'])
        ))
    session.commit()


def load_yield_amount():
    df = pd.read_csv(f"{DATA_DIR}YIELD AMOUNT.csv", encoding="latin1")
    df.columns = df.columns.str.strip().str.replace(" ", "")
    for _, row in df.iterrows():
        session.add(YieldAmount(
            food_id=int(row['FoodID']),
            yield_id=int(row['YieldID']),
            amount=row['YieldAmount'] if pd.notna(row['YieldAmount']) else None,
            date_of_entry=safe_parse_date(row['YieldDateofEntry'])
        ))
    session.commit()


# --- MAIN LOADING ---
clear_all_tables()
# Debugging: Check if the table is empty
refuse_name_count = session.execute(text("SELECT COUNT(*) FROM refuse_name")).scalar()
print(f"Rows in refuse_name after clearing: {refuse_name_count}")
# List of tables and their sequence columns
tables_and_columns = [
    ('food', 'food_id', 'food_food_id_seq'),
    ('food_group', 'food_group_id', 'food_group_food_group_id_seq'),
    ('food_source', 'food_source_id', 'food_source_food_source_id_seq'),
    ('nutrient_name', 'nutrient_name_id', 'nutrient_name_nutrient_name_id_seq'),
    ('nutrient_source', 'nutrient_source_id', 'nutrient_source_nutrient_source_id_seq'),
    ('conversion_factor', 'id', 'conversion_factor_id_seq'),
    ('nutrient_amount', 'id', 'nutrient_amount_id_seq'),
    ('refuse_amount', 'id', 'refuse_amount_id_seq'),
    ('yield_amount', 'id', 'yield_amount_id_seq'),
    ('measure_name', 'measure_id', 'measure_name_measure_id_seq'),
    ('refuse_name', 'refuse_id', 'refuse_name_refuse_id_seq'),
    ('yield_name', 'yield_id', 'yield_name_yield_id_seq')
]

# Call ensure_and_reset_sequence for each table
for table, column, sequence in tables_and_columns:
    ensure_and_reset_sequence(table, column, sequence)
# Debugging: Check the current sequence value
sequence_value = session.execute(text("""
    SELECT last_value FROM pg_sequences WHERE schemaname = 'public' AND sequencename = 'refuse_name_refuse_id_seq'
""")).scalar()
print(f"Current sequence value for refuse_name_refuse_id_seq: {sequence_value}")

# Load support tables first
load_support_table(FoodGroup, "FOOD GROUP.csv", {
    'food_group_id': 'FoodGroupID', 'code': 'FoodGroupCode', 'name': 'FoodGroupName', 'name_fr': 'FoodGroupNameF'})
load_support_table(FoodSource, "FOOD SOURCE.csv", {
    'food_source_id': 'FoodSourceID', 'code': 'FoodSourceCode', 'description': 'FoodSourceDescription',
    'description_fr': 'FoodSourceDescriptionF'})
load_support_table(NutrientName, "NUTRIENT NAME.csv", {
    'nutrient_name_id': 'NutrientID', 'code': 'NutrientCode', 'symbol': 'NutrientSymbol', 'unit': 'NutrientUnit',
    'name': 'NutrientName', 'name_fr': 'NutrientNameF', 'tagname': 'Tagname', 'decimals': 'NutrientDecimals'})
load_support_table(NutrientSource, "NUTRIENT SOURCE.csv", {
    'nutrient_source_id': 'NutrientSourceID', 'code': 'NutrientSourceCode', 'description': 'NutrientSourceDescription',
    'description_fr': 'NutrientSourcDescriptionF'})
load_support_table(MeasureName, "MEASURE NAME.csv", {
    'measure_id': 'MeasureID', 'name': 'MeasureDescription', 'name_fr': 'MeasureDescriptionF'})
load_support_table(RefuseName, "REFUSE NAME.csv", {
    'refuse_id': 'RefuseID', 'name': 'RefuseDescription', 'name_fr': 'RefuseDescriptionF'})
load_support_table(YieldName, "YIELD NAME.csv", {
    'yield_id': 'YieldID', 'name': 'YieldDescription', 'name_fr': 'YieldDescriptionF'})

# Load food data after support tables
load_food()
load_nutrient_amount()
load_conversion_factor()
load_refuse_amount()
load_yield_amount()

print("✅ All CNF tables loaded successfully.")
