import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def load_from_supabase(tid):
    try:
        res = conn.table("tournaments").select("*").eq("tournament_id", tid.lower()).execute()
        return res.data[0] if res.data and len(res.data) > 0 else None
    except Exception: return None

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, history, max_rounds, court_names):
    payload = {
        "tournament_id": tid.lower(), "round_number": round_num, "leaderboard": leaderboard,
        "matches": matches, "players": players, "fixed_teams": list(fixed_teams) if fixed_teams else [], 
        "history": history, "max_rounds": max_rounds, "court_names": court_names
    }
    try:
        conn.table("tournaments").upsert(payload).execute()
        st.toast(f"☁️ Synkroniseret: {tid.lower()}")
    except Exception as e: st.error(f"❌ Databasefejl: {e}")

# --- 2. INITIALISERING ---
if "current_tid" not in st.session_state:
    st.session_state.update({
        "players": [], "leaderboard": {}, "round_number": 1, 
        "matches": [], "fixed_teams": [], "history": [], 
        "max_rounds": 7, "current_tid": None, "court_names": []
    })

st.title("🎾 Padel Master Pro")
tid_raw = st.text_input("📍 Turnerings-ID", value=st.session_state.current_tid if st.session_state.current_tid else "").strip()
tid_input = tid_raw.lower() if tid_raw else None

if tid_input and tid_input != st.session_state.current_tid:
    data = load_from_supabase(tid_input)
    if data:
        st.session_state.update({
            "current_tid": tid_input, "players": data.get('players', []),
            "leaderboard": data.get('leaderboard', {}), "round_number": data.get('round_number', 1),
            "matches": data.get('matches', []), "fixed_teams": data.get('fixed_teams', []),
            "history": data.get('history', []), "max_rounds": data.get('max_rounds', 7),
            "court_names": data.get('court_names', [])
        })
        st.rerun()
    else: st.session_state.current_tid = tid_input

if not tid_input:
    st.info("👋 Velkommen! Indtast et Turnerings-ID for at starte.")
    st.stop()

# --- 3. GUIDE (Hvis ingen spillere) ---
if not st.session_state.players:
    st.info("💡 **Guide:** Åbn menuen til venstre (pil øverst til venstre), indtast navne og vælg format. Tryk derefter '🚀 START'.")

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opsætning")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    max_rounds_input = st.number_input("Runder før finale", 1, 20, value=st.session_state.max_rounds)
    
    # Banenavngivning (KUN Mexicano)
    current_court_names = []
    if g_format == "Mexicano" and st.session_state.players:
        st.divider()
        st.subheader("🏟️ Navngiv Baner")
        for i in range(len(st.session_state.players) // 4):
            default_n = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
            n = st.text_input(f"Bane {i+1}", value=default_n, key=f"court_input_{i}")
            current_court_names.append(n)
        st.session_state.court_names = current_court_names

    p_input = st.text_area("Deltagere (ét navn pr. linje)", value="\n".join(st.session_state.players), height=150)
    
    if st.button("🚀 START / NULSTIL"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0 and len(names) >= 4:
            st.session_state.update({
                "players": names, "round_number": 1, "matches": [], "history": [],
                "leaderboard": {n: {"Point": 0, "PF": 0, "V": 0, "U": 0, "T": 0} for n in names},
                "max_rounds": max_rounds_input
            })
            if p_type == "Faste hold":
                random.shuffle(names)
                st.session_state.fixed_teams = [names[i:i+2] for i in range(0, len(names), 2)]
            save_to_supabase(tid_input, 1, st.session_state.leaderboard, [], names, st.session_state.fixed_teams, [], max_rounds_input, st.session_state.court_names)
            st.rerun()
        else: st.error("Antal spillere skal gå op i 4!")

# --- 5. TABS ---
tab1, tab2, tab3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log & Rediger"])

with tab1:
    if st.session_state.players:
        is_over = st.session_state.round_number > st.session_state.max_rounds + 1
        is_finale = st.session_state.round_number > st.session_state.max_rounds and not is_over

        if is_over:
            st.balloons()
            st.header("🏆 Turneringen er slut!")
            df_final = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False).reset_index()
            st.dataframe(df_final.rename(columns={'index':'Spiller'}), use_container_width=True)
            st.download_button("📥 Hent CSV", df_final.to_csv(index=False).encode('utf-8'), f"{tid_input}.csv")
        else:
            st.subheader("🔥 FINALE" if is_finale else f"Runde {st.session_state.round_number} af {st.session_state.max_rounds}")
            
            # Generer kampe knap
            if not st.session_state.matches:
                if st.button("🎲 Generer Næste Kampe"):
                    df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
                    ranked = df.index.tolist()
                    new_m = []
                    for i in range(len(st.session_state.players) // 4):
                        b_navn = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
                        if i == 0 and g_format == "Mexicano": b_navn = f"🏆 {b_navn} (Vinderbane)"
                        
                        if is_finale or g_format == "Mexicano":
                            if p_type == "Skiftende makker":
                                p = ranked[i*4 : (i*4)+4]
                                h1, h2 = [p[0], p[3]], [p[1], p[2]]
                            else: # Faste hold logik
                                assigned, seen = [], set()
                                for p_n in ranked:
                                    for team in st.session_state.fixed_teams:
                                        t_tup = tuple(sorted(team))
                                        if p_n in team and t_tup not in seen:
                                            assigned.append(team); seen.add(t_tup)
                                h1, h2 = assigned[i*2], assigned[i*2+1]
                        else: # Americano / Runde 1
                            p_pool = st.session_state.players.copy() if i == 0 else p_pool
                            random.shuffle(p_pool)
                            p = [p_pool.pop() for _ in range(4)]
                            h1, h2 = [p[0], p[1]], [p[2], p[3]]
                        new_m.append({"Bane": b_navn, "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                    st.session_state.matches = new_m
                    save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds, st.session_state.court_names)
                    st.rerun()

            # Indtastning af point
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
                
                st.session_state.history.append({"R": st.session_state.round_number, "K": [f"{m['Bane']}: {m['S1']}-{m['S2']}" for m in st.session_state.matches]})
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, [], st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds, st.session_state.court_names)
                st.rerun()

with tab2:
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
        st.dataframe(df.reset_index().rename(columns={'index':'Spiller'}), use_container_width=True)

with tab3:
    st.subheader("🔧 Rediger Point")
    if st.session_state.players:
        p_edit = st.selectbox("Vælg spiller", st.session_state.players)
        col1, col2 = st.columns(2)
        new_p = col1.number_input("Samlet point", value=st.session_state.leaderboard[p_edit]["Point"])
        new_pf = col2.number_input("Samlet PF", value=st.session_state.leaderboard[p_edit]["PF"])
        if st.button("💾 Opdater Spiller"):
            st.session_state.leaderboard[p_edit]["Point"] = new_p
            st.session_state.leaderboard[p_edit]["PF"] = new_pf
            save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, st.session_state.matches, st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds, st.session_state.court_names)
            st.success("Opdateret!")
    
    st.divider()
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['R']}"):
            for k in e['K']: st.write(k)
