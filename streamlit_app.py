# --- OPDATERET GENERERINGS-LOGIK (Erstat blokken i tab1) ---

if not st.session_state.matches:
    if st.button("🎲 Generer Næste Kampe"):
        # Hent rangeret liste til Mexicano/Finale
        df = pd.DataFrame.from_dict(st.session_state.leaderboard, orient='index').sort_values(["Point", "PF", "V"], ascending=False)
        ranked = df.index.tolist()
        
        # Lav en kopi af alle spillere til Americano (tilfældig)
        pool = st.session_state.players.copy()
        random.shuffle(pool)
        
        new_m = []
        num_courts = len(st.session_state.players) // 4
        
        for i in range(num_courts):
            b_navn = st.session_state.court_names[i] if i < len(st.session_state.court_names) else f"Bane {i+1}"
            if i == 0 and g_format == "Mexicano": b_navn = f"🏆 {b_navn}"
            
            if is_finale or g_format == "Mexicano":
                # Tag de næste 4 fra den rangerede liste (Bane 1 = Top 4, Bane 2 = 5-8 osv.)
                p = ranked[i*4 : (i*4)+4]
                # Padel-standard: 1&4 vs 2&3 for jævne kampe
                h1, h2 = [p[0], p[3]], [p[1], p[2]]
            else:
                # Americano: Tag de næste 4 fra den rystede pose (Pool)
                # Dette sikrer at ingen optræder to gange
                p = [pool.pop() for _ in range(4)]
                h1, h2 = [p[0], p[1]], [p[2], p[3]]
                
            new_m.append({"Bane": b_navn, "H1": h1, "H2": h2, "S1": 16, "S2": 16})
        
        st.session_state.matches = new_m
        save_to_supabase()
        st.rerun()
