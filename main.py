import random
import streamlit as st


def generate_exercise(accepted_products):
    random_number = random.randint(1, 10)

    random_accepted_product = accepted_products[
        random.randint(0, len(accepted_products) - 1)
    ]

    correct_answer = random_number * random_accepted_product

    exercise_string = f"{random_accepted_product} x {random_number}"

    return exercise_string, correct_answer


def check_answer(correct_answer, user_answer):
    correct_answer = int(correct_answer)
    user_answer = int(user_answer)

    return correct_answer == user_answer


st.title("Maaltafels")

# --- INIT (order matters) ---
if "selected_tables" not in st.session_state:
    st.session_state.selected_tables = [2, 3, 4, 5, 6, 7, 8, 9]
if "exercise" not in st.session_state:
    st.session_state.exercise, st.session_state.correct = generate_exercise(
        st.session_state.selected_tables
    )
    st.session_state.last_result = None
    st.session_state.prev_exercise = None
    st.session_state.prev_correct = None
if "user_answer_str" not in st.session_state:
    st.session_state.user_answer_str = ""
if "reset_answer" not in st.session_state:
    st.session_state.reset_answer = False

# ✅ Reset the input BEFORE rendering the widget (and BEFORE the form)
if st.session_state.reset_answer:
    st.session_state.user_answer_str = ""
    st.session_state.reset_answer = False

st.write(f"Volgende oefening: **{st.session_state.exercise}**")

# --- FORM (answer) ---
with st.form("answer_form"):
    st.text_input(
        "Jouw antwoord:", key="user_answer_str", placeholder="Typ je antwoord..."
    )
    submitted = st.form_submit_button("OK")

# --- SUBMIT HANDLER ---
if submitted:
    raw = st.session_state.user_answer_str.strip()
    if not raw:
        st.warning("Vul eerst een antwoord in.")
    else:
        try:
            user_answer = int(raw)
        except ValueError:
            st.error("Gebruik alleen cijfers.")
        else:
            st.session_state.prev_exercise = st.session_state.exercise
            st.session_state.prev_correct = st.session_state.correct
            st.session_state.last_result = (
                "correct" if user_answer == st.session_state.correct else "wrong"
            )
            st.session_state.exercise, st.session_state.correct = generate_exercise(
                st.session_state.selected_tables
            )
            # schedule clearing input on next run (don't touch the key now)
            st.session_state.reset_answer = True
            st.rerun()

# --- FEEDBACK ---
if st.session_state.last_result == "correct":
    st.success(
        f"✅ Correct! {st.session_state.prev_exercise} = {st.session_state.prev_correct}"
    )
elif st.session_state.last_result == "wrong":
    st.error(
        f"❌ Niet juist! Het juiste antwoord is: {st.session_state.prev_exercise} = {st.session_state.prev_correct}"
    )

# --- SIDEBAR: Selection + OK button ---
st.sidebar.title("Instellingen")

with st.sidebar.form("settings"):
    st.multiselect(
        "Kies de tafel(s) die je wil oefenen:",
        options=[2, 3, 4, 5, 6, 7, 8, 9],
        default=st.session_state.selected_tables,
        key="pending_selected_tables",  # temporary selection
    )
    apply = st.form_submit_button("OK")

if apply:
    if st.session_state.pending_selected_tables:
        st.session_state.selected_tables = st.session_state.pending_selected_tables
        st.session_state.exercise, st.session_state.correct = generate_exercise(
            st.session_state.selected_tables
        )
        st.session_state.last_result = None
        st.session_state.prev_exercise = None
        st.session_state.prev_correct = None
        # schedule clearing the input; DO NOT assign to user_answer_str directly here
        st.session_state.reset_answer = True
        st.rerun()
    else:
        st.warning("Kies minstens één tafel.")
