import streamlit as st
from utils import fetch_verified_character, clean_text, strip_list_markers

# --- 1. CORE LOGIC FUNCTIONS ---

def get_complete_analysis(genai_client, username, titles):
    """
    Combines Connoisseur, Psychologist, and Critic into ONE API call.
    This prevents '429 Resource Exhausted' errors and ensures a cohesive report.
    """
    prompt = f"""
    Act as a Consortium of three distinct experts analyzing the anime taste of {username}
    based on this list: {', '.join(titles)}.

    1. THE ANIME CONNOISSEUR: Provide a high-impact editorial critique.
       - THEMATIC DNA: recurring themes/philosophical patterns (3-4 sentences).
       - PALETTE DIVERSITY: critique of range, eras, and genre gaps (3-4 sentences).
       - CRITIC VERDICT: summary of their maturity as a viewer (3-4 sentences).
       - SCORE: A number from 0-100.

    2. THE CLINICAL PSYCHOLOGIST: Provide a deep-dive personality assessment.
       - CORE ARCHETYPE: clinical summary of their primary personality (4-5 sentences).
       - THE SHADOW: traits they mask or repress (4-5 sentences).
       - SOCIAL DYNAMICS: relationship patterns and compatibility (4-5 sentences).
       - SPIRIT_CHARACTER: An anime character matching their Archetype. Format: Name (Anime)
       - SHADOW_CHARACTER: An anime character matching their Shadow. Format: Name (Anime)

    3. THE SNARKY CRITIC:
       - ROAST: A brutal 1-sentence insult based on their psychological flaws.

    CRITICAL CONSTRAINTS:
    - DO NOT select Light Yagami (Death Note) as the Shadow Character.
    - DO NOT use numbering or bullet points.

    Format response EXACTLY with these labels:
    THEMATIC DNA: [text]
    PALETTE DIVERSITY: [text]
    CRITIC VERDICT: [text]
    SCORE: [number]
    CORE ARCHETYPE: [text]
    THE SHADOW: [text]
    SOCIAL DYNAMICS: [text]
    SPIRIT_CHARACTER: [text]
    SHADOW_CHARACTER: [text]
    ROAST: [text]
    """

    response = genai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    res = response.text

    def extract(label, next_label=None):
        if label not in res: return "N/A"
        try:
            part = res.split(label)[1]
            if next_label and next_label in part: part = part.split(next_label)[0]
            return strip_list_markers(clean_text(part))
        except: return "N/A"

    return {
        "thematic": extract("THEMATIC DNA:", "PALETTE DIVERSITY:"),
        "palette": extract("PALETTE DIVERSITY:", "CRITIC VERDICT:"),
        "verdict": extract("CRITIC VERDICT:", "SCORE:"),
        "score": "".join(filter(str.isdigit, extract("SCORE:", "CORE ARCHETYPE:"))) or "50",
        "core": extract("CORE ARCHETYPE:", "THE SHADOW:"),
        "shadow_text": extract("THE SHADOW:", "SOCIAL DYNAMICS:"),
        "social": extract("SOCIAL DYNAMICS:", "SPIRIT_CHARACTER:"),
        "spirit_name": extract("SPIRIT_CHARACTER:", "SHADOW_CHARACTER:"),
        "shadow_name": extract("SHADOW_CHARACTER:", "ROAST:"),
        "roast": extract("ROAST:")
    }

def save_complete_profile(supabase, username, titles, data, spirit_img, shadow_img):
    """Saves the unified data dictionary to Supabase."""
    db_entry = {
        "username": username,
        "anime_list": ", ".join(titles),
        "score": int(data['score']),
        "connoisseur_thematic": data['thematic'],
        "connoisseur_palette": data['palette'],
        "connoisseur_verdict": data['verdict'],
        "core_archetype": data['core'],
        "shadow_analysis": data['shadow_text'],
        "social_compatibility": data['social'],
        "spirit_character": data['spirit_name'],
        "shadow_character": data['shadow_name'],
        "roast_text": data['roast'],
        "character_image_url": spirit_img,
        "shadow_image_url": shadow_img
    }
    return supabase.table("anime_list").insert(db_entry).execute()

# --- 2. MAIN VIEW FUNCTION ---

