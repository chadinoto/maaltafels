import streamlit as st
from datetime import datetime
import os
from datetime import timedelta
from functions import *
from time import time


DATA_PATH = "data"
SCORE_FILE = os.path.join(DATA_PATH, "scores.csv")


# (1) INITIALIZE DEFAULTS ----

init_session_state(generate_exercise, reset_progress)


# ✅ Reset the input BEFORE rendering the widget (and BEFORE the form)
if st.session_state.reset_answer:
    # st.session_state.user_answer_str = ""
    st.session_state.user_answer_num = None

    st.session_state.reset_answer = False


# (2) LAYOUT MAIN BODY ----
# Header section above tabs
st.write(f"Jouw verzamelde Pokemons:")
# Display unique Pokemon in rows with multiple columns but keep order
pokemon_list = st.session_state.pokemon
if pokemon_list:
    # Create rows of 10 Pokemon each
    pokemon_per_row = 10
    for i in range(0, len(pokemon_list), pokemon_per_row):
        cols = st.columns(pokemon_per_row)
        for j, pokemon in enumerate(pokemon_list[i:i+pokemon_per_row]):
            with cols[j]:
                # small font caption
                st.markdown(f"<div style='font-size: 8px;'>{pokemon}</div>", unsafe_allow_html=True)
                st.image(f"https://img.pokemondb.net/artwork/large/{pokemon.lower()}.jpg", width=70)
    
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
tabs = st.tabs(["Oefeningen", "Level","Stats"])
tab_oef, tab_level, tab_stats = tabs

# (A) TAB - OEFENINGEN ----

with tab_oef:
    # Oefeningen tab: the main exercises UI continues below
    st.subheader(f"Hallo {st.session_state.user}, klaar voor de maaltafels?")
    # (2.1) Start button ----
    col1, col2 = st.columns([1, 5])
    with col1:
        start_clicked = st.button("▶️ Start", type="secondary")
    with col2:
        st.caption(f"Start een ronde van {st.session_state.n_exercises} oefeningen.")

    if start_clicked:
        st.session_state.status = 1
        restart()

    # (2.2) Oefening generate ----
    if st.session_state.status and st.session_state.exercise_counter < st.session_state.n_exercises:
        st.write(f"Volgende oefening: **{st.session_state.exercise}**")

        # (2.3) Antwoord capture ----

        with st.form("answer_form"):
            # st.text_input(
            #     "Jouw antwoord:",
            #     key="user_answer_str",
            #     placeholder="Typ je antwoord...",
            # )
            st.number_input(
                "Jouw antwoord:",
                key="user_answer_num",
                value=None,
                step=1,
                format="%d",
                placeholder="Typ je antwoord...",
            )

            submitted = st.form_submit_button("OK")
    else:
        submitted = False

    # (2.4) Pressed OK button / pressed enter ----

    if submitted:
        # capture duration per exercise
        delta = datetime.now() - st.session_state.duration_time_start
        st.session_state.duration_time = round(delta.total_seconds(), 3)
        st.session_state.duration_time_start = datetime.now()

        # raw = st.session_state.user_answer_str.strip()
        raw = st.session_state.user_answer_num

        st.session_state.exercise_counter = st.session_state.exercise_counter + 1
        if not raw:
            st.warning("Vul eerst een antwoord in.")
        else:
            try:
                user_answer = int(raw)
                st.session_state.user_answer = user_answer
            except ValueError:
                st.error("Gebruik alleen cijfers.")
            else:
                st.session_state.prev_exercise = st.session_state.exercise
                st.session_state.prev_correct = st.session_state.correct
                st.session_state.last_result = "correct" if user_answer == st.session_state.correct else "wrong"
                # add_score_row()
                add_answer_row_to_db()
                (
                    st.session_state.exercise,
                    st.session_state.correct,
                    st.session_state.x1,
                    st.session_state.x2,
                ) = generate_exercise(st.session_state.selected_tables, st.session_state.difficulty_level, st.session_state.exercise_counter)
                # schedule clearing input on next run (don't touch the key now)
                st.session_state.reset_answer = True
                st.rerun()

    # (2.5) Voortgang ----

    # add full line
    st.markdown("---")
    update_progress(st.session_state.exercise_counter, st.session_state.last_result)
    render_progress()

    # (2.6) When finished ----
    if st.session_state.exercise_counter == st.session_state.n_exercises:
        st.session_state.df_scores = read_score_df_updated_db(user=st.session_state.user)
        st.session_state.status = 0
        st.session_state.last_result = None
        st.success(
            f"👏 Bravo {st.session_state.user}! Je oefeningen zijn allemaal afgwerkt!\nJe score is {st.session_state.score}/{st.session_state.n_exercises}"
        )
        duration_exercises = datetime.now() - st.session_state.starttime
        # if < 1minute, then in seconds, otherwise in minutes and seconds
        if duration_exercises < timedelta(minutes=1):
            st.write(f"Totale tijd: {duration_exercises.seconds} seconden.")
        else:
            minutes = duration_exercises.seconds // 60
            seconds = duration_exercises.seconds % 60
            st.write(f"Totale tijd: {minutes} minuten en {seconds} seconden.")
        
        list_correct_answers, list_wrong_answers = get_difficult_exercises(st.session_state.user, st.session_state.starttime)
        if len(list_wrong_answers) > 0:
            st.markdown("#### Voortgang")
            col1, col2 = st.columns(2)
            with col1:
                st.write("Jouw foute antwoorden:")
                for ex in list_wrong_answers:
                    st.write(f"❌ {ex}")
            with col2:
                st.write("De juiste antwoorden waren:")
                for ex in list_correct_answers:
                    st.write(f"✅ {ex}")

    if st.session_state.exercise_counter > st.session_state.n_exercises:
        restart()

    # (2.7) Controle check text: succes / wrong
    if st.session_state.last_result == "correct":
        st.success(f"✅ Correct! {st.session_state.prev_exercise} = {st.session_state.prev_correct}")

    elif st.session_state.last_result == "wrong":
        st.error(
            f"❌ {st.session_state.prev_exercise} = {st.session_state.user_answer} is niet juist! Het juiste antwoord is: {st.session_state.prev_exercise} = {st.session_state.prev_correct}"
        )

    if st.session_state.last_result is not None:
        st.write(f"Je deed er {st.session_state.duration_time:.0f} seconden over.")

