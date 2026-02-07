import streamlit as st
import time
from utils import fetch_verified_character, clean_text, strip_list_markers

# --- 1. INDIVIDUAL AGENT FUNCTIONS ---

def get_connoisseur_analysis(genai_client, username, titles):
    """Agent 1: The Anime Connoisseur - High-End Editorial Critique."""
    prompt = f"""
    Act as an elite, high-end anime connoisseur. 
    Analyze the curation style of {username} based on this list: {', '.join(titles)}.
    
    Structure your response EXACTLY with these labels:
    THEMATIC DNA: [3-4 punchy sentences about recurring philosophical patterns]
    PALETTE DIVERSITY: [3-4 sentences critiquing range, eras, and genre gaps]
    CRITIC VERDICT: [3-4 sentences summarizing their maturity as a viewer]
    SCORE: [A number from 0-100]
    """
    response = genai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    res = response.text
    
    def extract(label, next_label=None):
        if label not in res: return "N/A"
        try:
            part = res.split(label)[1]
            if next_label and next_label in part: part = part.split(next_label)[0]
            return clean_text(part)
        except: return "N/A"

    return {
        "thematic": extract("THEMATIC DNA:", "PALETTE DIVERSITY:"),
        "palette": extract("PALETTE DIVERSITY:", "CRITIC VERDICT:"),
        "verdict": extract("CRITIC VERDICT:", "SCORE:"),
        "score": "".join(filter(str.isdigit, extract("SCORE:"))) or "50"
    }

