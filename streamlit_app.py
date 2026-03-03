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
        st.toast("☁️ Synkroniseret med databasen")
    except Exception as e:
        st.error(f"Databasefejl: {e}")

def load_from_supabase(tid):
    try:
        res = conn.query("*", table="tournaments", ttl=0).eq("tournament_id", tid).execute()
        return res.data[0] if res.data else None
    except:
        return None

# --- INITIALISERING ---
st.title("🎾 Padel Master Pro - 32 Point Edition")

tid = st.text_input("Indtast Turnerings-ID (f.eks: Hørning2026)", "").strip()

if not tid:
    st.info("👋 Indtast et ID for at fortsætte eller starte en ny turnering.")
    st.stop()

# HENT DATA VED LOGIN / ID SKIFT
if 'current_tid' not in st.session_state or st.session_state.current_tid != tid:
    cloud_data = load_from_supabase(tid)
    if cloud_data:
        st.session_state.players = cloud_data.get('players', [])
        st.session_state.leaderboard = cloud_data.get('leaderboard', {})
        st.session_state.round_number = cloud_data.get('round_number', 1)
        st.session_state.matches = cloud_data.get('matches', [])
        st.session_state.fixed_teams = cloud_data.get('fixed_teams', [])
        # Konverter keys til int for banenavne
        raw_courts = cloud_data.get('court_names', {})
        st.session_state.court_names = {int(k): v for k, v in raw_courts.items()} if raw_courts else {}
        st.success(f"✅ Hentet turnering: {tid}")
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
    g_format = st.selectbox("Format", ["Americano", "Mexicano"], index=0)
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"], index=0)
    p_in = st.text_area("Spillere (ét navn pr. linje)", value="\n".join(st.session_state.players))
    
    if st.button("🚀 START / NULSTIL TURNERING"):
        names = [n.strip() for n in p_in.split('\n') if n.strip()]
        if len(names) % 4 == 0 and names:
            st.session_state.players = names
            st.session_state.leaderboard = {n: {"Point": 0, "V": 0, "U": 0, "T": 0, "Diff": 0, "Kampe": 0} for n in names}
            st.session_state.round_number = 1
            st.session_state.matches = []
            st.session_state.fixed_teams = []
            save_to_supabase(tid, 1, st.session_state.leaderboard, [], names, [], {})
            st.rerun()
        else:
            st.error("Antal spillere skal gå op i 4!")

# --- HOVEDSKÆRM ---
tab1, tab2 = st.tabs(["🎾 Kampe", "📊 Stilling"])

with tab1:
    if not st.session_state.players:
        st.warning("Indtast spillere i menuen til venstre.")
    else:
        is_final = st.session_state.round_number == 8
        st.subheader(f"{'🏆 FINALERUNDE' if is_final else f'Runde {st.session_state.round_number}'}")

        if not st.session_state.matches and st.session_state.round_number <= 8:
            if st.button("🎲 Generér Kampe"):
                # Faste hold logik
                if p_type == "Faste hold" and not st.session_state.fixed_teams:
                    tp = st.session_state.players.copy()
                    random.shuffle(tp)
                    st.session_state.fixed_teams = [tp[i:i+2] for i in range(0, len(tp), 2)]
                
                # Rangering
                df_rank = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "V", "Diff"], ascending=False)
                ranked = df_rank.index.tolist()
                
                num_courts = len(ranked) // 4
                new_m = []
                
                for i in range(num_courts):
                    # Mexicano / Finale Logik (Styrkebaseret)
                    if is_final or (g_format == "Mexicano" and st.session_state.round_number > 1):
                        if p_type == "Skiftende makker":
                            p = ranked[i*4 : (i*4)+4]
                            h1, h2 = [p[0], p[3]], [p[1], p[2]]
                        else:
                            teams_to_assign = []
                            seen = set()
                            for p in ranked:
                                for team in st.session_state.fixed_teams:
                                    if p in team and tuple(sorted(team)) not in seen:
                                        teams_to_assign.append(team)
                                        seen.add(tuple(sorted(team)))
                            h1, h2 = teams_to_assign[i*2], teams_to_assign[i*2+1]
                    # Americano / Runde 1 (Tilfældig)
                    else:
                        if p_type == "Skiftende makker":
                            tp = ranked.copy()
                            random.shuffle(tp)
                            p = tp[i*4 : (i*4)+4]
                            h1, h2 = [p[0], p[1]], [p[2], p[3]]
                        else:
                            tt = st.session_state.fixed_teams.copy()
                            random.shuffle(tt)
                            h1, h2 = tt[i*2], tt[i*2+1]
                    
                    new_m.append({"Bane": f"Bane {i+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams, st.session_state.court_names)
                st.rerun()

        # Vis og indtast kampe
        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                if i == 0 and (g_format == "Mexicano" or is_final): st.info("🔝 VINDERBANE")
                st.write(f"### {m['Bane']}")
                
                c1, c2 = st.columns(2)
                # SIKRING: Max 32 point, og automatisk beregning af det andet hold
                s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"match_{i}_s1")
                s2 = 32 - s1
                c2.markdown(f"<div style='margin-top:25px;'><b>{' & '.join(m['H2'])}</b></div>", unsafe_allow_html=True)
                c2.info(f"Point: {s2}")
                
                st.session_state.matches[i]['S1'] = s1
                st.session_state.matches[i]['S2'] = s2

        if st.session_state.matches and st.button("✅ GEM RESULTATER"):
            for m in st.session_state.matches:
                s1, s2 = m['S1'], m['S2']
                # V/U/T logik
                res1 = "V" if s1 > s2 else ("T" if s1 < s2 else "U")
                res2 = "V" if s2 > s1 else ("T" if s2 < s1 else "U")
                
                for p in m['H1']:
                    st.session_state.leaderboard[p]["Point"] += s1
                    st.session_state.leaderboard[p][res1] += 1
                    st.session_state.leaderboard[p]["Kampe"] += 1
                    st.session_state.leaderboard[p]["Diff"] += (s1 - s2)
                for p in m['H2']:
                    st.session_state.leaderboard[p]["Point"] += s2
                    st.session_state.leaderboard[p][res2] += 1
                    st.session_state.leaderboard[p]["Kampe"] += 1
                    st.session_state.leaderboard[p]["Diff"] += (s2 - s1)
            
            st.session_state.round_number += 1
            st.session_state.matches = []
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams, st.session_state.court_names)
            st.rerun()

with tab2:
    if st.session_state.leaderboard:
        st.subheader("Rangliste")
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        # Sortering: Flest point, derefter flest sejre, derefter diff
        df = df.sort_values(["Point", "V", "Diff"], ascending=False)
        st.table(df.reset_index().rename(columns={'index': 'Spiller'}))
