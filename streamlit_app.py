import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro v5.2", layout="wide", page_icon="🎾")
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
def p_key(a, b): return tuple(sorted([a, b]))

def full_reset(names, g_format, p_type, max_r):
    fixed = [[names[i], names[i+1]] for i in range(0, len(names), 2)] if p_type == "Faste hold" else []
    if p_type == "Faste hold": random.shuffle(fixed)
    st.session_state.update({
        "players": names, "game_format": g_format, "partner_type": p_type, "max_rounds": max_r,
        "round_number": 1, "matches": [], "history": [], "past_partnerships": {}, 
        "past_opponents": {}, "fixed_teams": fixed,
        "leaderboard": {n: {"KS":0, "V":0, "U":0, "T":0, "Point":0, "PF":0} for n in names}
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
                if p not in st.session_state.leaderboard: st.session_state.leaderboard[p] = {"KS":0, "V":0, "U":0, "T":0, "Point":0, "PF":0}
                s = st.session_state.leaderboard[p]
                s["KS"] += 1; s["Point"] += score; s["PF"] += (score - opp_score)
                if score > opp_score: s["V"] += 1
                elif score < opp_score: s["T"] += 1
                else: s["U"] += 1

def generate_matches():
    players = st.session_state.players
    nc = len(players) // 4
    # FINALE LOGIK (Runde > max_rounds)
    if st.session_state.round_number > st.session_state.max_rounds:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        ranked = df.sort_values(by=["Point", "V", "PF"], ascending=[False, False, False]).index.tolist()
        return [{"Bane": f"Finale {i+1}", "H1": [ranked[i*4], ranked[i*4+3]], "H2": [ranked[i*4+1], ranked[i*4+2]], "S1": 16, "S2": 16} for i in range(nc)]
    
    # NORMALE RUNDER
    if st.session_state.partner_type == "Faste hold":
        teams = list(st.session_state.fixed_teams); random.shuffle(teams)
        return [{"Bane": f"Bane {i+1}", "H1": teams[i*2], "H2": teams[i*2+1], "S1": 16, "S2": 16} for i in range(nc)]
    
    if st.session_state.game_format == "Mexicano":
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        df["jitter"] = [random.random() for _ in range(len(df))]
        ranked = df.sort_values(by=["Point", "jitter"], ascending=[False, True]).index.tolist()
        return [{"Bane": f"Bane {i+1}", "H1": [ranked[i*4], ranked[i*4+3]], "H2": [ranked[i*4+1], ranked[i*4+2]], "S1": 16, "S2": 16} for i in range(nc)]
    
    best_score, best_matches = float("inf"), []
    for _ in range(1000):
        pool = list(players); random.shuffle(pool); m, s = [], 0
        for c in range(nc):
            h1, h2 = [pool.pop(), pool.pop()], [pool.pop(), pool.pop()]
            s += st.session_state.past_partnerships.get(p_key(h1[0], h1[1]), 0) * 500
            s += st.session_state.past_opponents.get(p_key(h1[0], h2[0]), 0) * 10
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
st.title("🎾 Padel Master Pro v5.2")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid or "").strip().lower()
if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data: 
        d = res.data[0]
        st.session_state.update({"current_tid": tid_raw, "players": d['players'], "leaderboard": d['leaderboard'], "round_number": d['round_number'], "matches": d['matches'], "history": d['history'], "max_rounds": d['max_rounds'], "game_format": d['format'], "partner_type": d['partner_type'], "fixed_teams": d['fixed_teams']})
    else: st.session_state.current_tid = tid_raw
    st.rerun()

with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"], index=0 if st.session_state.game_format=="Americano" else 1)
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"], index=0 if st.session_state.partner_type=="Skiftende makker" else 1)
    max_r = st.number_input("Grundspils-runder", 1, 50, value=st.session_state.max_rounds)
    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players), height=200)
    if st.button("🚀 GEM SETUP / START NY"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0: full_reset(names, g_format, p_type, max_r); save_to_supabase(); st.rerun()

t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])
with t1:
    if st.session_state.round_number > (st.session_state.max_rounds + 1):
        st.balloons(); st.success("🏆 TURNERING AFSLUTTET!"); st.stop()
    if st.session_state.round_number == (st.session_state.max_rounds + 1): st.warning("🔥 FINALE-RUNDE: Spillere parres efter 1+4 vs 2+3!")
    
    if not st.session_state.matches:
        if st.button("🎲 Generer Næste Runde"): st.session_state.matches = generate_matches(); save_to_supabase(); st.rerun()
    
    for i, m in enumerate(st.session_state.matches):
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2,1,2]); col_a.markdown(f"**Hold 1:** {', '.join(m['H1'])}"); col_b.write("vs"); col_c.markdown(f"**Hold 2:** {', '.join(m['H2'])}")
            if st.button("✏️", key=f"edit_{i}"): st.session_state[f"buf_{i}"] = {"H1": list(m['H1']), "H2": list(m['H2'])}
            if f"buf_{i}" in st.session_state:
                b = st.session_state[f"buf_{i}"]
                c1, c2 = st.columns(2); b['H1'][0] = c1.text_input("H1S1", b['H1'][0]); b['H1'][1] = c1.text_input("H1S2", b['H1'][1]); b['H2'][0] = c2.text_input("H2S1", b['H2'][0]); b['H2'][1] = c2.text_input("H2S2", b['H2'][1])
                if st.button("Gem", key=f"s_{i}"): st.session_state.matches[i]['H1'], st.session_state.matches[i]['H2'] = b['H1'], b['H2']; del st.session_state[f"buf_{i}"]; st.rerun()
            s1 = st.number_input(f"Score for {' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
            st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32-s1
            
    if st.session_state.matches and st.button("✅ Gem Resultat & Log"):
        register_match_data(st.session_state.matches)
        st.session_state.history.append({"Runde": st.session_state.round_number, "Kampe": [f"{m['Bane']}: {'&'.join(m['H1'])} vs {'&'.join(m['H2'])} ({m['S1']}-{m['S2']})" for m in st.session_state.matches]})
        st.session_state.round_number += 1; st.session_state.matches = []
        save_to_supabase(); st.rerun()

with t2:
    if st.session_state.leaderboard: 
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
        st.dataframe(df[["KS", "V", "U", "T", "Point", "PF"]].sort_values(["Point", "V"], ascending=False), use_container_width=True)

with t3:
    for e in reversed(st.session_state.history): 
        with st.expander(f"Runde {e['Runde']}"): 
            for k in e['Kampe']: st.write(k)
