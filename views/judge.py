import streamlit as st
from utils import fetch_verified_character, clean_text, strip_list_markers

# --- 1. CORE LOGIC FUNCTIONS ---

def get_connoisseur_analysis(genai_client, username, titles):
    """Step 1: The Editorial Critic (Concise but Punchy)."""
    prompt = f"""
    Act as an elite, high-end anime connoisseur. 
    Analyze the curation style of {username} based on: {', '.join(titles)}.
    
    Structure your response EXACTLY with these labels:
    THEMATIC DNA: [3-4 punchy sentences]
    PALETTE DIVERSITY: [3-4 punchy sentences]
    CRITIC VERDICT: [3-4 punchy sentences]
    SCORE: [number]
    """
    response = genai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    res = response.text
    
    def extract(label, next_label=None):
        if label not in res: return "Data unavailable"
        try:
            part = res.split(label)[1]
            if next_label and next_label in part: part = part.split(next_label)[0]
            return clean_text(part)
        except: return "Data unavailable"

    return {
        "thematic": extract("THEMATIC DNA:", "PALETTE DIVERSITY:"),
        "palette": extract("PALETTE DIVERSITY:", "CRITIC VERDICT:"),
        "verdict": extract("CRITIC VERDICT:", "SCORE:"),
        "score": "".join(filter(str.isdigit, extract("SCORE:"))) or "50"
    }

def get_psychological_profile(genai_client, analysis_dict, titles):
    """Step 2: Deep Psychological Profiling + Character Selection."""
    # We feed the 'verdict' from the connoisseur as the primary context
    context = analysis_dict['verdict']
    
    prompt = f"""
    Act as a senior clinical psychologist. 
    Expert Critique: {context}
    Original Anime List: {', '.join(titles)}
    
    Task:
    1. CORE ARCHETYPE: 3-sentence clinical summary of their primary personality.
    2. THE SHADOW: Analysis of traits they mask or repress (their "darker" side).
    3. SOCIAL DYNAMICS: How they relate to others and the compatibility types they vibe with.
    4. SPIRIT_CHARACTER: Pick ANY anime character (does not have to be from their list) that perfectly matches their Archetype. 
       Format: Name (Anime)
    5. SHADOW_CHARACTER: Pick ANY anime character (does not have to be from their list) that perfectly matches their 'Shadow' side. 
       Format: Name (Anime)

    CRITICAL: Do NOT use numbers or bullet points.
    Format EXACTLY as:
    CORE ARCHETYPE: [text]
    THE SHADOW: [text]
    SOCIAL DYNAMICS: [text]
    SPIRIT_CHARACTER: [text]
    SHADOW_CHARACTER: [text]
    """
    response = genai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    res = response.text

    def extract(label, next_label=None):
        if label not in res: return "Psychological data missing"
        try:
            part = res.split(label)[1]
            if next_label and next_label in part: part = part.split(next_label)[0]
            return strip_list_markers(clean_text(part))
        except: return "Psychological data missing"

    return {
        "core": extract("CORE ARCHETYPE:", "THE SHADOW:"),
        "shadow_text": extract("THE SHADOW:", "SOCIAL DYNAMICS:"),
        "social": extract("SOCIAL DYNAMICS:", "SPIRIT_CHARACTER:"),
        "spirit_name": extract("SPIRIT_CHARACTER:", "SHADOW_CHARACTER:"),
        "shadow_name": extract("SHADOW_CHARACTER:")
    }

def get_snarky_roast(genai_client, verdict, core_psych, titles):
    prompt = f"""
    Based on this Critique: {verdict} and Psych: {core_psych},
    write a brutal 1-sentence roast for this user who likes {titles}.
    
    Format response EXACTLY as:
    ROAST: [Your insult here]
    """
    response = genai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    res = response.text
    # Explicitly looking for the ROAST: label to prevent parsing errors
    if "ROAST:" in res:
        return clean_text(res.split("ROAST:")[1])
    return "Your taste is so mid it actually drained my battery."

def save_complete_profile(supabase, username, titles, exp_data, psych_data, roast, spirit_img, shadow_img):
    """Step 4: Comprehensive Database Transaction."""
    db_entry = {
        "username": username,
        "anime_list": ", ".join(titles),
        "score": int(exp_data['score']),
        "connoisseur_thematic": exp_data['thematic'],
        "connoisseur_palette": exp_data['palette'],
        "connoisseur_verdict": exp_data['verdict'],
        "core_archetype": psych_data['core'],
        "shadow_analysis": psych_data['shadow_text'],
        "social_compatibility": psych_data['social'],
        "spirit_character": psych_data['spirit_name'],
        "shadow_character": psych_data['shadow_name'],
        "roast_text": roast,
        "character_image_url": spirit_img,
        "shadow_image_url": shadow_img
    }
    return supabase.table("anime_list").insert(db_entry).execute()

# --- 2. MAIN VIEW FUNCTION ---

