import random
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import re

# from dotenv import load_dotenv
from supabase import create_client, Client

# load_dotenv()
# url = os.getenv("SUPABASE_URL")
# key = os.getenv("SUPABASE_ANON_KEY")
# sb = create_client(url, key)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
sb = create_client(url, key)

# DATA_PATH = "data"
# SCORE_FILE = os.path.join(DATA_PATH, "scores.csv")


def generate_exercise(accepted_products, level, exercise_idx):
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

    return exercise_string, correct_answer, random_accepted_product, random_number


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
    print(f"Oefening nr: {exercise_counter}")
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


# def read_score_df():
#     """Read current score DataFrame from CSV."""
#     if os.path.exists(SCORE_FILE):
#         df = pd.read_csv(SCORE_FILE, sep=";")
#     else:
#         df = init_score_df()
#     return df


# def save_score_df(df):
#     """Save current score DataFrame to CSV."""
#     os.makedirs(DATA_PATH, exist_ok=True)
#     df.to_csv(SCORE_FILE, index=False, sep=";")


def read_score_df(user="Raphael",user_id=None, limit=100000):
    """Read scores from Supabase (filtered by user_id if provided)."""
    try:
        query = sb.table("results").select("*").eq("name", user).order("datetime_start", desc=True)
        if user_id:
            query = query.eq("user_id", user_id)
        res = query.limit(limit).execute()
        data = res.data or []
        if not data:
            print("No data found in Supabase, returning empty DataFrame.")
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # make all column names uppercase
        df.columns = [col.upper() for col in df.columns]
        df = df[df["NAME"] == user]
        return df
    except Exception as e:
        print(f"Error reading from Supabase: {e}")
        return pd.DataFrame()

    

def add_answer_row_to_db():
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
    }

    response = sb.table("results").insert(row).execute()

    print(f"SUCCES - Toegevoegd aan DB: {response.data}")


def save_score_df(df, user_id=None):
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



def add_prob(df):
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
    df = read_score_df(user=st.session_state.user)
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


def restart():
    st.session_state.pokemon = get_all_pokemons()
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
    ) = generate_exercise(st.session_state.selected_tables, st.session_state.difficulty_level, 0)
    st.session_state.exercise_counter = 0
    st.session_state.last_result = None
    st.rerun()
    render_progress()


def init_session_state(generate_exercise, reset_progress):
    defaults = {
        "user": "Raphael",
        "difficulty_level": "Moeilijk",
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
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # dependent inits
    if "progress" not in st.session_state:
        reset_progress(st.session_state.n_exercises)

    if "exercise" not in st.session_state:
        (
            st.session_state.exercise,
            st.session_state.correct,
            st.session_state.x1,
            st.session_state.x2,
        ) = generate_exercise(st.session_state.selected_tables, st.session_state.difficulty_level, 0)
        st.session_state.last_result = None
        st.session_state.prev_exercise = None
        st.session_state.prev_correct = None
        
    st.session_state.pokemon = get_all_pokemons()


def generate_prob_table(df):
    # display in a table that i can use in my streamlit app. cells with low values can be colored green, high values in red
    # First aggregate to handle duplicate TAFEL/RAND_NUM combinations
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


def generate_duration_table(df):
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
    # display in a table that i can use in my streamlit app. cells with low values can be colored green, high values in red
    # First aggregate to handle duplicate TAFEL/RAND_NUM combinations
    df = add_prob(df)
    pivot_table = (
        df[["TAFEL", "RAND_NUM", "SCORE"]]
        .assign(SCORE=lambda x: x["SCORE"].apply(lambda score: 1 if score == 1 else 0))
        .groupby(["TAFEL", "RAND_NUM"], as_index=False)
        .agg({"SCORE": "mean"})
        .assign(SCORE=lambda x: x["SCORE"].round(2))
        .pivot(index="TAFEL", columns="RAND_NUM", values="SCORE")
        .reset_index()  # bring TAFEL into columns so headers are on one row
    )

    # Optional: make column names ints/strings consistently for Streamlit
    pivot_table.columns = [str(c) for c in pivot_table.columns]

    # Style for Streamlit - color coding low values green, high values red
    # Apply gradient to numeric columns only; show blanks for NaN
    numeric_cols = [c for c in pivot_table.columns if c != "TAFEL"]
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
            .assign(
                WEEK_LABEL=lambda x: "Week "    
                + x["WEEK"].astype(str)
                + " ("
                + x["MONDAY_DATE"].dt.strftime("%d/%m")
                + ")"
            )
            .groupby(["WEEK_LABEL", "WEEKDAY"])
            .agg(TEXT=("TEXT", "first"))
            .reset_index()
            .pivot(index="WEEK_LABEL", columns="WEEKDAY", values="TEXT")
        )
    elif display == "duration":
        df_calendar = (df_calendar      
            .assign(
                TEXT=lambda x: "Tijd: "
                + x["MIN_PER_DAG"].apply(lambda y: str(int(np.ceil(y))))
                + " min"
            )
            .assign(WEEK=lambda x: x["DATE_START"].dt.isocalendar().week)
            .assign(
                MONDAY_DATE=lambda x: x["DATE_START"]
                - pd.to_timedelta(x["DATE_START"].dt.weekday, unit="D")
            )
            .assign(
                WEEK_LABEL=lambda x: "Week "    
                + x["WEEK"].astype(str)
                + " ("
                + x["MONDAY_DATE"].dt.strftime("%d/%m")
                + ")"
            )
            .groupby(["WEEK_LABEL", "WEEKDAY"])
            .agg(TEXT=("TEXT", "first"))
            .reset_index()
            .pivot(index="WEEK_LABEL", columns="WEEKDAY", values="TEXT")
        )

    # Apply styling to the DataFrame
    df_calendar_styled = df_calendar.style.map(highlight_cells)
    return df_calendar_styled


