import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def load_from_supabase(tid):
    try:
        # Vi henter specifikt rækken med det ID
        res = conn.table("tournaments").select("*").eq("tournament_id", tid.lower()).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        st.error(f"Kunne ikke hente data: {e}")
        return None

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, history, max_rounds, court_names):
    payload = {
        "tournament_id": tid.lower(),
        "round_number": round_num,
        "leaderboard": leaderboard,
        "matches": matches,
        "players": players,
        "fixed_teams": list(fixed_teams) if fixed_teams else [],
        "history": history,
        "max_rounds": max_rounds,
        "court_names": court_names
    }
    try:
        # Vi bruger upsert med 'on_conflict' for at sikre, at den overskriver eksisterende ID
        res = conn.table("tournaments").upsert(payload, on_conflict="tournament_id").execute()
        if res.data:
            st.toast(f"✅ Gemt i skyen: {tid.lower()}")
        else:
            st.error("⚠️ Data blev sendt, men ikke bekræftet af databasen.")
    except Exception as e:
        st.error(f"❌ DATABASE FEJL: {e}")
        st.info("Tjek om din Supabase tabel har 'tournament_id' som Primary Key.")

# --- 2. INITIALISERING ---
if "current_tid" not in st.session_state:
    st.session_state.update({"players":[], "leaderboard":{}, "round_number":1, "matches":[], "fixed_teams":[], "history":[], "max_rounds":7, "current_tid":None, "court_names":[]})

st.title("🎾 Padel Master Pro")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid if st.session_state.current_tid else "").strip()
tid_input = tid_raw.lower()

if tid_input and tid_input != st.session_state.current_tid:
    cloud_data = load_from_supabase(tid_input)
    if cloud_data:
        st.session_state.update({
            "current_tid": tid_input, "players": cloud_data.get('players', []),
            "leaderboard": cloud_data.get('leaderboard', {}), "round_number": cloud_data.get('round_number', 1),
            "matches": cloud_data.get('matches', []), "fixed_teams": cloud_data.get('fixed_teams', []),
            "history": cloud_data.get('history', []), "max_rounds": cloud_data.get('max_rounds', 7),
            "court_names": cloud_data.get('court_names', [])
        })
        st.rerun()
    else:
        st.session_state.current_tid = tid_input

if not tid_input:
    st.info("Indtast et ID for at starte.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opsætning")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    max_r = st.number_input("Runder før finale", 1, 20, value=st.session_state.max_rounds)
    
    c_names = []
    if g_format == "Mexicano" and st.session_state.players:
        st.divider()
        st.subheader("🏟️ Baner")
        for i in range(len(st.session_state.players) // 4):
            val = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
            c_names.append(st.text_input(f"Bane {i+1}", value=val, key=f"c_{i}"))
        st.session_state.court_names = c_names

    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players), height=150)
    
    if st.button("🚀 START / GEM"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0:
            st.session_state.update({
                "players": names, "round_number": 1, "matches": [], "history": [],
                "leaderboard": {n: {"Point": 0, "PF": 0, "V": 0, "U": 0, "T": 0} for n in names},
                "max_rounds": max_r
            })
            if p_type == "Faste hold":
                random.shuffle(names)
                st.session_state.fixed_teams = [names[i:i+2] for i in range(0, len(names), 2)]
            
            save_to_supabase(tid_input, 1, st.session_state.leaderboard, [], names, st.session_state.fixed_teams, [], max_r, c_names)
            st.rerun()

# --- 4. HOVEDSKÆRM ---
tab1, tab2, tab3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with tab1:
    if not st.session_state.players:
        st.warning("Brug menuen til venstre for at tilføje spillere og trykke 'Start'.")
    else:
        is_over = st.session_state.round_number > st.session_state.max_rounds + 1
        is_finale = st.session_state.round_number > st.session_state.max_rounds and not is_over

        if is_over:
            st.header("🏆 Slutresultat")
            df_final = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
            st.dataframe(df_final.reset_index(), use_container_width=True)
            csv = df_final.to_csv().encode('utf-8')
            st.download_button("📥 Download CSV", csv, f"{tid_input}.csv")
        else:
            st.subheader("🔥 FINALE" if is_finale else f"Runde {st.session_state.round_number}")
            
            if not st.session_state.matches:
                if st.button("🎲 Generer Næste Kampe"):
                    df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
                    ranked = df.index.tolist()
                    new_m = []
                    for i in range(len(st.session_state.players) // 4):
                        b_navn = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
                        if i == 0 and g_format == "Mexicano": b_navn = f"🏆 {b_navn}"
                        
                        if is_finale or g_format == "Mexicano":
                            if p_type == "Skiftende makker":
                                p = ranked[i*4 : (i*4)+4]
                                h1, h2 = [p[0], p[3]], [p[1], p[2]]
                            else:
                                assigned, seen = [], set()
                                for p_n in ranked:
                                    for team in st.session_state.fixed_teams:
                                        t_tup = tuple(sorted(team))
                                        if p_n in team and t_tup not in seen:
                                            assigned.append(team); seen.add(t_tup)
                                h1, h2 = assigned[i*2], assigned[i*2+1]
                        else:
                            p_pool = st.session_state.players.copy() if i == 0 else p_pool
                            random.shuffle(p_pool)
                            p = [p_pool.pop() for _ in range(4)]
                            h1, h2 = [p[0], p[1]], [p[2], p[3]]
                        new_m.append({"Bane": b_navn, "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                    st.session_state.matches = new_m
                    save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds, st.session_state.court_names)
                    st.rerun()

            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    s1 = st.number_input(f"{' & '.join(m['H1'])} vs {' & '.join(m['H2'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32-s1

            if st.session_state.matches and st.button("✅ Gem Resultater"):
                for m in st.session_state.matches:
                    for t, s, o in [(m['H1'], m['S1'], m['S2']), (m['H2'], m['S2'], m['S1'])]:
                        for p in t:
                            st.session_state.leaderboard[p]["Point"] += s
                            st.session_state.leaderboard[p]["PF"] += (s - o)
                st.session_state.history.append({"R": st.session_state.round_number, "K": [f"{m['Bane']}: {m['S1']}-{m['S2']}" for m in st.session_state.matches]})
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds, st.session_state.court_names)
                st.rerun()

with tab2:
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
        st.dataframe(df.reset_index().rename(columns={'index':'Spiller'}), use_container_width=True)

with tab3:
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['R']}"):
            for k in e['K']: st.write(k)