def show_judge_tab(supabase, genai_client):
    # --- Developer Test Mode Logic ---
    test_mode = st.sidebar.toggle("🛠️ Developer Test Mode")
    test_data = {
        "user": "CWLau2",
        "anime": ["Steins;Gate", "Yakitate Japan", "Hajime no Ippo", "Code Geass", "Naruto", 
                  "Yugioh", "Jobless Reincarnation", "GTO", "Orb"]
    }

    if test_mode:
        st.session_state["username_input"] = test_data["user"]
        for i in range(9):
            st.session_state[f"input_{i}"] = test_data["anime"][i]
    else:
        if "username_input" in st.session_state and st.session_state["username_input"] == test_data["user"]:
            st.session_state["username_input"] = ""
            for i in range(9):
                st.session_state[f"input_{i}"] = ""

    with st.form("main_form"):
        username = st.text_input("Enter a Username", key="username_input")
        st.write("Your Top 9 Anime:")
        cols = st.columns(3)
        titles = []
        
        for i in range(9):
            with cols[i % 3]:
                t = st.text_input(f"Anime {i+1}", key=f"input_{i}", label_visibility="collapsed", placeholder=f"Anime {i+1}")
                titles.append(t)
        
        submit_btn = st.form_submit_button("Start Multi-Agent Analysis")

    # --- Execution Logic ---
    if submit_btn and username and any(titles):
        valid_titles = [t for t in titles if t.strip()]
        results_area = st.empty()
        
        with st.status("🚀 Synchronizing AI Agent Network...", expanded=True) as status:
            try:
                # PIPELINE
                status.write("🧐 Agent 1: Critic performing thematic breakdown...")
                exp_data = get_connoisseur_analysis(genai_client, username, valid_titles)
                
                status.write("🧠 Agent 2: Psychologist identifying the shadow self...")
                # We no longer pass or check a forbidden list
                psych = get_psychological_profile(genai_client, exp_data, valid_titles)
                
                status.write("🔥 Agent 3: Critic drafting the roast...")
                roast = get_snarky_roast(genai_client, exp_data['verdict'], psych['core'], valid_titles)
                
                status.write("🔍 Jikan API: Retrieving duality images...")
                # Spirit Fetch
                spirit_n = psych['spirit_name'].split("(")[0].strip() if "(" in psych['spirit_name'] else psych['spirit_name']
                spirit_a = psych['spirit_name'].split("(")[1].replace(")","") if "(" in psych['spirit_name'] else ""
                spirit_img = fetch_verified_character(spirit_n, spirit_a)['image']
                
                # Shadow Fetch
                shadow_n = psych['shadow_name'].split("(")[0].strip() if "(" in psych['shadow_name'] else psych['shadow_name']
                shadow_a = psych['shadow_name'].split("(")[1].replace(")","") if "(" in psych['shadow_name'] else ""
                shadow_img = fetch_verified_character(shadow_n, shadow_a)['image']
                
                status.write("💾 Finalizing Encrypted Report...")
                save_complete_profile(supabase, username, valid_titles, exp_data, psych, roast, spirit_img, shadow_img)
                
                status.update(label="✅ Comprehensive Report Ready!", state="complete", expanded=False)

                # --- 3. RENDER RESULTS ---
                st.balloons()
                with results_area.container():
                    st.divider()
                    
                    # SECTION 1: HEADER & ROAST
                    col_img, col_main = st.columns([1, 2])
                    with col_img:
                        st.image(spirit_img, width='stretch')
                        st.caption(f"Spirit Archetype: {psych['spirit_name']}")
                    with col_main:
                        st.title(f"Taste Score: {exp_data['score']}/100")
                        st.subheader("Verdict")
                        st.write(exp_data['verdict'])
                        st.error(f"**🔥 THE CRITIC'S ROAST:**\n{roast}")

                    # 2. EDITORIAL CRITIQUE: Two-Column Deep Dive
                    st.divider()
                    st.header("🧐 Editorial Critique")
                    st.subheader("Thematic DNA")
                    st.write(exp_data['thematic'])
                    st.subheader("Palette Diversity")
                    st.write(exp_data['palette'])

                    # 3. CLINICAL ANALYSIS: (Same as before, follows below)
                    st.divider()
                    st.header("🧠 Clinical Analysis")
                    st.subheader("Core Personality Archetype")
                    st.write(psych['core'])
                    st.subheader("Social Dynamics & Compatibility")
                    st.write(psych['social'])
                    
                    # SECTION 3: THE SHADOW
                    st.divider()
                    col_shad_txt, col_shad_img = st.columns([2, 1])
                    with col_shad_txt:
                        st.header("🌑 The Shadow Side")
                        st.write(psych['shadow_text'])
                        st.caption(f"Manifestation: {psych['shadow_name']}")
                    with col_shad_img:
                        st.image(shadow_img, width='stretch')

            except Exception as e:
                status.update(label="❌ Agent Error", state="error")
                st.exception(e)
