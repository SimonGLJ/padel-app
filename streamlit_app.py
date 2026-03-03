import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro", layout="wide", page_icon="🎾")

# --- 1. DATABASE FORBINDELSE ---
conn = st.connection("supabase", type=SupabaseConnection)

def load_from_supabase(tid):
    try:
        # Tvinger Supabase til at hente nyeste data uden cache
        res = conn.table("tournaments").select("*").eq("tournament_id", tid).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        st.error(f"Databasefejl: {e}")
        return None

def save_to_supabase(tid, round_num, leaderboard, matches, players, fixed_teams, history, max_rounds, court_names):
    data = {
        "tournament_id": tid, "round_number": round_num, "leaderboard": leaderboard,
        "matches": matches, "players": players, "fixed_teams": list(fixed_teams) if fixed_teams else [], 
        "history": history, "max_rounds": max_rounds, "court_names": court_names
    }
    try:
        conn.table("tournaments").upsert(data).execute()
        st.toast(f"☁️ Synkroniseret: {tid}")
    except Exception as e: 
        st.error(f"Kunne ikke gemme: {e}")

# --- 2. SESSION STATE MANAGEMENT ---
# Vi sikrer, at alt bliver overskrevet korrekt ved genindlæsning
def sync_session_with_cloud(data, tid):
    st.session_state.current_tid = tid
    st.session_state.players = data.get('players', [])
    st.session_state.leaderboard = data.get('leaderboard', {})
    st.session_state.round_number = data.get('round_number', 1)
    st.session_state.matches = data.get('matches', [])
    st.session_state.fixed_teams = data.get('fixed_teams', [])
    st.session_state.history = data.get('history', [])
    st.session_state.max_rounds = data.get('max_rounds', 7)
    st.session_state.court_names = data.get('court_names', [])

if "current_tid" not in st.session_state:
    st.session_state.update({"players":[], "leaderboard":{}, "round_number":1, "matches":[], "fixed_teams":[], "history":[], "max_rounds":7, "current_tid":None, "court_names":[]})

# --- 3. HOVEDMENU ---
st.title("🎾 Padel Master Pro")
tid_input = st.text_input("📍 Indtast Turnerings-ID for at starte/genoptage", value=st.session_state.current_tid if st.session_state.current_tid else "").strip()

# TVUNGEN SYNC VED ID-MATCH
if tid_input:
    if tid_input != st.session_state.current_tid:
        cloud_data = load_from_supabase(tid_input)
        if cloud_data:
            sync_session_with_cloud(cloud_data, tid_input)
            st.success(f"✅ Turnering '{tid_input}' er genoprettet!")
            st.rerun()
        else:
            st.session_state.current_tid = tid_input
            st.info(f"🆕 '{tid_input}' er et nyt ID. Klar til opsætning.")

