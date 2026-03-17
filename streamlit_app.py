import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Score", layout="wide", page_icon="🎾")
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
        "tid_loaded": False, "pregenerated_rounds": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- HJÆLPEFUNKTION: Load fra Supabase-data ---
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
        "pregenerated_rounds": d.get("pregenerated_rounds", []),
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

# --- VALIDERING ---
def p_key(a, b):
    return tuple(sorted([a, b]))

def verify_no_duplicate_partners(pregenerated_rounds):
    partnership_count = {}
    issues = []
    for round_idx, rnd in enumerate(pregenerated_rounds):
        for match in rnd:
            for pair in [match["H1"], match["H2"]]:
                if len(pair) == 2:
                    k = p_key(pair[0], pair[1])
                    if k in partnership_count:
                        issues.append(
                            f"Runde {round_idx+1}: {pair[0]} & {pair[1]} "
                            f"har allerede spillet sammen i runde {partnership_count[k]}"
                        )
                    else:
                        partnership_count[k] = round_idx + 1
    return issues

# --- ROUND ROBIN ALGORITME ---
def round_robin_schedule(players):
    pool = list(players)
    random.shuffle(pool)
    n = len(pool)
    fixed = pool[0]
    rotating = pool[1:]
    rounds = []

    for round_idx in range(n - 1):
        current = [fixed] + rotating
        pairs = []
        for j in range(n // 2):
            pairs.append((current[j], current[n - 1 - j]))

        round_matches = []
        for c in range(n // 4):
            h1_pair = pairs[c * 2]
            h2_pair = pairs[c * 2 + 1]
            round_matches.append({
                "Bane": f"Bane {c + 1}",
                "H1": list(h1_pair),
                "H2": list(h2_pair),
                "S1": 0, "S2": 0
            })
        rounds.append(round_matches)
        rotating = [rotating[-1]] + rotating[:-1]

    return rounds

def pregenerate_americano_rounds(players, max_rounds, score_system):
    default_s1 = 16 if score_system == "32-point" else 0
    default_s2 = 16 if score_system == "32-point" else 0
    best_result = None
    best_issue_count = float("inf")

    for attempt in range(20):
        all_rounds = round_robin_schedule(players)
        result = []
        for rnd in all_rounds[:max_rounds]:
            round_with_scores = []
            for m in rnd:
                round_with_scores.append({
                    "Bane": m["Bane"],
                    "H1": m["H1"],
                    "H2": m["H2"],
                    "S1": default_s1,
                    "S2": default_s2
                })
            result.append(round_with_scores)

        issues = verify_no_duplicate_partners(result)
        if not issues:
            return result, []
        if len(issues) < best_issue_count:
            best_issue_count = len(issues)
            best_result = (result, issues)

    return best_result

# --- LOGIK ---
def update_s2(i):
    s1_val = st.session_state[f"s1_{i}"]
    st.session_state.matches[i]["S1"] = s1_val
    st.session_state.matches[i]["S2"] = 32 - s1_val

def full_reset(names, g_format, p_type, max_r, score_sys):
    if p_type == "Faste hold":
        shuffled = list(names)
        random.shuffle(shuffled)
        fixed = [[shuffled[i], shuffled[i+1]] for i in range(0, len(shuffled), 2)]
    else:
        fixed = []

    pregenerated = []
    gen_issues = []
    if g_format == "Americano" and p_type == "Skiftende makker":
        pregenerated, gen_issues = pregenerate_americano_rounds(names, max_r, score_sys)

    st.session_state.update({
        "players": names, "game_format": g_format, "partner_type": p_type,
        "max_rounds": max_r, "score_system": score_sys,
        "round_number": 1, "matches": [], "history": [],
        "past_partnerships": {}, "past_opponents": {}, "fixed_teams": fixed,
        "tid_loaded": True, "pregenerated_rounds": pregenerated,
        "leaderboard": {n: {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0} for n in names}
    })
    return gen_issues

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
                if p not in st.session_state.leaderboard:
                    st.session_state.leaderboard[p] = {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0}
                s = st.session_state.leaderboard[p]
                s["KS"] += 1
                s["Point"] += score
                s["PF"] += (score - opp_score)
                if score > opp_score:
                    s["V"] += 1
                elif score < opp_score:
                    s["T"] += 1
                else:
                    s["U"] += 1

def generate_matches():
    players = st.session_state.players
    nc = len(players) // 4
    default_s1 = 16 if st.session_state.score_system == "32-point" else 0
    default_s2 = 16 if st.session_state.score_system == "32-point" else 0
    runde_idx = st.session_state.round_number - 1

    # --- FINALE ---
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

    # --- AMERICANO MED FORHÅNDSGENEREREDE RUNDER ---
    if (st.session_state.game_format == "Americano"
            and st.session_state.partner_type == "Skiftende makker"
            and st.session_state.pregenerated_rounds
            and runde_idx < len(st.session_state.pregenerated_rounds)):
        rnd = st.session_state.pregenerated_rounds[runde_idx]
        matches = []
        for m in rnd:
            matches.append({
                "Bane": m["Bane"],
                "H1": m["H1"],
                "H2": m["H2"],
                "S1": default_s1,
                "S2": default_s2
            })
        return matches

    # --- FASTE HOLD ---
    if st.session_state.partner_type == "Faste hold":
        teams = list(st.session_state.fixed_teams)
        best_score = float("inf")
        best_order = None
        for _ in range(5000):
            shuffled = list(teams)
            random.shuffle(shuffled)
            s = 0
            for i in range(nc):
                t1 = shuffled[i*2]
                t2 = shuffled[i*2+1]
                for p1 in t1:
                    for p2 in t2:
                        s += st.session_state.past_opponents.get(p_key(p1, p2), 0) * 100
            if s < best_score:
                best_score = s
                best_order = shuffled
            if best_score == 0:
                break
        matches = []
        for i in range(nc):
            matches.append({
                "Bane": f"Bane {i+1}",
                "H1": best_order[i*2],
                "H2": best_order[i*2+1],
                "S1": default_s1, "S2": default_s2
            })
        return matches

    # --- MEXICANO ---
    if st.session_state.game_format == "Mexicano":
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        df["jitter"] = [random.random() for _ in range(len(df))]
        ranked = df.sort_values(by=["Point", "jitter"], ascending=[False, True]).index.tolist()
        matches = []
        for i in range(nc):
            matches.append({
                "Bane": f"Bane {i+1}",
                "H1": [ranked[i*4], ranked[i*4+3]],
                "H2": [ranked[i*4+1], ranked[i*4+2]],
                "S1": default_s1, "S2": default_s2
            })
        return matches

    # --- FALLBACK ---
    best_score_val = float("inf")
    best_matches = None
    for _ in range(5000):
        pool = list(players)
        random.shuffle(pool)
        m = []
        s = 0
        for c in range(nc):
            h1 = [pool.pop(), pool.pop()]
            h2 = [pool.pop(), pool.pop()]
            s += st.session_state.past_partnerships.get(p_key(h1[0], h1[1]), 0) * 10000
            s += st.session_state.past_partnerships.get(p_key(h2[0], h2[1]), 0) * 10000
            for p1 in h1:
                for p2 in h2:
                    s += st.session_state.past_opponents.get(p_key(p1, p2), 0) * 100
            m.append({"Bane": f"Bane {c+1}", "H1": h1, "H2": h2,
                      "S1": default_s1, "S2": default_s2})
        if s < best_score_val:
            best_score_val = s
            best_matches = m
        if best_score_val == 0:
            break
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
        "pregenerated_rounds": st.session_state.pregenerated_rounds,
        "past_partnerships": {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_partnerships.items()},
        "past_opponents": {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_opponents.items()}
    }
    conn.table("tournaments").upsert(payload).execute()

# --- UI ---
st.title("🎾 Padel Score")

with st.expander("📍 Turnerings-ID — tryk for at skifte eller genoptage turnering"):
    st.write("Skriv et unikt ID for at starte en ny turnering, eller genindtast et tidligere ID for at genoptage. Samme ID på flere enheder giver fælles adgang i realtid.")

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

    with st.expander("ℹ️ Hvad er spilformat?"):
        st.write("**Americano:** Alle runder genereres på forhånd med en round robin algoritme der garanterer unikke makkere hver runde.")
        st.write("**Mexicano:** Par dannes dynamisk ud fra stillingen — de bedste spiller mod de bedste. Første runde er tilfældig da ingen endnu har point. Makkere kan gentages da stillingen styrer parringen.")

    g_format = st.selectbox(
        "🎮 Spilformat", ["Americano", "Mexicano"],
        index=0 if st.session_state.game_format == "Americano" else 1
    )

    st.markdown("---")

    with st.expander("ℹ️ Hvad er makkertype?"):
        st.write("**Skiftende makker:** Round robin algoritmen garanterer unikke makkere i alle runder (op til n-1 runder for n spillere).")
        st.write("**Faste hold:** Makkerne trækkes tilfældigt ved opstart og er faste resten af turneringen. Algoritmen sikrer nye modstandere hver runde.")

    p_type = st.selectbox(
        "👥 Makkertype", ["Skiftende makker", "Faste hold"],
        index=0 if st.session_state.partner_type == "Skiftende makker" else 1
    )

    st.markdown("---")

    with st.expander("ℹ️ Hvad er pointsystem?"):
        st.write("**Frit:** Begge holds point indtastes manuelt — ingen begrænsning på totalen.")
        st.write("**32-point:** Kun Hold 1's score indtastes. Hold 2 får automatisk resten, så totalen altid er 32 (f.eks. 20–12).")

    score_sys = st.selectbox(
        "🔢 Pointsystem", ["Frit", "32-point"],
        index=0 if st.session_state.score_system == "Frit" else 1
    )

    st.markdown("---")

    with st.expander("ℹ️ Hvad er grundspilsrunder?"):
        st.write("Antal runder inden finalen. Efter grundspillet afholdes automatisk én finaleruunde hvor nr. 1+4 spiller mod nr. 2+3.")
        st.write("Ved 8 spillere anbefales max 7 runder for garanterede unikke makkere i Americano.")

    max_r = st.number_input(
        "🏁 Grundspilsrunder", min_value=1, max_value=50,
        value=st.session_state.max_rounds
    )

    st.markdown("---")

    with st.expander("ℹ️ Sådan tilføjer du deltagere"):
        st.write("Skriv ét navn per linje. Antal skal være deleligt med 4 (8, 12, 16 osv.).")
        st.write("Ved faste hold trækkes makkerne tilfældigt — rækkefølgen du skriver navnene i har ingen betydning.")

    p_input = st.text_area(
        "📋 Deltagere (ét navn per linje)",
        value="\n".join(st.session_state.players),
        height=200, placeholder="Anders\nBjørn\nCaroline\nDorthe"
    )

    st.markdown("---")

    if st.button("🚀 GEM SETUP / START NY TURNERING", use_container_width=True):
        names = [n.strip() for n in p_input.split("\n") if n.strip()]
        if len(names) % 4 != 0:
            st.error(f"Antal spillere skal være deleligt med 4. Du har {len(names)} spillere.")
        else:
            gen_issues = full_reset(names, g_format, p_type, max_r, score_sys)
            if g_format == "Americano" and p_type == "Skiftende makker":
                antal = len(st.session_state.pregenerated_rounds)
                max_mulige = len(names) - 1
                if max_r > max_mulige:
                    st.warning(
                        f"⚠️ Med {len(names)} spillere kan der kun genereres "
                        f"{max_mulige} runder med unikke makkere. "
                        f"Runde {max_mulige + 1}–{max_r} bruger en alternativ algoritme."
                    )
                if gen_issues:
                    st.warning("⚠️ Kunne ikke garantere helt unikke makkere efter 20 forsøg. Bedste mulige skema bruges.")
                else:
                    st.success(f"✅ Setup gemt! {antal} runder forhåndsgenereret — alle makkere er unikke.")
            else:
                st.success("✅ Setup gemt!")
            try:
                save_to_supabase()
            except Exception as e:
                st.error(f"Kunne ikke gemme setup: {e}")
            st.rerun()

# --- TABS ---
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

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

    if (st.session_state.game_format == "Americano"
            and st.session_state.partner_type == "Skiftende makker"
            and st.session_state.pregenerated_rounds):
        total = len(st.session_state.pregenerated_rounds)
        current = st.session_state.round_number
        if current <= total:
            st.caption(f"📋 Forhåndsgenereret turnering — Runde {current} af {total}")

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
                        runde_idx = st.session_state.round_number - 1
                        if (st.session_state.pregenerated_rounds
                                and runde_idx < len(st.session_state.pregenerated_rounds)
                                and i < len(st.session_state.pregenerated_rounds[runde_idx])):
                            st.session_state.pregenerated_rounds[runde_idx][i]["H1"] = b["H1"]
                            st.session_state.pregenerated_rounds[runde_idx][i]["H2"] = b["H2"]
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
        register_match_data(st.session_state.matches)
        st.session_state.history.append({
            "Runde": st.session_state.round_number,
            "Kampe": [
                f"{m.get('Bane', '?')}: {'&'.join(m['H1'])} vs {'&'.join(m['H2'])} ({m['S1']}-{m['S2']})"
                for m in st.session_state.matches
            ]
        })
        st.session_state.round_number += 1
        st.session_state.matches = []
        try:
            save_to_supabase()
        except Exception as e:
            st.error(f"Kunde ikke gemme: {e}")
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
    st.markdown("### 📜 Rundehistorik")
    if st.session_state.history:
        for e in reversed(st.session_state.history):
            with st.expander(f"Runde {e['Runde']}"):
                for k in e["Kampe"]:
                    st.write(k)
    else:
        st.info("Ingen runder spillet endnu.")
