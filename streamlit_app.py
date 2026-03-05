import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def save_to_supabase():
    if not st.session_state.current_tid:
        return
    payload = {
        "tournament_id": st.session_state.current_tid,
        "round_number": st.session_state.round_number,
        "leaderboard": st.session_state.leaderboard,
        "matches": st.session_state.matches,
        "players": st.session_state.players,
        "fixed_teams": list(st.session_state.fixed_teams),
        "history": st.session_state.history,
        "max_rounds": st.session_state.max_rounds,
        "court_names": st.session_state.court_names
    }
    try:
        conn.table("tournaments").upsert(payload).execute()
        st.toast(f"☁️ Synkroniseret: {st.session_state.current_tid}")
    except Exception as e:
        st.error(f"❌ Databasefejl: {e}")

# --- 2. INITIALISERING ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, 
        "matches": [], "fixed_teams": [], "history": [], 
        "max_rounds": 7, "current_tid": None, "court_names": []
    })

st.title("🎾 Padel Master Pro")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid if st.session_state.current_tid else "").strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data:
        d = res.data[0]
        st.session_state.update({
            "current_tid": tid_raw, "players": d.get('players', []),
            "leaderboard": d.get('leaderboard', {}), "round_number": d.get('round_number', 1),
            "matches": d.get('matches', []), "fixed_teams": d.get('fixed_teams', []),
            "history": d.get('history', []), "max_rounds": d.get('max_rounds', 7),
            "court_names": d.get('court_names', [])
        })
        st.rerun()
    else: st.session_state.current_tid = tid_raw

if not st.session_state.current_tid:
    st.info("👋 Indtast et ID for at starte.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    max_r = st.number_input("Runder før finale", 1, 20, value=st.session_state.max_rounds)
    
    c_names = []
    if g_format == "Mexicano" and st.session_state.players:
        st.subheader("🏟️ Baner")
        for i in range(len(st.session_state.players) // 4):
            val = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
            c_names.append(st.text_input(f"Bane {i+1}", value=val, key=f"c_n_{i}"))
        st.session_state.court_names = c_names

    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players), height=150)
    
    if st.button("🚀 START / NULSTIL"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.update({
                "players": names, "round_number": 1, "matches": [], "history": [],
                "leaderboard": {n: {"Point": 0, "PF": 0, "V": 0} for n in names},
                "max_rounds": max_r
            })
            if p_type == "Faste hold":
                # Vi tager navnene to og to som de står i listen
                st.session_state.fixed_teams = [names[i:i+2] for i in range(0, len(names), 2)]
            else:
                st.session_state.fixed_teams = []
            save_to_supabase()
            st.rerun()

# --- 4. TABS ---
tab1, tab2, tab3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log & Rediger"])

with tab1:
    if st.session_state.players:
        is_over = st.session_state.round_number > st.session_state.max_rounds + 1
        is_finale = st.session_state.round_number > st.session_state.max_rounds and not is_over

        if is_over:
            st.header("🏆 Slutresultat")
            df_f = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
            st.dataframe(df_f.reset_index().rename(columns={'index':'Spiller'}), use_container_width=True)
        else:
            if not st.session_state.matches:
                if st.button("🎲 Generer Næste Kampe"):
                    new_m = []
                    num_courts = len(st.session_state.players) // 4
                    
                    if p_type == "Faste hold":
                        # LOGIK FOR FASTE HOLD
                        teams_pool = list(st.session_state.fixed_teams)
                        
                        if is_finale or g_format == "Mexicano":
                            # Sorter hold efter gennemsnitlig point
                            team_ranks = []
                            for t in teams_pool:
                                avg_p = sum(st.session_state.leaderboard[p]["Point"] for p in t) / 2
                                team_ranks.append((t, avg_p))
                            team_ranks.sort(key=lambda x: x[1], reverse=True)
                            sorted_teams = [x[0] for x in team_ranks]
                            
                            for i in range(num_courts):
                                b_navn = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
                                h1 = sorted_teams[i*2]
                                h2 = sorted_teams[i*2+1]
                                new_m.append({"Bane": b_navn, "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                        else:
                            # Americano med faste hold (Tilfældig parring af hold)
                            random.shuffle(teams_pool)
                            for i in range(num_courts):
                                b_navn = f"Bane {i+1}"
                                h1 = teams_pool.pop()
                                h2 = teams_pool.pop()
                                new_m.append({"Bane": b_navn, "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                    
                    else:
                        # LOGIK FOR SKIFTENDE MAKKERE (Samme som v2.6)
                        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
                        ranked = df.index.tolist()
                        player_pool = st.session_state.players.copy()
                        random.shuffle(player_pool)
                        
                        for i in range(num_courts):
                            b_navn = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
                            if is_finale or g_format == "Mexicano":
                                p = ranked[i*4 : (i*4)+4]
                                h1, h2 = [p[0], p[3]], [p[1], p[2]]
                            else:
                                p = [player_pool.pop() for _ in range(4)]
                                h1, h2 = [p[0], p[1]], [p[2], p[3]]
                            new_m.append({"Bane": b_navn, "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                    
                    st.session_state.matches = new_m
                    save_to_supabase()
                    st.rerun()

            # Display Kampe
            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    c1, c2 = st.columns([2, 1])
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    s2 = 32 - s1
                    c2.info(f"{' & '.join(m['H2'])}: **{s2}**")
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, s2

            if st.session_state.matches and st.button("✅ Gem Resultater"):
                for m in st.session_state.matches:
                    for t, s, o in [(m['H1'], m['S1'], m['S2']), (m['H2'], m['S2'], m['S1'])]:
                        for p in t:
                            st.session_state.leaderboard[p]["Point"] += s
                            st.session_state.leaderboard[p]["PF"] += (s - o)
                            if s > o: st.session_state.leaderboard[p]["V"] += 1
                st.session_state.history.append({"R": st.session_state.round_number, "K": [f"{m['Bane']}: {m['S1']}-{m['S2']}" for m in st.session_state.matches]})
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase(); st.rerun()

with tab2:
    if st.session_state.leaderboard:
        df_v = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
        st.dataframe(df_v.reset_index().rename(columns={'index':'Spiller'}), use_container_width=True)

with tab3:
    st.subheader("🔧 Manuel Redigering")
    if st.session_state.players:
        p_edit = st.selectbox("Vælg spiller", st.session_state.players)
        c1, c2 = st.columns(2)
        new_p = c1.number_input("Point", value=st.session_state.leaderboard[p_edit]["Point"])
        new_pf = c2.number_input("PF", value=st.session_state.leaderboard[p_edit]["PF"])
        if st.button("💾 Opdater"):
            st.session_state.leaderboard[p_edit].update({"Point": new_p, "PF": new_pf})
            save_to_supabase(); st.success("Opdateret!")
    st.divider()
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['R']}"):
            for k in e['K']: st.write(k)
