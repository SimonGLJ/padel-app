import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Padel Turnerings App", layout="wide")

# --- INITIALISERING AF SESSION STATE ---
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'scores' not in st.session_state:
    st.session_state.scores = {}

st.title("🎾 Padel Master - 32 Point Edition")

# --- SIDEBAR: SETUP ---
st.sidebar.header("⚙️ Setup")
format_type = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"])
team_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"])

player_input = st.sidebar.text_area("Indtast spillere (ét navn pr. linje)")
if st.sidebar.button("Opdater spillerliste"):
    st.session_state.players = [name.strip() for name in player_input.split('\n') if name.strip()]

num_players = len(st.session_state.players)
num_courts = num_players // 4

if num_players > 0:
    st.sidebar.write(f"Antal spillere: {num_players}")
    st.sidebar.write(f"Antal baner nødvendige: {num_courts}")

# --- FANER ---
tab1, tab2, tab3 = st.tabs(["📋 Setup & Baner", "🎾 Kampprogram", "📊 Stilling"])

with tab1:
    st.subheader("Navngiv dine baner")
    court_names = []
    for i in range(num_courts):
        name = st.text_input(f"Navn på bane {i+1}", value=f"Bane {i+1}", key=f"court_{i}")
        court_names.append(name)

with tab2:
    st.subheader("Dagens Kampe")
    if num_players < 4:
        st.warning("I skal være mindst 4 spillere for at starte.")
    else:
        # Simpel logik til at generere én runde (Eksempel)
        if st.button("Generer Ny Runde"):
            temp_players = st.session_state.players.copy()
            random.shuffle(temp_players)
            new_matches = []
            for i in range(num_courts):
                p1, p2, p3, p4 = temp_players[i*4:(i*4)+4]
                new_matches.append({"Bane": court_names[i], "Hold A": f"{p1} & {p2}", "Hold B": f"{p3} & {p4}"})
            st.session_state.matches = new_matches

        # Vis kampene og input til score
        for i, match in enumerate(st.session_state.matches):
            with st.expander(f"🔥 {match['Bane']}: {match['Hold A']} vs {match['Hold B']}", expanded=True):
                col1, col2 = st.columns(2)
                
                # AUTO-32 LOGIK
                key_a = f"score_a_{i}"
                key_b = f"score_b_{i}"
                
                if key_a not in st.session_state: st.session_state[key_a] = 16
                if key_b not in st.session_state: st.session_state[key_b] = 16

                def update_b(idx=i):
                    st.session_state[f"score_b_{idx}"] = 32 - st.session_state[f"score_a_{idx}"]

                score_a = col1.number_input(f"Point {match['Hold A']}", 0, 32, key=key_a, on_change=update_b)
                score_b = col2.number_input(f"Point {match['Hold B']}", 0, 32, key=key_b)
                
                st.write(f"Status: {score_a} - {score_b}")

with tab3:
    st.subheader("Rangliste (Rå Point & V/U/T)")
    st.info("Her vil statistikken blive vist, når kampene gemmes (Logik under udvikling).")
