import streamlit as st
from google.genai import types
from utils import fetch_verified_character, clean_text


def get_ai_judgment(genai_client, username, valid_titles):
    """Handles the Gemini API call with the full prompt."""
    prompt = f"""
    User: {username}
    List: {', '.join(valid_titles)}

    Task:
    1. Provide a 'Taste Score' (0-100).
    2. COMMENTARY: [1 paragraph analysis]
    3. SNAPSHOT: [Bullet points]
    4. CHARACTER: Pick one character (and their anime) that represents them.
       Format: Full Character Name (Full Anime Title)
    5. ROAST: [1 sentence roast]

    STRICT FORMATTING RULE:
    - Return plain text ONLY.
    - DO NOT use markdown bolding (**), italics (_), or headers (###).
    - Use the exact labels below followed by a colon.
    - Start immediately with SCORE:.

    Format response:
    SCORE: [number]
    COMMENTARY: [text]
    SNAPSHOT: [text]
    CHARACTER: [Name] ([Anime])
    ROAST: [text]
    """

    response = genai_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.85,
            top_p=0.95,
            system_instruction="You are a snarky anime critic. You prioritize accuracy and wit."
        )
    )
    return response.text

def parse_and_fetch_image(res_text):
    """Parses raw AI text with safety fallbacks."""

    def safe_split(text, start_label, end_label):
        try:
            if start_label in text:
                content = text.split(start_label)[1]
                if end_label and end_label in content:
                    content = content.split(end_label)[0]
                return clean_text(content)
            return "N/A"
        except:
            return "N/A"

    score = safe_split(res_text, "SCORE:", "COMMENTARY:")
    commentary = safe_split(res_text, "COMMENTARY:", "SNAPSHOT:")
    snapshot = safe_split(res_text, "SNAPSHOT:", "CHARACTER:")
    char_info = safe_split(res_text, "CHARACTER:", "ROAST:")
    roast = safe_split(res_text, "ROAST:", None)

    # Logic to separate "Goku (Dragon Ball Z)"
    if "(" in char_info and char_info.endswith(")"):
        char_name = char_info.split("(")[0].strip()
        source_anime = char_info.split("(")[1].replace(")", "").strip()
    else:
        char_name, source_anime = char_info, ""

    jikan_data = fetch_verified_character(char_name, source_anime)

    return {
        "score": score, "commentary": commentary, "snapshot": snapshot,
        "char_info": char_info, "roast": roast, "jikan_data": jikan_data
    }

def save_to_db(supabase, username, valid_titles, data):
    """Handles the Supabase transaction."""
    db_entry = {
        "username": username,
        "anime_list": ", ".join(valid_titles),
        "score": int(data['score']) if data['score'].isdigit() else 0,
        "commentary": data['commentary'],
        "snapshot": data['snapshot'],
        "spirit_character": data['char_info'],
        "roast_text": data['roast'],
        "character_image_url": data['jikan_data']['image']
    }
    supabase.table("anime_list").insert(db_entry).execute()

def show_judge_tab(supabase, genai_client):
    with st.form("main_form"):
        username = st.text_input("Enter a Username")
        st.write("Your Top 9 Anime:")
        cols = st.columns(3)
        titles = [cols[i % 3].text_input(f"Anime {i+1}", key=f"input_{i}",
                  label_visibility="collapsed", placeholder=f"Anime {i+1}") for i in range(9)]
        
        submit_btn = st.form_submit_button("Judge My Taste")

    if submit_btn and username and any(titles):
        valid_titles = [t for t in titles if t.strip()]

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            # Step 1: Gemini
            status_text.text("⚖️ The Critic is watching your list...")
            ai_res = get_ai_judgment(genai_client, username, valid_titles)
            progress_bar.progress(33)

            # Step 2: Jikan
            status_text.text("🔍 Searching for your spirit character...")
            parsed_data = parse_and_fetch_image(ai_res)
            progress_bar.progress(66)

            # Step 3: Database
            status_text.text("💾 Recording your results...")
            save_to_db(supabase, username, valid_titles, parsed_data)
            progress_bar.progress(100)

            status_text.empty()
            progress_bar.empty()
            st.balloons()

            # --- DISPLAY RESULTS ---
            st.divider()
            res_col1, res_col2 = st.columns([1, 2])
            with res_col1:
                st.image(parsed_data['jikan_data']['image'], width='stretch')
                st.caption(f"Spirit: {parsed_data['char_info']}")
                st.info(f"🔥 {parsed_data['roast']}")

            with res_col2:
                st.header(f"Taste Score: {parsed_data['score']}/100")
                st.write(parsed_data['commentary'])
                st.markdown("### 👤 Snapshot")
                for point in parsed_data['snapshot'].split("\n"):
                    p = clean_text(point).lstrip("-• 123456789. ")
                    if p: st.markdown(f"* {p}")

        except Exception as e:
            st.error("The Judge's handwriting was too messy! Try again.")
            with st.expander("Debug Raw Response"):
                if 'ai_res' in locals(): st.code(ai_res)
                st.exception(e)
