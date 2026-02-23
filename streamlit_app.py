import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Padel Master 32", layout="wide")

# --- INITIALISERING ---
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

st.title("🎾 Padel Master - 32 Point Edition")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Konfiguration")
game_format = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"])
partner_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"])
player_input = st.sidebar.text_area("Deltagere (ét navn pr. linje)", height=200)

if st.sidebar.button("🚀 Start / Nulstil Turnering"):
    names = [n.strip() for n in player_input.split('\n') if n.strip()]
    if len(names) < 4 or len(names) % 4 != 0:
        st.sidebar.error("Antal spillere skal gå op i 4 (f.eks. 8, 12, 16, 20, 24).")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {n: {"V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for n in names}
        st.session_state.matches = []
        st.session_state.round_number = 1
        st.sidebar.success(f"Startet med {len(names)} spillere!")

num_players = len(st.session_state.players)
num_courts = num_players // 4

# --- FANER ---
tab1, tab2, tab3 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling", "🏢 Bane Navne"])

with tab3:
    st.subheader("Navngiv dine baner")
    for i in range(num_courts):
        court_key = i
        st.session_state.court_names[court_key] = st.text_input(
            f"Bane {i+1}", 
            value=st.session_state.court_names.get(court_key, f"Bane {i+1}"), 
            key=f"setup_court_{i}"
        )

with tab1:
    if not st.session_state.players:
        st.info("👈 Indtast spillere til venstre for at starte.")
    else:
        is_final_round = st.session_state.round_number == 8
        is_after_final = st.session_state.round_number > 8
        
        if is_after_final:
            st.success("Turneringen er slut!")
        else:
            status_text = "🏆 FINALERUNDE (1&4 vs 2&3)" if is_final_round else f"Runde {st.session_state.round_number} af 7"
            st.subheader(status_text)

            if not st.session_state.matches:
                if st.button("🎲 Generer Baner"):
                    new_matches = []
                    
                    # 1. Hent den aktuelle rangliste som en sorteret liste af navne
                    df_current = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
                    df_current = df_current.sort_values(by=["Point", "V", "Diff"], ascending=False)
                    ranked_players = df_current.index.tolist()

                    # 2. Generer kampe for hver bane
                    for i in range(num_courts):
                        # FINALE ELLER MEXICANO LOGIK
                        if is_final_round or (game_format == "Mexicano" and st.session_state.round_number > 1):
                            # Vi tager spillerne 4 af gangen fra ranglisten
                            # i=0 (Bane 1): Plads 1,2,3,4 (index 0,1,2,3)
                            # i=1 (Bane 2): Plads 5,6,7,8 (index 4,5,6,7)
                            idx = i * 4
                            p1 = ranked_players[idx]     # Bedste i gruppen
                            p2 = ranked_players[idx + 1] # Næstbedste
                            p3 = ranked_players[idx + 2] # Tredjebedste
                            p4 = ranked_players[idx + 3] # Fjerdebedste
                            
                            h1 = [p1, p4] # 1 & 4
                            h2 = [p2, p3] # 2 & 3
                        
                        else:
                            # AMERICANO / RUNDE 1: Tilfældig
                            if i == 0: # Bland kun én gang pr. runde
                                random.shuffle(st.session_state.players)
                            p = st.session_state.players[i*4 : (i*4)+4]
                            h1, h2 = [p[0], p[1]], [p[2], p[3]]
                        
                        new_matches.append({
                            "Bane": st.session_state.court_names.get(i, f"Bane {i+1}"),
                            "H1": h1, "H2": h2, "S1": 16, "S2": 16
                        })
                    st.session_state.matches = new_matches
                    st.rerun()

            # VIS KAMPE
            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    finale_type = ""
                    if is_final_round:
                        types = ["🥇 GULDFINALE (Plads 1-4)", "🥈 SØLVFINALE (Plads 5-8)", "🥉 BRONZEFINALE (Plads 9-12)"]
                        finale_type = types[i] if i < len(types) else f"Finale (Plads {i*4+1}-{i*4+4})"
                    
                    st.markdown(f"### {m['Bane']} {finale_type}")
                    c1, c2 = st.columns(2)
                    
                    # Score input
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=m['S1'], key=f"r{st.session_state.round_number}_m{i}_s1")
                    s2 = 32 - s1
                    c2.markdown(f"<div style='margin-top:25px;'><b>{' & '.join(m['H2'])}</b></div>", unsafe_allow_html=True)
                    c2.info(f"Point: {s2}")
                    
                    m['S1'], m['S2'] = s1, s2

            if st.session_state.matches:
                if st.button("✅ GEM RUNDE"):
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
        # Vis placering (1, 2, 3...) i stedet for 0-index
        df.index.name = "Spiller"
        display_df = df.reset_index()
        display_df.index = display_df.index + 1
        st.table(display_df)
        
        if st.session_state.round_number > 8:
            st.balloons()
            st.success(f"Vinderen er: {display_df.iloc[0]['Spiller']}! 🏆")
