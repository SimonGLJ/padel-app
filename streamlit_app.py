import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Score v6.4", layout="wide", page_icon="🎾")
conn = st.connection("supabase", type=SupabaseConnection)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp { background-color: #1e1e1e; color: #d4d4d4; }
    [data-testid="stSidebar"] { background-color: #252525; }
    [data-testid="stSidebar"] * { color: #d4d4d4 !important; }
    .stButton > button {
        background-color: #2e2e2e; color: #d4d4d4;
        border: 1px solid #555555; border-radius: 6px;
    }
    .stButton > button:hover {
        background-color: #3a3a3a; color: #ffffff;
        border: 1px solid #888888;
    }
    .stNumberInput input, .stTextInput input, .stTextArea textarea {
        background-color: #2a2a2a !important; color: #d4d4d4 !important;
        border: 1px solid #444444 !important; border-radius: 6px !important;
    }
    .stNumberInput input:disabled {
        background-color: #333333 !important;
        color: #d4d4d4 !important;
        border: 1px solid #555555 !important;
        -webkit-text-fill-color: #d4d4d4 !important;
        opacity: 1 !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #2a2a2a !important; color: #d4d4d4 !important;
        border: 1px solid #444444 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #252525 !important;
        border: 1px solid #3a3a3a !important; border-radius: 8px !important;
    }
    [data-testid="stExpander"] {
        background-color: #252525 !important;
        border: 1px solid #3a3a3a !important; border-radius: 6px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #252525; color: #d4d4d4;
        border-radius: 6px 6px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3a3a3a !important; color: #ffffff !important;
    }
    hr { border-color: #3a3a3a; }
    h1, h2, h3, h4 { color: #c8c8c8 !important; }
    p, li, label { color: #d4d4d4 !important; }
</style>
""", unsafe_allow_html=True)

# --- INITIALISERING ---
def init_session_state():
    defaults = {
        "players": [], "leaderboard": {}, "round_number": 1, "matches": [],
        "history": [], "max_rounds": 7, "current_tid": None,
        "past_partnerships": {}, "past_opponents": {},
        "game_format": "Americano", "partner_type": "Skiftende makker",
        "fixed_teams": [], "score_system": "Frit",
        "tid_loaded": False, "show_correction_msg": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- HJÆLPEFUNKTIONER ---
def p_key(a, b):
    return tuple(sorted([a, b]))

def get_group_key(players_4):
    """Returnerer en unik, sorteret nøgle for en 4-mands gruppe."""
    return tuple(sorted(players_4))

def match_config_key(h1, h2):
    """Returnerer en unik nøgle for en specifik kampopstilling uanset holdorden."""
    t1 = tuple(sorted(h1))
    t2 = tuple(sorted(h2))
    return tuple(sorted([t1, t2]))

def recalculate_leaderboard_and_stats():
    """Genberegner leaderboard, partner- og modstander-statistik helt fra grunden ud fra history."""
    players = st.session_state.players
    new_board = {n: {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0} for n in players}
    new_partnerships = {}
    new_opponents = {}

    for entry in st.session_state.history:
        for m in entry.get("Kampe_raw", []):
            h1, h2, s1, s2 = m["H1"], m["H2"], int(m["S1"]), int(m["S2"])
            
            # Opdater partnerskaber
            for pair in [h1, h2]:
                k = p_key(pair[0], pair[1])
                new_partnerships[k] = new_partnerships.get(k, 0) + 1
                
            # Opdater modstandere
            for p1 in h1:
                for p2 in h2:
                    k = p_key(p1, p2)
                    new_opponents[k] = new_opponents.get(k, 0) + 1
                    
            # Opdater leaderboard
            for team, score, opp_score in [(h1, s1, s2), (h2, s2, s1)]:
                for p in team:
                    if p not in new_board:
                        new_board[p] = {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0}
                    s = new_board[p]
                    s["KS"] += 1
                    s["Point"] += score
                    s["PF"] += (score - opp_score)
                    if score > opp_score:
                        s["V"] += 1
                    elif score < opp_score:
                        s["T"] += 1
                    else:
                        s["U"] += 1

    st.session_state.leaderboard = new_board
    st.session_state.past_partnerships = new_partnerships
    st.session_state.past_opponents = new_opponents

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

def update_s2(i):
    s1_val = st.session_state[f"s1_{i}"]
    st.session_state.matches[i]["S1"] = s1_val
    st.session_state.matches[i]["S2"] = 32 - s1_val

def update_hist_s2(real_r_idx, m_idx):
    s1_val = st.session_state[f"hist_s1_{real_r_idx}_{m_idx}"]
    st.session_state.history[real_r_idx]["Kampe_raw"][m_idx]["S1"] = s1_val
    st.session_state.history[real_r_idx]["Kampe_raw"][m_idx]["S2"] = 32 - s1_val

def full_reset(names, g_format, p_type, max_r, score_sys):
    fixed = [[names[i], names[i+1]] for i in range(0, len(names), 2)] if p_type == "Faste hold" else []
    if p_type == "Faste hold":
        random.shuffle(fixed)
    st.session_state.update({
        "players": names, "game_format": g_format, "partner_type": p_type,
        "max_rounds": max_r, "score_system": score_sys,
        "round_number": 1, "matches": [], "history": [],
        "past_partnerships": {}, "past_opponents": {}, "fixed_teams": fixed,
        "tid_loaded": True, "show_correction_msg": None,
        "leaderboard": {n: {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0} for n in names}
    })

def generate_matches():
    players = st.session_state.players
    nc = len(players) // 4
    default_s1 = 16 if st.session_state.score_system == "32-point" else 0
    default_s2 = 16 if st.session_state.score_system == "32-point" else 0

    if st.session_state.round_number == st.session_state.max_rounds + 1:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        ranked = df.sort_values(by=["Point", "V", "PF"], ascending=[False, False, False]).index.tolist()
        matches = []
        for i in range(nc):
            matches.append({
                "Bane": f"Finale {i+1}",
                "H1": [ranked[i*4], ranked[i*4+3]],
                "H2": [ranked[i*4+1], ranked[i*4+2]],
                "S1": default_s1, "S2": default_s2
            })
        return matches

    if st.session_state.partner_type == "Faste hold":
        teams = list(st.session_state.fixed_teams)
        random.shuffle(teams)
        matches = []
        for i in range(nc):
            matches.append({
                "Bane": f"Bane {i+1}",
                "H1": teams[i*2], "H2": teams[i*2+1],
                "S1": default_s1, "S2": default_s2
            })
        return matches

    if st.session_state.game_format == "Mexicano":
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        df["jitter"] = [random.random() for _ in range(len(df))]
        ranked = df.sort_values(by=["Point", "jitter"], ascending=[False, True]).index.tolist()
        
        # Kortlæg tidligere spillede opstillinger for 4-mands grupper
        past_group_configs = {}
        for entry in st.session_state.history:
            for m in entry.get("Kampe_raw", []):
                g_players = m["H1"] + m["H2"]
                if len(g_players) == 4:
                    g_key = get_group_key(g_players)
                    c_key = match_config_key(m["H1"], m["H2"])
                    if g_key not in past_group_configs:
                        past_group_configs[g_key] = set()
                    past_group_configs[g_key].add(c_key)

        matches = []
        for i in range(nc):
            p1, p2, p3, p4 = ranked[i*4], ranked[i*4+1], ranked[i*4+2], ranked[i*4+3]
            group_key = get_group_key([p1, p2, p3, p4])
            played_configs = past_group_configs.get(group_key, set())

            # De 3 mulige konfigurationer for denne 4-mands gruppe:
            # Opt A (Standard Mexicano): 1+4 vs 2+3
            # Opt B (Alternativ 1):       1+3 vs 2+4
            # Opt C (Alternativ 2):       1+2 vs 3+4
            opt_A = ([p1, p4], [p2, p3])
            opt_B = ([p1, p3], [p2, p4])
            opt_C = ([p1, p2], [p3, p4])

            chosen_h1, chosen_h2 = opt_A[0], opt_A[1]

            # Hvis A allerede er spillet af denne præcise gruppe, roterer vi
            if match_config_key(opt_A[0], opt_A[1]) in played_configs:
                if match_config_key(opt_B[0], opt_B[1]) not in played_configs:
                    chosen_h1, chosen_h2 = opt_B[0], opt_B[1]
                elif match_config_key(opt_C[0], opt_C[1]) not in played_configs:
                    chosen_h1, chosen_h2 = opt_C[0], opt_C[1]

            matches.append({
                "Bane": f"Bane {i+1}",
                "H1": chosen_h1, "H2": chosen_h2,
                "S1": default_s1, "S2": default_s2
            })
        return matches

    best_score, best_matches = float("inf"), []
    for _ in range(1000):
        pool = list(players)
        random.shuffle(pool)
        m, s = [], 0
        for c in range(nc):
            h1, h2 = [pool.pop(), pool.pop()], [pool.pop(), pool.pop()]
            s += st.session_state.past_partnerships.get(p_key(h1[0], h1[1]), 0) * 500
            s += st.session_state.past_opponents.get(p_key(h1[0], h2[0]), 0) * 10
            m.append({
                "Bane": f"Bane {c+1}",
                "H1": h1, "H2": h2,
                "S1": default_s1, "S2": default_s2
            })
        if s < best_score:
            best_score, best_matches = s, m
    return best_matches

def save_to_supabase():
    if not st.session_state.current_tid:
        return
    payload = {
        "tournament_id": st.session_state.current_tid,
        "round_number": st.session_state.round_number,
        "leaderboard": st.session_state.leaderboard,
        "matches": st.session_state.matches,
        "players": st.session_state.players,
        "history": st.session_state.history,
        "max_rounds": st.session_state.max_rounds,
        "format": st.session_state.game_format,
        "partner_type": st.session_state.partner_type,
        "fixed_teams": st.session_state.fixed_teams,
        "score_system": st.session_state.score_system,
        "past_partnerships": {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_partnerships.items()},
        "past_opponents": {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_opponents.items()}
    }
    conn.table("tournaments").upsert(payload).execute()

# --- AUTO-LOAD via URL query param ---
query_tid = st.query_params.get("tid", "")
if query_tid and not st.session_state.tid_loaded:
    res = conn.table("tournaments").select("*").eq("tournament_id", query_tid).execute()
    if res.data:
        load_from_data(query_tid, res.data[0])
        st.rerun()
    else:
        st.session_state.current_tid = query_tid
        st.session_state.tid_loaded = True

# --- UI ---
st.title("🎾 Padel Score v6.4")

# Vis korrektionskvittering hvis der lige er blevet gemt en ændring
if st.session_state.show_correction_msg:
    st.success(f"✅ {st.session_state.show_correction_msg}")
    st.session_state.show_correction_msg = None

with st.expander("📍 Turnerings-ID — tryk for at skifte eller genoptage turnering"):
    st.write("Skriv et unikt ID for at starte en ny turnering, eller genindtast et tidligere ID for at genoptage.")

tid_raw = st.text_input(
    "Turnerings-ID",
    value=st.session_state.current_tid or "",
    placeholder="f.eks. fredagspadel-uge22"
).strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    res = conn.table("tournaments").select("*").eq("tournament_id", tid_raw).execute()
    if res.data:
        load_from_data(tid_raw, res.data[0])
    else:
        st.session_state.current_tid = tid_raw
        st.session_state.tid_loaded = True
    st.query_params["tid"] = tid_raw
    st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Indstillinger")
    st.markdown("---")

    g_format = st.selectbox(
        "🎮 Spilformat", ["Americano", "Mexicano"],
        index=0 if st.session_state.game_format == "Americano" else 1
    )
    p_type = st.selectbox(
        "👥 Makkertype", ["Skiftende makker", "Faste hold"],
        index=0 if st.session_state.partner_type == "Skiftende makker" else 1
    )
    score_sys = st.selectbox(
        "🔢 Pointsystem", ["Frit", "32-point"],
        index=0 if st.session_state.score_system == "Frit" else 1
    )
    max_r = st.number_input(
        "🏁 Grundspilsrunder", min_value=1, max_value=50,
        value=st.session_state.max_rounds
    )
    p_input = st.text_area(
        "📋 Deltagere (ét navn per linje)",
        value="\n".join(st.session_state.players),
        height=200
    )

    if st.button("🚀 GEM SETUP / START NY TURNERING", use_container_width=True):
        names = [n.strip() for n in p_input.split("\n") if n.strip()]
        if len(names) % 4 != 0:
            st.error(f"Antal spillere skal være deleligt med 4. Du har {len(names)} spillere.")
        else:
            full_reset(names, g_format, p_type, max_r, score_sys)
            try:
                save_to_supabase()
                st.success("Setup gemt!")
            except Exception as e:
                st.error(f"Kunne ikke gemme setup: {e}")
            st.rerun()

# --- TABS ---
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log & Rediger"])

with t1:
    if not st.session_state.players:
        st.info("👈 Tilføj spillere og tryk 'GEM SETUP' i indstillingerne for at starte.")
        st.stop()

    tournament_finished = st.session_state.round_number > st.session_state.max_rounds + 1

    if tournament_finished:
        st.balloons()
        st.success("🏆 TURNERING AFSLUTTET!")
        st.markdown("### Endelig Stilling:")
        if st.session_state.leaderboard:
            df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
            st.dataframe(
                df[["KS", "V", "U", "T", "Point", "PF"]].sort_values(["Point", "V"], ascending=False),
                use_container_width=True
            )
        if st.button("🔄 Start helt forfra"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    if st.session_state.round_number == st.session_state.max_rounds + 1:
        st.warning("🔥 FINALE-RUNDE: Spillere parres efter 1+4 vs 2+3!")

    runde_label = "Finalen" if st.session_state.round_number == st.session_state.max_rounds + 1 else f"Runde {st.session_state.round_number}"
    st.markdown(f"#### ⏱️ Aktuel: {runde_label}")

    if not st.session_state.matches:
        if st.button(f"🎲 Generer {runde_label}", use_container_width=True):
            st.session_state.matches = generate_matches()
            try:
                save_to_supabase()
            except Exception as e:
                st.error(f"Kunne ikke gemme: {e}")
            st.rerun()

    for i, m in enumerate(st.session_state.matches):
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2, 1, 2])
            col_a.markdown(f"**🟦 {', '.join(m['H1'])}**")
            col_b.markdown("<div style='text-align:center;font-weight:bold;padding-top:6px'>vs</div>", unsafe_allow_html=True)
            col_c.markdown(f"**🟥 {', '.join(m['H2'])}**")

            st.caption(f"📍 {m.get('Bane', '?')}")

            if st.button("✏️ Rediger hold", key=f"edit_{i}"):
                st.session_state[f"buf_{i}"] = {"H1": list(m["H1"]), "H2": list(m["H2"])}

            if f"buf_{i}" in st.session_state:
                b = st.session_state[f"buf_{i}"]
                c1, c2 = st.columns(2)
                b["H1"][0] = c1.text_input("🟦 Spiller 1", b["H1"][0], key=f"b_h1s1_{i}")
                b["H1"][1] = c1.text_input("🟦 Spiller 2", b["H1"][1], key=f"b_h1s2_{i}")
                b["H2"][0] = c2.text_input("🟥 Spiller 1", b["H2"][0], key=f"b_h2s1_{i}")
                b["H2"][1] = c2.text_input("🟥 Spiller 2", b["H2"][1], key=f"b_h2s2_{i}")
                save_col, cancel_col = st.columns(2)
                if save_col.button("💾 Gem hold", key=f"s_{i}"):
                    if all([b["H1"][0], b["H1"][1], b["H2"][0], b["H2"][1]]):
                        st.session_state.matches[i]["H1"] = b["H1"]
                        st.session_state.matches[i]["H2"] = b["H2"]
                        del st.session_state[f"buf_{i}"]
                        st.rerun()
                    else:
                        st.error("Alle fire spillernavne skal udfyldes.")
                if cancel_col.button("✖ Annuller", key=f"cancel_{i}"):
                    del st.session_state[f"buf_{i}"]
                    st.rerun()

            sc1, sc2 = st.columns(2)

            if st.session_state.score_system == "32-point":
                sc1.number_input(
                    f"🟦 Score — {m['H1'][0]} & {m['H1'][1]}",
                    min_value=0, max_value=32,
                    value=int(m["S1"]),
                    key=f"s1_{i}",
                    on_change=update_s2,
                    args=(i,)
                )
                sc2.number_input(
                    f"🟥 Score — {m['H2'][0]} & {m['H2'][1]}",
                    min_value=0, max_value=32,
                    value=int(st.session_state.matches[i]["S2"]),
                    disabled=True,
                    help="Beregnes automatisk som 32 minus Hold 1's score"
                )
            else:
                s1 = sc1.number_input(
                    f"🟦 Score — {m['H1'][0]} & {m['H1'][1]}",
                    min_value=0, max_value=999,
                    value=int(m["S1"]),
                    key=f"s1_{i}"
                )
                s2 = sc2.number_input(
                    f"🟥 Score — {m['H2'][0]} & {m['H2'][1]}",
                    min_value=0, max_value=999,
                    value=int(m["S2"]),
                    key=f"s2_{i}"
                )
                st.session_state.matches[i]["S1"] = s1
                st.session_state.matches[i]["S2"] = s2

    if st.session_state.matches and st.button("✅ Gem Resultat & Gå til næste runde", use_container_width=True):
        st.session_state.history.append({
            "Runde": st.session_state.round_number,
            "Kampe_raw": [
                {
                    "Bane": m.get("Bane", "?"),
                    "H1": list(m["H1"]),
                    "H2": list(m["H2"]),
                    "S1": int(m["S1"]),
                    "S2": int(m["S2"])
                }
                for m in st.session_state.matches
            ]
        })
        st.session_state.round_number += 1
        st.session_state.matches = []
        recalculate_leaderboard_and_stats()
        try:
            save_to_supabase()
        except Exception as e:
            st.error(f"Kunne ikke gemme: {e}")
        st.rerun()

with t2:
    st.markdown("### 📊 Aktuel stilling")
    if st.session_state.leaderboard:
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        st.dataframe(
            df[["KS", "V", "U", "T", "Point", "PF"]].sort_values(["Point", "V"], ascending=False),
            use_container_width=True
        )
        st.caption("KS = Kampe spillet · V = Vundet · U = Uafgjort · T = Tabt · PF = Pointforskel")
    else:
        st.info("Ingen stilling endnu. Start en turnering i indstillingerne.")

with t3:
    st.markdown("### 📜 Rundehistorik & Redigering")
    if st.session_state.history:
        for r_idx, e in enumerate(reversed(st.session_state.history)):
            real_r_idx = len(st.session_state.history) - 1 - r_idx
            
            is_edited = e.get("edited", False)
            tag = " ✏️ (Korrigeret)" if is_edited else ""
            
            with st.expander(f"Runde {e['Runde']}{tag}"):
                
                if "Kampe_raw" in e:
                    for m_idx, m in enumerate(e["Kampe_raw"]):
                        st.markdown(f"**📍 {m.get('Bane', '?')}** — {', '.join(m['H1'])} vs {', '.join(m['H2'])}")
                        
                        col1, col2 = st.columns(2)
                        if st.session_state.score_system == "32-point":
                            col1.number_input(
                                f"Score Hold 1 ({'&'.join(m['H1'])})",
                                min_value=0, max_value=32,
                                value=int(m["S1"]),
                                key=f"hist_s1_{real_r_idx}_{m_idx}",
                                on_change=update_hist_s2,
                                args=(real_r_idx, m_idx)
                            )
                            col2.number_input(
                                f"Score Hold 2 ({'&'.join(m['H2'])})",
                                min_value=0, max_value=32,
                                value=int(m["S2"]),
                                disabled=True,
                                help="Beregnes automatisk som 32 minus Hold 1's score"
                            )
                        else:
                            ns1 = col1.number_input(
                                f"Score Hold 1 ({'&'.join(m['H1'])})",
                                min_value=0, max_value=999,
                                value=int(m["S1"]),
                                key=f"hist_s1_{real_r_idx}_{m_idx}"
                            )
                            ns2 = col2.number_input(
                                f"Score Hold 2 ({'&'.join(m['H2'])})",
                                min_value=0, max_value=999,
                                value=int(m["S2"]),
                                key=f"hist_s2_{real_r_idx}_{m_idx}"
                            )
                            m["S1"] = ns1
                            m["S2"] = ns2
                        st.markdown("---")
                    
                    if st.button(f"💾 Gem korrektion for Runde {e['Runde']}", key=f"save_hist_{real_r_idx}", use_container_width=True):
                        e["edited"] = True
                        recalculate_leaderboard_and_stats()
                        try:
                            save_to_supabase()
                            st.session_state.show_correction_msg = f"Runde {e['Runde']} blev korrigeret og gemt! Leaderboardet er opdateret."
                        except Exception as e:
                            st.error(f"Kunne ikke gemme til databasen: {e}")
                        st.rerun()
                else:
                    for k in e.get("Kampe", []):
                        st.write(k)
    else:
        st.info("Ingen runder spillet endnu.")
