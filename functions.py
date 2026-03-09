# (0) IMPORTS

import random
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re
from aux_functions import *
from supabase import create_client, Client
import plotly.express as px

# load_dotenv()
# url = os.getenv("SUPABASE_URL")
# key = os.getenv("SUPABASE_ANON_KEY")
# sb = create_client(url, key)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)



# (1) DATA READS

def read_score_df(user="Raphael",user_id=None, limit=1000000):
    print_white("Reading scores from session state...")
    df = st.session_state.get("df_scores")
    if df is not None:
        return df
    else:
        return pd.DataFrame()

def read_score_df_updated_db(user="Raphael", user_id=None, limit=1000000):
    print_orange("Reading scores from Supabase...")

    try:
        table = sb.table("results")
        base_query = table.select("*").eq("name", user).order("datetime_start", desc=True)
        if user_id:
            base_query = base_query.eq("user_id", user_id)

        all_data = []
        batch_size = 1000
        start = 0

        while True:
            end = start + batch_size - 1
            res = base_query.range(start, end).execute()
            rows = res.data or []
            if not rows:
                break
            all_data.extend(rows)
            if len(rows) < batch_size:
                break  # No more data
            start += batch_size

        if not all_data:
            print("No data found in Supabase, returning empty DataFrame.")
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        df.columns = [col.upper() for col in df.columns]
        df = df[df["NAME"] == user]

        if limit:  # Optional manual limit
            df = df.head(limit)

        return df

    except Exception as e:
        print(f"Error reading from Supabase: {e}")
        return pd.DataFrame()

def add_answer_row_to_db():
    print_function("add_answer_row_to_db()")
    """Add a single row to the results table in Supabase."""
    score_flag = 1 if st.session_state.user_answer == st.session_state.correct else 0.1
    duration = min(
        10,
        (
            float(st.session_state.duration_time)
            if st.session_state.duration_time
            else 0.0
        ),
    )

    # safe model score: higher when fast & correct
    eps = 1e-6
    model_score = score_flag / max(duration, eps)

    tafels_in_oef = ",".join([str(tafel) for tafel in st.session_state.selected_tables])

    row = {
        # "uuid": st.session_state.loggedin_user,
        "name": st.session_state.user,
        "datetime_start": st.session_state.starttime.strftime("%Y-%m-%d %H:%M:%S"),
        "date_start": st.session_state.starttime.strftime("%Y-%m-%d"),
        "time_start": st.session_state.starttime.strftime("%H:%M:%S"),
        "exercise_idx": st.session_state.exercise_counter,
        "tafel": st.session_state.x1,
        "rand_num": st.session_state.x2,
        "user_answer": st.session_state.user_answer,
        "score": score_flag,
        "duration_time": duration,  # max of 10 and duration
        "model_score": model_score,
        "probability": 0,  # temp; we recompute below for all rows
        "tafels_in_oef": tafels_in_oef,
        "difficulty_level": st.session_state.difficulty_level,
        "type_exercise": st.session_state.type_exercise,
    }

    response = sb.table("results").insert(row).execute()

    print_green(f"✅ Toegevoegd aan DB: {response.data}")

