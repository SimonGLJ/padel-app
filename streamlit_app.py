import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def load_from_supabase(tid):
    try:
        res = conn.table("tournaments").select("*").eq("tournament_id", tid).execute()
        return res.data[0] if res.data and len(res.data) > 0 else None
    except Exception: return None

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, history, max_rounds):
    data = {
        "tournament_id": tid, "round_number": round_num, "leaderboard": leaderboard,
        "matches": matches, "players": players, "fixed_teams": fixed_teams, 
        "history": history, "max_rounds": max_rounds
    }
    try:
        conn.table("tournaments").upsert(data).execute()
        st.toast(f"☁️ Gemt: {tid}")
    except Exception as e: st.error(f"Fejl: {e}")

# --- 2. INITIALISERING ---
st.title("🎾 Padel Master Pro")

tid = st.text_input("📍 Turnerings-ID", key="tid_input").strip()

if not tid:
    st.info("👋 Indtast et ID for at starte.")
    st.stop()

if "current_tid" not in st.session_state or st.session_state.current_tid != tid:
    cloud_data = load_from_supabase(tid)
    if cloud_data:
        st.session_state.update({
            "players": cloud_data.get('players', []),
            "leaderboard": cloud_data.get('leaderboard', {}),
            "round_number": cloud_data.get('round_number', 1),
            "matches": cloud_data.get('matches', []),
            "fixed_teams": cloud_data.get('fixed_teams', []),
            "history": cloud_data.get('history', []),
            "max_rounds": cloud_data.get('max_rounds', 7)
        })
    else:
        st.session_state.update({
            "players": [], "leaderboard": {}, "round_number": 1, "matches": [],
            "fixed_teams": [], "history": [], "max_rounds": 7
        })
    st.session_state.current_tid = tid

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Spilleform", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    max_r = st.number_input("Antal runder før finale", min_value=1, max_value=20, value=st.session_state.get('max_rounds', 7))
    st.session_state.max_rounds = max_r
    
    p_text = "\n".join(st.session_state.get('players', []))
    p_input = st.text_area("Deltagere (ét navn pr. linje)", value=p_text, height=150)
    
    if st.button("🚀 START NY TURNERING"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.players = names
            st.session_state.leaderboard = {n: {"Point": 0, "PF": 0, "V": 0, "U": 0, "T": 0} for n in names}
            st.session_state.round_number, st.session_state.matches, st.session_state.fixed_teams, st.session_state.history = 1, [], [], []
            save_to_supabase(tid, 1, st.session_state.leaderboard, [], names, [], [], max_r)
            st.rerun()
        else: st.error("Antal skal gå op i 4!")

# --- 4. HOVEDSKÆRM ---
tab1, tab2, tab3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with tab1:
    is_finale = st.session_state.round_number > st.session_state.max_rounds
    round_label = "🏆 FINALE-RUNDE" if is_finale else f"Runde {st.session_state.round_number} af {st.session_state.max_rounds}"
    st.subheader(round_label)

    if not st.session_state.get('matches'):
        if st.button("🎲 Generer Næste Kampe"):
            # Sortering
            df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
            ranked = df_rank.index.tolist()
            num_courts = len(st.session_state.players) // 4
            new_m = []

            for i in range(num_courts):
                if is_finale:
                    # --- FINALE LOGIK ---
                    if p_type == "Skiftende makker":
                        p = ranked[i*4 : (i*4)+4]
                        h1, h2 = [p[0], p[3]], [p[1], p[2]] # 1+4 mod 2+3
                    else:
                        # Faste hold finale: Hold 1 mod Hold 2 (Bane 1), Hold 3 mod Hold 4 (Bane 2)
                        assigned_teams = []
                        seen = set()
                        for p in ranked:
                            for team in st.session_state.fixed_teams:
                                if p in team and p not in seen:
                                    assigned_teams.append(team)
                                    for tp in team: seen.add(tp)
                        h1, h2 = assigned_teams[i*2], assigned_teams[i*2+1]
                else:
                    # --- ALMINDELIG RUNDE LOGIK (MEXICANO/AMERICANO) ---
                    if g_format == "Mexicano":
                        if p_type == "Skiftende makker":
                            p = ranked[i*4 : (i*4)+4]
                            h1, h2 = [p[0], p[3]], [p[1], p[2]]
                        else:
                            assigned_teams = []
                            seen = set()
                            for p in ranked:
                                for team in st.session_state.fixed_teams:
                                    if p in team and p not in seen:
                                        assigned_teams.append(team)
                                        for tp in team: seen.add(tp)
                            h1, h2 = assigned_teams[i*2], assigned_teams[i*2+1]
                    else:
                        # Americano
                        p_pool = st.session_state.players.copy() if i == 0 else p_pool
                        random.shuffle(p_pool)
                        p = [p_pool.pop() for _ in range(4)]
                        h1, h2 = [p[0], p[1]], [p[2], p[3]]

                new_m.append({"Bane": f"Bane {i+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
            
            st.session_state.matches = new_m
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds)
            st.rerun()

    # VIS KAMPE
    for i, m in enumerate(st.session_state.get('matches', [])):
        with st.container(border=True):
            st.write(f"### {m['Bane']}")
            c1, c2 = st.columns([2, 1])
            s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
            s2 = 32 - s1
            c2.write(f"**{' & '.join(m['H2'])}**")
            c2.info(f"Point: {s2}")
            st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, s2

    if st.session_state.get('matches') and st.button("✅ Gem Resultater"):
        for m in st.session_state.matches:
            s1, s2 = m['S1'], m['S2']
            for idx, p_list in enumerate([m['H1'], m['H2']]):
                score, opp_score = (s1, s2) if idx == 0 else (s2, s1)
                for p in p_list:
                    st.session_state.leaderboard[p]["Point"] += score
                    st.session_state.leaderboard[p]["PF"] += (score - opp_score)
                    if score > opp_score: st.session_state.leaderboard[p]["V"] += 1
                    elif score == opp_score: st.session_state.leaderboard[p]["U"] += 1
                    else: st.session_state.leaderboard[p]["T"] += 1
        
        st.session_state.history.append({"Runde": st.session_state.round_number, "Kampe": [f"{m['Bane']}: {m['S1']}-{m['S2']}" for m in st.session_state.matches]})
        st.session_state.round_number += 1
        st.session_state.matches = []
        save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds)
        st.rerun()

with tab2:
    st.subheader("🏆 Stilling")
    if st.session_state.get('leaderboard'):
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
        df.index.name = "Spiller"
        df = df.reset_index()
        df.index = df.index + 1
        
        # MOBILOPTIMERING: Brug dataframe i stedet for table for at tillade horisontal scroll
        st.dataframe(df, use_container_width=True)

with tab3:
    st.subheader("📜 Log")
    for entry in reversed(st.session_state.get('history', [])):
        with st.expander(f"Runde {entry['Runde']}"):
            for k in entry['Kampe']: st.write(k)