if not tid_input:
    st.warning("Indtast et ID for at fortsætte.")
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfiguration")
    g_format = st.selectbox("Format", ["Americano", "Mexicano"])
    p_type = st.selectbox("Makkere", ["Skiftende makker", "Faste hold"])
    max_r = st.number_input("Runder før finale", 1, 20, value=st.session_state.max_rounds)
    
    # Bane-navne (Kun Mexicano)
    c_names = []
    if g_format == "Mexicano" and st.session_state.players:
        st.divider()
        st.subheader("🏟️ Navngiv Baner")
        for i in range(len(st.session_state.players) // 4):
            val = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
            c_names.append(st.text_input(f"Bane {i+1}", value=val))
        st.session_state.court_names = c_names

    p_input = st.text_area("Deltagere", value="\n".join(st.session_state.players), height=150)
    
    if st.button("🚀 START / NULSTIL"):
        names = [n.strip() for n in p_input.split('\n') if n.strip()]
        if len(names) % 4 == 0:
            st.session_state.update({"players": names, "round_number": 1, "matches": [], "history": [], "leaderboard": {n: {"Point": 0, "PF": 0, "V": 0, "U": 0, "T": 0} for n in names}, "max_rounds": max_r})
            if p_type == "Faste hold":
                random.shuffle(names)
                st.session_state.fixed_teams = [names[i:i+2] for i in range(0, len(names), 2)]
            save_to_supabase(tid_input, 1, st.session_state.leaderboard, [], names, st.session_state.fixed_teams, [], max_r, c_names)
            st.rerun()
        else: st.error("Antal skal gå op i 4!")

# --- 5. TABS ---
tab1, tab2, tab3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log & Rediger"])

with tab1:
    if st.session_state.players:
        is_over = st.session_state.round_number > st.session_state.max_rounds + 1
        is_finale = st.session_state.round_number > st.session_state.max_rounds and not is_over

        if is_over:
            st.balloons()
            st.header("🏆 Resultat: " + tid_input)
            df_final = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF"], ascending=False)
            df_final = df_final.reset_index().rename(columns={'index':'Spiller'})
            df_final.index = df_final.index + 1
            
            c1, c2, c3 = st.columns(3)
            if len(df_final) >= 3:
                c1.metric("🥇 1. Plads", df_final.iloc[0]['Spiller'], f"{int(df_final.iloc[0]['Point'])} pts")
                c2.metric("🥈 2. Plads", df_final.iloc[1]['Spiller'], f"{int(df_final.iloc[1]['Point'])} pts")
                c3.metric("🥉 3. Plads", df_final.iloc[2]['Spiller'], f"{int(df_final.iloc[2]['Point'])} pts")
            
            st.dataframe(df_final, use_container_width=True)
            csv = df_final.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Hent Resultat", data=csv, file_name=f"{tid_input}.csv", mime='text/csv', use_container_width=True)
        else:
            st.subheader("🔥 FINALE" if is_finale else f"Runde {st.session_state.round_number} af {st.session_state.max_rounds}")
            
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
                            else:
                                assigned, seen = [], set()
                                for p_n in ranked:
                                    for team in st.session_state.fixed_teams:
                                        t_tup = tuple(sorted(team))
                                        if p_n in team and t_tup not in seen:
                                            assigned.append(team); seen.add(t_tup)
                                h1, h2 = assigned[i*2], assigned[i*2+1]
                        else:
                            p_pool = st.session_state.players.copy() if i == 0 else p_pool
                            random.shuffle(p_pool)
                            p = [p_pool.pop() for _ in range(4)]
                            h1, h2 = [p[0], p[1]], [p[2], p[3]]
                        new_m.append({"Bane": b_navn, "H1": h1, "H2": h2, "S1": 16, "S2": 16})
                    st.session_state.matches = new_m
                    save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, new_m, st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds, st.session_state.court_names)
                    st.rerun()

            for i, m in enumerate(st.session_state.matches):
                with st.container(border=True):
                    st.write(f"### {m['Bane']}")
                    c1, c2 = st.columns([2, 1])
                    s1 = c1.number_input(f"{' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                    st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32-s1
                    c2.info(f"{' & '.join(m['H2'])}: **{32-s1}**")

            if st.session_state.matches and st.button("✅ Gem Resultater"):
                for m in st.session_state.matches:
                    for t, s, o in [(m['H1'], m['S1'], m['S2']), (m['H2'], m['S2'], m['S1'])]:
                        for p in t:
                            st.session_state.leaderboard[p]["Point"] += s
                            st.session_state.leaderboard[p]["PF"] += (s - o)
                            if s > o: st.session_state.leaderboard[p]["V"] += 1
                            elif s == o: st.session_state.leaderboard[p]["U"] += 1
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
    st.subheader("🔧 Rediger/Log")
    if st.session_state.players:
        p_edit = st.selectbox("Vælg spiller", st.session_state.players)
        new_p = st.number_input("Samlet point", value=st.session_state.leaderboard[p_edit]["Point"])
        new_pf = st.number_input("Samlet PF", value=st.session_state.leaderboard[p_edit]["PF"])
        if st.button("💾 Opdater"):
            st.session_state.leaderboard[p_edit]["Point"] = new_p
            st.session_state.leaderboard[p_edit]["PF"] = new_pf
            save_to_supabase(tid_input, st.session_state.round_number, st.session_state.leaderboard, st.session_state.matches, st.session_state.players, st.session_state.fixed_teams, st.session_state.history, st.session_state.max_rounds, st.session_state.court_names)
            st.success("Opdateret!")
    
    for e in reversed(st.session_state.history):
        with st.expander(f"Runde {e['R']}"):
            for k in e['K']: st.write(k)
