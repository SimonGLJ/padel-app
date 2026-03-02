import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Padel Master 32", layout="wide")

# --- SIKKER INITIALISERING (Låser data fast) ---
def init_state():
    if 'initialized' not in st.session_state:
        st.session_state.players = []
        st.session_state.fixed_teams = []
        st.session_state.matches = []
        st.session_state.leaderboard = {}
        st.session_state.round_number = 1
        st.session_state.court_names = {}
        st.session_state.initialized = True

init_state()

st.title("🎾 Padel Master - 32 Point Edition")

# --- SIDEBAR: OPSÆTNING ---
st.sidebar.header("⚙️ Konfiguration")
game_format = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"], key="conf_format")
partner_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"], key="conf_partner")

# Brug en key på text_area for at bevare teksten ved reload
player_input = st.sidebar.text_area("1. Indtast spillere (ét pr. linje)", height=200, key="input_area")

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
        st.sidebar.error("Antal spillere skal gå op i 4.")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {n: {"Kampe": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for n in names}
        st.session_state.matches = []
        st.session_state.fixed_teams = []
        st.session_state.round_number = 1
        st.sidebar.success("Turnering startet!")
        st.rerun()

# --- HOVEDSKÆRM ---
tab1, tab2 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling"])

with tab1:
    if not st.session_state.players:
        st.info("👈 Indtast spillere og baner i menuen til venstre for at starte.")
    else:
        is_final_round = st.session_state.round_number == 8
        is_after_final = st.session_state.round_number > 8
        
        if is_after_final:
            st.success("Turneringen er afsluttet! Se vinderen under 'Stilling'.")
        else:
            st.subheader(f"{'🏆 FINALERUNDE' if is_final_round else f'Runde {st.session_state.round_number} af 7'}")

            # GENERER KAMPE
            if not st.session_state.matches:
                if st.button("🎲 Start ny runde"):
                    # Dan faste hold hvis nødvendigt
                    if partner_type == "Faste hold" and not st.session_state.fixed_teams:
                        temp_p = st.session_state.players.copy()
                        random.shuffle(temp_p)
                        st.session_state.fixed_teams = [temp_p[i:i+2] for i in range(0, len(temp_p), 2)]

                    df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
                    df_rank = df_rank.sort_values(by=["Point", "V", "Diff"], ascending=False)
                    ranked_players = df_rank.index.tolist()

                    new_matches = []
                    num_courts = len(st.session_state.players) // 4
                    
                    for i in range(num_courts):
                        # MEXICANO / FINALE
                        if is_final_round or (game_format == "Mexicano" and st.session_state.round_number > 1):
                            if partner_type == "Skiftende makker":
                                p = ranked_players[i*4 : (i*4)+4]
                                h1, h2 = [p[0], p[3]], [p[1], p[2]]
                            else:
                                teams_sorted = st.session_state.fixed_teams.copy()
                                teams_sorted.sort(key=lambda t: (st.session_state.leaderboard[t[0]]["Point"] + st.session_state.leaderboard[t[1]]["Point"]), reverse=True)
                                h1, h2 = teams_sorted[i*2], teams_sorted[i*2+1]
                        # AMERICANO / RUNDE 1
                        else:
                            if partner_type == "Skiftende makker":
                                temp_p = st.session_state.players.copy()
                                random.shuffle(temp_p)
                                p = temp_p[i*4 : (i*4)+4]
                                h1, h2 = [p[0], p[1]], [p[2], p[3]]
                            else:
                                temp_t = st.session_state.fixed_teams.copy()
                                random.shuffle(temp_t)
                                h1, h2 = temp_t[i*2], temp_t[i*2+1]
                        
                        new_matches.append({"Bane": st.session_state.court_names.get(i, f"Bane {i+1}"), "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                    
                    st.session_state.matches = new_matches
                    st.rerun()

            # VIS KAMPE OG INDTASTNING
            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    show_vinder = (i == 0 and (game_format == "Mexicano" or is_final_round))
                    st.markdown(f"### {'🔝 VINDERBANE: ' if show_vinder else ''}{m['Bane']}")
                    
                    c1, c2 = st.columns(2)
                    # SIKRING: Gem scoren direkte i session_state m['S1']
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=m['S1'], key=f"score_r{st.session_state.round_number}_m{i}")
                    s2 = 32 - s1
                    c2.markdown(f"<div style='margin-top:25px;'><b>{' & '.join(m['H2'])}</b></div>", unsafe_allow_html=True)
                    c2.info(f"Point: {s2}")
                    
                    # Gem værdien med det samme så den ikke glemmes ved reload
                    st.session_state.matches[i]['S1'] = s1
                    st.session_state.matches[i]['S2'] = s2

            if st.session_state.matches:
                if st.button("✅ GEM RESULTATER"):
                    for m in st.session_state.matches:
                        sa, sb = m["S1"], m["S2"]
                        res1, res2 = ("V", "T") if sa > sb else (("T", "V") if sa < sb else ("U", "U"))
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
