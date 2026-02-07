import time
import streamlit as st
from supabase import create_client
from utils import fetch_verified_character

# 1. Setup Connection (Reusing your streamlit secrets)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def parse_char_string(char_str):
    """Splits 'Name (Anime)' into ('Name', 'Anime')"""
    if not char_str or "(" not in char_str:
        return char_str, ""
    name = char_str.split("(")[0].strip()
    anime = char_str.split("(")[1].replace(")", "").strip()
    return name, anime

def run_image_fix():
    # 2. Find rows with missing images
    # We check for NULL or the 'Pending' placeholder we set earlier
    res = supabase.table("anime_list").select("*").or_(
        "character_image_url.is.null,shadow_image_url.is.null"
    ).execute()

    if not res.data:
        print("✅ No missing images found!")
        return

    print(f"Found {len(res.data)} users with missing images. Starting surgical fetch...")

    for row in res.data:
        username = row['username']
        updates = {}

        # Handle Spirit Character Image
        if not row.get('character_image_url'):
            name, anime = parse_char_string(row['spirit_character'])
            print(f"[{username}] Fetching Spirit: {name} from {anime}...")
            result = fetch_verified_character(name, anime)
            updates['character_image_url'] = result['image']
            time.sleep(1) # Extra safety for Jikan API

        # Handle Shadow Character Image
        if not row.get('shadow_image_url'):
            name, anime = parse_char_string(row['shadow_character'])
            print(f"[{username}] Fetching Shadow: {name} from {anime}...")
            result = fetch_verified_character(name, anime)
            updates['shadow_image_url'] = result['image']
            time.sleep(1)

        # 3. Push updates back to Supabase
        if updates:
            supabase.table("anime_list").update(updates).eq("username", username).execute()
            print(f"✅ Updated {username}")

if __name__ == "__main__":
    # Note: Run this via 'python fix_images.py' 
    # OR call it from a temporary button in your Streamlit app
    run_image_fix()