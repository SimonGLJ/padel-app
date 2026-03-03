import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide")

# --- DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, court_names):
    data = {
        "tournament_id": tid,
        "round_number": round_num,
        "leaderboard": leaderboard,
        "matches": matches,
        "players": players,
        "fixed_teams": fixed_teams,
        "court_names": court_names
    }
    try:
        conn.table("tournaments").upsert(data).execute()
        st.toast("☁️ Gemt i skyen!")
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")

def load_from_supabase(tid):
    try:
        res = conn.query("*", table="tournaments", ttl=0).eq("tournament_id", tid).execute()
        return res.data[0] if res.data else None
    except:
        return None

# --- APP START ---
st.title("🎾 Padel Master Pro")

tid = st.text_input("Indtast Turnerings-ID (f.eks: FredagsCup2026)", "").strip()

if not tid:
    st.info("👋 Indtast et ID for at fortsætte eller starte en ny turnering.")
    st.stop()

# HENT DATA VED LOGIN
if 'current_tid' not in st.session_state or st.session_state.current_tid != tid:
    cloud_data = load_from_supabase(tid)
    if cloud_data:
        st.session_state.players = cloud_data['players']
        st.session_state.leaderboard = cloud_data['leaderboard']
        st.session_state.round_number = cloud_data['round_number']
        st.session_state.matches = cloud_data['matches']
        st.session_state.fixed_teams = cloud_data['fixed_teams']
        st.session_state.court_names = {int(k): v for k, v in cloud_data['court_names'].items()}
        st.success(f"✅ Fortsætter '{tid}' fra runde {st.session_state.round_number}")
    else:
        st.session_state.players = []
        st.session_state.leaderboard = {}
        st.session_state.round_number = 1
        st.session_state.matches = []
        st.session_state.fixed_teams = []
        st.session_state.court_names = {}
    st.session_state.current_tid = tid

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Setup")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende", "Faste"])
    p_in = st.text_area("Spillere", value="\n".join(st.session_state.players))
    
    if st.button("🚀 Start / Reset"):
        names = [n.strip() for n in p_in.split('\n') if n.strip()]
        if len(names) % 4 == 0 and names:
            st.session_state.players = names
            st.session_state.leaderboard = {n: {"Point": 0, "V": 0, "Diff": 0} for n in names}
            st.session_state.round_number = 1
            st.session_state.matches = []
            st.session_state.fixed_teams = []
            save_to_supabase(tid, 1, st.session_state.leaderboard, [], names, [], {})
            st.rerun()

# --- KAMPE ---
tab1, tab2 = st.tabs(["🎾 Kampe", "📊 Stilling"])

with tab1:
    if st.session_state.players:
        if not st.session_state.matches:
            if st.button("🎲 Start ny runde"):
                # Simpel lodtrækning/parring
                if p_type == "Faste" and not st.session_state.fixed_teams:
                    tp = st.session_state.players.copy()
                    random.shuffle(tp)
                    st.session_state.fixed_teams = [tp[i:i+2] for i in range(0, len(tp), 2)]
                
                # Sortering (Mexicano vs Americano)
                df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values("Point", ascending=False)
                ranked = df_rank.index.tolist()
                
                # Her genereres kampe (1&4 vs 2&3)
                num_courts = len(ranked) // 4
                new_m = []
                for i in range(num_courts):
                    if g_format == "Mexicano" and st.session_state.round_number > 1:
                        p = ranked[i*4 : (i*4)+4]
                        h1, h2 = [p[0], p[3]], [p[1], p[2]]
                    else:
                        p = ranked.copy()
                        random.shuffle(p)
                        h1, h2 = [p[0], p[1]], [p[2], p[3]]
                    new_m.append({"Bane": f"Bane {i+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams, {})
                st.rerun()

        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                st.write(f"### {m['Bane']}")
                s1 = st.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=m['S1'], key=f"s_{i}")
                st.session_state.matches[i]['S1'] = s1
                st.session_state.matches[i]['S2'] = 32 - s1
                st.write(f"Mod: {' & '.join(m['H2'])} ({32-s1} point)")

        if st.session_state.matches and st.button("✅ Gem Runde"):
            for m in st.session_state.matches:
                s1, s2 = m['S1'], m['S2']
                res1 = "V" if s1 > s2 else "T"
                res2 = "V" if s2 > s1 else "T"
                for p in m['H1']:
                    st.session_state.leaderboard[p]["Point"] += s1
                for p in m['H2']:
                    st.session_state.leaderboard[p]["Point"] += s2
            
            st.session_state.round_number += 1
            st.session_state.matches = []
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams, {})
            st.rerun()

with tab2:
    if st.session_state.leaderboard:
        st.table(pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values("Point", ascending=False))
