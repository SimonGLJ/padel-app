import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Padel Master", layout="wide")

# --- INITIALISERING AF SESSION STATE ---
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = {}
if 'round_number' not in st.session_state:
    st.session_state.round_number = 1

st.title("🎾 Padel Master - 32 Point Edition")

# --- SIDEBAR: KONFIGURATION ---
st.sidebar.header("⚙️ Konfiguration")
game_format = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"])
partner_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"])

player_input = st.sidebar.text_area("Indtast spillere/hold (ét pr. linje)", 
                                  help="Ved faste hold, skriv f.eks. 'Jesper/Mads'")

if st.sidebar.button("Nulstil & Start Turnering"):
    names = [name.strip() for name in player_input.split('\n') if name.strip()]
    if len(names) < 4 or (partner_type == "Skiftende makker" and len(names) % 4 != 0):
        st.sidebar.error("Antal skal gå op i 4 ved skiftende makkere.")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {name: {"V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for name in names}
        st.session_state.matches = []
        st.session_state.round_number = 1
        st.sidebar.success("Turnering startet!")

num_players = len(st.session_state.players)
num_courts = num_players // (4 if partner_type == "Skiftende makker" else 2)

# --- FANER ---
tab1, tab2, tab3 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling", "📋 Bane Navne"])

with tab3:
    court_names = [st.text_input(f"Bane {i+1}", value=f"Bane {i+1}", key=f"cn_{i}") for i in range(num_courts)]

with tab1:
    if not st.session_state.players:
        st.info("Indtast deltagere i menuen til venstre.")
    else:
        status = "FINALERUNDE" if st.session_state.round_number > 7 else f"Runde {st.session_state.round_number}"
        st.subheader(status)

        # GENERER KAMPE LOGIK
        if not st.session_state.matches:
            if st.button("Generer Kampe"):
                new_matches = []
                
                # 1. LOGIK FOR FINALE (Runde 8)
                if st.session_state.round_number > 7:
                    df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(by=["V", "Point", "Diff"], ascending=False)
                    plist = df_rank.index.tolist()
                    for i in range(num_courts):
                        p = plist[i*4 : (i*4)+4] if partner_type == "Skiftende makker" else plist[i*2 : (i*2)+2]
                        # Finale parring (1&4 vs 2&3)
                        new_matches.append({"Bane": court_names[i], "H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                
                # 2. LOGIK FOR MEXICANO (Styrkebaseret efter runde 1)
                elif game_format == "Mexicano" and st.session_state.round_number > 1:
                    df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(by=["Point"], ascending=False)
                    plist = df_rank.index.tolist()
                    for i in range(num_courts):
                        p = plist[i*4 : (i*4)+4]
                        new_matches.append({"Bane": court_names[i], "H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                
                # 3. STANDARD / AMERICANO (Tilfældig)
                else:
                    temp_p = st.session_state.players.copy()
                    random.shuffle(temp_p)
                    for i in range(num_courts):
                        if partner_type == "Skiftende makker":
                            p = temp_p[i*4:(i*4)+4]
                            new_matches.append({"Bane": court_names[i], "H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16})
                        else:
                            p = temp_p[i*2:(i*2)+2]
                            new_matches.append({"Bane": court_names[i], "H1": [p[0]], "H2": [p[1]], "S1": 16, "S2": 16})
                
                st.session_state.matches = new_matches
                st.rerun()

        # VIS KAMPE MED AUTO-32 LOGIK
        for i, m in enumerate(st.session_state.matches):
            with st.expander(f"🔥 {m['Bane']}", expanded=True):
                col1, col2 = st.columns(2)
                
                # Funktion til at sikre summen 32
                def sync_scores(idx=i, source='A'):
                    if source == 'A':
                        st.session_state.matches[idx]["S2"] = 32 - st.session_state.matches[idx]["S1"]
                    else:
                        st.session_state.matches[idx]["S1"] = 32 - st.session_state.matches[idx]["S2"]

                m["S1"] = col1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=m["S1"], key=f"s1_{i}", on_change=sync_scores, args=(i, 'A'))
                m["S2"] = col2.number_input(f"{' & '.join(m['H2'])}", 0, 32, value=m["S2"], key=f"s2_{i}", on_change=sync_scores, args=(i, 'B'))

        if st.session_state.matches and st.button("✅ GEM OG NÆSTE"):
            for m in st.session_state.matches:
                res1 = "V" if m["S1"] > m["S2"] else ("T" if m["S1"] < m["S2"] else "U")
                res2 = "V" if m["S2"] > m["S1"] else ("T" if m["S2"] < m["S1"] else "U")
                for p in m["H1"]:
                    st.session_state.leaderboard[p][res1] += 1
                    st.session_state.leaderboard[p]["Point"] += m["S1"]
                    st.session_state.leaderboard[p]["Diff"] += (m["S1"] - m["S2"])
                for p in m["H2"]:
                    st.session_state.leaderboard[p][res2] += 1
                    st.session_state.leaderboard[p]["Point"] += m["S2"]
                    st.session_state.leaderboard[p]["Diff"] += (m["S2"] - m["S1"])
            
            st.session_state.round_number += 1
            st.session_state.matches = []
            st.rerun()

with tab2:
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(by=["V", "Point", "Diff"], ascending=False)
        st.table(df)
