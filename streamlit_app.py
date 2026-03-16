import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro v3.6", layout="wide", page_icon="🎾")
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
            if len(current_pool) < 4: break
            p = [current_pool.pop() for _ in range(4)]
            h1, h2 = [p[0], p[1]], [p[2], p[3]]
            
            p1_key = tuple(sorted(h1))
            p2_key = tuple(sorted(h2))
            current_score += past_partners.get(p1_key, 0) * 500 
            current_score += past_partners.get(p2_key, 0) * 500
            
            for player1 in h1:
                for player2 in h2:
                    opp_key = tuple(sorted([player1, player2]))
                    current_score += past_opponents.get(opp_key, 0) * 10 
            
            current_matches.append({"Bane": f"Bane {c+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        
        if current_score < best_score:
            best_score = current_score
            best_matches = current_matches
            if best_score == 0: break 
            
    return best_matches

def save_to_supabase():
    if not st.session_state.current_tid: return
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

st.title("🎾 Padel Master Pro v3.6")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid or "").strip().lower()

# Logik til at hente data hvis ID skifter
if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data:
        d = res.data[0]
        past_p = {tuple(k.split('|')): v for k, v in d.get('past_partnerships', {}).items()}
        past_o = {tuple(k.split('|')): v for k, v in d.get('past_opponents', {}).items()}
        st.session_state.update({
            "current_tid": tid_raw, "players": d.get('players', []),
            "leaderboard": d.get('leaderboard', {}), "round_number": d.get('round_number', 1),
            "matches": d.get('matches', []), "history": d.get('history', []), 
            "max_rounds": d.get('max_rounds', 7), 
            "past_partnerships": past_p, "past_opponents": past_o
        })
    else:
        # Hvis ID er nyt, nulstil kun ID'et og lad brugeren skrive navne
        st.session_state.current_tid = tid_raw
    st.rerun()

if not st.session_state.current_tid:
    st.info("👋 Indtast et unikt ID (f.eks. 'klub-2024') for at starte.")
    st.stop()

# --- 3. SIDEBAR (NU ALTID SYNLIG) ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    # Vi henter værdier fra session_state så de overlever load
    p_input = st.text_area("Deltagere (én pr. linje)", value="\n".join(st.session_state.players), height=300)
    max_r = st.number_input("Antal runder totalt", 1, 50, value=st.session_state.max_rounds)
    
    st.divider()
    if st.button("🚀 OPDATER / START NY"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            # Spørg om man vil nulstille point hvis man ændrer spillere
            st.session_state.update({
                "players": names,
                "leaderboard": {n: st.session_state.leaderboard.get(n, {"Point": 0, "PF": 0, "V": 0}) for n in names},
                "max_rounds": max_r
            })
            # Hvis man trykker her, antager vi man vil gemme ændringerne
            save_to_supabase()
            st.success("Indstillinger gemt!")
            st.rerun()
        else:
            st.error("Antal spillere skal gå op i 4!")

    if st.button("⚠️ Nulstil ALT (Point & Historik)"):
        st.session_state.update({
            "round_number": 1, "matches": [], "history": [],
            "leaderboard": {n: {"Point": 0, "PF": 0, "V": 0} for n in st.session_state.players},
            "past_partnerships": {}, "past_opponents": {}
        })
        save_to_supabase()
        st.rerun()

# --- 4. TABS ---
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with t1:
    if not st.session_state.players:
        st.warning("👈 Start med at tilføje spillere i menuen til venstre.")
    else:
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
                    s1 = c1.number_input(f"Score: {' & '.join(m['H1'])}", 0, 100, value=int(m['S1']), key=f"s1_{i}")
                    s2 = 32 - s1
                    c2.markdown(f"<p style='margin-top:10px; color:gray;'>Auto-score</p><b>{' & '.join(m['H2'])}: {s2}</b>", unsafe_allow_html=True)
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, s2

            if st.session_state.matches and st.button("✅ Gem Resultater & Næste Runde"):
                for m in st.session_state.matches:
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
        else:
            st.balloons()
            st.header("🏆 Turneringen er slut!")

with t2:
    if st.session_state.leaderboard:
        df_v = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
        st.dataframe(df_v.reset_index().rename(columns={'index':'Spiller'}), use_container_width=True)

with t3:
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['R']}"):
            for k in e['K']: st.write(k)
