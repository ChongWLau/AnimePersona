import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client, Client
from jikanpy import Jikan
import time
import requests
import matplotlib.pyplot as plt
import numpy as np

# --- 1. INITIALIZATION ---
GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

client = genai.Client(api_key=GEMINI_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
jikan = Jikan()

# Streamlit Page Config
st.set_page_config(page_title="Anime Persona Judge", page_icon="🎴", layout="wide")

# CSS for a polished look
st.markdown("""
    <style>
    .stImage img { border-radius: 12px; border: 3px solid #1e1e1e; transition: 0.3s; }
    .stImage img:hover { transform: scale(1.02); }
    [data-testid="stMetricValue"] { color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎴 Anime Persona")

tab1, tab2 = st.tabs(["🔥 Get Judged", "🏆 Hall of Fame"])

# --- HELPER FUNCTIONS ---
def fetch_character_data(name):
    """Searches Jikan API v4 with deep-nested safe access for images."""
    try:
        api_url = f"https://api.jikan.moe/v4/characters?q={name}&limit=1"
        time.sleep(0.5) # Rate limit protection
        
        response = requests.get(api_url)
        if response.status_code == 200:
            results = response.json().get('data', [])
            if results:
                char = results[0]
                images = char.get('images', {}).get('jpg', {})
                img_url = images.get('large_image_url') or images.get('image_url')
                
                return {
                    "image": img_url if img_url else "https://placehold.co/400x600?text=No+Image+Found",
                    "url": char.get('url', '#')
                }
    except Exception as e:
        st.error(f"Jikan Error: {e}")
        
    return {
        "image": "https://placehold.co/400x600?text=Spirit+Not+Found", 
        "url": "#"
    }

# def create_radar_chart(stats, username):
#     labels = np.array(['Wit', 'Depth', 'Grit', 'Whimsy', 'Realism', 'Chaos'])
#     num_vars = len(labels)
    
#     # Split angles for 6 points
#     angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
#     # Close the loop
#     stats = stats + stats[:1]
#     angles = angles + angles[:1]

#     fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(polar=True))
#     ax.fill(angles, stats, color='#FF4B4B', alpha=0.25)
#     ax.plot(angles, stats, color='#FF4B4B', linewidth=2)

#     # Styling the chart for a dark/modern look
#     ax.set_thetagrids(np.degrees(angles[:-1]), labels)
#     for label in ax.get_xticklabels():
#         label.set_fontsize(13)
#         label.set_fontweight('bold')
#         label.set_color('white')

#     ax.set_ylim(0, 100)
#     ax.set_yticklabels([])     # Remove y-axis numbers

#     ax.spines['polar'].set_visible(False)
    
#     # Transparent background for Streamlit
#     fig.patch.set_alpha(0.0)
#     ax.set_facecolor('#0E1117')
#     return fig

# --- TAB 1: SUBMISSION ---
with tab1:
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
            
            # --- 1. UPDATED PROMPT (Strict on Formatting) ---
            prompt = f"""
            User: {username}
            List: {', '.join(valid_titles)}

            Task:
            1. Provide a 'Taste Score' (0-100).
            2. COMMENTARY: What this list says about this person (paragraph).
            3. SNAPSHOT: Provide a personality snapshot as a few plain text bullet points.
            4. CHARACTER: Pick the ONE character from these shows that best represents them (Full Name).
            5. ROAST: A short 1 sentence brutal roast based on why this character fits.

            STRICT FORMATTING RULE: 
            - Return plain text ONLY. 
            - DO NOT use markdown bolding (**), italics (_), or headers (###).
            - Use the exact labels below followed by a colon.

            Format response:
            SCORE: [number]
            COMMENTARY: [text]
            SNAPSHOT: [text]
            CHARACTER: [full name]
            ROAST: [text]
            """

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are a cynical, accurate anime critic. You never use markdown formatting like asterisks or bolding in your response labels or content."
                )
            )

            try:
                res = response.text
                # --- 2. CLEANING FUNCTION ---
                def clean_text(text):
                    return text.replace("**", "").replace("__", "").replace("*", "").strip()

                # --- 3. ROBUST PARSING ---
                score_raw = res.split("SCORE:")[1].split("COMMENTARY:")[0]
                score = clean_text(score_raw)

                commentary_raw = res.split("COMMENTARY:")[1].split("SNAPSHOT:")[0]
                commentary = clean_text(commentary_raw)

                snapshot_raw = res.split("SNAPSHOT:")[1].split("CHARACTER:")[0]
                snapshot = clean_text(snapshot_raw)

                char_name_raw = res.split("CHARACTER:")[1].split("ROAST:")[0]
                char_name = clean_text(char_name_raw)

                roast_raw = res.split("ROAST:")[1]
                roast = clean_text(roast_raw)

                # --- 4. FETCH JIKAN DATA (With Clean Name) ---
                # We also remove anything in parentheses like "(Steins;Gate)" so Jikan doesn't get confused
                search_name = char_name.split("(")[0].strip()
                jikan_data = fetch_character_data(search_name)

                # --- 5. SAVE TO DATABASE ---
                db_entry = {
                    "username": username,
                    "anime_list": ", ".join(valid_titles),
                    "score": int(score) if score.isdigit() else 0,
                    "commentary": commentary,
                    "snapshot": snapshot,
                    "spirit_character": char_name, # Keeps full name for display
                    "roast_text": roast,
                    "character_image_url": jikan_data['image']
                }
                supabase.table("anime_list").insert(db_entry).execute()
                
                # --- 6. UI FEEDBACK ---
                st.balloons()
                st.divider()
                res_col1, res_col2 = st.columns([1, 2])
                
                with res_col1:
                    st.image(jikan_data['image'], width="stretch")
                    st.caption(f"Spirit Character: {char_name}")
                    st.info(f"🔥 {roast}")
                    st.markdown(f"🔗 [View on MyAnimeList]({jikan_data['url']})")
                
                with res_col2:
                    st.header(f"Taste Score: {score}/100")
                    st.markdown("### 📝 The Breakdown")
                    st.write(commentary)
                    
                    st.markdown("### 👤 Snapshot")
                    # Clean up the bullet points for Streamlit display
                    for point in snapshot.split("\n"):
                        p = clean_text(point).lstrip("-• 123456789. ")
                        if p:
                            st.markdown(f"* {p}")

            except Exception as e:
                st.error("The Judge's handwriting was too messy to read (Parsing Error). Please try again!")
                with st.expander("Debug Raw Response"):
                    st.write(res)
                    st.write(f"Error: {e}")

# --- TAB 2: LEADERBOARD ---
with tab2:
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