# (B) TAB - STATS ----

with tab_stats:
    st.header(f"Statistieken voor {st.session_state.user}")
    df_scores = read_score_df(st.session_state.user)
    if df_scores.empty:
        st.info("Geen statistieken beschikbaar.")
    else:
        st.subheader("Tijd geoefend per dag")
        # display calendar table
        df = create_calendar_table(df_scores, "duration")
        st.dataframe(df, width="stretch")
        
        st.subheader("Score per dag")
        # display calendar table
        df = create_calendar_table(df_scores, "score")
        st.dataframe(df, width="stretch")

        st.subheader("Prestaties per tafel")
        tafel_stats = (
            df_scores.groupby("TAFEL")
            .agg(
                **{
                    "Percentage juist": (
                        "SCORE",
                        lambda x: f"{x.sum() / len(x) * 100:.0f}%",
                    ),
                    "Aantal pogingen": ("SCORE", "count"),
                }
            )
            .reset_index()
            .rename(columns={"TAFEL": "Tafel"})
            .sort_values(by="Tafel", ascending=True)
        )

        # display table but dont display index
        st.dataframe(
            tafel_stats,
            hide_index=True,
            width="stretch",
            column_config={
                "Tafel": st.column_config.TextColumn(width="small"),
                "Percentage juist": st.column_config.TextColumn(width="medium"),
                "Aantal pogingen": st.column_config.TextColumn(width="medium"),
            },
        )

        st.subheader("Kans dat een bepaalde tafel wordt gekozen")
        prob_table = generate_prob_table(df_scores)
        st.dataframe(
            prob_table,
            hide_index=True,
            width="stretch",
            column_config={
                "Tafel": st.column_config.TextColumn(width="small"),
                "Kans gekozen te worden": st.column_config.TextColumn(width="medium"),
            },
        )

        st.subheader("Gemiddeld aantal seconden per tafel")
        time_table = generate_duration_table(df_scores)
        st.dataframe(
            time_table,
            hide_index=True,
            width="stretch",
            column_config={
                "Tafel": st.column_config.TextColumn(width="small"),
                "Gemiddelde tijd (s)": st.column_config.TextColumn(width="medium"),
            },
        )

        st.subheader("Gemiddelde score per tafel")
        score_table = generate_score_table(df_scores)
        st.dataframe(
            score_table,
            hide_index=True,
            width="stretch",
            column_config={
                "Tafel": st.column_config.TextColumn(width="small"),
                "Gemiddelde score": st.column_config.TextColumn(width="medium"),
            },
        )

        st.subheader("Recente gedetailleerde resultaten")
        st.dataframe(
            (
                df_scores.sort_values(by=["DATE_START", "TIME_START"], ascending=[False, False])
                .drop(
                    columns=[
                        "ID",
                        "USER_ID",
                        "CREATED_AT",
                        "DATETIME_START",
                        "EXERCISE_IDX",
                        "MODEL_SCORE",
                        "PROBABILITY",
                    ]
                )
                .assign(**{"RESULTAAT": lambda x: x["SCORE"].apply(lambda score: "✅" if score == 1 else "❌")})
                .drop(columns=["SCORE"])
            ),
            hide_index=True,
        )
        