def generate_level_chart(df_scores, user=None):
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
    # 20	Pikachu	Electric	45
    
    level_info = get_level_info()
    
    # transform to dataframe
    df_level = pd.DataFrame.from_dict(
        level_info,
        orient="index",
        columns=["idx","Level", "Wat moet je kunnen om deze Pokemon te krijgen?", "Pokémon"],
    ).reset_index(drop=True)
    
    # add an image placeholder in the dataframe called 'Image'
    df_level["Afbeelding"] = df_level["Pokémon"].apply(
        lambda name: f"https://img.pokemondb.net/artwork/large/{name.lower()}.jpg"
        
    )
    
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
    df = read_score_df(user=st.session_state.user)
    level_0 = True
    if df.empty:
        level_1 = False; level_2 = False; level_3 = False; level_4 = False; level_5 = False; level_6 = False; level_7 = False; level_8 = False; level_9 = False; level_10 = False; level_11 = False; level_12 = False; level_13 = False; level_14 = False; level_15 = False; level_16 = False; level_17 = False; level_18 = False;  
    else:
        
        df_tmp = (df 
            .groupby(["DATETIME_START","DIFFICULTY_LEVEL","TAFELS_IN_OEF"], as_index=False)
            .agg(N_EXERCISES=("EXERCISE_IDX", "count"), TOTAL_SCORE=("SCORE", "sum"), TOTAL_MINUTES=("DURATION_TIME", "sum"))
            .query("N_EXERCISES>=20 and TOTAL_SCORE>=20 and DIFFICULTY_LEVEL!='Makkelijk' and TOTAL_MINUTES<=120")
            )
        
        df_tmp["LEN_TAFELS_IN_OEF"] = df_tmp["TAFELS_IN_OEF"].apply(lambda x: len(x.split(",")))
        
        level_1 = len(df_tmp.query("TAFELS_IN_OEF=='2'")) > 0
        level_2 = len(df_tmp.query("TAFELS_IN_OEF=='3'")) > 0
        level_3 = len(df_tmp.query("TAFELS_IN_OEF=='4'")) > 0
        level_4 = len(df_tmp.query("TAFELS_IN_OEF=='5'")) > 0
        level_5 = len(df_tmp.query("TAFELS_IN_OEF=='6'")) > 0
        level_6 = len(df_tmp.query("TAFELS_IN_OEF=='7'")) > 0
        level_7 = len(df_tmp.query("TAFELS_IN_OEF=='8'")) > 0
        level_8 = len(df_tmp.query("TAFELS_IN_OEF=='9'")) > 0
        level_9 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=2")) > 0
        level_10 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=3")) > 0
        level_11 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=5")) > 0
        level_12 = len(df_tmp.query("LEN_TAFELS_IN_OEF>=7")) > 0
        level_13 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=120")) > 0
        level_14 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=108")) > 0
        level_15 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=90")) > 0
        level_16 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=72")) > 0
        level_17 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=60")) > 0
        level_18 = len(df_tmp.query("LEN_TAFELS_IN_OEF==8 and TOTAL_MINUTES<=45")) > 0

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
    }
    
