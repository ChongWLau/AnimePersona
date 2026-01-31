import streamlit as st
from google.genai import types
from utils import fetch_verified_character, clean_text

def show_judge_tab(supabase, genai_client):
    with st.form("main_form"):
        username = st.text_input("Enter a Username")
        st.write("Your Top 9 Anime (in no particular order):")
        cols = st.columns(3)
        titles = []
        for i in range(9):
            with cols[i % 3]:
                t = st.text_input("Anime Title", key=f"input_{i}", label_visibility="collapsed", placeholder=f"Anime {i+1}")
                titles.append(t)
        
        submit_btn = st.form_submit_button("Judge My Taste")

    if submit_btn and username and any(titles):
        with st.spinner("The Critic is sharpening their pen..."):
            valid_titles = [t for t in titles if t.strip()]
            
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

            Format response (No asterisks):
            SCORE: [number]
            COMMENTARY: [text]
            SNAPSHOT: [text]
            CHARACTER: [Name] ([Anime])
            ROAST: [text]
            """

            try:
                # Gemini Call
                response = genai_client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.85,  # Increased from default (usually 0.7) for more variety
                        top_p=0.95,        # Helps ensure the model considers a wider range of tokens
                        system_instruction="You are a snarky anime critic."
                    )
                )
                res = response.text

                # Parsing and Sanitizing
                score = clean_text(res.split("SCORE:")[1].split("COMMENTARY:")[0])
                commentary = clean_text(res.split("COMMENTARY:")[1].split("SNAPSHOT:")[0])
                snapshot = clean_text(res.split("SNAPSHOT:")[1].split("CHARACTER:")[0])
                # char_name = clean_text(res.split("CHARACTER:")[1].split("ROAST:")[0])
                roast = clean_text(res.split("ROAST:")[1])

                # Fetch Character Image
                # Inside your try block in views/judge.py
                res = response.text

                # ... usual splitting for Score, Commentary, etc ...
                char_info = clean_text(res.split("CHARACTER:")[1].split("ROAST:")[0])

                # Logic to separate "Goku (Dragon Ball Z)" -> "Goku" and "Dragon Ball Z"
                if "(" in char_info and char_info.endswith(")"):
                    char_name = char_info.split("(")[0].strip()
                    source_anime = char_info.split("(")[1].replace(")", "").strip()
                else:
                    # Fallback if AI forgets parentheses
                    char_name = char_info
                    source_anime = "" 

                # Now pass both to your verified fetcher
                jikan_data = fetch_verified_character(char_name, source_anime)

                # Database Insert
                db_entry = {
                    "username": username,
                    "anime_list": ", ".join(valid_titles),
                    "score": int(score) if score.isdigit() else 0,
                    "commentary": commentary,
                    "snapshot": snapshot,
                    "spirit_character": char_info,
                    "roast_text": roast,
                    "character_image_url": jikan_data['image']
                }
                supabase.table("anime_list").insert(db_entry).execute()
                
                # Immediate UI Feedback
                st.balloons()
                st.divider()
                res_col1, res_col2 = st.columns([1, 2])
                
                with res_col1:
                    st.image(jikan_data['image'], width="stretch")
                    st.caption(f"Spirit Character: {char_info}")
                    st.info(f"🔥 {roast}")
                
                with res_col2:
                    st.header(f"Taste Score: {score}/100")
                    st.markdown("### 📝 The Breakdown")
                    st.write(commentary)
                    
                    st.markdown("### 👤 Snapshot")
                    for point in snapshot.split("\n"):
                        p = clean_text(point).lstrip("-• 123456789. ")
                        if p:
                            st.markdown(f"* {p}")

            except Exception as e:
                st.error("The Judge's handwriting was too messy to read. Try again!")
                st.exception(e) # Helpful for debugging while developing