# (3) TAB - LEVEL ----
with tab_level:
    st.header(f"Level van {st.session_state.user}")
    df_scores = read_score_df(user=st.session_state.user)
    if df_scores.empty:
        st.info("Geen level beschikbaar.")
    else:
        st.data_editor(
            generate_level_chart(df_scores, st.session_state.user),
            column_config={
                "Afbeelding": st.column_config.ImageColumn("Afbeelding", width="medium"),
                "Level": "Level",
                "Wat moet je kunnen om deze Pokémon te krijgen?": "Beschrijving",
                "Pokémon": "Pokémon",
            },
            hide_index=True,
            width="stretch",
        )



# (3) SIDEBAR ----
st.sidebar.title("Instellingen")


with st.sidebar.form("settings"):
    # Get current user index, defaulting to 0 (Raphael) if not found
    USERS = ["Raphael", "Mama", "Papa", "Lea"]


    st.selectbox(
        "Kies de gebruiker:",
        options=USERS,
        key="pending_user",  # keeps value across reruns
    )
    
    st.selectbox(
        "Kies niveau van moeilijkheid:",
        options=["Makkelijk", "Middelmatig","Moeilijk"],
        key = "pending_difficulty_level",
    )
    

    st.multiselect(
        "Kies de tafel(s) die je wil oefenen:",
        options=[2, 3, 4, 5, 6, 7, 8, 9],
        default=st.session_state.selected_tables,
        key="pending_selected_tables",
    )
    # use a separate widget key + show current value as the default
    pending_n = st.number_input(
        "Aantal oefeningen per ronde:",
        min_value=1,
        max_value=50,
        value=st.session_state.n_exercises,  # reflect current choice
        step=1,
        key="pending_n_exercises",
    )
    apply = st.form_submit_button("OK")


if apply:
    if st.session_state.pending_selected_tables:
        st.session_state.selected_tables = st.session_state.pending_selected_tables
        st.session_state.user = st.session_state.pending_user
        st.session_state.n_exercises = int(st.session_state.pending_n_exercises)
        st.session_state.difficulty_level = st.session_state.pending_difficulty_level
        reset_progress(st.session_state.n_exercises)
        (
            st.session_state.exercise,
            st.session_state.correct,
            st.session_state.x1,
            st.session_state.x2,
        ) = generate_exercise(st.session_state.selected_tables, st.session_state.difficulty_level, 0)
        st.session_state.last_result = None
        st.session_state.prev_exercise = None
        st.session_state.prev_correct = None
        st.session_state.reset_answer = True
        st.session_state.pokemon = get_all_pokemons()
        st.session_state.df_scores = read_score_df_updated_db(user=st.session_state.user)
        st.rerun()
        
    else:
        st.warning("Kies minstens één tafel.")

