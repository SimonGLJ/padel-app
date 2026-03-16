import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import random

# ... (Samme konfiguration og hjælpemotorer som v3.9) ...

# --- OPDATERET LOGIK: MERE DETALJERET LOG ---
def add_to_history(round_num, matches):
    history_entry = {"Runde": round_num, "Kampe": []}
    for m in matches:
        history_entry["Kampe"].append({
            "Bane": m["Bane"],
            "Hold1": " & ".join(m["H1"]),
            "Hold2": " & ".join(m["H2"]),
            "Score": f"{m['S1']}-{m['S2']}"
        })
    st.session_state.history.append(history_entry)

# --- HOVEDSKÆRM ---
t1, t2, t3 = st.tabs(["🎾 Kampe", "📊 Stilling", "📜 Log & Redigering"])

with t1:
    # ... (Generering af kampe ...)
    if st.session_state.matches:
        for i, m in enumerate(st.session_state.matches):
            with st.container(border=True):
                # MANUEL REDIGERING
                col_title, col_edit = st.columns([4, 1])
                col_title.write(f"### {m['Bane']}")
                if col_edit.button("✏️", key=f"edit_{i}"):
                    st.session_state[f"editing_{i}"] = True
                
                if st.session_state.get(f"editing_{i}"):
                    m['H1'][0] = st.text_input("Hold 1, Spiller 1", m['H1'][0])
                    m['H1'][1] = st.text_input("Hold 1, Spiller 2", m['H1'][1])
                    m['H2'][0] = st.text_input("Hold 2, Spiller 1", m['H2'][0])
                    m['H2'][1] = st.text_input("Hold 2, Spiller 2", m['H2'][1])
                    if st.button("Gem ændring", key=f"save_{i}"):
                        st.session_state[f"editing_{i}"] = False
                        st.rerun()
                
                # Input af score
                s1 = st.number_input(f"Score: {' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
                st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32 - s1

            if st.button("✅ Gem Resultat & Log"):
                add_to_history(st.session_state.round_number, st.session_state.matches)
                # ... (Point-opdatering ...)
                save_to_supabase(); st.rerun()

with t3:
    st.subheader("📜 Kamp Log")
    for entry in reversed(st.session_state.history):
        with st.expander(f"Runde {entry['Runde']}"):
            for k in entry["Kampe"]:
                st.write(f"**{k['Bane']}**: {k['Hold1']} vs {k['Hold2']} | **Resultat**: {k['Score']}")
