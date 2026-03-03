import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def load_from_supabase(tid):
    try:
        res = conn.table("tournaments").select("*").eq("tournament_id", tid).execute()
        return res.data[0] if res.data and len(res.data) > 0 else None
    except Exception: return None

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, history, max_rounds):
    data = {
        "tournament_id": tid, "round_number": round_num, "leaderboard": leaderboard,
        "matches": matches, "players": players, "fixed_teams": list(fixed_teams) if fixed_teams else [], 
        "history": history, "max_rounds": max_rounds
    }
    try:
        conn.table("tournaments").upsert(data).execute()
        st.toast(f"☁️ Synkroniseret: {tid}")
    except Exception as e: st.error(f"Fejl ved gem: {e}")

# --- 2. INITIALISERING AF SESSION STATE ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, 
        "matches": [], "fixed_teams": [], "history": [], 
        "max_rounds": 7, "current_tid": None
    })

# --- 3. TURNERINGS-ID ---
st.title("🎾 Padel Master Pro")
tid_input = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid if st.session_state.current_tid else "").strip()

if tid_input and tid_input != st.session_state.current_tid:
    data = load_from_supabase(tid_input)
    if data:
        st.session_state.update({
            "current_tid": tid_input, "players": data.get('players', []), 
            "leaderboard": data.get('leaderboard', {}), "round_number": data.get('round_number', 1), 
            "matches": data.get('matches', []), "fixed_teams": data.get('fixed_teams', []), 
            "history": data.get('history', []), "max_rounds": data.get('max_rounds', 7)
        })
        st.success(f"✅ Turnering '{tid_input}' hentet.")
    else:
        st.session_state.current_tid = tid_input
        st.info(f"🆕 Nyt ID: {tid_input}")

if not tid_input:
    st.warning("Indtast et ID for at fortsætte.")
    st.stop()

# --- 4. GUIDE HVIS TOM ---
if not st.session_state.players:
    st.info("💡 **Kom i gang:** Åbn menuen til venstre, indtast spillere og tryk på 'Start Turnering'.")

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opsætning")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    max_r = st.number_input("Runder før finale", 1, 20, value=st.session_state.max_rounds)
    
    p_text = "\n".join(st.session_state.players)
    p_input = st.text_area("Deltagere (ét navn pr. linje)", value=p_text, height=200)
    
    if st.button("🚀 START TURNERING"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.players = names
            st.session_state.leaderboard = {n: {"Point": 0, "PF": 0, "V": 0, "U": 0, "T": 0} for n in names}
            st.session_state.round_number, st.session_state.matches, st.session_state.history = 1, [], []
            st.session_state.max_rounds = max_r
            
            if p_type == "Faste hold":
                random.shuffle(names)
                st.session_state.fixed_teams = [names[i:i+2] for i in range(0, len(names), 2)]
            else:
                st.session_state.fixed_teams = []
                
            save_to_supabase(tid_input, 1, st.session_state.leaderboard, [], names, st.session_state.fixed_teams, [], max_r)
            st.rerun()
        else: st.error("Antal skal gå op i 4!")

# --- 6. HOVEDSKÆRM ---
tab1, tab2, tab3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

with tab1:
    if st.session_state.players:
        is_finale = st.session_state.round_number > st.session_state.max_rounds
        st.subheader("🏆 FINALE" if is_finale else f"Runde {st.session_state.round_number} af {st.session_state.max_rounds}")

        if not st.session_state.matches:
            if st.button("🎲 Generer Næste Kampe"):
                df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
                ranked = df.index.tolist()
                new_m = []
                num_courts = len(st.session_state.players) // 4

                for i in range(num_courts):
                    if is_finale or g_format == "Mexicano":
                        if p_type == "Skiftende makker":
                            p = ranked[i*4 : (i*4)+4]
                            h1, h2 = [p[0], p[3]], [p[1], p[2]]
                        else:
                            # Robust hold-finding til faste hold
                            assigned = []
                            seen_teams = set()
                            for p_name in ranked:
                                for team in st.session_state.fixed_teams:
                                    team_tuple = tuple(sorted(team))
                                    if p_name in team and team_tuple not in seen_teams:
                                        assigned.append(team)
                                        seen_teams.add(team_tuple)
                            h1, h2 = assigned[i*2], assigned[i*2+1]
                    else:
                        p_pool = st.session_state.players.copy() if i == 0 else p_pool
                        random.shuffle(p_pool)
                        p = [p_pool.pop() for _ in range(4)]
                        h1, h2 = [p[0], p[1]], [p[2], p[3]]
                    
                    new_m.append({"Bane": f"Bane {i+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                
                st.session_state.matches = new_m
                st.rerun()

        # Visning af kampe
        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                st.write(f"### {m['Bane']}")
                c1, c2 = st.columns([2, 1])
                s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32-s1
                c2.info(f"{' & '.join(m['H2'])}: **{32-s1}**")

        if st.session_state.matches and st.button("✅ Gem Resultater"):
            for m in st.session_state.matches:
                s1, s2 = m['S1'], m['S2']
                for team, my_s, op_s in [(m['H1'], s1, s2), (m['H2'], s2, s1)]:
                    for p in team:
                        st.session_state.leaderboard[p]["Point"] += my_s
                        st.session_state.leaderboard[p]["PF"] += (my_s - op_s)
                        if my_s > op_s: st.session_state.leaderboard[p]["V"] += 1
                        elif my_s == op_s: st.session_state.leaderboard[p]["U"] += 1
                        else: st.session_state.leaderboard[p]["T"] += 1
            
            st.session_state.history.append({"Runde": st.session_state.round_number, "Kampe": [f"{m['Bane']}: {m['S1']}-{m['S2']}" for m in st.session_state.matches]})
            st.session_state.round_number += 1
            st.session_state.matches = []
            save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds)
            st.rerun()

with tab2:
    if st.session_state.leaderboard:
        st.subheader("📊 Stilling")
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
        df_disp = df.reset_index().rename(columns={'index':'Spiller', 'PF':'Pointforskel', 'V':'Vundne', 'U':'Uafgjorte', 'T':'Tabte'})
        df_disp.index = df_disp.index + 1
        st.dataframe(df_disp, use_container_width=True)

with tab3:
    st.subheader("📜 Historik")
    for entry in reversed(st.session_state.history):
        with st.expander(f"Runde {entry['Runde']}"):
            for k in entry['Kampe']: st.write(k)
