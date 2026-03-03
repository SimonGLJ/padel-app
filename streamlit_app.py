import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, history, max_rounds, court_names):
    # Vi sikrer os, at alle lister er rigtige lister, før de sendes som JSON
    payload = {
        "tournament_id": str(tid).lower(),
        "round_number": int(round_num),
        "leaderboard": dict(leaderboard),
        "matches": list(matches),
        "players": list(players),
        "fixed_teams": list(fixed_teams),
        "history": list(history),
        "max_rounds": int(max_rounds),
        "court_names": list(court_names)
    }
    try:
        # Vi gemmer og fanger svaret
        res = conn.table("tournaments").upsert(payload).execute()
        if res.data:
            st.toast(f"✅ Gemt i Supabase: {tid}")
        return res
    except Exception as e:
        # HER får vi den rå sandhed om hvorfor den ikke vil gemme
        st.error(f"❌ DATABASE STOP: {e}")
        st.write("Teknisk detalje til fejlretning:", e)
        return None

# --- INITIALISERING ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, 
        "matches": [], "fixed_teams": [], "history": [], 
        "max_rounds": 7, "current_tid": None, "court_names": []
    })

st.title("🎾 Padel Master Pro")
tid_input = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid if st.session_state.current_tid else "").strip().lower()

# --- KNAP TIL AT TVINGE EN GEMNING (TEST) ---
if st.sidebar.button("🛠️ TVING GEM (Debug)"):
    if tid_input:
        save_to_supabase(
            tid_input, st.session_state.round_number, st.session_state.leaderboard,
            st.session_state.matches, st.session_state.players, st.session_state.fixed_teams,
            st.session_state.history, st.session_state.max_rounds, st.session_state.court_names
        )
    else:
        st.error("Indtast et ID først")

# (Resten af din logik for runder og point følger herunder som i v1.6...)
