import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Padel Master 32", layout="wide")

# --- INITIALISERING ---
if 'players' not in st.session_state:
    st.session_state.players = []
if 'fixed_teams' not in st.session_state:
    st.session_state.fixed_teams = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = {}
if 'round_number' not in st.session_state:
    st.session_state.round_number = 1
if 'court_names' not in st.session_state:
    st.session_state.court_names = {}

st.title("🎾 Padel Master - 32 Point Edition")

# --- SIDEBAR: KONFIGURATION ---
st.sidebar.header("⚙️ Konfiguration")
game_format = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"])
partner_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"])
player_input = st.sidebar.text_area("1. Indtast spillere (ét navn pr. linje)", height=200)

names = [n.strip() for n in player_input.split('\n') if n.strip()]
num_courts_needed = len(names) // 4

if len(names) >= 4:
    st.sidebar.markdown("---")
    st.sidebar.write("2. Navngiv baner")
    for i in range(num_courts_needed):
        st.session_state.court_names[i] = st.sidebar.text_input(
            f"Bane {i+1}", 
            value=st.session_state.court_names.get(i, f"Bane {i+1}"), 
            key=f"setup_court_{i}"
        )

if st.sidebar.button("🚀 START TURNERING / NULSTIL"):
    if len(names) < 4 or len(names) % 4 != 0:
        st.sidebar.error("Antal spillere skal gå op i 4 (f.eks. 8, 12, 16, 20, 24).")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {n: {"Kampe": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for n in names}
        st.session_state.matches = []
        st.session_state.fixed_teams = []
        st.session_state.round_number = 1
        st.sidebar.success("Turnering klar!")

# --- FANER ---
tab1, tab2 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling"])

with tab1:
    if not st.session_state.players:
        st.info("👈 Indtast spillere og baner i menuen til venstre for at starte.")
    else:
        is_final_round = st.session_state.round_number == 8
        status_text = "🏆 FINALERUNDE" if is_final_round else f"Runde {st.session_state.round_number} af 7"
        st.subheader(status_text)

        if not st.session_state.matches:
            if st.button("🎲 Start ny runde"):
                # 1. GENERER FASTE HOLD HVIS DET ER RUNDE 1
                if partner_type == "Faste hold" and not st.session_state.fixed_teams:
                    temp_names = st.session_state.players.copy()
                    random.shuffle(temp_names)
                    st.session_state.fixed_teams = [temp_names[i:i+2] for i in range(0, len(temp_names), 2)]

                # 2. HENT RANGERET LISTE
                df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
                df_rank = df_rank.sort_values(by=["Point", "V", "Diff"], ascending=False)
                ranked_players = df_rank.index.tolist()

                new_matches = []
                num_courts = len(st.session_state.players) // 4
                
                # 3. GENERER KAMPE
                if is_final_round or (game_format == "Mexicano" and st.session_state.round_number > 1):
                    # STYRKEBASERET (MEXICANO / FINALE)
                    if partner_type == "Skiftende makker":
                        for i in range(num_courts):
                            p = ranked_players[i*4 : (i*4)+4]
                            new_matches.append({"Bane": st.session_state.court_names.get(i, f"Bane {i+1}"), "H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                    else:
                        # Faste hold rangeret efter bedste spiller på holdet
                        seen_teams = []
                        for p in ranked_players:
                            for team in st.session_state.fixed_teams:
                                if p in team and team not in seen_teams:
                                    seen_teams.append(team)
                        for i in range(num_courts):
                            t1, t2 = seen_teams[i*2], seen_teams[i*2+1]
                            new_matches.append({"Bane": st.session_state.court_names.get(i, f"Bane {i+1}"), "H1": t1, "H2": t2, "S1": 16, "S2": 16})
                else:
                    # TILFÆLDIG (AMERICANO / RUNDE 1)
                    if partner_type == "Skiftende makker":
                        temp_p = st.session_state.players.copy()
                        random.shuffle(temp_p)
                        for i in range(num_courts):
                            p = temp_p[i*4 : (i*4)+4]
                            new_matches.append({"Bane": st.session_state.court_names.get(i, f"Bane {i+1}"), "H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16})
                    else:
                        temp_teams = st.session_state.fixed_teams.copy()
                        random.shuffle(temp_teams)
                        for i in range(num_courts):
                            t1, t2 = temp_teams[i*2], temp_teams[i*2+1]
                            new_matches.append({"Bane": st.session_state.court_names.get(i, f"Bane {i+1}"), "H1": t1, "H2": t2, "S1": 16, "S2": 16})
                
                st.session_state.matches = new_matches
                st.rerun()

            # VIS KAMPE
            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    # Vinderbane tekst kun i Mexicano eller Finale
                    show_vinder = (i == 0 and (game_format == "Mexicano" or is_final_round))
                    header = f"### {'🔝 VINDERBANE: ' if show_vinder else ''}{m['Bane']}"
                    st.markdown(header)
                    
                    c1, c2 = st.columns(2)
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=m['S1'], key=f"r{st.session_state.round_number}_m{i}_s1")
                    s2 = 32 - s1
                    c2.markdown(f"<div style='margin-top:25px;'><b>{' & '.join(m['H2'])}</b></div>", unsafe_allow_html=True)
                    c2.info(f"Point: {s2}")
                    m['S1'], m['S2'] = s1, s2

            if st.session_state.matches:
                if st.button("✅ GEM RESULTATER"):
                    for m in st.session_state.matches:
                        sa, sb = m["S1"], m["S2"]
                        res1 = "V" if sa > sb else ("T" if sa < sb else "U")
                        res2 = "V" if sb > sa else ("T" if sb < sa else "U")
                        # Opdater alle spillere individuelt
                        for p in m["H1"]:
                            st.session_state.leaderboard[p]["Kampe"] += 1
                            st.session_state.leaderboard[p][res1] += 1
                            st.session_state.leaderboard[p]["Point"] += sa
                            st.session_state.leaderboard[p]["Diff"] += (sa - sb)
                        for p in m["H2"]:
                            st.session_state.leaderboard[p]["Kampe"] += 1
                            st.session_state.leaderboard[p][res2] += 1
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
        st.table(df.reset_index().rename(columns={'index': 'Spiller'}))
        if st.session_state.round_number > 8:
            st.balloons()
