import streamlit as st
import pandas as pd
import random

# Grundlæggende konfiguration af appen
st.set_page_config(page_title="Padel Master 32", layout="wide")

# --- INITIALISERING AF SESSION STATE (Sikrer at data overlever genindlæsning) ---
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = {}
if 'round_number' not in st.session_state:
    st.session_state.round_number = 1
if 'court_names' not in st.session_state:
    st.session_state.court_names = {}

st.title("🎾 Padel Master - 2 mod 2 (32 Point)")

# --- SIDEBAR: KONFIGURATION ---
st.sidebar.header("⚙️ Konfiguration")
game_format = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"])
partner_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"])

player_input = st.sidebar.text_area("Deltagere (ét navn pr. linje)", height=200)

if st.sidebar.button("🚀 Start / Nulstil Turnering"):
    names = [n.strip() for n in player_input.split('\n') if n.strip()]
    if partner_type == "Skiftende makker" and len(names) % 4 != 0:
        st.sidebar.error("Ved skiftende makker skal antallet deles med 4.")
    elif len(names) < 4:
        st.sidebar.error("Indtast mindst 4 deltagere.")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {n: {"V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for n in names}
        st.session_state.matches = []
        st.session_state.round_number = 1
        st.sidebar.success(f"Startet med {len(names)} spillere!")

# Beregn antal baner baseret på spillere
num_players = len(st.session_state.players)
num_courts = num_players // 4 if num_players >= 4 else 0

# --- FANER ---
tab1, tab2, tab3 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling", "🏢 Bane Navne"])

with tab3:
    st.subheader("Navngiv dine baner")
    if num_players < 4:
        st.info("Indtast spillere først for at se baner.")
    else:
        for i in range(num_courts):
            st.session_state.court_names[i] = st.text_input(
                f"Bane {i+1}", 
                value=st.session_state.court_names.get(i, f"Bane {i+1}"),
                key=f"setup_court_{i}"
            )

with tab1:
    if not st.session_state.players:
        st.info("👈 Indtast spillere til venstre for at starte.")
    else:
        is_final_round = st.session_state.round_number > 7
        status_text = "🏆 FINALERUNDE (1&4 vs 2&3)" if is_final_round else f"Runde {st.session_state.round_number}"
        st.subheader(status_text)

        if not st.session_state.matches:
            if st.button("🎲 Generer Baner"):
                new_matches = []
                # Hent rangliste
                df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
                if not df_rank.empty:
                    df_rank = df_rank.sort_values(by=["Point", "V", "Diff"], ascending=False)
                    ranked_players = df_rank.index.tolist()
                else:
                    ranked_players = st.session_state.players.copy()
                
                temp_p = st.session_state.players.copy()
                if not is_final_round and game_format == "Americano":
                    random.shuffle(temp_p)

                for i in range(num_courts):
                    # FINALE LOGIK: 1&4 mod 2&3
                    if is_final_round:
                        p = ranked_players[i*4 : (i*4)+4]
                        h1, h2 = [p[0], p[3]], [p[1], p[2]]
                    
                    # MEXICANO LOGIK
                    elif game_format == "Mexicano" and st.session_state.round_number > 1:
                        p = ranked_players[i*4 : (i*4)+4]
                        h1, h2 = [p[0], p[3]], [p[1], p[2]]
                        
                    # STANDARD
                    else:
                        p = temp_p[i*4 : (i*4)+4]
                        h1, h2 = [p[0], p[1]], [p[2], p[3]]
                    
                    new_matches.append({
                        "Bane": st.session_state.court_names.get(i, f"Bane {i+1}"),
                        "H1": h1, "H2": h2, "S1": 16, "S2": 16
                    })
                st.session_state.matches = new_matches
                st.rerun()

        # VIS BANER
        for i, m in enumerate(st.session_state.matches):
            with st.container():
                st.markdown(f"### 📍 {m['Bane']}")
                col1, col2 = st.columns(2)
                
                s1 = col1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=m['S1'], key=f"r{st.session_state.round_number}_m{i}_s1")
                s2 = 32 - s1
                col2.markdown(f"<div style='margin-top:35px;'><b>{' & '.join(m['H2'])}</b></div>", unsafe_allow_html=True)
                col2.info(f"Point: {s2}")
                m['S1'], m['S2'] = s1, s2
                st.divider()

        if st.session_state.matches:
            btn_label = "🏆 AFSLUT FINALE" if is_final_round else "✅ GEM RUNDE & NÆSTE"
            if st.button(btn_label):
                for m in st.session_state.matches:
                    sa, sb = m["S1"], m["S2"]
                    res_a = "V" if sa > sb else ("T" if sa < sb else "U")
                    res_b = "V" if sb > sa else ("T" if sb < sa else "U")
                    for p in m["H1"]:
                        st.session_state.leaderboard[p][res_a] += 1
                        st.session_state.leaderboard[p]["Point"] += sa
                        st.session_state.leaderboard[p]["Diff"] += (sa - sb)
                    for p in m["H2"]:
                        st.session_state.leaderboard[p][res_b] += 1
                        st.session_state.leaderboard[p]["Point"] += sb
                        st.session_state.leaderboard[p]["Diff"] += (sb - sa)
                
                st.session_state.round_number += 1
                st.session_state.matches = []
                st.rerun()

with tab2:
    if st.session_state.leaderboard:
        st.subheader("Rangliste")
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        df = df.sort_values(by=["Point", "V", "Diff"], ascending=False)
        st.table(df)
        if st.session_state.round_number > 8:
            st.balloons()
            st.success(f"Vinderen er: {df.index[0]}")
