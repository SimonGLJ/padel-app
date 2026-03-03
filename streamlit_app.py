import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
# Vi pakker forbindelsen ind i en try-block for at se om dine Secrets virker
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error(f"Kunne ikke finde Supabase-nøgler. Tjek 'Secrets' i Streamlit Cloud! Fejl: {e}")

def load_from_supabase(tid):
    try:
        res = conn.table("tournaments").select("*").eq("tournament_id", tid.lower()).execute()
        return res.data[0] if res.data and len(res.data) > 0 else None
    except Exception: return None

def save_to_supabase(payload):
    try:
        # Vi bruger upsert (opdater hvis findes, ellers indsæt)
        res = conn.table("tournaments").upsert(payload).execute()
        if res.data:
            st.toast(f"✅ Gemt i skyen: {payload['tournament_id']}")
        return res
    except Exception as e:
        st.error(f"❌ KUNNE IKKE GEMME: {e}")
        st.info("Tjek om dine kolonnenavne i Supabase er: tournament_id, round_number, leaderboard, matches, players, fixed_teams, history, max_rounds, court_names")

# --- 2. INITIALISERING ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, 
        "matches": [], "fixed_teams": [], "history": [], 
        "max_rounds": 7, "current_tid": None, "court_names": []
    })

st.title("🎾 Padel Master Pro")
tid_raw = st.text_input("📍 Indtast Turnerings-ID", value=st.session_state.current_tid if st.session_state.current_tid else "").strip()
tid_input = tid_raw.lower() if tid_raw else None

# HENT DATA HVIS ID ÆNDRES
if tid_input and tid_input != st.session_state.current_tid:
    data = load_from_supabase(tid_input)
    if data:
        st.session_state.update({
            "current_tid": tid_input, "players": data.get('players', []),
            "leaderboard": data.get('leaderboard', {}), "round_number": data.get('round_number', 1),
            "matches": data.get('matches', []), "fixed_teams": data.get('fixed_teams', []),
            "history": data.get('history', []), "max_rounds": data.get('max_rounds', 7),
            "court_names": data.get('court_names', [])
        })
        st.rerun()
    else:
        st.session_state.current_tid = tid_input

if not tid_input:
    st.info("Indtast et ID for at fortsætte.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opsætning")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    max_r = st.number_input("Runder før finale", 1, 20, value=st.session_state.max_rounds)
    
    p_input = st.text_area("Deltagere (ét navn pr. linje)", value="\n".join(st.session_state.players), height=150)
    
    if st.button("🚀 START TURNERING"):
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
            
            # GEM STRAKS
            payload = {
                "tournament_id": tid_input, "round_number": 1, "leaderboard": st.session_state.leaderboard,
                "matches": [], "players": names, "fixed_teams": list(st.session_state.fixed_teams),
                "history": [], "max_rounds": max_r, "court_names": []
            }
            save_to_supabase(payload)
            st.rerun()
        else: st.error("Antal skal gå op i 4!")

# --- 4. TABS ---
tab1, tab2, tab3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with tab1:
    if st.session_state.players:
        is_over = st.session_state.round_number > st.session_state.max_rounds + 1
        if is_over:
            st.header("🏆 Resultat for " + tid_input.upper())
            df_final = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
            st.dataframe(df_final.reset_index(), use_container_width=True)
            st.download_button("📥 Hent CSV", df_final.to_csv().encode('utf-8'), f"{tid_input}.csv")
        else:
            st.subheader(f"Runde {st.session_state.round_number}")
            if not st.session_state.matches:
                if st.button("🎲 Generer Kampe"):
                    # Genereringslogik (Mexicano/Americano)
                    df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
                    ranked = df.index.tolist()
                    new_m = []
                    for i in range(len(st.session_state.players) // 4):
                        p = ranked[i*4 : (i*4)+4] if g_format == "Mexicano" else random.sample(st.session_state.players, 4)
                        new_m.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[-1]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                    st.session_state.matches = new_m
                    st.rerun()

            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    s1 = st.number_input(f"{' & '.join(m['H1'])} vs {' & '.join(m['H2'])}", 0, 32, value=16, key=f"m_{i}")
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32-s1

            if st.session_state.matches and st.button("✅ Gem Runde"):
                # Opdater leaderboard...
                for m in st.session_state.matches:
                    for t, s, o in [(m['H1'], m['S1'], m['S2']), (m['H2'], m['S2'], m['S1'])]:
                        for p in t:
                            st.session_state.leaderboard[p]["Point"] += s
                            st.session_state.leaderboard[p]["PF"] += (s - o)
                
                st.session_state.history.append({"R": st.session_state.round_number, "K": [f"{m['S1']}-{m['S2']}" for m in st.session_state.matches]})
                st.session_state.round_number += 1
                st.session_state.matches = []
                
                # GEM ALTID TIL SKYEN VED RUNDESLUT
                payload = {
                    "tournament_id": tid_input, "round_number": st.session_state.round_number,
                    "leaderboard": st.session_state.leaderboard, "matches": [],
                    "players": st.session_state.players, "fixed_teams": list(st.session_state.fixed_teams),
                    "history": st.session_state.history, "max_rounds": st.session_state.max_rounds,
                    "court_names": st.session_state.court_names
                }
                save_to_supabase(payload)
                st.rerun()

with tab2:
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
        st.dataframe(df, use_container_width=True)
