import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro v3.5", layout="wide", page_icon="🎾")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 1. OPTIMERET ROTATIONS-MOTOR ---
def generate_best_possible_round(players, past_partners, past_opponents):
    num_courts = len(players) // 4
    best_score = float('inf')
    best_matches = []

    for _ in range(1000):
        current_pool = list(players)
        random.shuffle(current_pool)
        current_matches = []
        current_score = 0
        
        for c in range(num_courts):
            p = [current_pool.pop() for _ in range(4)]
            h1, h2 = [p[0], p[1]], [p[2], p[3]]
            
            # Bug 1 Fix: Brug dictionary counts til straf (count * vægt)
            p1_key = tuple(sorted(h1))
            p2_key = tuple(sorted(h2))
            current_score += past_partners.get(p1_key, 0) * 500 # Massiv straf for gensyn
            current_score += past_partners.get(p2_key, 0) * 500
            
            for player1 in h1:
                for player2 in h2:
                    opp_key = tuple(sorted([player1, player2]))
                    current_score += past_opponents.get(opp_key, 0) * 10 # Mindre straf for modstander-gensyn
            
            current_matches.append({"Bane": f"Bane {c+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        
        if current_score < best_score:
            best_score = current_score
            best_matches = current_matches
            if best_score == 0: break 
            
    return best_matches

def save_to_supabase():
    if not st.session_state.current_tid: return
    # Konverter tuples til strings for JSON-kompatibilitet i Supabase
    partners_serializable = {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_partnerships.items()}
    opponents_serializable = {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_opponents.items()}
    
    conn.table("tournaments").upsert({
        "tournament_id": st.session_state.current_tid,
        "round_number": st.session_state.round_number,
        "leaderboard": st.session_state.leaderboard,
        "matches": st.session_state.matches,
        "players": st.session_state.players,
        "history": st.session_state.history,
        "max_rounds": st.session_state.max_rounds,
        "past_partnerships": partners_serializable,
        "past_opponents": opponents_serializable
    }).execute()

# --- 2. INITIALISERING ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, "matches": [], 
        "history": [], "max_rounds": 7, "current_tid": None, 
        "past_partnerships": {}, "past_opponents": {}
    })

st.title("🎾 Padel Master Pro v3.5")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid or "").strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data:
        d = res.data[0]
        # Bug 2 Fix: Validering ved indlæsning
        loaded_players = d.get('players', [])
        if len(loaded_players) % 4 != 0:
            st.error("⚠️ Fejl i data: Spillerantallet i databasen er ugyldigt.")
        else:
            # Gendan dictionaries fra strings
            past_p = {tuple(k.split('|')): v for k, v in d.get('past_partnerships', {}).items()}
            past_o = {tuple(k.split('|')): v for k, v in d.get('past_opponents', {}).items()}
            
            st.session_state.update({
                "current_tid": tid_raw, "players": loaded_players,
                "leaderboard": d.get('leaderboard', {}), "round_number": d.get('round_number', 1),
                "matches": d.get('matches', []), "history": d.get('history', []), 
                "max_rounds": d.get('max_rounds', 7), 
                "past_partnerships": past_p, "past_opponents": past_o
            })
            st.rerun()

if not st.session_state.current_tid:
    st.info("👋 Indtast ID for at starte.")
    st.stop()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("Opsætning")
    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players))
    max_r = st.number_input("Antal runder", 1, 20, value=st.session_state.max_rounds)
    if st.button("🚀 START NY TURNERING"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0:
            st.session_state.update({
                "players": names, "round_number": 1, "matches": [], "history": [],
                "leaderboard": {n: {"Point": 0, "PF": 0, "V": 0} for n in names},
                "max_rounds": max_r, "past_partnerships": {}, "past_opponents": {}
            })
            save_to_supabase(); st.rerun()
        else: st.error("Antallet skal gå op i 4!")

# --- 4. TABS ---
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with t1:
    if st.session_state.players:
        if st.session_state.round_number <= st.session_state.max_rounds:
            if not st.session_state.matches:
                if st.button("🎲 Generer Næste Runde"):
                    st.session_state.matches = generate_best_possible_round(
                        st.session_state.players, st.session_state.past_partnerships, st.session_state.past_opponents
                    )
                    save_to_supabase(); st.rerun()

            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    c1, c2 = st.columns([2, 2])
                    # Bug 3 Fix: UI forbedring for låste point
                    s1 = c1.number_input(f"Score for: {' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    s2 = 32 - s1
                    c2.markdown(f"<p style='margin-bottom:0px; font-size:0.8rem; color:gray;'>Auto-score</p><b>{' & '.join(m['H2'])}: {s2}</b>", unsafe_allow_html=True)
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, s2

            if st.session_state.matches and st.button("✅ Gem Resultater"):
                for m in st.session_state.matches:
                    # Opdater makkerskab (Counter-stil)
                    p1_key, p2_key = tuple(sorted(m['H1'])), tuple(sorted(m['H2']))
                    st.session_state.past_partnerships[p1_key] = st.session_state.past_partnerships.get(p1_key, 0) + 1
                    st.session_state.past_partnerships[p2_key] = st.session_state.past_partnerships.get(p2_key, 0) + 1
                    
                    for p1 in m['H1']:
                        for p2 in m['H2']:
                            opp_key = tuple(sorted([p1, p2]))
                            st.session_state.past_opponents[opp_key] = st.session_state.past_opponents.get(opp_key, 0) + 1
                    
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