def get_highest_level_pokemon():
    level_dict = calculate_level()
    pokemon = ["Magikarp"]
    level_info = get_level_info()

    
    for level, achieved in level_dict.items():
        if achieved:
            highest_level = level
            
    # get highest level where achieved is True
    for level, achieved in level_dict.items():
        if achieved:
            highest_level = level
            pokemon = level_info[level][3]
    
    return pokemon

def get_all_pokemons():
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
    level_info = {
        0: (0, 0, "Beginner: Geen oefeningen voltooid", "Magikarp"),
        1: (1, 45, "Tafel van 2: 20 oefeningen correct in 2 minuten", "Pikachu"),
        2: (2, 50, "Tafel van 3: 20 oefeningen correct in 2 minuten", "Lapras"),
        3: (3, 52, "Tafel van 4: 20 oefeningen correct in 2 minuten", "Snorlax"),
        4: (4, 55, "Tafel van 5: 20 oefeningen correct in 2 minuten", "Jolteon"),
        5: (5, 58, "Tafel van 6: 20 oefeningen correct in 2 minuten", "Machamp"),
        6: (6, 60, "Tafel van 7: 20 oefeningen correct in 2 minuten", "Charizard"),
        7: (7, 63, "Tafel van 8: 20 oefeningen correct in 2 minuten", "Greninja"),
        8: (8, 65, "Tafel van 9: 20 oefeningen correct in 2 minuten", "Scizor"),
        9: (9, 68, "2 verschillende tafels: 20 oefeningen correct in 2 minuten", "Gengar"),
        10: (10, 70, "3 verschillende tafels: 20 oefeningen correct in 2 minuten", "Alakazam"),
        11: (11, 72, "5 verschillende tafels: 20 oefeningen correct in 2 minuten", "Arcanine"),
        12: (12, 75, "7 verschillende tafels: 20 oefeningen correct in 2 minuten", "Lucario"),
        13: (13, 78, "Alle tafels tot 9: 20 oefeningen correct in 2 minuten", "Gyarados"),
        14: (14, 80, "Alle tafels tot 9: 20 oefeningen correct in 1.8 minuten", "Salamence"),
        15: (15, 83, "Alle tafels tot 9: 20 oefeningen correct in 1.5 minuut", "Dragonite"),
        16: (16, 85, "Alle tafels tot 9: 20 oefeningen correct in 1.2 minuut", "Tyranitar"),
        17: (17, 88, "Alle tafels tot 9: 20 oefeningen correct in 1 minuut", "Metagross"),
        18: (18, 720, "Alle tafels tot 9: 20 oefeningen correct in 45 seconden", "Arceus"),
    }
    
    return level_info


def get_difficult_exercises(user, starttime):
    df = read_score_df(user=user)
    df_filtered = df[(df["NAME"] == user) & (pd.to_datetime(df["DATETIME_START"]).dt.strftime("%Y-%m-%d %H:%M:%S") == pd.to_datetime(starttime).strftime("%Y-%m-%d %H:%M:%S"))]
    
    df_wrong_answers = df_filtered[df_filtered.SCORE<1]
    df_wrong_answers = df_wrong_answers.assign(ANSWER=lambda x: (x["TAFEL"]*x["RAND_NUM"]).astype(str))
    
    list_correct_answers = df_wrong_answers.assign(EXERCISE=lambda x: x["RAND_NUM"].astype(str) + " x " + x["TAFEL"].astype(str) + " = " + x["ANSWER"].astype(str))["EXERCISE"].tolist()
    
    list_wrong_answers = df_wrong_answers.assign(EXERCISE=lambda x: x["RAND_NUM"].astype(str) + " x " + x["TAFEL"].astype(str) + " = " + x["USER_ANSWER"].astype(str))["EXERCISE"].tolist()

    return list_correct_answers, list_wrong_answers