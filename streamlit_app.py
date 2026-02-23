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

st.title("🎾 Padel Master - 2 mod 2 (32 Point)")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Konfiguration")
game_format = st.sidebar.selectbox("Vælg Format", ["Americano", "Mexicano"])
partner_type = st.sidebar.selectbox("Makker Type", ["Skiftende makker", "Faste hold"])

player_input = st.sidebar.text_area("Deltagere (ét navn pr. linje)", height=200)

if st.sidebar.button("🚀 Start / Nulstil Turnering"):
    names = [n.strip() for n in player_input.split('\n') if n.strip()]
    if partner_type == "Skiftende makker" and len(names) % 4 != 0:
        st.sidebar.error("Ved skiftende makker skal antallet af spillere kunne deles med 4 (f.eks. 8, 12, 16).")
    elif len(names) < 4:
        st.sidebar.error("Indtast mindst 4 deltagere.")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {n: {"V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for n in names}
        st.session_state.matches = []
        st.session_state.round_number = 1
        st.sidebar.success(f"Turnering startet med {len(names)} spillere!")

# Beregn baner (4 spillere pr. bane)
num_players = len(st.session_state.players)
num_courts = num_players // 4

# --- FANER ---
tab1, tab2 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling"])

with tab1:
    if not st.session_state.players:
        st.info("👈 Indtast spillere til venstre for at starte.")
    else:
        status_text = "🏆 FINALERUNDE (1&4 vs 2&3)" if st.session_state.round_number > 7 else f"Runde {st.session_state.round_number}"
        st.subheader(status_text)

        if not st.session_state.matches:
            if st.button("🎲 Generer Baner (2 mod 2)"):
                new_matches = []
                
                # Hent rangliste til Mexicano/Finale
                df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(by=["Point", "V"], ascending=False)
                plist = df_rank.index.tolist()
                
                # 1. FINALERUNDE ELLER MEXICANO (Styrke-parring)
                if st.session_state.round_number > 7 or (game_format == "Mexicano" and st.session_state.round_number > 1):
                    for i in range(num_courts):
                        p = plist[i*4 : (i*4)+4]
                        # Logik: Nr 1 & 4 mod Nr 2 & 3 på banen
                        new_matches.append({"H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                
                # 2. AMERICANO / RUNDE 1 (Tilfældig parring)
                else:
                    temp_p = st.session_state.players.copy()
                    random.shuffle(temp_p)
                    for i in range(num_courts):
                        p = temp_p[i*4 : (i*4)+4]
                        new_matches.append({"H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16})
                
                st.session_state.matches = new_matches
                st.rerun()

        # VIS BANER OG AUTO-32
        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                st.write(f"**Bane {i+1}**")
                col1, col2 = st.columns(2)
                
                # Input for Hold 1 (2 spillere)
                names_h1 = " & ".join(m['H1'])
                s1 = col1.number_input(f"Hold A: {names_h1}", 0, 32, value=m['S1'], key=f"r{st.session_state.round_number}_m{i}_s1")
                
                # Auto-beregn Hold 2
                s2 = 32 - s1
                names_h2 = " & ".join(m['H2'])
                col2.markdown(f"<div style='margin-top:25px;'><b>Hold B: {names_h2}</b></div>", unsafe_allow_html=True)
                col2.info(f"Point: {s2}")
                
                m['S1'], m['S2'] = s1, s2

        if st.session_state.matches:
            if st.button("✅ GEM RUNDE & OPDATER TABEL"):
                for m in st.session_state.matches:
                    sa, sb = m["S1"], m["S2"]
                    res_a = "V" if sa > sb else ("T" if sa < sb else "U")
                    res_b = "V" if sb > sa else ("T" if sb < sa else "U")
                    
                    # Giv point til alle 4 spillere på banen
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
        st.subheader("Rangliste (Individuelle point)")
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        df = df.sort_values(by=["Point", "V", "Diff"], ascending=False)
        st.table(df)
