# --- INDSÆT DENNE OPPDATEREDE T1-FANE ---
with t1:
    tournament_finished = st.session_state.round_number > (st.session_state.max_rounds + 1)
    
    # Vis finalestilling hvis turneringen er slut
    if tournament_finished:
        st.balloons()
        st.success("🏆 TURNERING AFSLUTTET!")
        st.markdown("### Den endelige stilling:")
        if st.session_state.leaderboard:
            df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index')
            st.dataframe(df[["KS", "V", "U", "T", "Point", "PF"]].sort_values(["Point", "V"], ascending=False), use_container_width=True)
        if st.button("🔄 Nulstil alt til ny turnering"):
            st.session_state.clear()
            st.rerun()
        st.stop()

    # Advarsel hvis vi er i finalen
    if st.session_state.round_number == (st.session_state.max_rounds + 1):
        st.warning("🔥 FINALE-RUNDE: Spillere parres efter 1+4 vs 2+3!")
    
    # Generering
    if not st.session_state.matches:
        if st.button("🎲 Generer Næste Runde"): 
            st.session_state.matches = generate_matches()
            save_to_supabase()
            st.rerun()
    
    # Input feltet skal kun vises hvis der er kampe
    for i, m in enumerate(st.session_state.matches):
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2,1,2]); col_a.markdown(f"**Hold 1:** {', '.join(m['H1'])}"); col_b.write("vs"); col_c.markdown(f"**Hold 2:** {', '.join(m['H2'])}")
            
            # Edit buffer
            if st.button("✏️", key=f"edit_{i}"): st.session_state[f"buf_{i}"] = {"H1": list(m['H1']), "H2": list(m['H2'])}
            if f"buf_{i}" in st.session_state:
                b = st.session_state[f"buf_{i}"]
                c1, c2 = st.columns(2); b['H1'][0] = c1.text_input("H1S1", b['H1'][0]); b['H1'][1] = c1.text_input("H1S2", b['H1'][1]); b['H2'][0] = c2.text_input("H2S1", b['H2'][0]); b['H2'][1] = c2.text_input("H2S2", b['H2'][1])
                if st.button("Gem", key=f"s_{i}"): st.session_state.matches[i]['H1'], st.session_state.matches[i]['H2'] = b['H1'], b['H2']; del st.session_state[f"buf_{i}"]; st.rerun()
            
            s1 = st.number_input(f"Score for {' & '.join(m['H1'])}", 0, 32, value=int(m['S1']), key=f"s1_{i}")
            st.session_state.matches[i]['S1'], st.session_state.matches[i]['S2'] = s1, 32-s1
            
    if st.session_state.matches and st.button("✅ Gem Resultat & Log"):
        register_match_data(st.session_state.matches)
        st.session_state.history.append({"Runde": st.session_state.round_number, "Kampe": [f"{m['Bane']}: {'&'.join(m['H1'])} vs {'&'.join(m['H2'])} ({m['S1']}-{m['S2']})" for m in st.session_state.matches]})
        st.session_state.round_number += 1 
        st.session_state.matches = []
        save_to_supabase()
        st.rerun()
