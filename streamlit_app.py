import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro v4.1", layout="wide", page_icon="🎾")
conn = st.connection("supabase", type=SupabaseConnection)

# --- INITIALISERING AF SESSION STATE ---
def init_session_state():
    defaults = {
        "players": [], "leaderboard": {}, "round_number": 1, "matches": [], 
        "history": [], "max_rounds": 7, "current_tid": None, 
        "past_partnerships": {}, "past_opponents": {},
        "game_format": "Americano", "partner_type": "Skiftende makker", "fixed_teams": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- ROTATIONS-MOTORER ---
def generate_americano_skiftende(players, past_partners, past_opponents):
    num_courts = len(players) // 4
    best_score, best_matches = float('inf'), []
    for _ in range(1000):
        pool = list(players); random.shuffle(pool)
        round_matches, score = [], 0
        for c in range(num_courts):
            p = [pool.pop() for _ in range(4)]
            h1, h2 = [p[0], p[1]], [p[2], p[3]]
            score += past_partners.get(tuple(sorted(h1)), 0) * 500
            score += past_partners.get(tuple(sorted(h2)), 0) * 500
            round_matches.append({"Bane": f"Bane {c+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        if score < best_score:
            best_score, best_matches = score, round_matches
            if best_score == 0: break
    return best_matches

def generate_mexicano_skiftende(leaderboard, players):
    num_courts = len(players) // 4
    df = pd.DataFrame.from_dict(leaderboard, orient='index').sort_values("Point", ascending=False)
    ranked = df.index.tolist()
    matches = []
    for i in range(num_courts):
        p = ranked[i*4 : (i*4)+4]
        matches.append({"Bane": f"Bane {i+1}", "H1": [p[0], p[3]], "H2": [p[1], p[2]], "S1": 16, "S2": 16})
    return matches

def save_to_supabase():
    if not st.session_state.current_tid: return
    p_ser = {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_partnerships.items()}
    o_ser = {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_opponents.items()}
    payload = {
        "tournament_id": st.session_state.current_tid, "round_number": st.session_state.round_number,
        "leaderboard": st.session_state.leaderboard, "matches": st.session_state.matches,
        "players": st.session_state.players, "history": st.session_state.history,
        "max_rounds": st.session_state.max_rounds, "format": st.session_state.game_format,
        "partner_type": st.session_state.partner_type, "fixed_teams": st.session_state.fixed_teams,
        "past_partnerships": p_ser, "past_opponents": o_ser
    }
    try: conn.table("tournaments").upsert(payload).execute()
    except Exception as e: st.error(f"DB Fejl: {e}")

# --- HOVEDSKÆRM ---
st.title("🎾 Padel Master Pro v4.1")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid or "").strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data:
        d = res.data[0]
        st.session_state.update({
            "current_tid": tid_raw, "players": d.get('players', []),
            "leaderboard": d.get('leaderboard', {}), "round_number": d.get('round_number', 1),
            "matches": d.get('matches', []), "history": d.get('history', []), 
            "max_rounds": d.get('max_rounds', 7), "game_format": d.get('format', "Americano"),
            "partner_type": d.get('partner_type', "Skiftende makker"), "fixed_teams": d.get('fixed_teams', []),
            "past_partnerships": {tuple(k.split('|')): v for k, v in d.get('past_partnerships', {}).items()} if d.get('past_partnerships') else {},
            "past_opponents": {tuple(k.split('|')): v for k, v in d.get('past_opponents', {}).items()} if d.get('past_opponents') else {}
        })
    else: st.session_state.current_tid = tid_raw
    st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"], index=0 if st.session_state.game_format == "Americano" else 1)
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"], index=0 if st.session_state.partner_type == "Skiftende makker" else 1)
    max_r = st.number_input("Runder", 1, 50, value=st.session_state.max_rounds)
    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players), height=200)
    if st.button("🚀 GEM SETUP / START NY"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0:
            st.session_state.update({"players": names, "game_format": g_format, "partner_type": p_type, "max_rounds": max_r, 
                "leaderboard": {n: {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0} for n in names}})
            save_to_supabase(); st.rerun()

# --- TABS ---
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with t1:
    if st.session_state.get("players"):
        if st.session_state.round_number <= st.session_state.max_rounds:
            if not st.session_state.get("matches"):
                if st.button("🎲 Generer Næste Runde"):
                    if st.session_state.partner_type == "Faste hold":
                        teams = list(st.session_state.fixed_teams); random.shuffle(teams)
                        st.session_state.matches = [{"Bane": f"Bane {i+1}", "H1": teams.pop(), "H2": teams.pop(), "S1": 16, "S2": 16} for i in range(len(st.session_state.players)//4)]
                    elif st.session_state.game_format == "Mexicano": st.session_state.matches = generate_mexicano_skiftende(st.session_state.leaderboard, st.session_state.players)
                    else: st.session_state.matches = generate_americano_skiftende(st.session_state.players, st.session_state.past_partnerships, st.session_state.past_opponents)
                    save_to_supabase(); st.rerun()

            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    # Redigering
                    if st.button("✏️ Rediger", key=f"edit_{i}"): st.session_state[f"edit_{i}"] = True
                    if st.session_state.get(f"edit_{i}"):
                        m['H1'][0] = st.text_input("H1 P1", m['H1'][0]); m['H1'][1] = st.text_input("H1 P2", m['H1'][1])
                        m['H2'][0] = st.text_input("H2 P1", m['H2'][0]); m['H2'][1] = st.text_input("H2 P2", m['H2'][1])
                        if st.button("Gem", key=f"save_{i}"): st.session_state[f"edit_{i}"] = False; st.rerun()
                    
                    s1 = st.number_input(f"Score: {' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32 - s1

            if st.session_state.matches and st.button("✅ Gem Resultat & Log"):
                for m in st.session_state.matches:
                    for t, s, o in [(m['H1'], m['S1'], m['S2']), (m['H2'], m['S2'], m['S1'])]:
                        for p in t:
                            stats = st.session_state.leaderboard[p]
                            stats["KS"] += 1
                            if s > o: stats["V"] += 1
                            elif s < o: stats["T"] += 1
                            else: stats["U"] += 1
                            stats["Point"] += s; stats["PF"] += (s - o)
                st.session_state.history.append({"Runde": st.session_state.round_number, "Kampe": [f"{m['Bane']}: {'&'.join(m['H1'])} vs {'&'.join(m['H2'])} ({m['S1']}-{m['S2']})" for m in st.session_state.matches]})
                st.session_state.round_number += 1; st.session_state.matches = []; save_to_supabase(); st.rerun()

with t2:
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')[["KS", "V", "U", "T", "Point", "PF"]].sort_values(["Point", "V"], ascending=False)
        st.dataframe(df, use_container_width=True)

with t3:
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['Runde']}"):
            for k in e['Kampe']: st.write(k)
