import streamlit as st
from utils import clean_text

def show_lookup_tab(supabase):
    st.header("🔍 Retrieve Your Judgment")
    search_user = st.text_input("Enter your username exactly as submitted:")
    search_btn = st.button("Fetch My Profile")

    if search_btn and search_user:
        res = supabase.table("anime_list")\
            .select("*")\
            .ilike("username", search_user)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if res.data:
            user_data = res.data[0]
            st.success(f"Found you, {user_data['username']}!")
            st.divider()

            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(user_data['character_image_url'], width="stretch")
                st.caption(f"Spirit: {user_data['spirit_character']}")
                st.info(f"🔥 {user_data['roast_text']}")
            
            with col2:
                st.header(f"Score: {user_data['score']}/100")
                st.markdown("### 📝 The Judge's Take")
                st.write(user_data['commentary'])
                
                st.markdown("### 👤 Snapshot")
                for point in user_data['snapshot'].split("\n"):
                    p = clean_text(point).lstrip("-• 123456789. ")
                    if p:
                        st.markdown(f"* {p}")
        else:
            st.warning("No judgment found. Did you spell it correctly?")
