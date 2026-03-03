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
        st.toast("☁️ Data gemt i skyen!")
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")

def load_from_supabase(tid):
    try:
        res = conn.query("*", table="tournaments", ttl=0).eq("tournament_id", tid).execute()
        return res.data[0] if res.data else None
    except:
        return None

# --- APP START ---
st.title("🎾 Padel Master Pro - 32 Point Format")

tid = st.text_input("Indtast Turnerings-ID (f.eks: Hørning2026)", "").strip()

if not tid:
    st.info("👋 Indtast et ID for at fortsætte eller starte en ny turnering.")
    st.stop()

# INITIALISERING / HENT DATA
if 'current_tid' not in st.session_state or st.session_state.current_tid != tid:
    cloud_data = load_from_supabase(tid)
    if cloud_data:
        st.session_state.players = cloud_data.get('players', [])
        st.session_state.leaderboard = cloud_data.get('leaderboard', {})
        st.session_state.round_number = cloud_data.get('round_number', 1)
        st.session_state.matches = cloud_data.get('matches', [])
        st.session_state.fixed_teams = cloud_data.get('fixed_teams', [])
        st.success(f"✅ Fortsætter turnering: {tid}")
    else:
        st.session_state.players = []
        st.session_state.leaderboard = {}
        st.session_state.round_number = 1
        st.session_state.matches = []
        st.session_state.fixed_teams = []
    st.session_state.current_tid = tid

# --- SIDEBAR: KONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Setup")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    p_in = st.text_area("Indtast spillere (ét navn pr. linje)", value="\n".join(st.session_state.players))
    
    if st.button("🚀 START / NULSTIL TURNERING"):
        names = [n.strip() for n in p_in.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.players = names
            st.session_state.leaderboard = {n: {"Point": 0, "V": 0, "Diff": 0, "Kampe": 0} for n in names}
            st.session_state.round_number = 1
            st.session_state.matches = []
            st.session_state.fixed_teams = []
            save_to_supabase(tid, 1, st.session_state.leaderboard, [], names, [])
            st.rerun()
        else:
            st.error("Antal spillere skal gå op i 4 (f.eks. 4, 8, 12, 16...)")

# --- HOVEDSKÆRM ---
tab1, tab2 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling"])

with tab1:
    if not st.session_state.players:
        st.warning("Indtast spillere i menuen til venstre.")
    else:
        st.subheader(f"Runde {st.session_state.round_number}")

        if not st.session_state.matches:
            if st.button("🎲 Generér Kampe"):
                # SIKRING AF FASTE HOLD
                if p_type == "Faste hold" and not st.session_state.fixed_teams:
                    temp_p = st.session_state.players.copy()
                    random.shuffle(temp_p)
                    st.session_state.fixed_teams = [temp_p[i:i+2] for i in range(0, len(temp_p), 2)]

                # RANGER SPILLERE/HOLD
                df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "V", "Diff"], ascending=False)
                ranked_names = df_rank.index.tolist()
                
                new_m = []
                num_courts = len(st.session_state.players) // 4

                # MEXICANO / RUNDE > 1 (STYRKEBASERET)
                if g_format == "Mexicano" and st.session_state.round_number > 1:
                    if p_type == "Skiftende makker":
                        for i in range(num_courts):
                            p = ranked_names[i*4 : (i*4)+4]
                            new_m.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                    else:
                        # Find hold baseret på spillernes samlede rangering
                        teams_to_use = []
                        seen_players = set()
                        for p in ranked_names:
                            if p not in seen_players:
                                for team in st.session_state.fixed_teams:
                                    if p in team:
                                        teams_to_use.append(team)
                                        seen_players.update(team)
                        for i in range(num_courts):
                            new_m.append({"Bane": f"Bane {i+1}", "H1": teams_to_use[i*2], "H2": teams_to_use[i*2+1], "S1": 16, "S2": 16})
                
                # AMERICANO / RUNDE 1 (TILFÆLDIG)
                else:
                    if p_type == "Skiftende makker":
                        temp_players = st.session_state.players.copy()
                        random.shuffle(temp_players)
                        for i in range(num_courts):
                            p = temp_players[i*4 : (i*4)+4]
                            new_m.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16})
                    else:
                        temp_teams = st.session_state.fixed_teams.copy()
                        random.shuffle(temp_teams)
                        for i in range(num_courts):
                            new_m.append({"Bane": f"Bane {i+1}", "H1": temp_teams[i*2], "H2": temp_teams[i*2+1], "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams)
                st.rerun()

        # VIS KAMPE
        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                if i == 0 and g_format == "Mexicano": st.info("🔝 VINDERBANE")
                st.write(f"### {m['Bane']}")
                c1, c2 = st.columns(2)
                
                # HOLD 1 POINT
                s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"m_{i}_s1")
                # HOLD 2 POINT BEREGNES AUTOMATISK
                s2 = 32 - s1
                
                c2.write(f"**{' & '.join(m['H2'])}**")
                c2.info(f"Point: {s2}")
                
                st.session_state.matches[i]['S1'] = s1
                st.session_state.matches[i]['S2'] = s2

        if st.session_state.matches and st.button("✅ GEM RESULTATER OG NÆSTE RUNDE"):
            for m in st.session_state.matches:
                p1, p2 = m['H1']
                p3, p4 = m['H2']
                s1, s2 = m['S1'], m['S2']
                
                # Opdater spillerstatistikker individuelt
                for p in [p1, p2]:
                    st.session_state.leaderboard[p]["Point"] += s1
                    st.session_state.leaderboard[p]["Kampe"] += 1
                    st.session_state.leaderboard[p]["Diff"] += (s1 - s2)
                    if s1 > s2: st.session_state.leaderboard[p]["V"] += 1
                
                for p in [p3, p4]:
                    st.session_state.leaderboard[p]["Point"] += s2
                    st.session_state.leaderboard[p]["Kampe"] += 1
                    st.session_state.leaderboard[p]["Diff"] += (s2 - s1)
                    if s2 > s1: st.session_state.leaderboard[p]["V"] += 1
            
            st.session_state.round_number += 1
            st.session_state.matches = []
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams)
            st.rerun()

with tab2:
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        df = df.sort_values(["Point", "V", "Diff"], ascending=False)
        st.table(df.reset_index().rename(columns={'index': 'Spiller'}))
