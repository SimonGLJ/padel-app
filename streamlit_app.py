import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide")

# --- DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def save_to_supabase(tid, round_num, leaderboard, matches, players):
    data = {
        "tournament_id": tid,
        "round_number": round_num,
        "leaderboard": leaderboard,
        "matches": matches,
        "players": players
    }
    try:
        conn.table("tournaments").upsert(data).execute()
        st.toast(f"☁️ Gemt i skyen for: {tid}")
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")

def load_from_supabase(tid):
    try:
        res = conn.query("*", table="tournaments", ttl=0).eq("tournament_id", tid).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"Kunne ikke forbinde til database: {e}")
        return None

# --- APP LOGIK START ---
st.title("🎾 Padel Master Pro")

# 1. INDTAST ID
tid = st.text_input("Indtast Turnerings-ID (f.eks: FredagsCup)", key="tid_input").strip()

if not tid:
    st.info("👋 Velkommen! Indtast et Turnerings-ID for at starte eller fortsætte.")
    st.stop()

# 2. HENT DATA HVIS ID ER ÆNDRET ELLER NYT
if "current_tid" not in st.session_state or st.session_state.current_tid != tid:
    with st.spinner('Henter data fra databasen...'):
        cloud_data = load_from_supabase(tid)
        
        if cloud_data:
            # Vi overskriver session_state med data fra databasen
            st.session_state.players = cloud_data.get('players', [])
            st.session_state.leaderboard = cloud_data.get('leaderboard', {})
            st.session_state.round_number = cloud_data.get('round_number', 1)
            st.session_state.matches = cloud_data.get('matches', [])
            st.success(f"✅ Turnering '{tid}' indlæst. {len(st.session_state.players)} spillere fundet.")
        else:
            # Nyt ID - nulstil alt
            st.session_state.players = []
            st.session_state.leaderboard = {}
            st.session_state.round_number = 1
            st.session_state.matches = []
            st.warning("🆕 Nyt ID. Ingen eksisterende data fundet.")
        
        st.session_state.current_tid = tid

# --- SIDEBAR OPSÆTNING ---
with st.sidebar:
    st.header("⚙️ Opsætning")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    
    # Her viser vi spillerne. Hvis de er hentet fra databasen, står de her allerede!
    p_text = "\n".join(st.session_state.get('players', []))
    p_input = st.text_area("Spillere (ét navn pr. linje)", value=p_text, height=200)
    
    if st.button("🚀 Gem/Opdater Spillere"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.players = names
            # Opret kun nyt leaderboard hvis det er tomt
            if not st.session_state.leaderboard:
                st.session_state.leaderboard = {n: {"Point": 0, "V": 0, "T": 0, "Kampe": 0} for n in names}
            
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, st.session_state.matches, names)
            st.rerun()
        else:
            st.error("Antallet skal gå op i 4!")

    if st.button("🗑️ Nulstil alt for dette ID"):
        save_to_supabase(tid, 1, {}, [], [])
        st.session_state.clear()
        st.rerun()

# --- HOVEDSKÆRM ---
tab1, tab2 = st.tabs(["🎾 Kampe", "📊 Stilling"])

with tab1:
    if not st.session_state.get('players'):
        st.warning("👈 Indtast spillere i menuen til venstre for at starte.")
    else:
        st.subheader(f"Runde {st.session_state.round_number}")
        
        # Generer kampe hvis de ikke findes
        if not st.session_state.get('matches'):
            if st.button("🎲 Generer nye kampe"):
                # Sortering til Mexicano
                df_temp = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values("Point", ascending=False)
                ranked = df_temp.index.tolist()
                
                num_courts = len(st.session_state.players) // 4
                new_m = []
                
                # Simpel lodtrækning (Americano/Runde 1)
                if g_format == "Americano" or st.session_state.round_number == 1:
                    pool = st.session_state.players.copy()
                    random.shuffle(pool)
                    for i in range(num_courts):
                        p = [pool.pop() for _ in range(4)]
                        new_m.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16})
                else:
                    # Mexicano (1&4 vs 2&3)
                    for i in range(num_courts):
                        p = ranked[i*4 : (i*4)+4]
                        new_m.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players)
                st.rerun()

        # Vis kampe
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

            if st.button("✅ Gem Resultater"):
                for m in st.session_state.matches:
                    s1, s2 = m['S1'], m['S2']
                    # Opdater alle 4 spillere individuelt
                    for p in m['H1']:
                        st.session_state.leaderboard[p]["Point"] += s1
                        st.session_state.leaderboard[p]["Kampe"] += 1
                        if s1 > s2: st.session_state.leaderboard[p]["V"] += 1
                        if s1 < s2: st.session_state.leaderboard[p]["T"] += 1
                    for p in m['H2']:
                        st.session_state.leaderboard[p]["Point"] += s2
                        st.session_state.leaderboard[p]["Kampe"] += 1
                        if s2 > s1: st.session_state.leaderboard[p]["V"] += 1
                        if s2 < s1: st.session_state.leaderboard[p]["T"] += 1
                
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players)
                st.rerun()

with tab2:
    if st.session_state.get('leaderboard'):
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        df = df.sort_values(["Point", "V"], ascending=False)
        st.table(df.reset_index().rename(columns={'index': 'Spiller'}))
