import requests
import time
import re


def fetch_verified_character(char_name, source_anime):
    """
    Surgical Fetch:
    1. Search for the specific anime first to get its ID.
    2. Fetch the full character list for that anime ID.
    3. Match the character name within that specific show's cast.
    4. Fallback to broad search only if the anime-specific lookup fails.
    """
    try:
        # Step 1: Search for the Anime to get its MAL ID
        anime_url = f"https://api.jikan.moe/v4/anime?q={source_anime}&limit=1"
        time.sleep(1) # Respect Jikan rate limits
        anime_res = requests.get(anime_url).json()
        
        if anime_res.get('data'):
            anime_id = anime_res['data'][0]['mal_id']
            
            # Step 2: Fetch characters for that specific anime
            char_url = f"https://api.jikan.moe/v4/anime/{anime_id}/characters"
            time.sleep(1)
            char_res = requests.get(char_url).json()
            
            # Step 3: Match the name in this specific show's cast
            for entry in char_res.get('data', []):
                # MAL names are often "Last, First" -> change to "Last First" for matching
                mal_name = entry['character']['name'].lower().replace(",", "")
                target_parts = char_name.lower().split()
                
                # Check if all parts of the target name exist in the MAL name
                if all(part in mal_name for part in target_parts):
                    images = entry['character'].get('images', {}).get('jpg', {})
                    return {
                        "image": images.get('large_image_url') or images.get('image_url'),
                        "url": entry['character'].get('url', '#')
                    }

        # Step 4: Fallback Broad Search
        search_url = f"https://api.jikan.moe/v4/characters?q={char_name}&limit=3"
        time.sleep(1)
        fallback_res = requests.get(search_url).json()
        
        if fallback_res.get('data'):
            top_result = fallback_res['data'][0]
            images = top_result.get('images', {}).get('jpg', {})
            return {
                "image": images.get('large_image_url') or images.get('image_url'),
                "url": top_result.get('url', '#')
            }

    except Exception as e:
        print(f"Fetch Error: {e}")
    
    return {"image": "https://placehold.co/400x600?text=Character+Not+Found", "url": "#"}


def clean_text(text):
    return text.replace("**", "").replace("__", "").replace("*", "").strip()


def strip_list_markers(text):
    """Removes '1.', '2.', and other list artifacts from AI responses."""
    # Removes numbers like "1. ", bullets like "- ", or "• " from the start
    return re.sub(r'^(\d+\.|\-|\•)\s*', '', text.strip())


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