def save_score_df(df, user_id=None):
    print_function("save_score_df()")
    """Write new score rows to Supabase."""
    try:
        # make all column names lowercase
        df.columns = [col.lower() for col in df.columns]

        # Ensure all JSON-serializable values
        df = df.copy()
        # if "datetime_start" in df:
        #     df["datetime_start"] = pd.to_datetime(
        #         df["datetime_start"], errors="coerce"
        #     ).dt.strftime("%Y-%m-%d %H:%M:%S")
        if "date_start" in df:
            df["date_start"] = pd.to_datetime(
                df["date_start"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")
        if "time_start" in df:
            df["time_start"] = pd.to_datetime(
                df["time_start"].astype(str), errors="coerce"
            ).dt.strftime("%H:%M:%S")

        if user_id and "user_id" not in df:
            df["user_id"] = user_id

        records = df.to_dict(orient="records")
        if not records:
            print("Nothing to save.")
            return

        sb.table("results").insert(records).execute()
        print(f"✅ Saved {len(records)} rows to Supabase.")
    except Exception as e:
        print(f"Error writing to Supabase: {e}")

# (2) EXERCISES

def generate_exercise(accepted_products, level, exercise_idx, type):
    print_title("NEW EXERCISE")
    print_function("New Exercise Generated: vermenigvuldiging")
    if type == "vermenigvuldiging": 
        random_accepted_product = accepted_products[
            random.randint(0, len(accepted_products) - 1)
        ]
        if level == "Moeilijk":
            table_probs = get_table_probs(random_accepted_product)

            # choose a rand index from df table_probs based on probability in PROBABILITY col
            random_number = int(
                random.choices(
                    table_probs["RAND_NUM"].tolist(),
                    weights=table_probs["PROBABILITY"].tolist(),
                    k=1,
                )[0]
            )
            
        elif level == "Middelmatig":
            random_number = random.randint(1, 10)
        
        else:

            if (exercise_idx + 1) <= 10:
                random_number = exercise_idx + 1
            else: 
                random_number = (exercise_idx+1) % 10
            
            if random_number == 0:
                random_number = 10
            

        correct_answer = random_number * random_accepted_product

        exercise_string = f"{random_number} x {random_accepted_product}"
        print_white(exercise_string)

        return exercise_string, correct_answer, random_accepted_product, random_number

    elif type == "deling":
        print_title("NEW EXERCISE")
        print_function("New Exercise Generated: deling")
        random_accepted_product = accepted_products[
            random.randint(0, len(accepted_products) - 1)
        ]
        random_number = random.randint(1, 10)
        
        quotient = random_number * random_accepted_product
        
        correct_answer = random_number
        
        exercise_string = f"{quotient} : {random_accepted_product}"
        print_white(exercise_string)
        return exercise_string, correct_answer, random_accepted_product, quotient


def add_prob(df):
    df = df.copy()
    eps = 1e-6

    # Recompute PROBABILITY safely for all rows
    ms = pd.to_numeric(df["MODEL_SCORE"], errors="coerce").fillna(0.0)
    ms = ms.clip(lower=eps)
    df["PROBABILITY"] = 1.0 / ms

    # normalize probabilities to sum to 1 for sampling
    df["PROBABILITY"] = df["PROBABILITY"] / df["PROBABILITY"].sum()

    # if prob = na, then change to 1 (means it has never seen exercise before)
    df["PROBABILITY"] = df["PROBABILITY"].fillna(1)

    return df

def get_table_probs(table):
    print_function("get_table_probs()")
    df = read_score_df(user=st.session_state.user)
    df = df.query("TYPE_EXERCISE == 'vermenigvuldiging'")
    eps = 1e-6
    # groupby TAFEL and RAND_NUM and take average of SCORE and DURATION
    table_stats = (
        df.loc[(df["TAFEL"] == table) & (df["NAME"] == st.session_state.user)]
        .groupby(["TAFEL", "RAND_NUM"], as_index=False)
        .agg(MEAN_MODEL_SCORE=("MODEL_SCORE", "mean"))
    )

    # if rand_num column misses any numbers between 1 and 10, then add them to the df with mean_model_score = 0
    existing_nums = set(table_stats["RAND_NUM"].tolist())
    # get diff between range 1:10 and existing_nums
    missing_nums = set(range(1, 11)) - existing_nums

    # add missing_nums to table_stats with MEAN_MODEL_SCORE=0
    for num in missing_nums:
        table_stats = pd.concat(
            [
                table_stats,
                pd.DataFrame(
                    {
                        "TAFEL": [table],
                        "RAND_NUM": [num],
                        "MEAN_MODEL_SCORE": [0.0],
                        "PROBABILITY": [1.0],  # will be normalized later
                    }
                ),
            ],
            ignore_index=True,
        )

    ms = pd.to_numeric(table_stats["MEAN_MODEL_SCORE"], errors="coerce").fillna(0.0)
    ms = ms.clip(lower=eps)
    table_stats["PROBABILITY"] = 1.0 / ms
    table_stats["PROBABILITY"] = (
        table_stats["PROBABILITY"] / table_stats["PROBABILITY"].sum()
    )

    return table_stats

def generate_prob_table(df):
    print_function("generate_prob_table()")
    # display in a table that i can use in my streamlit app. cells with low values can be colored green, high values in red
    # First aggregate to handle duplicate TAFEL/RAND_NUM combinations
    df = df.query("TYPE_EXERCISE == 'vermenigvuldiging'")
    df = add_prob(df)
    pivot_table = (
        df[["TAFEL", "RAND_NUM", "PROBABILITY"]]
        .groupby(["TAFEL", "RAND_NUM"], as_index=False)
        .agg({"PROBABILITY": "mean"})
        .assign(PROBABILITY_PCT=lambda x: x["PROBABILITY"] * 100)
        .round({"PROBABILITY_PCT": 2})
        .pivot(index="TAFEL", columns="RAND_NUM", values="PROBABILITY_PCT")
        .reset_index()  # bring TAFEL into columns so headers are on one row
    )

    # Optional: make column names ints/strings consistently for Streamlit
    pivot_table.columns = [str(c) for c in pivot_table.columns]

    # Style for Streamlit - color coding low values green, high values red
    # Apply gradient to numeric columns only; show blanks for NaN
    numeric_cols = [c for c in pivot_table.columns if c != "TAFEL"]
    styled_table = pivot_table.style.background_gradient(
        cmap="RdYlGn_r", subset=numeric_cols, axis=None
    ).format({c: "{:.2f}%" for c in numeric_cols})

    # Display the styled table
    return styled_table


# (3) EVALUATION

def check_answer(correct_answer, user_answer):
    correct_answer = int(correct_answer)
    user_answer = int(user_answer)

    return correct_answer == user_answer

def reset_progress(n_exercises):
    # display n_exercises white circle emojis
    st.session_state.duration_time_start = datetime.now()
    st.session_state.starttime = datetime.now()
    st.session_state.progress = ["⚪"] * n_exercises

def render_progress():
    """Display the circles as emoji."""
    circles = st.session_state.get("progress", [])
    if not circles:
        return
    row1 = " ".join(circles)
    st.markdown("#### Voortgang")
    st.markdown(f"{row1}")

def update_progress(exercise_counter, answer_type):
    print_function(f"update_progress(exercise_counter={exercise_counter}, answer_type={answer_type})")
    # ignore if we're at the start or out of bounds
    if exercise_counter <= 0 or exercise_counter > len(st.session_state.progress):
        return

    idx = exercise_counter - 1

    if answer_type == "correct":
        st.session_state.progress[idx] = "🟢"
        st.session_state.score += 1

    elif answer_type == "wrong":
        st.session_state.progress[idx] = "🔴"

    else:
        st.session_state.progress[idx] = "⚪"

    # def init_score_df():
    # os.makedirs(DATA_PATH, exist_ok=True)
    # if os.path.exists(SCORE_FILE):
    #     df = pd.read_csv(SCORE_FILE)
    # else:
    #     df = pd.DataFrame(
    #         columns=[
    #             "NAME",
    #             "DATETIME_START",
    #             "DATE_START",
    #             "TIME_START",
    #             "EXERCISE_IDX",
    #             "TAFEL",
    #             "RAND_NUM",
    #             "USER_ANSWER",
    #             "SCORE",
    #             "DURATION_TIME",
    #             "MODEL_SCORE",
    #             "PROBABILITY",
    #         ]
    #     )
    #     # csv with ; as separator
    #     df.to_csv(SCORE_FILE, index=False, sep=";")
    # return df


# (4) STREAMLIT

def restart():
    print_function("restart()")
    # st.session_state.pokemon = get_all_pokemons()
    st.session_state.round_active = True
    st.session_state.round_count = 0
    st.session_state.score = 0
    reset_progress(
        n_exercises=st.session_state.n_exercises
    )  # 👈 reset circles to all white
    (
        st.session_state.exercise,
        st.session_state.correct,
        st.session_state.x1,
        st.session_state.x2,
    ) = generate_exercise(st.session_state.selected_tables, st.session_state.difficulty_level, 0, st.session_state.type_exercise)
    st.session_state.exercise_counter = 0
    st.session_state.last_result = None
    st.session_state.render_pokemon = True # reset pokemon header when user has changed anhything in instellingen

    st.rerun()
    render_progress()

def init_session_state(generate_exercise, reset_progress):
    print_function("init_session_state()")
    defaults = {
        "user": "Raphael",
        "difficulty_level": "Middelmatig",
        "starttime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_exercises": 20,
        "selected_tables": [2, 3, 4, 5, 6, 7, 8, 9],
        "score": 0,
        "exercise_counter": 0,
        "user_answer_str": "",
        "reset_answer": False,
        "x1": 0,
        "x2": 0,
        "user_answer": 0,
        "duration_time_start": datetime.now(),
        "duration_time": 0.0,
        "status": 1,
        "pokemon": ["Magikarp"],
        "df_scores": pd.DataFrame(),
        "type_exercise": "vermenigvuldiging",
        "render_pokemon": True,
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
            if key == "df_scores":
                st.session_state.df_scores = read_score_df_updated_db(user=st.session_state.user)
                st.session_state.pokemon = get_all_pokemons()
        


    # dependent inits
    if "progress" not in st.session_state:
        reset_progress(st.session_state.n_exercises)

    if "exercise" not in st.session_state:
        (
            st.session_state.exercise,
            st.session_state.correct,
            st.session_state.x1,
            st.session_state.x2,
        ) = generate_exercise(st.session_state.selected_tables, st.session_state.difficulty_level, 0, st.session_state.type_exercise)
        st.session_state.last_result = None
        st.session_state.prev_exercise = None
        st.session_state.prev_correct = None



    # st.session_state.pokemon = get_all_pokemons()

# (5) STATS


def generate_duration_table(df):
    print_function("generate_duration_table()")
    # display in a table that i can use in my streamlit app. cells with low values can be colored green, high values in red
    # First aggregate to handle duplicate TAFEL/RAND_NUM combinations
    df = add_prob(df)
    pivot_table = (
        df[["TAFEL", "RAND_NUM", "DURATION_TIME"]]
        .groupby(["TAFEL", "RAND_NUM"], as_index=False)
        .agg({"DURATION_TIME": "mean"})
        .assign(DURATION_TIME=lambda x: x["DURATION_TIME"].apply(np.ceil).astype(int))
        .pivot(index="TAFEL", columns="RAND_NUM", values="DURATION_TIME")
        .reset_index()  # bring TAFEL into columns so headers are on one row
    )

    # Optional: make column names ints/strings consistently for Streamlit
    pivot_table.columns = [str(c) for c in pivot_table.columns]

    # Style for Streamlit - color coding low values green, high values red
    # Apply gradient to numeric columns only; show blanks for NaN
    numeric_cols = [c for c in pivot_table.columns if c != "TAFEL"]
    styled_table = pivot_table.style.background_gradient(
        cmap="RdYlGn_r", subset=numeric_cols, axis=None
    ).format({c: "{:.0f}" for c in numeric_cols})

    # Display the styled table
    return styled_table

def generate_score_table(df):
    print_function("generate_score_table()")
    # display in a table that i can use in my streamlit app. cells with low values can be colored green, high values in red
    # First aggregate to handle duplicate TAFEL/RAND_NUM combinations
    
    print_white("add prob")
    df = add_prob(df)
    
    print_white("create pivot")
    pivot_table = (
        df[["TAFEL", "RAND_NUM", "SCORE"]]
        .assign(SCORE=lambda x: x["SCORE"].apply(lambda score: 1 if score == 1 else 0))
        .groupby(["TAFEL", "RAND_NUM"], as_index=False)
        .agg({"SCORE": "mean"})
        .assign(SCORE=lambda x: x["SCORE"].round(2))
        .pivot(index="TAFEL", columns="RAND_NUM", values="SCORE")
        .reset_index()  # bring TAFEL into columns so headers are on one row
    )

    print_white("convert all cols to str")
    # Optional: make column names ints/strings consistently for Streamlit
    pivot_table.columns = [str(c) for c in pivot_table.columns]

    # Style for Streamlit - color coding low values green, high values red
    # Apply gradient to numeric columns only; show blanks for NaN
    
    print_white("process some nums values")
    numeric_cols = [c for c in pivot_table.columns if c != "TAFEL"]
    
    print_white("add color styling")
    styled_table = pivot_table.style.background_gradient(
        cmap="RdYlGn", subset=numeric_cols, axis=None
    ).format({c: "{:.2f}" for c in numeric_cols})

    # Display the styled table
    return styled_table

def get_min_per_dag(df):
    df_per_day = (
        df.groupby(["DATE_START"], as_index=False)
        .agg(SEC_PER_DAG=("DURATION_TIME", "sum"))
        .assign(MIN_PER_DAG=lambda x: x["SEC_PER_DAG"] / 60)
    )

    return df_per_day

def highlight_cells(val):
    if pd.isna(val):
        return ""
    # Extract the minutes value from the text
    try:
        # Extract minutes from text like "2024-01-15\n[Timer: 5 min, score: 80%]"
        minutes = float(re.search(r"Tijd:\s*(\d+)\s*min", val).group(1))
        if minutes >= 10:
            return "background-color: green; color: white; font-weight: bold;"
        elif minutes > 0:
            return "background-color: orange; color: black; font-weight: bold;"
        else:
            return "background-color: red; color: white; font-weight: bold;"
    except:
        return ""

def create_calendar_table(df, display):
    print_function("create_calendar_table()")
    df["SCORE"] = df["SCORE"].apply(lambda d: 0 if d == 0.1 else d)

    df_per_day = (
        df.groupby(["DATE_START"], as_index=False)
        .agg(SEC_PER_DAG=("DURATION_TIME", "sum"), SCORE_PER_DAG=("SCORE", "mean"))
        .assign(MIN_PER_DAG=lambda x: x["SEC_PER_DAG"] / 60)
        .assign(SCORE_PER_DAG=lambda x: (x["SCORE_PER_DAG"].fillna(0).round(2) * 100))
    )

    # add rows for missing DATE_START until today
    all_dates = pd.date_range(
        start=df_per_day["DATE_START"].min(),
        end=datetime.now().strftime("%Y-%m-%d"),
    )

    # check which dates are not in df_per_day and add them with MIN_PER_DAG=0
    existing_dates = set(pd.to_datetime(df_per_day["DATE_START"]).dt.date)
    missing_dates = set(all_dates.date) - existing_dates

    for date in missing_dates:
        df_per_day = pd.concat(
            [
                df_per_day,
                pd.DataFrame(
                    [{"DATE_START": date, "SEC_PER_DAG": 0, "MIN_PER_DAG": 0}]
                ),
            ],
            ignore_index=True,
        )
        
    df_calendar = (
            df_per_day.assign(DATE_START=pd.to_datetime(df_per_day["DATE_START"]))
            .assign(WEEKDAY=lambda x: x["DATE_START"].dt.day_name())
            # translate weekday to dutch
            .replace(
                {
                    "WEEKDAY": {
                        "Monday": "Maandag",
                        "Tuesday": "Dinsdag",
                        "Wednesday": "Woensdag",
                        "Thursday": "Donderdag",
                        "Friday": "Vrijdag",
                        "Saturday": "Zaterdag",
                        "Sunday": "Zondag",
                    }
                }
            )
            # change to categorical with ordered categories
            .assign(WEEKDAY=lambda x: pd.Categorical(x["WEEKDAY"], ordered=True, categories=["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]))
    )
    


    if display == "score":
        df_calendar = (df_calendar      
            .assign(
                TEXT=lambda x: 
                "score: "
                + x["SCORE_PER_DAG"].fillna(0).apply(lambda y: str(int(y)))
                + "%"
            )
            .assign(WEEK=lambda x: x["DATE_START"].dt.isocalendar().week)
            .assign(
                MONDAY_DATE=lambda x: x["DATE_START"]
                - pd.to_timedelta(x["DATE_START"].dt.weekday, unit="D")
            )
            .assign(YEAR=lambda x:x["DATE_START"].dt.isocalendar().year)
            .assign(
                WEEK_LABEL=lambda x: x["YEAR"].astype(str) + " Week "    
                + x["WEEK"].astype(str)
                + " ("
                + x["MONDAY_DATE"].dt.strftime("%d/%m")
                + ")"
            )
            .groupby(["WEEK_LABEL", "WEEKDAY"], observed=True)
            .agg(TEXT=("TEXT", "first"))
            .reset_index()
            .pivot(index="WEEK_LABEL", columns="WEEKDAY", values="TEXT")
        )
    elif display == "duration":
        df_calendar['MIN_PER_DAG'] = "Tijd: " + np.ceil(df_calendar['MIN_PER_DAG']).astype(int).astype(str) + " min"
        df_calendar['WEEKSTART'] = df_calendar['DATE_START'] - pd.to_timedelta(df_calendar['DATE_START'].dt.weekday, unit='D')
        df_calendar = df_calendar.sort_values('WEEKSTART')
        df_calendar = df_calendar.pivot(index="WEEKSTART", columns="WEEKDAY", values="MIN_PER_DAG")
        df_calendar = df_calendar.reset_index()
        df_calendar['WEEKSTART'] = df_calendar['WEEKSTART'].dt.strftime("%d %b'%y")
        df_calendar.set_index('WEEKSTART', inplace=True)

    # Reorder columns to maintain proper weekday order 
    weekday_order = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    existing_weekdays = [day for day in weekday_order if day in df_calendar.columns]
    df_calendar = df_calendar[existing_weekdays]

    # Apply styling to the DataFrame
    df_calendar_styled = df_calendar.style.map(highlight_cells)
    return df_calendar_styled

def generate_level_chart(df_scores, user=None):
    print_function("generate_level_chart()")
    # create a table with header and 20 rows. Each rows shows level from 1 to 20.
    # it has these columns: Level, Wat moet je kunnen?, Pokemon
    # Rank	Pokémon	Type(s)	Level
    # 1	Mewtwo	Psychic	100
    # 2	Rayquaza	Dragon / Flying	95
    # 3	Garchomp	Dragon / Ground	90
    # 4	Metagross	Steel / Psychic	88
    # 5	Tyranitar	Rock / Dark	85
    # 6	Dragonite	Dragon / Flying	83
    # 7	Salamence	Dragon / Flying	80
    # 8	Gyarados	Water / Flying	78
    # 9	Lucario	Fighting / Steel	75
    # 10	Arcanine	Fire	72
    # 11	Alakazam	Psychic	70
    # 12	Gengar	Ghost / Poison	68
    # 13	Scizor	Bug / Steel	65
    # 14	Greninja	Water / Dark	63
    # 15	Charizard	Fire / Flying	60
    # 16	Machamp	Fighting	58
    # 17	Jolteon	Electric	55
    # 18	Snorlax	Normal	52
    # 19	Lapras	Water / Ice	50
    #  19	Lapras	Water / Ice	50
    # 20	Pikachu	Electric	45
    
    level_info = get_level_info()
    
    # transform to dataframe
    df_level = pd.DataFrame.from_dict(
        level_info,
        orient="index",
        columns=["idx","Level", "Wat moet je kunnen om deze Pokemon te krijgen?", "Pokémon","Wat meer uitleg over jouw Pokemon 😊"],
    ).reset_index(drop=True)
    
    # add an image placeholder in the dataframe called 'Image'
    df_level["Afbeelding"] = df_level["Pokémon"].apply(
        lambda name: "https://img.pokemondb.net/artwork/large/giratina-altered.jpg" if name == "Giratina" else f"https://img.pokemondb.net/artwork/large/{name.lower()}.jpg"
    )
    
    
    df_level = df_level[["idx","Level", "Wat moet je kunnen om deze Pokemon te krijgen?", "Pokémon","Afbeelding","Wat meer uitleg over jouw Pokemon 😊"]]
    
    # afbeelding leeg indien level = False
    user_level_dict = calculate_level()
    for idx, row in df_level.iterrows():
        level_num = row["idx"]
        if user_level_dict.get(level_num, False):
            continue
        else:
            df_level.at[idx, "Afbeelding"] = ""
    
    df_level = df_level.drop(columns=["idx"])
    
    return df_level

def calculate_level():
    print_function("calculate_level()")    
    df = read_score_df(user=st.session_state.user)
    level_0 = True
    if df.empty:
        level_1 = False; level_2 = False; level_3 = False; level_4 = False; level_5 = False; level_6 = False; level_7 = False; level_8 = False; level_9 = False;
        level_10 = False; level_11 = False; level_12 = False; level_13 = False; level_14 = False; level_15 = False; level_16 = False; level_17 = False; level_18 = False;
        level_19 = False; level_20 = False; level_21 = False; level_22 = False; level_23 = False; level_24 = False; level_25 = False; level_26 = False; level_27 = False;
        level_28 = False; level_29 = False; level_30 = False; level_31 = False; level_32 = False; level_33 = False; level_34 = False; level_35 = False; level_36 = False; level_37 = False;
        level_38 = False; level_39 = False; level_40 = False;level_39 = False; level_40 = False;level_41 = False; level_42 = False; level_43 = False; level_44 = False; level_45 = False; level_46 = False; 
        level_47 = False; level_48 = False; level_49 = False
    else:
        
        df_tmp = (df 
            .groupby(["DATETIME_START","DIFFICULTY_LEVEL","TAFELS_IN_OEF","TYPE_EXERCISE"], as_index=False)
            .agg(N_EXERCISES=("EXERCISE_IDX", "count"), TOTAL_SCORE=("SCORE", "sum"), TOTAL_MINUTES=("DURATION_TIME", "sum"))
            .query("N_EXERCISES>=20 and TOTAL_SCORE>=20 and DIFFICULTY_LEVEL!='Makkelijk' and TYPE_EXERCISE=='vermenigvuldiging'")
            )
        
        df_tmp["LEN_TAFELS_IN_OEF"] = df_tmp["TAFELS_IN_OEF"].apply(lambda x: len(x.split(",")))
        
        df_tmp_deling = (df 
            .groupby(["DATETIME_START","DIFFICULTY_LEVEL","TAFELS_IN_OEF","TYPE_EXERCISE"], as_index=False)
            .agg(N_EXERCISES=("EXERCISE_IDX", "count"), TOTAL_SCORE=("SCORE", "sum"), TOTAL_MINUTES=("DURATION_TIME", "sum"))
            .query("N_EXERCISES>=20 and TOTAL_SCORE>=20 and TOTAL_MINUTES<=120 and TYPE_EXERCISE=='deling'")
            )
        
        df_tmp_deling["LEN_TAFELS_IN_OEF"] = df_tmp_deling["TAFELS_IN_OEF"].apply(lambda x: len(x.split(",")))

        level_1 = len(df_tmp.query("TAFELS_IN_OEF=='2' and TOTAL_MINUTES<=120")) > 0
        level_2 = len(df_tmp.query("TAFELS_IN_OEF=='3' and TOTAL_MINUTES<=120")) > 0
        level_3 = len(df_tmp.query("TAFELS_IN_OEF=='4' and TOTAL_MINUTES<=120")) > 0
        level_4 = len(df_tmp.query("TAFELS_IN_OEF=='5' and TOTAL_MINUTES<=120")) > 0
        level_5 = len(df_tmp.query("TAFELS_IN_OEF=='6' and TOTAL_MINUTES<=120")) > 0
        level_6 = len(df_tmp.query("TAFELS_IN_OEF=='7' and TOTAL_MINUTES<=120")) > 0
        level_7 = len(df_tmp.query("TAFELS_IN_OEF=='8' and TOTAL_MINUTES<=120")) > 0
        level_8 = len(df_tmp.query("TAFELS_IN_OEF=='9' and TOTAL_MINUTES<=120")) > 0
        level_9 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=2 and TOTAL_MINUTES<=120")) > 0
        level_10 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=3 and TOTAL_MINUTES<=120")) > 0
        level_11 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=5 and TOTAL_MINUTES<=120")) > 0
        level_12 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=7 and TOTAL_MINUTES<=120")) > 0
        level_13 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=120")) > 0
        level_14 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=108")) > 0
        level_15 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=90")) > 0
        level_16 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=72")) > 0
        level_17 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=60")) > 0
        level_18 = len(df_tmp.query("TAFELS_IN_OEF=='6' and TOTAL_MINUTES<=105")) > 0
        level_19 = len(df_tmp.query("TAFELS_IN_OEF=='7' and TOTAL_MINUTES<=105")) > 0
        level_20 = len(df_tmp.query("TAFELS_IN_OEF=='8' and TOTAL_MINUTES<=105")) > 0
        level_21 = len(df_tmp.query("TAFELS_IN_OEF=='6,7,8' and TOTAL_MINUTES<=120")) > 0
        level_22 = len(df_tmp.query("TAFELS_IN_OEF=='6,7,8' and TOTAL_MINUTES<=105")) > 0
        level_23 = len(df_tmp.query("TAFELS_IN_OEF=='6' and TOTAL_MINUTES<=90 and DIFFICULTY_LEVEL=='Moeilijk'")) > 0
        level_24 = len(df_tmp.query("TAFELS_IN_OEF=='7' and TOTAL_MINUTES<=90 and DIFFICULTY_LEVEL=='Moeilijk'")) > 0
        level_25 = len(df_tmp.query("TAFELS_IN_OEF=='8' and TOTAL_MINUTES<=90 and DIFFICULTY_LEVEL=='Moeilijk'")) > 0
        level_26 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=90 and DIFFICULTY_LEVEL=='Moeilijk'")) > 0
        level_27 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=75 and DIFFICULTY_LEVEL=='Moeilijk'")) > 0
        
        # delingen
        level_28 = len(df_tmp_deling.query("TAFELS_IN_OEF=='2' and TOTAL_MINUTES<=120")) > 0
        level_29 = len(df_tmp_deling.query("TAFELS_IN_OEF=='3' and TOTAL_MINUTES<=120")) > 0
        level_30 = len(df_tmp_deling.query("TAFELS_IN_OEF=='4' and TOTAL_MINUTES<=120")) > 0
        level_31 = len(df_tmp_deling.query("TAFELS_IN_OEF=='5' and TOTAL_MINUTES<=120")) > 0
        level_32 = len(df_tmp_deling.query("TAFELS_IN_OEF=='6' and TOTAL_MINUTES<=120")) > 0
        level_33 = len(df_tmp_deling.query("TAFELS_IN_OEF=='7' and TOTAL_MINUTES<=120")) > 0
        level_34 = len(df_tmp_deling.query("TAFELS_IN_OEF=='8' and TOTAL_MINUTES<=120")) > 0
        level_35 = len(df_tmp_deling.query("TAFELS_IN_OEF=='9' and TOTAL_MINUTES<=120")) > 0
        level_36 = len(df_tmp_deling.query("LEN_TAFELS_IN_OEF>=3 and TOTAL_MINUTES<=120")) > 0
        level_37 = len(df_tmp_deling.query("LEN_TAFELS_IN_OEF>=5 and TOTAL_MINUTES<=120")) > 0
        level_38 = len(df_tmp_deling.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=120")) > 0
        level_39 = len(df_tmp_deling.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=105")) > 0
        level_40 = len(df_tmp_deling.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=90")) > 0
        level_41 = len(df_tmp_deling.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=75")) > 0
        level_42 = len(df_tmp_deling.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=60")) > 0
        
        # veel oefeningen in korte tijd
        level_43 = len(df_tmp.query("N_EXERCISES==40 and TOTAL_SCORE==40 and LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=180")) > 0
        level_44 = len(df_tmp.query("N_EXERCISES==50 and TOTAL_SCORE==50 and LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=300")) > 0
        level_45 = len(df_tmp.query("N_EXERCISES==50 and TOTAL_SCORE==50 and LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=200")) > 0
        level_46 = len(df_tmp.query("N_EXERCISES==50 and TOTAL_SCORE==50 and LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=150")) > 0
        
        level_47 = len(df_tmp.query("N_EXERCISES==100 and TOTAL_SCORE==100 and LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=300")) > 0
        level_48 = len(df_tmp_deling.query("N_EXERCISES==100 and TOTAL_SCORE==100 and LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=300")) > 0

        # arceus  
        level_49 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=45")) > 0

    return {
        0: level_0,
        1: level_1,
        2: level_2,
        3: level_3,
        4: level_4,
        5: level_5,
        6: level_6,
        7: level_7,
        8: level_8,
        9: level_9,
        10: level_10,
        11: level_11,
        12: level_12,
        13: level_13,
        14: level_14,
        15: level_15,
        16: level_16,
        17: level_17,
        18: level_18,
        19: level_19,
        20: level_20,
        21: level_21,
        22: level_22,
        23: level_23,
        24: level_24,
        25: level_25,
        26: level_26,
        27: level_27,
        28: level_28,
        29: level_29,
        30: level_30,
        31: level_31,
        32: level_32,
        33: level_33,
        34: level_34,
        35: level_35,
        36: level_36,
        37: level_37,
        38: level_38,
        39: level_39,
        40: level_40,
        41: level_41,
        42: level_42,
        43: level_43,
        44: level_44,
        45: level_45,
        46: level_46,
        47: level_47,
        48: level_48,
        49: level_49
    }

def get_all_pokemons():
    print_function("get_all_pokemons()")

    level_dict = calculate_level()
    pokemon = ["Magikarp"]
    level_info = get_level_info()
    
    for level, achieved in level_dict.items():
        if achieved:
            pokemon.append(level_info[level][3])
            
    pokemon_list = []
    for iter_pokemon in pokemon:
        if iter_pokemon not in pokemon_list:
            pokemon_list.append(iter_pokemon)

    return pokemon_list


@st.fragment
def render_pokemon_header(target, pokemon_list):
    with target.container():
        st.write("Jouw verzamelde Pokemons:")
        if pokemon_list:
            pokemon_per_row = 13
            for i in range(0, len(pokemon_list), pokemon_per_row):
                cols = st.columns(pokemon_per_row)
                for j, pokemon in enumerate(pokemon_list[i:i+pokemon_per_row]):
                    with cols[j]:
                        if pokemon != "Giratina":
                            # small font caption
                            st.markdown(f"<div style='font-size: 8px;'>{pokemon}</div>", unsafe_allow_html=True)
                            st.image(f"https://img.pokemondb.net/artwork/large/{pokemon.lower()}.jpg", width=70)
                        else: 
                            st.markdown(f"<div style='font-size: 8px;'>{pokemon}</div>", unsafe_allow_html=True)
                            st.image(f"https://img.pokemondb.net/artwork/large/giratina-altered.jpg", width=70)

            st.markdown(
                """
                <style>
                img {
                border: 2px solid #ccc;
                border-radius: 8px;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
        st.markdown("<div style='font-size: 12px; color: grey;'>Ga naar 'Level' om te zien welke Pokémons je hebt verdiend en wat je nog moet doen om de volgende te krijgen!</div>", unsafe_allow_html=True)
        st.write("") 


def get_pokemon_hover_text(pokemon):
    level_info = get_level_info()
    # get row where pokemon matches 
    hover_text = ""
    for level, info in level_info.items():
        if info[3] == pokemon:
            hover_text = f"Level {info[0]}: {info[2]} - Pokémon: {info[3]}"
            break
    return hover_text

def get_level_info():
    print_function("get_level_info()")

    level_info = {
        0: (0, 0, "Beginner: Geen oefeningen voltooid", "Magikarp", "Zwakke vis-Pokémon die bijna niets kan, maar evolueert in de machtige Gyarados."),
        1: (1, 45, "Tafel van 2: 20 oefeningen juist in 2 minuten", "Pikachu", "Bekende mascotte van Pokémon; gebruikt elektrische aanvallen zoals Thunderbolt."),
        2: (2, 50, "Tafel van 3: 20 oefeningen juist in 2 minuten", "Lapras", "Zachtaardige zeepokémon die mensen vaak over zee vervoert."),
        2: (2, 50, "Tafel van 3: 20 oefeningen juist in 2 minuten", "Lapras", "Zachtaardige zeepokémon die mensen vaak over zee vervoe5t."),
        3: (3, 52, "Tafel van 4: 20 oefeningen juist in 2 minuten", "Snorlax", "Grote, luie Pokémon die meestal slaapt maar enorm sterk is."),
        4: (4, 55, "Tafel van 5: 20 oefeningen juist in 2 minuten", "Jolteon", "Snel en dodelijk elektrisch type met razendsnelle aanvallen."),
        5: (5, 58, "Tafel van 6: 20 oefeningen juist in 2 minuten", "Machamp", "Vierarmige vechter met brute fysieke kracht en hoge aanval."),
        6: (6, 60, "Tafel van 7: 20 oefeningen juist in 2 minuten", "Charizard", "Iconische vuurspuwende draak, populair in zowel games als anime."),
        7: (7, 63, "Tafel van 8: 20 oefeningen juist in 2 minuten", "Greninja", "Ninja-kikker met hoge snelheid en slimme tactieken."),
        8: (8, 65, "Tafel van 9: 20 oefeningen juist in 2 minuten", "Scizor", "Evolutie van Scyther; combineert kracht en verdediging met metalen klauwen."),
        9: (9, 68, "2 verschillende tafels: 20 oefeningen juist in 2 minuten", "Gengar", "Ondeugende schaduw die vijanden bang maakt en energie steelt."),
        10: (10, 70, "3 verschillende tafels: 20 oefeningen juist in 2 minuten", "Alakazam", "Extreem intelligente Pokémon met telekinetische krachten."),
        11: (11, 72, "5 verschillende tafels: 20 oefeningen juist in 2 minuten", "Arcanine", "Edele, snelle Pokémon die bekendstaat als de Legendarische Hond."),
        12: (12, 75, "7 verschillende tafels: 20 oefeningen juist in 2 minuten", "Lucario", "Aura-meester die energie van anderen kan voelen en manipuleren."),
        13: (13, 78, "Alle tafels tot 9: 20 oefeningen juist in 2 minuten", "Gyarados", "Woeste zeedraak die uit Magikarp evolueert en vernietigend sterk is."),
        14: (14, 80, "Alle tafels tot 9: 20 oefeningen juist in 1 minuut en 48 seconden", "Salamence", "Machtige draak die zijn droom om te vliegen waarmaakt."),
        15: (15, 83, "Alle tafels tot 9: 20 oefeningen juist in 1 minuut en 30 seconden", "Dragonite", "Goedaardige draak die verrassend vriendelijk is ondanks zijn kracht."),
        16: (16, 85, "Alle tafels tot 9: 20 oefeningen juist in 1 minuut en 12 seconden", "Tyranitar", "Gigantische en agressieve Pokémon die bergen kan verplaatsen."),
        17: (17, 88, "Alle tafels tot 9: 20 oefeningen juist in 1 minuut", "Metagross", "Superintelligente Pokémon met een computerachtig brein en enorme kracht."),
        18: (18, 89, "Tafel van 6: 20 oefeningen juist in 1 minuut en 45 seconden", "Garchomp", "Supersnelle draak die bliksemsnel toeslaat met vernietigende kracht."),
        19: (19, 90, "Tafel van 7: 20 oefeningen juist in 1 minuut en 45 seconden", "Hydreigon", "Driekoppige draak die alles verwoest wat hij niet vertrouwt."),
        20: (20, 91, "Tafel van 8: 20 oefeningen juist in 1 minuut en 45 seconden", "Darkrai", "Schimmige Pokémon die nachtmerries veroorzaakt bij zijn tegenstanders."),
        21: (21, 92, "Tafels van 6,7,8: 20 oefeningen juist in 2 minuten", "Rayquaza", "Legendarische draak die de balans bewaart tussen land en zee."),
        22: (22, 93, "Tafels van 6,7,8: 20 oefeningen juist in 1 minuut en 45 seconden", "Mewtwo", "Genetisch gecreëerde super-Pokémon met ongeëvenaarde psychische kracht."),
        23: (23, 94, "Tafel van 6: 20 moeilijke oefeningen juist in 1 minuut en 30 seconden", "Zacian","Legendarische zwaard-Pokémon die ongekende aanvalskracht bezit en moeiteloos draken kan verslaan."),
        24: (24, 95, "Tafel van 7: 20 moeilijke oefeningen juist in 1 minuut en 30 seconden", "Eternatus","Reusachtige Pokémon van buiten de wereld, bron van oneindige energie en Dynamax-kracht."),
        25: (25, 96, "Tafel van 8: 20 moeilijke oefeningen juist in 1 minuut en 30 seconden", "Lugia","Bewaker van de zeeën, met vleugels die stormen kunnen kalmeren of ontketenen."),
        26: (26, 97, "Alle tafels tot 9: 20 moeilijke oefeningen juist in 1 minuut en 30 seconden", "Giratina","Heerser van de omgekeerde wereld, die balans houdt tussen leven en dood."),
        27: (27, 98, "Alle tafels tot 9: 20 moeilijke oefeningen juist in 1 minuut en 15 seconden", "Ho-Oh","Mythische regenboogvogel die geluk brengt en herboren zielen tot leven wekt."),
        # 15 nieuwe pokémon — allemaal minder krachtig dan Arceus
        28: (28, 100, "Deling van 2: 20 oefeningen juist in 2 minuten", "Blaziken", "Vuur/Vecht Pokémon die bekendstaat om zijn snelheid en krachtige kicks."),
        29: (29, 102, "Deling van 3: 20 oefeningen juist in 2 minuten", "Infernape", "Razendsnelle vechter die fysieke en speciale aanvallen combineert."),
        30: (30, 104, "Deling van 4: 20 oefeningen juist in 2 minuten", "Swampert", "Water/Aarde Pokémon die sterk is tegen vele types."),
        31: (31, 106, "Deling van 5: 20 oefeningen juist in 2 minuten", "Sceptile", "Supersnelle gras-Pokémon die vlijmscherpe bladeren gebruikt."),
        32: (32, 108, "Deling van 6: 20 oefeningen juist in 2 minuten", "Aegislash", "Zwaard/Pantserschild Pokémon die tussen aanval en verdediging wisselt."),
        33: (33, 110, "Deling van 7: 20 oefeningen juist in 2 minuten", "Goodra", "Lieve maar taaie draak met enorme speciale verdediging."),
        34: (34, 112, "Deling van 8: 20 oefeningen juist in 2 minuten", "Volcarona", "Vuur/BUG Pokémon die vlammenscènes kan creëren met zijn vleugels."),
        35: (35, 114, "Deling van 9: 20 oefeningen juist in 2 minuten", "Milotic", "Elegante water-Pokémon met sterke verdediging en charme."),
        36: (36, 116, "Deling van 3 verschillende tafels: 20 oefeningen juist in 2 minuten", "Haxorus", "Bijtende draak met brute fysieke kracht."),
        37: (37, 118, "Deling van 5 verschillende tafels: 20 oefeningen juist in 2 minuten", "Weavile", "Slijmsnelle ijs/donker Pokémon die scherpe klauwen gebruikt."),
        38: (38, 120, "Deling van alle tafels: 20 oefeningen juist in 2 minuten", "Excadrill", "Metaalmol met enorme aanvalskracht onder de grond."),
        39: (39, 122, "Deling van alle tafels: 20 oefeningen juist in 1 minuut en 45 seconden", "Gliscor", "Vliegende schorpioen met hoge mobiliteit en taaiheid."),
        40: (40, 124, "Deling van alle tafels: 20 oefeningen juist in 1 minuut en 30 seconden", "Roserade", "Giftige rozen die verrassend hard toeslaan."),
        41: (41, 126, "Deling van alle tafels: 20 oefeningen juist in 1 minuut en 15 seconden", "Ninetales", "IJs/fee Pokémon met sierlijke maar gevaarlijke aanvallen."),
        42: (42, 128, "Deling van alle tafels: 20 oefeningen juist in 1 minuut", "Dragapult", "Supersnelle draak/spook Pokémon die Dreepies als projectielen lanceert."),
        
         # veel oefeningen in korte tijd
        # level_43 = len(df_tmp.query("N_EXERCISES>=40 and TOTAL_SCORE>=40 andLEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=180")) > 0
        # level_44 = len(df_tmp.query("N_EXERCISES>=50 and TOTAL_SCORE>=50 andLEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=300")) > 0
        # level_45 = len(df_tmp.query("N_EXERCISES>=50 and TOTAL_SCORE>=50 andLEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=200")) > 0
        # level_46 = len(df_tmp.query("N_EXERCISES>=50 and TOTAL_SCORE>=50 andLEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=150")) > 0
       
        
        # veel oefeningen in korte tijd
        43: (43, 140, "Alle tafels tot 9: 40 oefeningen juist in 3 minuten",
             "Latios", 
             "Snelle en intelligente draak/Psychic Pokémon die razendsnelle speciale aanvallen gebruikt."),

        44: (44, 160, "Alle tafels tot 9: 50 oefeningen juist in 5 minuten", 
             "Latias", 
             "Elegante draak/Psychic Pokémon met sterke verdediging en beschermende krachten."),

        45: (45, 180, "Alle tafels tot 9: 50 oefeningen juist in 3 minuten en 20 seconden", 
             "Regigigas", 
             "Titanische Pokémon met overweldigende fysieke kracht die hele landschappen kan verplaatsen."),

        46: (46, 200, "Alle tafels tot 9: 50 oefeningen juist in 2 minuten en 30 seconden", 
             "Necrozma", 
             "Lichtabsorberende ultra-Pokémon die verwoestende energieaanvallen kan ontketenen."),
        
        47: (47, 220, "Alle tafels tot 9: 100 oefeningen juist in 5 minuten", "Charizard-Mega-X", "Vuurloze draakvorm met extreme fysieke kracht en meedogenloze aanvallen die alles op zijn pad verbrandt met pure woede."),
        
        48: (48, 240, "Alle deeltafels tot 9: 100 oefeningen juist in 5 minuten", "Palkia", "Legendarische Pokémon die ruimte en dimensies beheerst en stabiliteit brengt in een uitgestrekte wereld."),

        # Arceus verplaatst naar 43    
        49: (49, 720, "Alle tafels tot 9: 20 oefeningen juist in 45 seconden", "Arceus", "De God van alle Pokémon; schepper van het Pokémon-universum."),
    }

    return level_info

def get_difficult_exercises(user, starttime):
    print_function(f"get_difficult_exercises(user={user}, starttime={starttime})")
    df = read_score_df(user=user)
    df_filtered = df[(df["NAME"] == user) & (pd.to_datetime(df["DATETIME_START"]).dt.strftime("%Y-%m-%d %H:%M:%S") == pd.to_datetime(starttime).strftime("%Y-%m-%d %H:%M:%S"))]
    
    df_wrong_answers = df_filtered[df_filtered.SCORE<1]
    
    if not df_wrong_answers.empty:
        if df_wrong_answers.iloc[0]['TYPE_EXERCISE'] == 'vermenigvuldiging':
            type_signal = ' x '
            
            df_wrong_answers = df_wrong_answers.rename(columns={"X1": "RAND_NUM", "X2": "TAFEL", "USER_ANSWER": "USER_ANSWER"})
            
            df_wrong_answers = df_wrong_answers.assign(ANSWER=lambda x: (x["TAFEL"]*x["RAND_NUM"]).astype(str))
            
            list_correct_answers = df_wrong_answers.assign(EXERCISE=lambda x: x["RAND_NUM"].astype(str) + type_signal + x["TAFEL"].astype(str) + " = " + x["ANSWER"].astype(str))["EXERCISE"].tolist()
            
            list_wrong_answers = df_wrong_answers.assign(EXERCISE=lambda x: x["RAND_NUM"].astype(str) + type_signal + x["TAFEL"].astype(str) + " = " + x["USER_ANSWER"].astype(str))["EXERCISE"].tolist()
            
        elif df_wrong_answers.iloc[0]['TYPE_EXERCISE'] == 'deling':
            type_signal = " : "
            
            # df_wrong_answers = df_wrong_answers.rename(columns={"X1": "RAND_NUM", "X2": "TAFEL", "USER_ANSWER": "RAND_NUM"})
            
            df_wrong_answers = df_wrong_answers.assign(ANSWER=lambda x: (x["RAND_NUM"]/x["TAFEL"]).astype(str))
            
            list_correct_answers = df_wrong_answers.assign(EXERCISE=lambda x: x["RAND_NUM"].astype(str) + type_signal + x["TAFEL"].astype(str) + " = " + x["ANSWER"].astype(float).astype(int).astype(str))["EXERCISE"].tolist()
            
            list_wrong_answers = df_wrong_answers.assign(EXERCISE=lambda x: x["RAND_NUM"].astype(str) + type_signal + x["TAFEL"].astype(str) + " = " + x["USER_ANSWER"].astype(float).astype(int).astype(str))["EXERCISE"].tolist()

        return list_correct_answers, list_wrong_answers
    
    else:
        return [], []

def plot_evolution_per_tafel(user, tafel):
    print_function(f"plot_evolution_per_tafel(user={user}, tafel={tafel})")
    # get df_scores from db and plot evoluation per day
    df_scores = read_score_df_updated_db(user="Raphael")
    # group by date and get metrics on mean score, total duration time and number of exercises done
    df_daily = (
        df_scores[df_scores["TAFEL"] == tafel]
        .groupby("DATE_START", as_index=False)
        .agg(
            MEAN_SCORE=("SCORE", "mean"),
            TOTAL_DURATION=("DURATION_TIME", "sum"),
            N_EXERCISES=("EXERCISE_IDX", "count"),
        )
        .assign(DATE_START=pd.to_datetime(df_scores["DATE_START"]))
        .sort_values("DATE_START")
    )

    # plot evolution
    def plot_mean_score():
        import plotly.express as px
        fig = px.line(
            df_daily,
            x="DATE_START",
            y="MEAN_SCORE",
            title=f"Gemiddelde score per dag voor tafel {tafel}",
            labels={"DATE_START": "Datum", "MEAN_SCORE": "Gemiddelde Score"},
        )
    
    # show plot
        st.plotly_chart(fig)

def score_per_set(df_scores):
    print_function("score_per_set(df_scores)")
    df_scores["SCORE"] = df_scores["SCORE"].apply(lambda d: 0 if d<1 else d)
    df_out = (df_scores
     .groupby(["DATE_START","TIME_START","TAFELS_IN_OEF","DIFFICULTY_LEVEL","TYPE_EXERCISE"], as_index=False)
     .agg(AANTAL_OEFENINGEN=("EXERCISE_IDX","count"), SCORE=("SCORE","sum"), TIJD=("DURATION_TIME","sum"))
     .assign(TIJD=lambda x: x["TIJD"].apply(lambda d: translate_sec_to_min_sec(d)))
     .sort_values(by=["DATE_START","TIME_START"], ascending=[False,False])
     .reset_index()
     .drop(columns=["index"])
     .assign(SCORE=lambda x:x["SCORE"].astype(int))
    )

    return df_out

def translate_sec_to_min_sec(seconds):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{int(minutes)} min {int(sec)} sec"
        
def reset_exercises():
    print_title("Settings changed")
    print_function("Reset_exercises()")

    pending_tables = st.session_state.get("pending_selected_tables", [])
    if not pending_tables:
        st.warning("Kies minstens één tafel.")
        return

    new_user  = st.session_state.get("pending_user", st.session_state.user)
    new_level = st.session_state.get("pending_difficulty_level", st.session_state.difficulty_level)
    new_type = st.session_state.get("pending_type", st.session_state.type_exercise)
    new_tables = list(pending_tables)
    new_n = int(st.session_state.get("pending_n_exercises", st.session_state.n_exercises))
    new_n = max(1, min(1000, new_n))

    # Skip heavy work when nothing changed
    if (
        new_user  == st.session_state.user
        and new_level == st.session_state.difficulty_level
        and new_tables == st.session_state.selected_tables
        and new_n == st.session_state.n_exercises
        and new_type == st.session_state.type_exercise
    ):
        return

    # Commit the new settings (these keys are NOT widget-owned)
    st.session_state.user = new_user
    st.session_state.difficulty_level = new_level
    st.session_state.selected_tables = new_tables
    st.session_state.n_exercises = new_n
    st.session_state.type_exercise = new_type
    st.session_state.df_scores = read_score_df_updated_db(user=st.session_state.user)

    reset_progress(st.session_state.n_exercises)
    (
        st.session_state.exercise,
        st.session_state.correct,
        st.session_state.x1,
        st.session_state.x2,
    ) = generate_exercise(
        st.session_state.selected_tables,
        st.session_state.difficulty_level,
        0,
        st.session_state.type_exercise,
    )
    st.session_state.last_result = None
    st.session_state.prev_exercise = None
    st.session_state.prev_correct = None
    st.session_state.reset_answer = True
    print_red(f"st.session_state.user: {st.session_state.user}")

    st.session_state.pokemon = get_all_pokemons()
    st.session_state.df_scores = read_score_df_updated_db(user=st.session_state.user)
    
    
    # st.session_state.render_pokemon = True # reset pokemon header when user has changed anhything in instellingen
    
    # render_pokemon_header(st.empty(),st.session_state.pokemon)
    # No st.rerun(): Streamlit reruns automatically after on_change.


def plot_progress(df, displaytype='SCORE'):
    # df = read_score_df(user=st.session_state.user)
    df_plot = (
        df
        .assign(SCORE=lambda x: x["SCORE"].mask(x["SCORE"] < 1, 0))
        .groupby(["DATE_START", "TAFEL"])
        .agg(SCORE=("SCORE", "sum"), TIJD=("DURATION_TIME", "mean"), N=("DURATION_TIME", "count"))
        .assign(SCORE_PERC=lambda x: x["SCORE"] / x["N"])
        .assign(SCORE_LABEL=lambda x: x["SCORE_PERC"].apply(lambda d: f"{d * 100:.0f}%"))
        .assign(DURATION_TIME_LABEL=lambda x: x["TIJD"].apply(lambda d: f"{d:.0f}sec"))
        .reset_index()
        .assign(TAFEL=lambda x: pd.Categorical(x["TAFEL"], categories=[2, 3, 4, 5, 6, 7, 8, 9], ordered=True))
        .drop(columns=["SCORE"])
    )

    # chose between SCORE and DURATION_TIME
    if displaytype == 'SCORE':

        fig=(
            px.line(df_plot, x="DATE_START", y="SCORE_PERC", color="TAFEL", text="SCORE_LABEL", title="Vooruitgang voor elke tafel",
                    markers=True,color_discrete_sequence=px.colors.qualitative.Set2, category_orders={"TAFEL":[2,3,4,5,6,7,8,9]},
                    facet_col="TAFEL", facet_col_wrap=1,template="simple_white")
                .update_traces(
                    textposition="top center",
                    textfont_size=10,
                    mode="lines+markers+text"
                )
                # .update_layout(xaxis_title="Datum", yaxis_title="Score", height=2000)
                # .update_yaxes(range=[0,1.2])
                .update_xaxes(showticklabels=True, title_text="Datum")
                .update_yaxes(title_text="Score")
                .update_layout(height=2000, showlegend=False)
            )

        # margin for y axis max to display text
        if not df_plot.empty:
            y_max = float(df_plot["SCORE_PERC"].max())
            y_min = float(df_plot["SCORE_PERC"].min())
            fig.update_yaxes(range=[y_min*0.8, y_max * 1.2])

    if displaytype == 'DURATION_TIME':

        fig = (
            px.line(df_plot, x="DATE_START", y="TIJD", color="TAFEL", text="DURATION_TIME_LABEL",
                    title="Vooruitgang voor elke tafel",
                    markers=True, color_discrete_sequence=px.colors.qualitative.Set2,
                    category_orders={"TAFEL": [2, 3, 4, 5, 6, 7, 8, 9]},
                    facet_col="TAFEL", facet_col_wrap=1,
                    template="simple_white")
            .update_traces(
                textposition="top center",
                textfont_size=10,
                mode="lines+markers+text"
            )
            # .update_layout(xaxis_title="Datum", yaxis_title="Tijd", height=2000)
            .update_xaxes(showticklabels=True, title_text="Datum")
            .update_yaxes(title_text="Tijd")
            .update_layout(height=2000, showlegend=False)
        )

        # margin for y axis max to display text
        if not df_plot.empty:
            y_max = float(df_plot["TIJD"].max())
            y_min = float(df_plot["TIJD"].min())
            fig.update_yaxes(range=[y_min*0.8, y_max*1.2])

    return fig

def plot_avg_time_per_maaltafel_evolution(avg_time_table):
    print_function("plot_avg_time_per_maaltafel_evolution()")

    # Filter out NaN values before plotting
    avg_time_table_filtered = avg_time_table.dropna(subset=["gemiddelde_tijd_per_tafel"])
    
    fig = px.line(
        avg_time_table_filtered,
        x="DATE_START",
        y="gemiddelde_tijd_per_tafel",
        labels={"DATE_START": "Datum", "AVG_TIME_PER_MAALTAFEL": "Gemiddelde tijd per maaltafel (sec)"},
        markers=True,
        # line color = branded color blue
        color_discrete_sequence=["#1f77b4"]
    )

    fig.update_traces(
        textposition="top center",
        textfont_size=10,
        mode="lines+markers+text"
    )

    fig.update_xaxes(showticklabels=True, title_text="Datum")
    fig.update_yaxes(title_text="Gemiddelde tijd per maaltafel (sec)")
    
    # add text on top of the marker
    fig.update_traces(text=avg_time_table_filtered["gemiddelde_tijd_per_tafel"].round(2).astype(str))

    return fig