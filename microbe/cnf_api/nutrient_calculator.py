# File: nutrient_calculator.py

from sqlalchemy import create_engine, text
import pandas as pd

# Database connection settings
DB_PARAMS = {
    "host": "localhost",
    "database": "cnf",  # <-- your real DB name
    "user": "postgres",
    "password": "postgres",
    "port": 5432
}


def create_engine_from_params():
    """Create a SQLAlchemy engine from DB params."""
    url = f"postgresql+psycopg2://{DB_PARAMS['user']}:{DB_PARAMS['password']}@{DB_PARAMS['host']}:{DB_PARAMS['port']}/{DB_PARAMS['database']}"
    return create_engine(url)


def check_database_connection(engine):
    """Check if the database connection works."""
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
    except Exception as e:
        raise ConnectionError(f"Cannot connect to database: {e}")


def get_dataframe(engine, query, params=None):
    """Utility to run a query and return as pandas DataFrame."""
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)

def get_food_id_by_name(food_identifier):

    engine = create_engine_from_params()
    check_database_connection(engine)

    if isinstance(food_identifier, int) or (isinstance(food_identifier, str) and food_identifier.isdigit()):
        food_id = int(food_identifier)
    else:
        # 1a. Search by name
        food_query = """
                SELECT "food_id", "description"
                FROM food
                WHERE LOWER("description") LIKE LOWER(:food)
                LIMIT 1
            """
        food_df = get_dataframe(engine, food_query, params={"food": f"%{food_identifier}%"})
        if food_df.empty:
            raise ValueError(f"Food '{food_identifier}' not found.")
        food_id = int(food_df.iloc[0]['food_id'])

    return food_id

def calculate_nutrients(food_identifier, measure_search_name, quantity=1, adjust_for_refuse=True, adjust_for_yield=True, debug=False):
    """
    Calculate nutrient breakdown for a given food and measure.

    Args:
        food_search_name (str): Name of the food (e.g., "chicken leg")
        measure_search_name (str): Name of the measure (e.g., "1 leg")
        quantity (float): Quantity of the measure (default = 1)

    Returns:
        pd.DataFrame: Nutrient breakdown with scaled amounts
        :param adjust_for_refuse_and_yield:
    """
    engine = create_engine_from_params()
    check_database_connection(engine)

    food_id=get_food_id_by_name(food_identifier)

    # 2. Find MeasureID
    measure_query = """
           SELECT mn."measure_id", mn."name"
           FROM conversion_factor cf
           JOIN measure_name mn ON cf."measure_id" = mn."measure_id"
           WHERE cf."food_id" = :food_id
             AND LOWER(mn."name") LIKE :measure
           LIMIT 1
       """
    measure_df = get_dataframe(engine, measure_query,
                               params={"food_id": food_id, "measure": f"%{measure_search_name.lower()}%"})


    if measure_df.empty:
        raise ValueError(f"Measure '{measure_search_name}' not found for food '{food_id}'.")
    measure_id = int(measure_df.iloc[0]['measure_id'])

    # 3. Find Conversion Factor
    conversion_query = """
        SELECT "value"
        FROM conversion_factor
        WHERE "food_id" = :food_id AND "measure_id" = :measure_id
        LIMIT 1
    """
    conv_df = get_dataframe(engine, conversion_query, params={"food_id": food_id, "measure_id": measure_id})
    if conv_df.empty:
        raise ValueError(f"No conversion factor found for MeasureID '{measure_id}'.")
    gram_weight = float(conv_df.iloc[0]['value']) * 100
    total_grams = gram_weight * quantity

    # ⚡ If Gm_Wgt is NaN or missing, fallback to 100g
    if pd.isna(total_grams) or total_grams == 0:
        print(f"⚠️ No Gm_Wgt found for this measure, assuming 100g per unit.")
        total_grams = 100 * quantity

    if adjust_for_refuse:
        # Get refuse percent (if exists)
        refuse_query = """
                    SELECT "amount"
                    FROM "refuse_amount"
                    WHERE "food_id" = :food_id
                    LIMIT 1
                """
        refuse_df = get_dataframe(engine, refuse_query, params={"food_id": food_id})

        if not refuse_df.empty and refuse_df.iloc[0]['amount'] is not None:
            refuse_percent = refuse_df.iloc[0]['amount']
            print(f"Refuse amount found: {refuse_percent}%")
            total_grams *= (100 - refuse_percent) / 100
            print(f"Adjusted grams after refuse: {total_grams:.2f}g")

    if adjust_for_yield:
        # Get yield percent (if exists)
        yield_query = """
                    SELECT "amount"
                    FROM "yield_amount"
                    WHERE "food_id" = :food_id
                    LIMIT 1
                """
        yield_df = get_dataframe(engine, yield_query, params={"food_id": food_id})

        if not yield_df.empty and yield_df.iloc[0]['amount'] is not None:
            yield_percent = yield_df.iloc[0]['amount']
            print(f"Yield amount found: {yield_percent}%")
            total_grams *= yield_percent / 100
            print(f"Adjusted grams after yield: {total_grams:.2f}g")

    # 4. Find Nutrients per 100g
    nutrients_query = """
        SELECT na."value", nn."symbol", nn."name", nn."unit"
        FROM nutrient_amount na
        JOIN nutrient_name nn ON na."nutrient_name_id" = nn."nutrient_name_id"
        WHERE na."food_id" = :food_id
    """
    nutrients_df = get_dataframe(engine, nutrients_query, params={"food_id": food_id})

    if nutrients_df.empty:
        raise ValueError(f"No nutrient data found for FoodID '{food_id}'.")

    # 5. Scale nutrients
    nutrients_df['AmountPerMeasure'] = nutrients_df['value'].astype(float) * (total_grams / 100)

    # Inside the try block
    print(f"🔎 Food: {food_identifier} (ID: {food_id})")
    print(f"🔎 Measure requested: {measure_search_name} ➔ Measure ID: {measure_id}")
    print(f"🔎 Base grams (before refuse/yield adjustment): {gram_weight:.2f}g")
    print(f"🔎 Final grams (after refuse/yield adjustment): {total_grams:.2f}g")

    # 6. Return result
    result = nutrients_df[['symbol', 'name', 'AmountPerMeasure', 'unit']].sort_values('symbol')
    dict = result[['name','AmountPerMeasure']].to_dict('tight')['data']
    if debug:
        return dict.to_string(index=False)
    else:
        return dict

