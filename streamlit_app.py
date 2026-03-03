import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide")

# --- DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams):
    data = {
        "tournament_id": tid,
        "round_number": round_num,
        "leaderboard": leaderboard,
        "matches": matches,
        "players": players,
        "fixed_teams": fixed_teams
    }
    try:
        conn.table("tournaments").upsert(data).execute()
        st.toast(f"✅ Alt data gemt for ID: {tid}")
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")

def load_from_supabase(tid):
    try:
        res = conn.query("*", table="tournaments", ttl=0).eq("tournament_id", tid).execute()
        return res.data[0] if res.data else None
    except:
        return None

# --- APP START ---
st.title("🎾 Padel Master - Database Mode")

# 1. Indtast ID først
tid = st.text_input("Indtast Turnerings-ID (f.eks: Fredag_Hørning)", "").strip()

if not tid:
    st.info("👋 Indtast et ID for at åbne din turnering.")
    st.stop()

# 2. HENT DATA FRA SKYEN (KUN VED NYT ID ELLER OPSTART)
if 'current_tid' not in st.session_state or st.session_state.current_tid != tid:
    cloud_data = load_from_supabase(tid)
    if cloud_data:
        st.session_state.players = cloud_data.get('players', [])
        st.session_state.leaderboard = cloud_data.get('leaderboard', {})
        st.session_state.round_number = cloud_data.get('round_number', 1)
        st.session_state.matches = cloud_data.get('matches', [])
        st.session_state.fixed_teams = cloud_data.get('fixed_teams', [])
        st.success(f"📂 Turnering fundet! Gendannet {len(st.session_state.players)} spillere.")
    else:
        # Hvis ID er helt nyt
        st.session_state.players = []
        st.session_state.leaderboard = {}
        st.session_state.round_number = 1
        st.session_state.matches = []
        st.session_state.fixed_teams = []
        st.info("🆕 Nyt ID fundet. Indtast spillere i menuen til venstre for at starte.")
    st.session_state.current_tid = tid

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Setup")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    
    # Vis de gemte spillere i tekstfeltet
    p_in = st.text_area("Spillere (ét pr. linje)", value="\n".join(st.session_state.players))
    
    if st.button("🚀 START / OPDATER SPILLERE"):
        names = [n.strip() for n in p_in.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.players = names
            # Kun nulstil leaderboard hvis det er helt nyt
            if not st.session_state.leaderboard:
                st.session_state.leaderboard = {n: {"Point": 0, "V": 0, "Diff": 0, "Kampe": 0} for n in names}
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, st.session_state.matches, names, st.session_state.fixed_teams)
            st.rerun()
        else:
            st.error("Antal skal gå op i 4!")

    if st.button("🔴 SLET ALT (Nulstil ID)"):
        st.session_state.leaderboard = {}
        st.session_state.players = []
        st.session_state.round_number = 1
        st.session_state.matches = []
        save_to_supabase(tid, 1, {}, [], [], [])
        st.rerun()

# --- HOVEDLOGIK ---
tab1, tab2 = st.tabs(["🎾 Kampe", "📊 Stilling"])

with tab1:
    if not st.session_state.players:
        st.warning("👈 Indtast spillere i menuen til venstre for at komme i gang.")
    else:
        st.subheader(f"Runde {st.session_state.round_number}")

        if not st.session_state.matches:
            if st.button("🎲 Generér Runde"):
                # Sortering til Mexicano
                df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "V", "Diff"], ascending=False)
                ranked = df_rank.index.tolist()
                
                num_courts = len(st.session_state.players) // 4
                new_m = []

                for i in range(num_courts):
                    # Mexicano (1&4 vs 2&3)
                    if g_format == "Mexicano" and st.session_state.round_number > 1:
                        p = ranked[i*4 : (i*4)+4]
                        h1, h2 = [p[0], p[3]], [p[1], p[2]]
                    else:
                        # Americano / Runde 1 (Tilfældig)
                        pool = st.session_state.players.copy() if i == 0 else pool
                        random.shuffle(pool)
                        p = [pool.pop() for _ in range(4)]
                        h1, h2 = [p[0], p[1]], [p[2], p[3]]
                    
                    new_m.append({"Bane": f"Bane {i+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams)
                st.rerun()

        # Vis kampe og gem point
        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                st.write(f"### {m['Bane']}")
                c1, c2 = st.columns(2)
                s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                s2 = 32 - s1
                c2.info(f"{' & '.join(m['H2'])}: **{s2} point**")
                st.session_state.matches[i]['S1'] = s1
                st.session_state.matches[i]['S2'] = s2

        if st.session_state.matches and st.button("✅ GEM RUNDE & NÆSTE"):
            for m in st.session_state.matches:
                s1, s2 = m['S1'], m['S2']
                # Opdater alle 4 spillere
                for p in m['H1']:
                    st.session_state.leaderboard[p]["Point"] += s1
                    st.session_state.leaderboard[p]["Diff"] += (s1 - s2)
                    st.session_state.leaderboard[p]["Kampe"] += 1
                    if s1 > s2: st.session_state.leaderboard[p]["V"] += 1
                for p in m['H2']:
                    st.session_state.leaderboard[p]["Point"] += s2
                    st.session_state.leaderboard[p]["Diff"] += (s2 - s1)
                    st.session_state.leaderboard[p]["Kampe"] += 1
                    if s2 > s1: st.session_state.leaderboard[p]["V"] += 1
            
            st.session_state.round_number += 1
            st.session_state.matches = []
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams)
            st.rerun()

with tab2:
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        st.table(df.sort_values(["Point", "V", "Diff"], ascending=False).reset_index().rename(columns={'index': 'Spiller'}))
