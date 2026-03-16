import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro v4.7", layout="wide", page_icon="🎾")
conn = st.connection("supabase", type=SupabaseConnection)

# --- INITIALISERING ---
def init_session_state():
    defaults = {
        "players": [], "leaderboard": {}, "round_number": 1, "matches": [], 
        "history": [], "max_rounds": 7, "current_tid": None, 
        "past_partnerships": {}, "past_opponents": {},
        "game_format": "Americano", "partner_type": "Skiftende makker", "fixed_teams": []
    }
    for key, value in defaults.items():
        if key not in st.session_state: st.session_state[key] = value

init_session_state()

# --- HJÆLPEFUNKTIONER ---
def register_match_data(matches):
    for m in matches:
        p1_key, p2_key = tuple(sorted(m['H1'])), tuple(sorted(m['H2']))
        st.session_state.past_partnerships[p1_key] = st.session_state.past_partnerships.get(p1_key, 0) + 1
        st.session_state.past_partnerships[p2_key] = st.session_state.past_partnerships.get(p2_key, 0) + 1
        for p1 in m['H1']:
            for p2 in m['H2']:
                opp_key = tuple(sorted([p1, p2]))
                st.session_state.past_opponents[opp_key] = st.session_state.past_opponents.get(opp_key, 0) + 1
        for team, score, opp_score in [(m['H1'], m['S1'], m['S2']), (m['H2'], m['S2'], m['S1'])]:
            for p in team:
                stats = st.session_state.leaderboard[p]
                stats["KS"] += 1
                if score > opp_score: stats["V"] += 1
                elif score < opp_score: stats["T"] += 1
                else: stats["U"] += 1
                stats["Point"] += score
                stats["PF"] += (score - opp_score)

def generate_matches():
    players = st.session_state.players
    # Faste hold logik
    if st.session_state.partner_type == "Faste hold":
        if not st.session_state.fixed_teams:
            temp = list(players); random.shuffle(temp)
            st.session_state.fixed_teams = [[temp[i], temp[i+1]] for i in range(0, len(temp), 2)]
        teams = list(st.session_state.fixed_teams); random.shuffle(teams)
        return [{"Bane": f"Bane {i+1}", "H1": teams.pop(), "H2": teams.pop(), "S1": 16, "S2": 16} for i in range(len(players)//4)]
    
    # Mexicano logik
    if st.session_state.game_format == "Mexicano":
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        df['jitter'] = [random.random() for _ in range(len(df))]
        ranked = df.sort_values(by=["Point", "jitter"], ascending=[False, False]).index.tolist()
        return [{"Bane": f"Bane {i+1}", "H1": [ranked[i*4], ranked[i*4+3]], "H2": [ranked[i*4+1], ranked[i*4+2]], "S1": 16, "S2": 16} for i in range(len(players)//4)]
    
    # Americano Monte Carlo
    best_score, best_matches = float('inf'), []
    for _ in range(500):
        pool = list(players); random.shuffle(pool)
        m, s = [], 0
        for c in range(len(players)//4):
            h1, h2 = [pool.pop(), pool.pop()], [pool.pop(), pool.pop()]
            s += st.session_state.past_partnerships.get(tuple(sorted(h1)), 0) * 500
            m.append({"Bane": f"Bane {c+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        if s < best_score: best_score, best_matches = s, m
    return best_matches

def save_to_supabase():
    if not st.session_state.current_tid: return
    payload = {
        "tournament_id": st.session_state.current_tid, "round_number": st.session_state.round_number,
        "leaderboard": st.session_state.leaderboard, "matches": st.session_state.matches,
        "players": st.session_state.players, "history": st.session_state.history,
        "max_rounds": st.session_state.max_rounds, "format": st.session_state.game_format,
        "partner_type": st.session_state.partner_type, "fixed_teams": st.session_state.fixed_teams,
        "past_partnerships": {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_partnerships.items()},
        "past_opponents": {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_opponents.items()}
    }
    conn.table("tournaments").upsert(payload).execute()

# --- UI ---
st.title("🎾 Padel Master Pro v4.7")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid or "").strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data:
        d = res.data[0]
        st.session_state.update({
            "current_tid": tid_raw, "players": d.get('players', []), "leaderboard": d.get('leaderboard', {}),
            "round_number": d.get('round_number', 1), "matches": d.get('matches', []), "history": d.get('history', []),
            "game_format": d.get('format', "Americano"), "partner_type": d.get('partner_type', "Skiftende makker"),
            "fixed_teams": d.get('fixed_teams', []), "past_partnerships": {tuple(k.split('|')): v for k, v in d.get('past_partnerships', {}).items()},
            "past_opponents": {tuple(k.split('|')): v for k, v in d.get('past_opponents', {}).items()}
        })
    else: st.session_state.current_tid = tid_raw
    st.rerun()

with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"], index=0 if st.session_state.game_format=="Americano" else 1)
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"], index=0 if st.session_state.partner_type=="Skiftende makker" else 1)
    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players), height=200)
    if st.button("🚀 GEM SETUP / START NY"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0:
            st.session_state.update({"players": names, "game_format": g_format, "partner_type": p_type, "round_number": 1, "matches": [], "history": [], "past_partnerships": {}, "past_opponents": {}, "fixed_teams": [[names[i], names[i+1]] for i in range(0, len(names), 2)] if p_type=="Faste hold" else [], "leaderboard": {n: {"KS":0, "V":0, "U":0, "T":0, "Point":0, "PF":0} for n in names}})
            save_to_supabase(); st.rerun()

t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])
with t1:
    if st.session_state.players and not st.session_state.matches:
        if st.button("🎲 Generer Næste Runde"): st.session_state.matches = generate_matches(); save_to_supabase(); st.rerun()
    for i, m in enumerate(st.session_state.matches):
        with st.container(border=True):
            if st.button("✏️", key=f"edit_{i}"): st.session_state[f"buf_{i}"] = {"H1": list(m['H1']), "H2": list(m['H2'])}
            if f"buf_{i}" in st.session_state:
                b = st.session_state[f"buf_{i}"]
                b['H1'][0] = st.text_input("Hold 1 Spiller 1", b['H1'][0], key=f"e1_{i}")
                b['H1'][1] = st.text_input("Hold 1 Spiller 2", b['H1'][1], key=f"e2_{i}")
                if st.button("Gem", key=f"s_{i}"): st.session_state.matches[i]['H1'], st.session_state.matches[i]['H2'] = b['H1'], b['H2']; del st.session_state[f"buf_{i}"]; st.rerun()
            s1 = st.number_input(f"Score: {' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
            st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32-s1
    if st.session_state.matches and st.button("✅ Gem Resultat & Log"):
        register_match_data(st.session_state.matches)
        st.session_state.history.append({"Runde": st.session_state.round_number, "Kampe": [f"{m['Bane']}: {'&'.join(m['H1'])} vs {'&'.join(m['H2'])} ({m['S1']}-{m['S2']})" for m in st.session_state.matches]})
        st.session_state.round_number += 1; st.session_state.matches = []; save_to_supabase(); st.rerun()

with t2:
    st.subheader("📊 Aktuel Stilling")
    if st.session_state.get("leaderboard"):
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        if not df.empty and all(c in df.columns for c in ["KS", "V", "U", "T", "Point", "PF"]):
            st.dataframe(df[["KS", "V", "U", "T", "Point", "PF"]].sort_values(["Point", "V"], ascending=False), use_container_width=True)
        else: st.warning("Stillingen opdateres efter første kamp.")

with t3:
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['Runde']}"):
            for k in e['Kampe']: st.write(k)
