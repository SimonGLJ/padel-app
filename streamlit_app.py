import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def load_from_supabase(tid):
    try:
        res = conn.table("tournaments").select("*").eq("tournament_id", tid).execute()
        return res.data[0] if res.data and len(res.data) > 0 else None
    except Exception as e:
        st.error(f"Database-læsefejl: {e}")
        return None

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, history):
    data = {
        "tournament_id": tid,
        "round_number": round_num,
        "leaderboard": leaderboard,
        "matches": matches,
        "players": players,
        "fixed_teams": fixed_teams,
        "history": history # Vi gemmer nu også historikken
    }
    try:
        conn.table("tournaments").upsert(data).execute()
        st.toast(f"☁️ Data synkroniseret: {tid}")
    except Exception as e:
        st.error(f"Database-gemmefejl: {e}")

# --- 2. APP LOGIK START ---
st.title("🎾 Padel Master Pro")

tid = st.text_input("Indtast Turnerings-ID", key="tid_input").strip()

if not tid:
    st.info("👋 Indtast et Turnerings-ID for at starte.")
    st.stop()

# HENT DATA VED OPSTART
if "current_tid" not in st.session_state or st.session_state.current_tid != tid:
    cloud_data = load_from_supabase(tid)
    if cloud_data:
        st.session_state.players = cloud_data.get('players', [])
        st.session_state.leaderboard = cloud_data.get('leaderboard', {})
        st.session_state.round_number = cloud_data.get('round_number', 1)
        st.session_state.matches = cloud_data.get('matches', [])
        st.session_state.fixed_teams = cloud_data.get('fixed_teams', [])
        st.session_state.history = cloud_data.get('history', [])
    else:
        st.session_state.players = []
        st.session_state.leaderboard = {}
        st.session_state.round_number = 1
        st.session_state.matches = []
        st.session_state.fixed_teams = []
        st.session_state.history = []
    st.session_state.current_tid = tid

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    p_text = "\n".join(st.session_state.get('players', []))
    p_input = st.text_area("Deltagere", value=p_text, height=200)
    
    if st.button("🚀 Start / Opdater"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.players = names
            st.session_state.leaderboard = {n: {"Point": 0, "V": 0, "Kampe": 0} for n in names}
            st.session_state.round_number = 1
            st.session_state.matches = []
            st.session_state.fixed_teams = []
            st.session_state.history = []
            save_to_supabase(tid, 1, st.session_state.leaderboard, [], names, [], [])
            st.rerun()
        else:
            st.error("Antal skal gå op i 4!")

    if st.button("🗑️ Nulstil ID"):
        save_to_supabase(tid, 1, {}, [], [], [], [])
        st.session_state.clear()
        st.rerun()

# --- 4. HOVEDSKÆRM ---
tab1, tab2, tab3 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling", "📜 Log/Historik"])

with tab1:
    if not st.session_state.get('players'):
        st.warning("Indtast spillere i siden.")
    else:
        st.subheader(f"Runde {st.session_state.round_number}")
        
        if not st.session_state.get('matches'):
            if st.button("🎲 Generer Kampe"):
                if p_type == "Faste hold" and not st.session_state.fixed_teams:
                    temp_p = st.session_state.players.copy()
                    random.shuffle(temp_p)
                    st.session_state.fixed_teams = [temp_p[i:i+2] for i in range(0, len(temp_p), 2)]

                df_temp = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values("Point", ascending=False)
                ranked = df_temp.index.tolist()
                num_courts = len(st.session_state.players) // 4
                new_m = []

                for i in range(num_courts):
                    if g_format == "Mexicano" and st.session_state.round_number > 1:
                        if p_type == "Skiftende makker":
                            p = ranked[i*4 : (i*4)+4]
                            h1, h2 = [p[0], p[3]], [p[1], p[2]]
                        else:
                            assigned = []
                            seen = set()
                            for p in ranked:
                                for team in st.session_state.fixed_teams:
                                    if p in team and tuple(sorted(team)) not in seen:
                                        assigned.append(team)
                                        seen.add(tuple(sorted(team)))
                            h1, h2 = assigned[i*2], assigned[i*2+1]
                    else:
                        if p_type == "Skiftende makker":
                            p_pool = st.session_state.players.copy() if i == 0 else p_pool
                            random.shuffle(p_pool)
                            p = [p_pool.pop() for _ in range(4)]
                            h1, h2 = [p[0], p[1]], [p[2], p[3]]
                        else:
                            t_pool = st.session_state.fixed_teams.copy() if i == 0 else t_pool
                            random.shuffle(t_pool)
                            h1, h2 = t_pool.pop(), t_pool.pop()
                    new_m.append({"Bane": f"Bane {i+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams, st.session_state.history)
                st.rerun()

        if st.session_state.get('matches'):
            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    c1, c2 = st.columns(2)
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    s2 = 32 - s1
                    c2.info(f"{' & '.join(m['H2'])}: **{s2} point**")
                    st.session_state.matches[i]['S1'] = s1
                    st.session_state.matches[i]['S2'] = s2

            if st.button("✅ Gem Runde"):
                current_round_log = {"Runde": st.session_state.round_number, "Kampe": []}
                for m in st.session_state.matches:
                    s1, s2 = m['S1'], m['S2']
                    # Log resultatet
                    current_round_log["Kampe"].append(f"{m['Bane']}: {' & '.join(m['H1'])} ({s1}) vs {' & '.join(m['H2'])} ({s2})")
                    # Opdater leaderboard
                    for p in m['H1']:
                        st.session_state.leaderboard[p]["Point"] += s1
                        st.session_state.leaderboard[p]["Kampe"] += 1
                        if s1 > s2: st.session_state.leaderboard[p]["V"] += 1
                    for p in m['H2']:
                        st.session_state.leaderboard[p]["Point"] += s2
                        st.session_state.leaderboard[p]["Kampe"] += 1
                        if s2 > s1: st.session_state.leaderboard[p]["V"] += 1
                
                st.session_state.history.append(current_round_log)
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams, st.session_state.history)
                st.rerun()

with tab2:
    if st.session_state.get('leaderboard'):
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        st.table(df.sort_values(["Point", "V"], ascending=False).reset_index().rename(columns={'index': 'Spiller'}))

with tab3:
    st.subheader("📜 Historik over runder")
    if not st.session_state.history:
        st.write("Ingen runder er afsluttet endnu.")
    else:
        for entry in reversed(st.session_state.history):
            with st.expander(f"Runde {entry['Runde']}"):
                for kamp in entry['Kampe']:
                    st.write(kamp)