def filter_foods_in_cnf_node(state):
    valid_foods = []
    for food in state["selected_foods"]:
        try:
            _ = get_food_id_by_name(food)
            valid_foods.append(food)
        except ValueError:
            continue
    return {**state, "valid_substitutions": valid_foods}

def calculate_nutrient_summary_node(state):
    summary_lines = []
    for food in state["valid_substitutions"]:
        try:
            nutrients = calculate_nutrients(
                food_identifier=food,
                measure_search_name="100g",  # or guess from query
                quantity=1,
                debug=False
            )
            summary = "\n".join([f"{k}: {v:.2f}" for k, v in nutrients])
            summary_lines.append(f"🔹 {food}:\n{summary}")
        except Exception as e:
            summary_lines.append(f"⚠️ Skipped {food}: {str(e)}")
    return {**state, "nutrient_analysis": "\n\n".join(summary_lines)}

if __name__ == "__main__":
    try:
        print("Checking database connection...")
        engine = create_engine_from_params()
        check_database_connection(engine)
        print("✅ Database connection successful.\n")

        food = "Chicken, broiler, leg, meat and skin, roasted"
        measure = "1 leg"
        quantity = 1  # default

        df = calculate_nutrients(food, measure, quantity, adjust_for_refuse=False, adjust_for_yield=False)
        dict = df[['name','AmountPerMeasure']].to_dict('tight')['data']
        #print(f"Energy intake: {df[df['symbol'] == 'KCAL']['AmountPerMeasure'].values[0]} kcal")
        #print(df.to_string(index=False))
        print(dict)


    except ValueError as e:

        print(f"❌ ValueError: {e}")

    except Exception as e:

        print(f"❌ Unexpected error: {e}")

def nutrient_calculator_tool(input_str: str) -> str:
    """
    Expects input like: "Butter, regular | 9.46g"
    """
    try:
        food, quantity_str = input_str.split("|")
        food = food.strip()
        quantity = float(quantity_str.strip().lower().replace("g", "").strip())

        result = calculate_nutrients(
            food_identifier=food,
            measure_search_name="100g",
            quantity=quantity,  # Since 100g is the base
            debug=False
        )

        if not result:
            return "❌ No nutrient data found."

        formatted = "\n".join([f"{name}: {amount:.2f}" for name, amount in result])
        return f"✅ Nutrient summary for {food} ({quantity}g):\n{formatted}"

    except Exception as e:
        return f"❌ Error in NutrientCalculator: {str(e)}"

def food_selector_tool(input_str: str) -> str:
    """
    Checks if a food exists in the CNF.
    Input: food name as string (e.g., "Kefir")
    """
    try:
        food_id = get_food_id_by_name(input_str.strip())
        return f"✅ '{input_str.strip()}' exists in CNF (Food ID: {food_id})"
    except Exception as e:
        return f"❌ '{input_str.strip()}' not found in CNF: {str(e)}"
