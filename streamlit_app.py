import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Padel Master", layout="wide")

# --- INITIALISERING AF DATA ---
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = {}
if 'round_number' not in st.session_state:
    st.session_state.round_number = 1

st.title("🎾 Padel Master - 32 Point Edition")

# --- SIDEBAR: OPSÆTNING ---
st.sidebar.header("⚙️ Konfiguration")
game_format = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"])
partner_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"])

player_input = st.sidebar.text_area("Indtast deltagere (ét navn pr. linje)", 
                                  placeholder="Jesper\nMads\nSøren...",
                                  height=200)

if st.sidebar.button("🚀 Start / Nulstil Turnering"):
    names = [n.strip() for n in player_input.split('\n') if n.strip()]
    if len(names) < 4:
        st.sidebar.error("Indtast mindst 4 spillere!")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {n: {"V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for n in names}
        st.session_state.matches = []
        st.session_state.round_number = 1
        st.sidebar.success("Turnering startet!")

# Beregn baner
num_players = len(st.session_state.players)
players_per_match = 4 if partner_type == "Skiftende makker" else 2
num_courts = num_players // players_per_match

# --- FANER ---
tab1, tab2 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling"])

with tab1:
    if not st.session_state.players:
        st.info("👈 Start med at indtaste spillere i menuen til venstre.")
    else:
        status_text = "🏆 FINALERUNDE" if st.session_state.round_number > 7 else f"Runde {st.session_state.round_number}"
        st.subheader(status_text)

        # GENERER KAMPE
        if not st.session_state.matches:
            if st.button("🎲 Generer Kampe for denne runde"):
                new_matches = []
                
                # FINALERUNDE LOGIK (Runde 8+)
                if st.session_state.round_number > 7:
                    df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(by=["V", "Point", "Diff"], ascending=False)
                    plist = df_rank.index.tolist()
                    for i in range(num_courts):
                        p = plist[i*4 : (i*4)+4] if partner_type == "Skiftende makker" else plist[i*2 : (i*2)+2]
                        if partner_type == "Skiftende makker":
                            new_matches.append({"H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                        else:
                            new_matches.append({"H1": [p[0]], "H2": [p[1]], "S1": 16, "S2": 16})

                # MEXICANO LOGIK (Styrkebaseret efter runde 1)
                elif game_format == "Mexicano" and st.session_state.round_number > 1:
                    df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(by=["Point"], ascending=False)
                    plist = df_rank.index.tolist()
                    for i in range(num_courts):
                        p = plist[i*4 : (i*4)+4] if partner_type == "Skiftende makker" else plist[i*2 : (i*2)+2]
                        if partner_type == "Skiftende makker":
                            new_matches.append({"H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                        else:
                            new_matches.append({"H1": [p[0]], "H2": [p[1]], "S1": 16, "S2": 16})

                # STANDARD/AMERICANO (Tilfældig)
                else:
                    temp_p = st.session_state.players.copy()
                    random.shuffle(temp_p)
                    for i in range(num_courts):
                        if partner_type == "Skiftende makker":
                            p = temp_p[i*4:(i*4)+4]
                            new_matches.append({"H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16})
                        else:
                            p = temp_p[i*2:(i*2)+2]
                            new_matches.append({"H1": [p[0]], "H2": [p[1]], "S1": 16, "S2": 16})
                
                st.session_state.matches = new_matches
                st.rerun()

        # VIS KAMPE OG SCORE (AUTO-32 LOGIK)
        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                st.write(f"**Bane {i+1}**")
                col1, col2 = st.columns(2)
                
                # Input for Hold 1
                s1 = col1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=m['S1'], key=f"r{st.session_state.round_number}_m{i}_s1")
                
                # AUTO-32 BEREGNING
                s2 = 32 - s1
                col2.markdown(f"<div style='margin-top:25px;'><b>{' & '.join(m['H2'])}</b></div>", unsafe_allow_html=True)
                col2.info(f"Point: {s2}")
                
                # Opdater session state løbende
                m['S1'], m['S2'] = s1, s2

        if st.session_state.matches:
            if st.button("✅ GEM RESULTATER OG GÅ TIL NÆSTE RUNDE"):
                for m in st.session_state.matches:
                    sa, sb = m["S1"], m["S2"]
                    res1 = "V" if sa > sb else ("T" if sa < sb else "U")
                    res2 = "V" if sb > sa else ("T" if sb < sa else "U")
                    
                    for p in m["H1"]:
                        st.session_state.leaderboard[p][res1] += 1
                        st.session_state.leaderboard[p]["Point"] += sa
                        st.session_state.leaderboard[p]["Diff"] += (sa - sb)
                    for p in m["H2"]:
                        st.session_state.leaderboard[p][res2] += 1
                        st.session_state.leaderboard[p]["Point"] += sb
                        st.session_state.leaderboard[p]["Diff"] += (sb - sa)
                
                st.session_state.round_number += 1
                st.session_state.matches = []
                st.success("Resultater gemt!")
                st.rerun()

with tab2:
    st.subheader("Rangliste")
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        df = df.sort_values(by=["V", "Point", "Diff"], ascending=False)
        st.table(df)
    else:
        st.info("Ingen resultater endnu.")
