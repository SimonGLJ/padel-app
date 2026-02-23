import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Padel Turnerings App", layout="wide")

# --- INITIALISERING ---
if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = {}
if 'round_number' not in st.session_state:
    st.session_state.round_number = 1
if 'is_final' not in st.session_state:
    st.session_state.is_final = False

st.title("🎾 Padel Master - 32 Point Edition")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Setup")
player_input = st.sidebar.text_area("Indtast spillere (ét navn pr. linje)", 
                                  value="\n".join(st.session_state.players) if st.session_state.players else "")

if st.sidebar.button("Start/Nulstil Turnering"):
    names = [name.strip() for name in player_input.split('\n') if name.strip()]
    if len(names) < 4 or len(names) % 4 != 0:
        st.sidebar.error("Antal spillere skal kunne deles med 4.")
    else:
        st.session_state.players = names
        st.session_state.leaderboard = {name: {"V": 0, "U": 0, "T": 0, "Point": 0, "Diff": 0} for name in names}
        st.session_state.matches = []
        st.session_state.round_number = 1
        st.session_state.is_final = False
        st.sidebar.success("Turnering startet!")

num_players = len(st.session_state.players)
num_courts = num_players // 4

# --- FANER ---
tab1, tab2, tab3 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling", "📋 Bane Navne"])

with tab3:
    court_names = []
    for i in range(num_courts):
        name = st.text_input(f"Navn på bane {i+1}", value=f"Bane {i+1}", key=f"cn_{i}")
        court_names.append(name)

with tab1:
    if not st.session_state.players:
        st.info("Indtast spillere i menuen til venstre.")
    else:
        status_tekst = "FINALERUNDE" if st.session_state.is_final else f"Runde {st.session_state.round_number} (af 7)"
        st.subheader(status_tekst)
        
        # GENERER KAMPE LOGIK
        if not st.session_state.matches:
            knap_label = "Generer Finaler (Baseret på rangliste)" if st.session_state.round_number > 7 else "Generer Næste Runde"
            
            if st.button(knap_label):
                if st.session_state.round_number > 7:
                    # FINALE LOGIK: 1&4 vs 2&3
                    st.session_state.is_final = True
                    df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
                    df_rank = df_rank.sort_values(by=["V", "Point", "Diff"], ascending=False)
                    sorted_players = df_rank.index.tolist()
                    
                    new_matches = []
                    for i in range(num_courts):
                        # Tag spillere 4 og 4 fra den sorterede liste
                        p = sorted_players[i*4 : (i*4)+4]
                        new_matches.append({
                            "Bane": f"FINALE - {court_names[i]}",
                            "Hold_A": [p[0], p[3]], # Nr 1 og 4
                            "Hold_B": [p[1], p[2]], # Nr 2 og 3
                            "Score_A": 16, "Score_B": 16
                        })
                else:
                    # NORMAL RUNDE LOGIK (Tilfældig Americano-ish)
                    temp_players = st.session_state.players.copy()
                    random.shuffle(temp_players)
                    new_matches = []
                    for i in range(num_courts):
                        p = temp_players[i*4:(i*4)+4]
                        new_matches.append({
                            "Bane": court_names[i], 
                            "Hold_A": [p[0], p[1]], "Hold_B": [p[2], p[3]],
                            "Score_A": 16, "Score_B": 16
                        })
                st.session_state.matches = new_matches
                st.rerun()

        # VIS KAMPE
        for i, match in enumerate(st.session_state.matches):
            with st.expander(f"Bane {match['Bane']}", expanded=True):
                c1, c2 = st.columns(2)
                def update_b(idx=i):
                    st.session_state.matches[idx]["Score_B"] = 32 - st.session_state.matches[idx]["Score_A"]
                
                match["Score_A"] = c1.number_input(f"{' & '.join(match['Hold_A'])}", 0, 32, value=match["Score_A"], key=f"ma_{i}", on_change=update_b)
                match["Score_B"] = c2.number_input(f"{' & '.join(match['Hold_B'])}", 0, 32, value=match["Score_B"], key=f"mb_{i}")

        if st.session_state.matches:
            if st.button("✅ GEM RESULTATER"):
                for m in st.session_state.matches:
                    sa, sb = m["Score_A"], m["Score_B"]
                    res_a = "V" if sa > sb else ("T" if sa < sb else "U")
                    res_b = "V" if sb > sa else ("T" if sb < sa else "U")
                    for p in m["Hold_A"]:
                        st.session_state.leaderboard[p][res_a] += 1
                        st.session_state.leaderboard[p]["Point"] += sa
                        st.session_state.leaderboard[p]["Diff"] += (sa - sb)
                    for p in m["Hold_B"]:
                        st.session_state.leaderboard[p][res_b] += 1
                        st.session_state.leaderboard[p]["Point"] += sb
                        st.session_state.leaderboard[p]["Diff"] += (sb - sa)
                
                st.session_state.round_number += 1
                st.session_state.matches = []
                st.success("Resultater gemt!")
                st.rerun()

with tab2:
    st.subheader("Rangliste (Løbende)")
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        df = df.sort_values(by=["V", "Point", "Diff"], ascending=False)
        st.table(df)
