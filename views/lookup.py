import streamlit as st
from utils import clean_text

def show_lookup_tab(supabase):
    st.header("🔍 Retrieve Your Judgment")
    search_user = st.text_input("Enter your username exactly as submitted:")
    search_btn = st.button("Fetch My Profile")

    if search_btn and search_user:
        # Fetch the most recent entry for this user
        res = supabase.table("anime_list")\
            .select("*")\
            .ilike("username", search_user)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()

        if res.data:
            user_data = res.data[0]
            st.success(f"Welcome back, {user_data['username']}!")
            st.divider()

            # --- SECTION 1: HEADER & ROAST (Mirroring judge.py) ---
            col_img, col_main = st.columns([1, 2])
            with col_img:
                st.image(user_data['character_image_url'], width='stretch')
                st.caption(f"Archetype: {user_data['spirit_character']}")
            with col_main:
                st.title(f"Score: {user_data['score']}/100")
                st.error(f"**🔥 THE ROAST:** {user_data['roast_text']}")
                st.subheader("Verdict")
                st.write(user_data.get('connoisseur_verdict', 'N/A'))

            # 2. EDITORIAL CRITIQUE: Two-Column Deep Dive
            st.divider()
            st.header("🧐 Editorial Critique")
            st.subheader("Thematic DNA")
            st.write(user_data.get('connoisseur_thematic', 'N/A'))
            st.subheader("Palette Diversity")
            st.write(user_data.get('connoisseur_palette', 'N/A'))

            # --- SECTION 2: PSYCHOLOGY DEEP DIVE ---
            st.divider()
            st.header("🧠 Clinical Analysis")
            st.subheader("Core Personality Archetype")
            st.write(user_data.get('core_archetype', 'No data found.'))

            st.subheader("Social Dynamics & Compatibility")
            st.write(user_data.get('social_compatibility', 'No data found.'))

            # --- SECTION 3: THE SHADOW SIDE (Flipped Layout) ---
            st.divider()
            col_shad_txt, col_shad_img = st.columns([2, 1])
            with col_shad_txt:
                st.header("🌑 The Shadow Side")
                st.write(user_data.get('shadow_analysis', 'No data found.'))
                st.caption(f"Manifestation: {user_data.get('shadow_character', 'Unknown')}")
            with col_shad_img:
                # Fallback to placeholder if no shadow image exists for older records
                shadow_img = user_data.get('shadow_image_url') or "https://placehold.co/400x600?text=Shadow+Unknown"
                st.image(shadow_img, width='stretch')

        else:
            st.warning("No judgment found. Did you spell it correctly?")