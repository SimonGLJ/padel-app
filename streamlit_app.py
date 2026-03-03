import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random
import datetime

st.set_page_config(page_title="DEBUG - Padel Master Pro", layout="wide")

# --- 1. DATABASE FORBINDELSE ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
    st.sidebar.success("✅ Forbundet til Supabase-klient")
except Exception as e:
    st.sidebar.error(f"❌ Forbindelse mislykkedes: {e}")

def save_debug(payload):
    """Gemmer data og viser et debug-panel med svaret"""
    st.session_state.last_debug_time = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        # Forsøg at sende data
        res = conn.table("tournaments").upsert(payload).execute()
        st.session_state.last_status = "SUCCES"
        st.session_state.last_response = res.data
        return res
    except Exception as e:
        st.session_state.last_status = "FEJL"
        st.session_state.last_response = str(e)
        return None

# --- INITIALISERING AF STATE ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, "matches": [], 
        "fixed_teams": [], "history": [], "max_rounds": 7, "current_tid": None, 
        "court_names": [], "last_status": "Ingen forsøg", "last_response": "", "last_debug_time": "-"
    })

st.title("🎾 Padel Master Pro - Debug Mode")

# --- 2. ID INPUT & AUTOMATISK HENTNING ---
tid_raw = st.text_input("📍 Indtast Turnerings-ID", value=st.session_state.current_tid if st.session_state.current_tid else "").strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    try:
        res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
        if res.data and len(res.data) > 0:
            d = res.data[0]
            st.session_state.update({
                "current_tid": tid_raw, "players": d.get('players', []),
                "leaderboard": d.get('leaderboard', {}), "round_number": d.get('round_number', 1),
                "matches": d.get('matches', []), "fixed_teams": d.get('fixed_teams', []),
                "history": d.get('history', []), "max_rounds": d.get('max_rounds', 7),
                "court_names": d.get('court_names', [])
            })
            st.success(f"✅ Data hentet for '{tid_raw}'")
            st.rerun()
        else:
            st.session_state.current_tid = tid_raw
            st.info(f"ℹ️ ID '{tid_raw}' findes ikke i databasen endnu.")
    except Exception as e:
        st.error(f"Fejl ved hentning: {e}")

if not tid_raw:
    st.stop()

# --- 3. SIDEBAR OPSÆTNING ---
with st.sidebar:
    st.header("⚙️ Indstillinger")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    max_r = st.number_input("Runder", 1, 20, value=st.session_state.max_rounds)
    p_input = st.text_area("Spillere (en pr. linje)", value="\n".join(st.session_state.players))
    
    if st.button("🚀 START & GEM"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0:
            st.session_state.update({
                "players": names, "round_number": 1, "matches": [], "history": [],
                "leaderboard": {n: {"Point": 0, "PF": 0} for n in names}, "max_rounds": max_r
            })
            # DEBUG GEM
            payload = {
                "tournament_id": tid_raw, "round_number": 1, 
                "leaderboard": st.session_state.leaderboard, "players": names,
                "matches": [], "fixed_teams": [], "history": [], 
                "max_rounds": max_r, "court_names": []
            }
            save_debug(payload)
            st.rerun()

# --- 4. DEBUG PANEL (DETTE FINDER FEJLEN) ---
st.divider()
with st.expander("🛠️ DATABASE DEBUG LOG (Åbn for at se fejl)", expanded=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", st.session_state.last_status)
    c2.metric("Sidste forsøg", st.session_state.last_debug_time)
    
    if st.session_state.last_status == "FEJL":
        st.error(f"**Rå fejlbesked fra Supabase:**\n\n{st.session_state.last_response}")
        st.info("💡 Hvis der står 'column does not exist', skal du tilføje kolonnen i Supabase Dashboard.")
    else:
        st.write("**Sidste svar fra server:**", st.session_state.last_response)

# --- 5. KAMPE (Simpel version for test) ---
if st.session_state.players:
    st.subheader(f"Runde {st.session_state.round_number}")
    if st.button("🎲 Generer Kampe & Gem"):
        # Simpel generering for test
        p = st.session_state.players.copy()
        random.shuffle(p)
        new_m = [{"Bane": "Bane 1", "H1": [p[0], p[1]], "H2": [p[2], p[3]], "S1": 16, "S2": 16}]
        st.session_state.matches = new_m
        
        payload = {
            "tournament_id": tid_raw, "round_number": st.session_state.round_number,
            "leaderboard": st.session_state.leaderboard, "matches": new_m,
            "players": st.session_state.players, "fixed_teams": [], "history": [],
            "max_rounds": st.session_state.max_rounds, "court_names": []
        }
        save_debug(payload)
