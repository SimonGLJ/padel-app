import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro v5.6", layout="wide", page_icon="🎾")
conn = st.connection("supabase", type=SupabaseConnection)

# --- INITIALISERING ---
def init_session_state():
    defaults = {
        "players": [], "leaderboard": {}, "round_number": 1, "matches": [],
        "history": [], "max_rounds": 7, "current_tid": None,
        "past_partnerships": {}, "past_opponents": {},
        "game_format": "Americano", "partner_type": "Skiftende makker",
        "fixed_teams": [], "score_system": "Frit",
        "tid_loaded": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- HJÆLPEFUNKTION: Load fra Supabase-data ---
def load_from_data(tid, d):
    st.session_state.update({
        "current_tid": tid,
        "players": d.get("players", []),
        "leaderboard": d.get("leaderboard", {}),
        "round_number": d.get("round_number", 1),
        "matches": d.get("matches", []),
        "history": d.get("history", []),
        "max_rounds": d.get("max_rounds", 7),
        "game_format": d.get("format", "Americano"),
        "partner_type": d.get("partner_type", "Skiftende makker"),
        "fixed_teams": d.get("fixed_teams", []),
        "score_system": d.get("score_system", "Frit"),
        "past_partnerships": {
            tuple(k.split("|")): v
            for k, v in d.get("past_partnerships", {}).items()
        },
        "past_opponents": {
            tuple(k.split("|")): v
            for k, v in d.get("past_opponents", {}).items()
        },
        "tid_loaded": True
    })

# --- AUTO-LOAD ved app-start hvis current_tid er sat men ikke loaded endnu ---
if st.session_state.current_tid and not st.session_state.tid_loaded:
    res = conn.table("tournaments").select("*").eq("tournament_id", st.session_state.current_tid).execute()
    if res.data:
        load_from_data(st.session_state.current_tid, res.data[0])
        st.rerun()

# --- LOGIK ---
def p_key(a, b):
    return tuple(sorted([a, b]))

def full_reset(names, g_format, p_type, max_r, score_sys):
    fixed = [[names[i], names[i+1]] for i in range(0, len(names), 2)] if p_type == "Faste hold" else []
    if p_type == "Faste hold":
        random.shuffle(fixed)
    st.session_state.update({
        "players": names, "game_format": g_format, "partner_type": p_type,
        "max_rounds": max_r, "score_system": score_sys,
        "round_number": 1, "matches": [], "history": [],
        "past_partnerships": {}, "past_opponents": {}, "fixed_teams": fixed,
        "tid_loaded": True,
        "leaderboard": {n: {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0} for n in names}
    })

def register_match_data(matches):
    for m in matches:
        for pair in [m["H1"], m["H2"]]:
            k = p_key(pair[0], pair[1])
            st.session_state.past_partnerships[k] = st.session_state.past_partnerships.get(k, 0) + 1
        for p1 in m["H1"]:
            for p2 in m["H2"]:
                k = p_key(p1, p2)
                st.session_state.past_opponents[k] = st.session_state.past_opponents.get(k, 0) + 1
        for team, score, opp_score in [(m["H1"], m["S1"], m["S2"]), (m["H2"], m["S2"], m["S1"])]:
            for p in team:
                if p not in st.session_state.leaderboard:
                    st.session_state.leaderboard[p] = {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0}
                s = st.session_state.leaderboard[p]
                s["KS"] += 1
                s["Point"] += score
                s["PF"] += (score - opp_score)
                if score > opp_score:
                    s["V"] += 1
                elif score < opp_score:
                    s["T"] += 1
                else:
                    s["U"] += 1

def generate_matches():
    players = st.session_state.players
    nc = len(players) // 4
    default_s1 = 16 if st.session_state.score_system == "32-point" else 0
    default_s2 = 16 if st.session_state.score_system == "32-point" else 0

    if st.session_state.round_number == st.session_state.max_rounds + 1:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        ranked = df.sort_values(by=["Point", "V", "PF"], ascending=[False, False, False]).index.tolist()
        return [
            {"Bane": f"Finale {i+1}",
             "H1": [ranked[i*4], ranked[i*4+3]],
             "H2": [ranked[i*4+1], ranked[i*4+2]],
             "S1": default_s1, "S2": default_s2}
            for i in range(nc)
        ]

    if st.session_state.partner_type == "Faste hold":
        teams = list(st.session_state.fixed_teams)
        random.shuffle(teams)
        return [
            {"Bane": f"Bane {i+1}", "H1": teams[i*2], "H2": teams[i*2+1],
             "S1": default_s1, "S2": default_s2}
            for i in range(nc)
        ]

    if st.session_state.game_format == "Mexicano":
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        df["jitter"] = [random.random() for _ in range(len(df))]
        ranked = df.sort_values(by=["Point", "jitter"], ascending=[False, True]).index.tolist()
        return [
            {"Bane": f"Bane {i+1}",
             "H1": [ranked[i*4], ranked[i*4+3]],
             "H2": [ranked[i*4+1], ranked[i*4+2]],
             "S1": default_
