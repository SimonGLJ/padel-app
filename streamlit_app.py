import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random
import itertools

st.set_page_config(page_title="Padel Master Pro v3.4", layout="wide", page_icon="🎾")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 1. DEN AVANCEREDE ROTATIONS-MOTOR ---
def generate_best_possible_round(players, past_partners, past_opponents):
    """
    Finder den kombination af kampe, der minimerer gengangere.
    Vi tester 1000 tilfældige sammensætninger og vælger den med færrest 'synder'.
    """
    num_courts = len(players) // 4
    best_score = float('inf')
    best_matches = []

    for _ in range(1000):
        current_pool = list(players)
        random.shuffle(current_pool)
        current_matches = []
        current_score = 0
        
        for c in range(num_courts):
            # Træk 4 spillere
            p = [current_pool.pop() for _ in range(4)]
            h1, h2 = [p[0], p[1]], [p[2], p[3]]
            
            # Beregn straf-point (straf for gengangere)
            # Makker-straf (Vægtet højest: Vi VIL have nye makkere)
            if tuple(sorted(h1)) in past_partners: current_score += 100
            if tuple(sorted(h2)) in past_partners: current_score += 100
            
            # Modstander-straf (Vægtet lavere: Det er okay at møde de samme, hvis man har ny makker)
            for p1 in h1:
                for p2 in h2:
                    if tuple(sorted([p1, p2])) in past_opponents:
                        current_score += 1
            
            current_matches.append({"Bane": f"Bane {c+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        
        if current_score < best_score:
            best_score = current_score
            best_matches = current_matches
            if best_score == 0: break # Perfekt runde fundet!
            
    return best_matches

def save_to_supabase():
    if not st.session_state.current_tid: return
    conn.table("tournaments").upsert({
        "tournament_id": st.session_state.current_tid,
        "round_number": st.session_state.round_number,
        "leaderboard": st.session_state.leaderboard,
        "matches": st.session_state.matches,
        "players": st.session_state.players,
        "history": st.session_state.history,
        "max_rounds": st.session_state.max_rounds,
        "past_partnerships": st.session_state.get("past_partnerships", []),
        "past_opponents": st.session_state.get("past_opponents", [])
    }).execute()

# --- 2. INITIALISERING ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, 
        "matches": [], "history": [], "max_rounds": 7, 
        "current_tid": None, "past_partnerships": [], "past_opponents": []
    })

st.title("🎾 Padel Master Pro v3.4")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid or "").strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data:
        d = res.data[0]
        st.session_state.update({
            "current_tid": tid_raw, "players": d.get('players', []),
            "leaderboard": d.get('leaderboard', {}), "round_number": d.get('round_number', 1),
            "matches": d.get('matches', []), "history": d.get('history', []), 
            "max_rounds": d.get('max_rounds', 7), 
            "past_partnerships": [tuple(p) for p in d.get('past_partnerships', [])],
            "past_opponents": [tuple(o) for o in d.get('past_opponents', [])]
        })
        st.rerun()
    else: st.session_state.current_tid = tid_raw

if not st.session_state.current_tid:
    st.info("👋 Indtast ID for at starte.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("Konfiguration")
    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players))
    max_r = st.number_input("Antal runder", 1, 20, value=st.session_state.max_rounds)
    
    if st.button("🚀 START NY TURNERING"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0:
            st.session_state.update({
                "players": names, "round_number": 1, "matches": [], "history": [],
                "leaderboard": {n: {"Point": 0, "PF": 0, "V": 0} for n in names},
                "max_rounds": max_r, "past_partnerships": [], "past_opponents": []
            })
            save_to_supabase(); st.rerun()

# --- 4. TABS ---
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with t1:
    if st.session_state.players:
        if st.session_state.round_number <= st.session_state.max_rounds:
            if not st.session_state.matches:
                if st.button("🎲 Generer Næste Runde"):
                    new_m = generate_best_possible_round(
                        st.session_state.players, 
                        st.session_state.past_partnerships,
                        st.session_state.past_opponents
                    )
                    st.session_state.matches = new_m
                    save_to_supabase(); st.rerun()

            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    c1, c2 = st.columns([2, 1])
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    s2 = 32 - s1
                    c2.info(f"{' & '.join(m['H2'])}: **{s2}**")
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, s2

            if st.session_state.matches and st.button("✅ Gem Resultater"):
                for m in st.session_state.matches:
                    # Gem makkere
                    st.session_state.past_partnerships.append(tuple(sorted(m['H1'])))
                    st.session_state.past_partnerships.append(tuple(sorted(m['H2'])))
                    # Gem modstandere
                    for p1 in m['H1']:
                        for p2 in m['H2']:
                            st.session_state.past_opponents.append(tuple(sorted([p1, p2])))
                    
                    for t, s, o in [(m['H1'], m['S1'], m['S2']), (m['H2'], m['S2'], m['S1'])]:
                        for p in t:
                            st.session_state.leaderboard[p]["Point"] += s
                            st.session_state.leaderboard[p]["PF"] += (s - o)
                            if s > o: st.session_state.leaderboard[p]["V"] += 1
                
                st.session_state.history.append({"R": st.session_state.round_number, "K": [f"{m['Bane']}: {m['S1']}-{m['S2']}" for m in st.session_state.matches]})
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase(); st.rerun()

with t2:
    if st.session_state.leaderboard:
        df_v = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
        st.dataframe(df_v.reset_index().rename(columns={'index':'Spiller'}), use_container_width=True)

with t3:
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['R']}"):
            for k in e['K']: st.write(k)
