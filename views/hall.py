import streamlit as st


def show_hall_of_fame(supabase):
    st.header("🏆 The Global Rankings")
    
    # Fetch from Supabase
    db_res = supabase.table("anime_list").select("*").order("score", desc=True).execute()
    data = db_res.data

    if data:
        # --- THE PODIUM (Top 3) ---
        st.subheader("🥇 Top Tier Taste")
        top_3 = data[:3]
        pod_cols = st.columns(len(top_3))
        pod_labels = ["🥇 1st", "🥈 2nd", "🥉 3rd"]

        for idx, entry in enumerate(top_3):
            with pod_cols[idx]:
                with st.container(border=True):
                    st.markdown(f"<h2 style='text-align: center;'>{pod_labels[idx]}</h2>", unsafe_allow_html=True)
                    st.markdown(f"<h3 style='text-align: center;'>{entry['username']}</h3>", unsafe_allow_html=True)
                    st.image(entry['character_image_url'], width="stretch")
                    st.caption(f"Spirit: {entry['spirit_character']}")
                    st.write(f"_{entry['roast_text']}_")
                    st.metric("Taste Score", f"{entry['score']}/100")
                    
                    # List of anime moved into the expander as bullet points
                    with st.expander("View Top 9"):
                        # Split the string back into a list
                        titles = entry['anime_list'].split(", ")
                        for title in titles:
                            st.markdown(f"* {title}")

        # --- THE REST ---
        if len(data) > 3:
            st.divider()
            st.subheader("📜 Other Candidates")
            other_cols = st.columns(4)
            for idx, entry in enumerate(data[3:]):
                with other_cols[idx % 4]:
                    with st.container(border=True):
                        st.markdown(f"### **{entry['username']}**")
                        st.image(entry['character_image_url'], width="stretch")
                        st.caption(f"Spirit: {entry['spirit_character']}")
                        st.info(entry['roast_text'])
                        st.metric("Taste Score", f"{entry['score']}/100")
                        
                        # List of anime moved into the expander as bullet points
                        with st.expander("View Top 9"):
                            # Split the string back into a list
                            titles = entry['anime_list'].split(", ")
                            for title in titles:
                                st.markdown(f"* {title}")
    else:
        st.write("No one has been judged yet.")
