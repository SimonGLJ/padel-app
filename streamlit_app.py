import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide")

# --- 1. DATABASE FORBINDELSE ---
# Bruger den nyeste standard for st-supabase-connection
conn = st.connection("supabase", type=SupabaseConnection)

def load_from_supabase(tid):
    try:
        # Henter data for det specifikke Turnerings-ID
        res = conn.table("tournaments").select("*").eq("tournament_id", tid).execute()
        return res.data[0] if res.data and len(res.data) > 0 else None
    except Exception as e:
        st.error(f"Database-læsefejl: {e}")
        return None

def save_to_supabase(tid, round_num, leaderboard, matches, players):
    data = {
        "tournament_id": tid,
        "round_number": round_num,
        "leaderboard": leaderboard,
        "matches": matches,
        "players": players
    }
    try:
        # Upsert opdaterer eksisterende række eller opretter en ny
        conn.table("tournaments").upsert(data).execute()
        st.toast(f"☁️ Synkroniseret med skyen: {tid}")
    except Exception as e:
        st.error(f"Database-gemmefejl: {e}")

# --- 2. APP LOGIK START ---
st.title("🎾 Padel Master Pro")

# Indtast Turnerings-ID (Nøglen til din data)
tid = st.text_input("Indtast Turnerings-ID (f.eks: FredagsCup2026)", key="tid_input").strip()

if not tid:
    st.info("👋 Velkommen! Indtast et Turnerings-ID for at starte eller fortsætte.")
    st.stop()

# HENT DATA HVIS ID ER ÆNDRET ELLER APPEN GENSTARTER
if "current_tid" not in st.session_state or st.session_state.current_tid != tid:
    with st.spinner('Henter data fra databasen...'):
        cloud_data = load_from_supabase(tid)
        
        if cloud_data:
            st.session_state.players = cloud_data.get('players', [])
            st.session_state.leaderboard = cloud_data.get('leaderboard', {})
            st.session_state.round_number = cloud_data.get('round_number', 1)
            st.session_state.matches = cloud_data.get('matches', [])
            st.success(f"✅ Turnering '{tid}' indlæst. {len(st.session_state.players)} spillere fundet.")
        else:
            st.session_state.players = []
            st.session_state.leaderboard = {}
            st.session_state.round_number = 1
            st.session_state.matches = []
            st.warning("🆕 Nyt ID fundet. Indtast spillere for at starte.")
        
        st.session_state.current_tid = tid

# --- 3. SIDEBAR OPSÆTNING ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    
    # Viser de gemte spillere i tekstfeltet
    p_text = "\n".join(st.session_state.get('players', []))
    p_input = st.text_area("Deltagere (ét navn pr. linje)", value=p_text, height=250)
    
    if st.button("🚀 Gem/Opdater Spillere"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.players = names
            # Initialiser leaderboard hvis det er tomt
            if not st.session_state.leaderboard:
                st.session_state.leaderboard = {n: {"Point": 0, "V": 0, "Kampe": 0} for n in names}
            
            save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, st.session_state.matches, names)
            st.rerun()
        else:
            st.error("Antallet af spillere skal gå op i 4!")

    st.divider()
    if st.button("🗑️ Nulstil alt for dette ID"):
        save_to_supabase(tid, 1, {}, [], [])
        st.session_state.clear()
        st.rerun()

# --- 4. HOVEDSKÆRM ---
tab1, tab2 = st.tabs(["🎾 Aktuel Runde", "📊 Stilling & Statistik"])

with tab1:
    if not st.session_state.get('players'):
        st.warning("👈 Indtast spillere i menuen til venstre for at starte.")
    else:
        st.subheader(f"Runde {st.session_state.round_number}")
        
        # Generer kampe hvis de ikke findes for denne runde
        if not st.session_state.get('matches'):
            if st.button("🎲 Generer nye kampe"):
                # Sortering til Mexicano (Baseret på point)
                df_temp = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values("Point", ascending=False)
                ranked = df_temp.index.tolist()
                
                num_courts = len(st.session_state.players) // 4
                new_m = []
                
                # Americano eller Runde 1 (Tilfældig lodtrækning)
                if g_format == "Americano" or st.session_state.round_number == 1:
                    pool = st.session_state.players.copy()
                    random.shuffle(pool)
                    for i in range(num_courts):
                        p = [pool.pop() for _ in range(4)]
                        new_m.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16})
                else:
                    # Mexicano (1&4 vs 2&3 styrkebaseret)
                    for i in range(num_courts):
                        p = ranked[i*4 : (i*4)+4]
                        new_m.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players)
                st.rerun()

        # Vis kampe og indtast resultater
        if st.session_state.get('matches'):
            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    c1, c2 = st.columns(2)
                    
                    # HOLD 1
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    # HOLD 2 (Beregnes automatisk så summen altid er 32)
                    s2 = 32 - s1
                    
                    c2.markdown(f"<br><b>{' & '.join(m['H2'])}</b>", unsafe_allow_html=True)
                    c2.info(f"Point: {s2}")
                    
                    # Opdater midlertidigt i session_state
                    st.session_state.matches[i]['S1'] = s1
                    st.session_state.matches[i]['S2'] = s2

            if st.button("✅ Gem Runde & Gå til Næste"):
                # Opdater leaderboard for alle spillere
                for m in st.session_state.matches:
                    s1, s2 = m['S1'], m['S2']
                    # Hold 1 spillere
                    for p in m['H1']:
                        st.session_state.leaderboard[p]["Point"] += s1
                        st.session_state.leaderboard[p]["Kampe"] += 1
                        if s1 > s2: st.session_state.leaderboard[p]["V"] += 1
                    # Hold 2 spillere
                    for p in m['H2']:
                        st.session_state.leaderboard[p]["Point"] += s2
                        st.session_state.leaderboard[p]["Kampe"] += 1
                        if s2 > s1: st.session_state.leaderboard[p]["V"] += 1
                
                # Gør klar til næste runde og gem alt i databasen
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase(tid, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players)
                st.rerun()

with tab2:
    if st.session_state.get('leaderboard'):
        st.subheader("Rangliste")
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        # Sorter efter Point og derefter Sejre
        df = df.sort_values(["Point", "V"], ascending=False)
        st.table(df.reset_index().rename(columns={'index': 'Spiller'}))