def get_psychological_profile(genai_client, connoisseur_verdict, titles, forbidden_list):
    """Agent 2: The Senior Psychologist - Clinical Personality Assessment."""
    # Ensure the AI avoids characters already in the Hall of Fame
    forbidden_str = ", ".join(forbidden_list[-50:]) if forbidden_list else "None"
    
    prompt = f"""
    Act as a senior clinical psychologist. 
    Review this Expert Critique: "{connoisseur_verdict}" and the user's list: {', '.join(titles)}.
    
    Task:
    1. CORE ARCHETYPE: 4-5 sentences clinical summary of their primary personality.
    2. THE SHADOW: 4-5 sentences on traits they mask or repress.
    3. SOCIAL DYNAMICS: 4-5 sentences on relationship patterns and compatibility.
    4. SPIRIT_CHARACTER: An anime character matching their Archetype. Format: Name (Anime)
    5. SHADOW_CHARACTER: An anime character matching their Shadow. Format: Name (Anime)

    DIVERSITY CONSTRAINT:
    You MUST NOT choose any of these characters: {forbidden_str}. 
    Additionally, avoid 'Light Yagami' to keep it creative.
    
    Format response EXACTLY as:
    CORE ARCHETYPE: [text]
    THE SHADOW: [text]
    SOCIAL DYNAMICS: [text]
    SPIRIT_CHARACTER: [text]
    SHADOW_CHARACTER: [text]
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
        "core": extract("CORE ARCHETYPE:", "THE SHADOW:"),
        "shadow_text": extract("THE SHADOW:", "SOCIAL DYNAMICS:"),
        "social": extract("SOCIAL DYNAMICS:", "SPIRIT_CHARACTER:"),
        "spirit_name": extract("SPIRIT_CHARACTER:", "SHADOW_CHARACTER:"),
        "shadow_name": extract("SHADOW_CHARACTER:")
    }

def get_snarky_roast(genai_client, verdict, core_psych, titles):
    """Agent 3: The Snarky Critic - Brutal Personality-Based Insult."""
    prompt = f"""
    Based on this Critique: {verdict} and Psychological Profile: {core_psych},
    write a brutal, condescending 1-sentence roast for this user who likes {titles}.
    
    Format response EXACTLY as:
    ROAST: [Your insult here]
    """
    response = genai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
    res = response.text
    return clean_text(res.split("ROAST:")[1]) if "ROAST:" in res else "Your taste is a cry for help."

# --- 2. DATABASE SAVING ---

def save_complete_profile(supabase, username, titles, connoisseur, psych, roast, spirit_img, shadow_img):
    """Saves all agent data using upsert to avoid duplicate usernames."""
    db_entry = {
        "username": username,
        "anime_list": ", ".join(titles),
        "score": int(connoisseur['score']),
        "connoisseur_thematic": connoisseur['thematic'],
        "connoisseur_palette": connoisseur['palette'],
        "connoisseur_verdict": connoisseur['verdict'],
        "core_archetype": psych['core'],
        "shadow_analysis": psych['shadow_text'],
        "social_compatibility": psych['social'],
        "spirit_character": psych['spirit_name'],
        "shadow_character": psych['shadow_name'],
        "roast_text": roast,
        "character_image_url": spirit_img,
        "shadow_image_url": shadow_img
    }
    # .upsert() handles both new insertions and regenerations
    return supabase.table("anime_list").upsert(db_entry, on_conflict="username").execute()

# --- 3. UI AND ORCHESTRATION ---

def show_judge_tab(supabase, genai_client):
    st.header("⚖️ The Great Anime Judgment")
    
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
        titles = [cols[i%3].text_input(f"Anime {i+1}", key=f"input_{i}", label_visibility="collapsed") for i in range(9)]
        submit_btn = st.form_submit_button("Start Multi-Agent Analysis")

    if submit_btn and username and any(titles):
        valid_titles = [t for t in titles if t.strip()]
        results_area = st.empty()
        
        with st.status("🚀 Initializing Sequential Agent Network...", expanded=True) as status:
            try:
                # 0. Sync Character Diversity (Deduplication)
                status.write("📊 Querying database for character diversity...")
                res = supabase.table("anime_list").select("spirit_character, shadow_character").execute()
                forbidden = list(set([r[k] for r in res.data for k in r if r[k]]))

                # 1. Sequential Execution (Multi-Call)
                status.write("🧐 Agent 1: The Connoisseur is critiquing your thematic DNA...")
                connoisseur = get_connoisseur_analysis(genai_client, username, valid_titles)
                
                status.write("🧠 Agent 2: The Psychologist is unmasking your shadow self...")
                psych = get_psychological_profile(genai_client, connoisseur['verdict'], valid_titles, forbidden)
                
                status.write("🔥 Agent 3: The Critic is drafting your roast...")
                roast = get_snarky_roast(genai_client, connoisseur['verdict'], psych['core'], valid_titles)
                
                # 2. Surgical Image Retrieval
                status.write("🔍 Jikan API: Mapping dualities...")
                # Fixed parse_char function
                def parse_char(s): 
                    if "(" in s:
                        name = s.split("(")[0].strip()
                        anime = s.split("(")[1].replace(")", "").strip()
                        return name, anime
                    return s.strip(), "" # Returns exactly two values
                
                sn, sa = parse_char(psych['spirit_name'])
                spirit_img = fetch_verified_character(sn, sa)['image']
                
                shn, sha = parse_char(psych['shadow_name'])
                shadow_img = fetch_verified_character(shn, sha)['image']
                
                # 3. Save to Supabase
                status.write("💾 Archiving psychological profile...")
                save_complete_profile(supabase, username, valid_titles, connoisseur, psych, roast, spirit_img, shadow_img)
                
                status.update(label="✅ Comprehensive Report Ready!", state="complete", expanded=False)

                # --- 4. RENDER UI ---
                st.balloons()
                with results_area.container():
                    st.divider()
                    
                    # Row 1: The Overview
                    col_img, col_main = st.columns([1, 2])
                    with col_img:
                        st.image(spirit_img, width='stretch')
                        st.caption(f"Spirit Archetype: {psych['spirit_name']}")
                    with col_main:
                        st.title(f"Taste Score: {connoisseur['score']}/100")
                        st.error(f"**🔥 THE CRITIC'S ROAST:**\n{roast}")
                        st.subheader("The Expert's Verdict")
                        st.write(connoisseur['verdict'])

                    # Row 2: Editorial Critique Grid
                    st.divider()
                    st.header("🧐 Editorial Critique")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Thematic DNA")
                        st.write(connoisseur['thematic'])
                    with c2:
                        st.subheader("Palette Diversity")
                        st.write(connoisseur['palette'])

                    # Row 3: Psychological Deep Dive
                    st.divider()
                    st.header("🧠 Clinical Analysis")
                    st.subheader("Core Personality Archetype")
                    st.write(psych['core'])
                    st.subheader("Social Dynamics & Compatibility")
                    st.write(psych['social'])
                    
                    # Row 4: Shadow Reveal
                    st.divider()
                    col_shad_txt, col_shad_img = st.columns([2, 1])
                    with col_shad_txt:
                        st.header("🌑 The Shadow Side")
                        st.write(psych['shadow_text'])
                        st.caption(f"Manifestation: {psych['shadow_name']}")
                    with col_shad_img:
                        st.image(shadow_img, width='stretch')

            except Exception as e:
                status.update(label="❌ Agent Breakdown", state="error")
                st.exception(e)