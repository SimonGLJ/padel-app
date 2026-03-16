import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

st.set_page_config(page_title="Padel Master Pro v5.0", layout="wide", page_icon="🎾")
conn = st.connection("supabase", type=SupabaseConnection)

# ---------------------------------------------------------------------------
# INITIALISERING
# ---------------------------------------------------------------------------
def init_session_state():
    defaults = {
        "players": [],
        "leaderboard": {},
        "round_number": 1,
        "matches": [],
        "history": [],
        "max_rounds": 7,
        "current_tid": None,
        "past_partnerships": {},   # {tuple(sorted([p1,p2])): count}
        "past_opponents": {},      # {tuple(sorted([p1,p2])): count}
        "game_format": "Americano",
        "partner_type": "Skiftende makker",
        "fixed_teams": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ---------------------------------------------------------------------------
# HJÆLPEFUNKTIONER
# ---------------------------------------------------------------------------
def p_key(a, b):
    """Sorteret nøgle til par-opslag – brugt konsekvent overalt."""
    return tuple(sorted([a, b]))


def full_reset(names, g_format, p_type, max_r):
    """Nulstiller al turneringsstate fuldstændigt."""
    fixed = []
    if p_type == "Faste hold":
        temp = list(names)
        random.shuffle(temp)
        fixed = [[temp[i], temp[i + 1]] for i in range(0, len(temp), 2)]
    st.session_state.update({
        "players":          names,
        "game_format":      g_format,
        "partner_type":     p_type,
        "max_rounds":       max_r,
        "round_number":     1,
        "matches":          [],
        "history":          [],
        "past_partnerships": {},
        "past_opponents":   {},
        "fixed_teams":      fixed,
        "leaderboard":      {n: {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0} for n in names},
    })

# ---------------------------------------------------------------------------
# KAMP-REGISTRERING
# ---------------------------------------------------------------------------
def register_match_data(matches):
    """
    Opdaterer past_partnerships, past_opponents og leaderboard
    for en liste af afsluttede kampe.
    """
    for m in matches:
        # Makkere
        for pair in [m["H1"], m["H2"]]:
            k = p_key(pair[0], pair[1])
            st.session_state.past_partnerships[k] = st.session_state.past_partnerships.get(k, 0) + 1

        # Modstandere
        for p1 in m["H1"]:
            for p2 in m["H2"]:
                k = p_key(p1, p2)
                st.session_state.past_opponents[k] = st.session_state.past_opponents.get(k, 0) + 1

        # Statistik
        for team, score, opp_score in [
            (m["H1"], m["S1"], m["S2"]),
            (m["H2"], m["S2"], m["S1"]),
        ]:
            for p in team:
                if p not in st.session_state.leaderboard:
                    # Sikkerhedsnet: spiller mangler i LB (kan ske efter redigering)
                    st.session_state.leaderboard[p] = {"KS": 0, "V": 0, "U": 0, "T": 0, "Point": 0, "PF": 0}
                stats = st.session_state.leaderboard[p]
                stats["KS"]    += 1
                stats["Point"] += score
                stats["PF"]    += score - opp_score
                if   score > opp_score: stats["V"] += 1
                elif score < opp_score: stats["T"] += 1
                else:                   stats["U"] += 1

# ---------------------------------------------------------------------------
# MATCH-GENERERING
# ---------------------------------------------------------------------------
def generate_matches():
    players = st.session_state.players
    nc      = len(players) // 4

    # --- FASTE HOLD ---
    if st.session_state.partner_type == "Faste hold":
        # Auto-generer hold hvis de mangler (bør ikke ske, men sikkerhedsnet)
        if not st.session_state.fixed_teams:
            temp = list(players)
            random.shuffle(temp)
            st.session_state.fixed_teams = [[temp[i], temp[i + 1]] for i in range(0, len(temp), 2)]

        teams = list(st.session_state.fixed_teams)
        random.shuffle(teams)
        matches = []
        for i in range(nc):
            h1 = list(teams[i * 2])       # kopi – undgår mutation af fixed_teams
            h2 = list(teams[i * 2 + 1])
            matches.append({"Bane": f"Bane {i+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        return matches

    # --- MEXICANO ---
    if st.session_state.game_format == "Mexicano":
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient="index")
        # Jitter kun brugt til at bryde slips – sortér primært på Point (desc)
        df["jitter"] = [random.random() for _ in range(len(df))]
        ranked = df.sort_values(by=["Point", "jitter"], ascending=[False, True]).index.tolist()
        matches = []
        for i in range(nc):
            p = ranked[i * 4 : i * 4 + 4]
            # Mexicano-pairing: rank 1 & 4 vs rank 2 & 3 (balanceret)
            matches.append({
                "Bane": f"Bane {i+1}",
                "H1": [p[0], p[3]],
                "H2": [p[1], p[2]],
                "S1": 16, "S2": 16,
            })
        return matches

    # --- AMERICANO (Monte Carlo) ---
    # Straf: makkergentagelse * 500, modstandergentagelse * 10
    best_score, best_matches = float("inf"), []
    for _ in range(1000):
        pool = list(players)
        random.shuffle(pool)
        m_list, score = [], 0
        for c in range(nc):
            h1 = [pool.pop(), pool.pop()]
            h2 = [pool.pop(), pool.pop()]
            score += st.session_state.past_partnerships.get(p_key(h1[0], h1[1]), 0) * 500
            score += st.session_state.past_partnerships.get(p_key(h2[0], h2[1]), 0) * 500
            for a in h1:
                for b in h2:
                    score += st.session_state.past_opponents.get(p_key(a, b), 0) * 10
            m_list.append({"Bane": f"Bane {c+1}", "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        if score < best_score:
            best_score, best_matches = score, m_list
            if best_score == 0:
                break  # Perfekt runde fundet
    return best_matches

# ---------------------------------------------------------------------------
# SUPABASE
# ---------------------------------------------------------------------------
def save_to_supabase():
    if not st.session_state.current_tid:
        return
    # Serialisér tuple-nøgler til strings (JSON kræver string-nøgler)
    payload = {
        "tournament_id":    st.session_state.current_tid,
        "round_number":     st.session_state.round_number,
        "leaderboard":      st.session_state.leaderboard,
        "matches":          st.session_state.matches,
        "players":          st.session_state.players,
        "history":          st.session_state.history,
        "max_rounds":       st.session_state.max_rounds,
        "format":           st.session_state.game_format,
        "partner_type":     st.session_state.partner_type,
        "fixed_teams":      st.session_state.fixed_teams,
        "past_partnerships": {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_partnerships.items()},
        "past_opponents":    {f"{k[0]}|{k[1]}": v for k, v in st.session_state.past_opponents.items()},
    }
    try:
        conn.table("tournaments").upsert(payload).execute()
    except Exception as e:
        st.error(f"Supabase fejl: {e}")


def load_from_supabase(tid):
    """Indlæser turnering og returnerer True hvis den fandtes."""
    res = conn.table("tournaments").select("*").eq("tournament_id", tid).execute()
    if not res.data:
        return False
    d = res.data[0]

    def parse_pair_dict(raw):
        if not raw:
            return {}
        return {tuple(k.split("|")): v for k, v in raw.items()}

    st.session_state.update({
        "current_tid":      tid,
        "players":          d.get("players", []),
        "leaderboard":      d.get("leaderboard", {}),
        "round_number":     d.get("round_number", 1),
        "matches":          d.get("matches", []),
        "history":          d.get("history", []),
        "max_rounds":       d.get("max_rounds", 7),
        "game_format":      d.get("format", "Americano"),
        "partner_type":     d.get("partner_type", "Skiftende makker"),
        "fixed_teams":      d.get("fixed_teams", []),
        "past_partnerships": parse_pair_dict(d.get("past_partnerships")),
        "past_opponents":    parse_pair_dict(d.get("past_opponents")),
    })
    return True

# ---------------------------------------------------------------------------
# UI – HOVED
# ---------------------------------------------------------------------------
st.title("🎾 Padel Master Pro v5.0")

tid_raw = st.text_input(
    "📍 Turnerings-ID (del dette med dine medspillere)",
    value=st.session_state.current_tid or "",
).strip().lower()

if tid_raw and tid_raw != st.session_state.current_tid:
    found = load_from_supabase(tid_raw)
    if not found:
        st.session_state.current_tid = tid_raw
        st.info("Nyt turnerings-ID – konfigurér og tryk **GEM SETUP / START NY** i sidebaren.")
    st.rerun()

if not st.session_state.current_tid:
    st.info("👋 Indtast et Turnerings-ID ovenfor for at starte eller genoptage en turnering.")
    st.stop()

# ---------------------------------------------------------------------------
# SIDEBAR – KONFIGURATION
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Konfiguration")

    g_format = st.selectbox(
        "Format",
        ["Americano", "Mexicano"],
        index=0 if st.session_state.game_format == "Americano" else 1,
        help="Americano: tilfældige makkere optimeret mod gentagelser. Mexicano: makkere parres efter stilling.",
    )
    p_type = st.selectbox(
        "Makkere",
        ["Skiftende makker", "Faste hold"],
        index=0 if st.session_state.partner_type == "Skiftende makker" else 1,
        help="Faste hold: samme makkerpar hele turneringen.",
    )
    max_r = st.number_input("Max runder", min_value=1, max_value=50, value=st.session_state.max_rounds)
    p_input = st.text_area(
        "Deltagere (én pr. linje – skal være delelig med 4)",
        value="\n".join(st.session_state.players),
        height=200,
    )

    if st.button("🚀 GEM SETUP / START NY", use_container_width=True):
        names = [n.strip() for n in p_input.split("\n") if n.strip()]
        if len(names) == 0:
            st.error("Tilføj mindst 4 spillere.")
        elif len(names) % 4 != 0:
            st.error(f"Antal spillere skal være delelig med 4. Du har {len(names)}.")
        else:
            full_reset(names, g_format, p_type, max_r)
            save_to_supabase()
            st.rerun()

    # Vis aktuel turneringsstatus i sidebaren
    if st.session_state.players:
        st.divider()
        st.caption(f"**ID:** {st.session_state.current_tid}")
        st.caption(f"**Runde:** {st.session_state.round_number} / {st.session_state.max_rounds}")
        st.caption(f"**Spillere:** {len(st.session_state.players)}")
        st.caption(f"**Format:** {st.session_state.game_format} · {st.session_state.partner_type}")

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log"])

# ── TAB 1: KAMPE ────────────────────────────────────────────────────────────
with t1:
    if not st.session_state.players:
        st.info("Ingen spillere endnu – konfigurér i sidebaren.")
        st.stop()

    tournament_done = st.session_state.round_number > st.session_state.max_rounds

    if tournament_done and not st.session_state.matches:
        st.success(f"🏆 Turneringen er færdig! ({st.session_state.max_rounds} runder spillet)")
        st.stop()

    # Vis knap til at generere næste runde
    if not st.session_state.matches and not tournament_done:
        st.info(f"Runde **{st.session_state.round_number}** af **{st.session_state.max_rounds}** – klar til at generere kampe.")
        if st.button("🎲 Generer næste runde", use_container_width=True):
            with st.spinner("Beregner bedste kampe..."):
                st.session_state.matches = generate_matches()
            save_to_supabase()
            st.rerun()

    # Vis aktive kampe
    for i, m in enumerate(st.session_state.matches):
        with st.container(border=True):
            # Hold-visning
            col_a, col_b, col_c = st.columns([5, 1, 5])
            col_a.markdown(f"### {' & '.join(m['H1'])}")
            col_b.markdown("<div style='text-align:center;padding-top:8px'><b>vs</b></div>", unsafe_allow_html=True)
            col_c.markdown(f"### {' & '.join(m['H2'])}")

            # Score-input
            s_col1, s_col2 = st.columns(2)
            s1 = s_col1.number_input(
                f"Point til **{' & '.join(m['H1'])}**",
                min_value=0, max_value=32,
                value=int(m["S1"]),
                key=f"s1_{i}",
            )
            s2 = 32 - s1
            s_col2.metric(label=f"Point til {' & '.join(m['H2'])}", value=s2)

            st.session_state.matches[i]["S1"] = s1
            st.session_state.matches[i]["S2"] = s2

            # Rediger kamp-knap (buffer-baseret – ingen direkte mutation)
            if st.button("✏️ Rediger spillere", key=f"edit_{i}"):
                st.session_state[f"buf_{i}"] = {"H1": list(m["H1"]), "H2": list(m["H2"])}

            if f"buf_{i}" in st.session_state:
                b = st.session_state[f"buf_{i}"]
                ec1, ec2 = st.columns(2)
                with ec1:
                    st.markdown("**Hold 1**")
                    b["H1"][0] = st.text_input("Spiller 1", b["H1"][0], key=f"e1_{i}")
                    b["H1"][1] = st.text_input("Spiller 2", b["H1"][1], key=f"e2_{i}")
                with ec2:
                    st.markdown("**Hold 2**")
                    b["H2"][0] = st.text_input("Spiller 3", b["H2"][0], key=f"e3_{i}")
                    b["H2"][1] = st.text_input("Spiller 4", b["H2"][1], key=f"e4_{i}")
                if st.button("💾 Gem ændringer", key=f"s_{i}"):
                    # Validér at ingen spillernavn er tomt
                    all_names = b["H1"] + b["H2"]
                    if any(n.strip() == "" for n in all_names):
                        st.error("Spillernavne må ikke være tomme.")
                    else:
                        st.session_state.matches[i]["H1"] = list(b["H1"])
                        st.session_state.matches[i]["H2"] = list(b["H2"])
                        del st.session_state[f"buf_{i}"]
                        st.rerun()

    # Gem resultater
    if st.session_state.matches:
        st.divider()
        if st.button("✅ Gem resultater & gå til næste runde", type="primary", use_container_width=True):
            # Dobbelttjek: ingen duplikerede spillere på tværs af baner
            all_players_in_round = [p for m in st.session_state.matches for p in m["H1"] + m["H2"]]
            if len(all_players_in_round) != len(set(all_players_in_round)):
                st.error("Fejl: Samme spiller optræder på flere baner. Ret navnene og prøv igen.")
            else:
                register_match_data(st.session_state.matches)
                st.session_state.history.append({
                    "Runde": st.session_state.round_number,
                    "Kampe": [
                        f"{m['Bane']}: {' & '.join(m['H1'])} vs {' & '.join(m['H2'])} ({m['S1']}-{m['S2']})"
                        for m in st.session_state.matches
                    ],
                })
                st.session_state.round_number += 1
                st.session_state.matches = []
                save_to_supabase()
                st.rerun()

# ── TAB 2: STILLING ─────────────────────────────────────────────────────────
with t2:
    lb = st.session_state.get("leaderboard", {})
    if not lb:
        st.info("Ingen resultater endnu.")
    else:
        df = pd.DataFrame.from_dict(lb, orient="index")
        if not df.empty:
            df = df[["KS", "V", "U", "T", "Point", "PF"]].sort_values(
                ["Point", "V", "PF"], ascending=False
            )
            df.index.name = "Spiller"

            # Medaljer til top 3
            medals = {0: "🥇", 1: "🥈", 2: "🥉"}
            df.insert(0, "  ", [medals.get(i, "") for i in range(len(df))])

            st.dataframe(df, use_container_width=True)

            # Downloadknap
            csv = df.drop(columns=["  "]).to_csv().encode("utf-8")
            st.download_button(
                "⬇️ Download stilling som CSV",
                data=csv,
                file_name=f"stilling_{st.session_state.current_tid}.csv",
                mime="text/csv",
            )

# ── TAB 3: LOG ──────────────────────────────────────────────────────────────
with t3:
    if not st.session_state.history:
        st.info("Ingen runder gemt endnu.")
    else:
        for e in reversed(st.session_state.history):
            with st.expander(f"Runde {e['Runde']}"):
                for k in e["Kampe"]:
                    st.write(k)