def show_judge_tab(supabase, genai_client):
    # 1. Secret URL Check (keeps the dev tools hidden)
    is_dev_url = st.query_params.get("dev") == "true"
    test_mode = False
    if is_dev_url:
        test_mode = st.sidebar.toggle("🛠️ Developer Test Mode")

    # 2. Define Multiple Test Profiles
    all_test_profiles = {
        "CWLau2": [
            "Steins;Gate", "Yakitate Japan", "Hajime no Ippo", "Code Geass", "Naruto",
            "Yugioh", "Jobless Reincarnation", "GTO", "Orb"
        ],
        "LD": [
            "Attack on titan", "Death note", "Hajime no Ippo", "Code Geass", "Fate stay night UBW",
            "Toradora", "Utawarerumono", "Clannad S1", "Naruto"
        ],
        "LMN": [
            "Clannad", "GTO", "Code geass", "Fullmetal Alchemist Brotherhood", "Death note",
            "Eureka seven", "D. Grayman", "Elfen Lied", "5cm per second"
        ],
        "GLL": [
            "Grander musashi", "Haikyu", "Naruto", "Chuuka ichiban", "Initial D",
            "GTO", "Ouran high school host club", "Hajime no Ippo", "Kyo kara ore wa"
        ],
    }

    # 3. Handle Profile Selection and Session State Injection
    if test_mode:
        selected_name = st.sidebar.selectbox("Select Test Profile", options=list(all_test_profiles.keys()))

        # Inject the selected user
        st.session_state["username_input"] = selected_name

        # Inject the selected anime list
        anime_list = all_test_profiles[selected_name]
        for i in range(9):
            # Ensure we don't index out of range if a test list is short
            val = anime_list[i] if i < len(anime_list) else ""
            st.session_state[f"input_{i}"] = val

    with st.form("main_form"):
        username = st.text_input("Enter a Username", key="username_input")
        cols = st.columns(3)
        titles = [cols[i%3].text_input(f"Anime {i+1}", key=f"input_{i}", label_visibility="collapsed", placeholder=f"Anime {i+1}") for i in range(9)]
        submit_btn = st.form_submit_button("Generate Complete Persona Report")

    if submit_btn and username and any(titles):
        valid_titles = [t for t in titles if t.strip()]
        results_area = st.empty()

        with st.status("🚀 Consulting the Expert Consortium...", expanded=True) as status:
            try:
                # 1. THE SINGLE API CALL
                status.write("🧠 Unified Agent Network analyzing taste and psyche...")
                full_data = get_complete_analysis(genai_client, username, valid_titles)

                # 2. IMAGE RETRIEVAL
                status.write("🔍 Jikan API: Mapping dualities...")

                # Spirit Archetype Fetch
                sn = full_data['spirit_name'].split("(")[0].strip() if "(" in full_data['spirit_name'] else full_data['spirit_name']
                sa = full_data['spirit_name'].split("(")[1].replace(")","") if "(" in full_data['spirit_name'] else ""
                spirit_img = fetch_verified_character(sn, sa)['image']

                # Shadow Side Fetch
                shn = full_data['shadow_name'].split("(")[0].strip() if "(" in full_data['shadow_name'] else full_data['shadow_name']
                sha = full_data['shadow_name'].split("(")[1].replace(")","") if "(" in full_data['shadow_name'] else ""
                shadow_img = fetch_verified_character(shn, sha)['image']

                # 3. DB SAVE
                status.write("💾 Archiving psychological profile...")
                save_complete_profile(supabase, username, valid_titles, full_data, spirit_img, shadow_img)

                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

                # --- 3. RENDER RESULTS (UI Makeover) ---
                st.balloons()
                with results_area.container():
                    st.divider()

                    # Row 1: The Overview
                    col_img, col_main = st.columns([1, 2])
                    with col_img:
                        st.image(spirit_img, width='stretch')
                        st.caption(f"Spirit Archetype: {full_data['spirit_name']}")
                    with col_main:
                        st.title(f"Taste Score: {full_data['score']}/100")
                        st.error(f"**🔥 THE CRITIC'S ROAST:**\n{full_data['roast']}")
                        st.subheader("The Expert's Verdict")
                        st.write(full_data['verdict'])

                    # Row 2: Editorial Critique Grid
                    st.divider()
                    st.header("🧐 Editorial Critique")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Thematic DNA")
                        st.write(full_data['thematic'])
                    with c2:
                        st.subheader("Palette Diversity")
                        st.write(full_data['palette'])

                    # Row 3: Psychological Deep Dive
                    st.divider()
                    st.header("🧠 Clinical Analysis")
                    st.subheader("Core Personality Archetype")
                    st.write(full_data['core'])
                    st.subheader("Social Dynamics & Compatibility")
                    st.write(full_data['social'])

                    # Row 4: Shadow Side
                    st.divider()
                    col_shad_txt, col_shad_img = st.columns([2, 1])
                    with col_shad_txt:
                        st.header("🌑 The Shadow Side")
                        st.write(full_data['shadow_text'])
                        st.caption(f"Shadow Manifestation: {full_data['shadow_name']}")
                    with col_shad_img:
                        st.image(shadow_img, width='stretch')

            except Exception as e:
                status.update(label="❌ Agent Breakdown", state="error")
                st.exception(e)