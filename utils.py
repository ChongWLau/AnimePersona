import requests
import time
import re


def fetch_verified_character(char_name, source_anime):
    """
    1. Search for the character name broadly.
    2. Fetch the top 5 results.
    3. For each result, check their 'anime' list for the source_anime.
    """
    try:
        # Step 1: Broad Search for the Character
        search_url = f"https://api.jikan.moe/v4/characters?q={char_name}&limit=5"
        time.sleep(1) # Rate limit protection
        search_res = requests.get(search_url).json()
        
        results = search_res.get('data', [])
        if not results:
            return {"image": "https://placehold.co/400x600?text=No+Character+Found", "url": "#"}

        # Step 2: Manually filter the top 5
        for entry in results:
            char_id = entry['mal_id']
            
            # Fetch this specific character's anime appearances
            appearances_url = f"https://api.jikan.moe/v4/characters/{char_id}/anime"
            time.sleep(1) # Respect the 1-second rule
            app_res = requests.get(appearances_url).json()
            
            # Step 3: Check if source_anime is in their history
            # We use fuzzy matching (.lower() and 'in') to catch partial titles
            for appearance in app_res.get('data', []):
                anime_title = appearance['anime']['title'].lower()
                if source_anime.lower() in anime_title or anime_title in source_anime.lower():
                    # Match found! Use this image.
                    images = entry.get('images', {}).get('jpg', {})
                    return {
                        "image": images.get('large_image_url') or images.get('image_url'),
                        "url": entry.get('url', '#')
                    }
                    
        # Fallback: If no match in the top 5, just use the first result
        first_char = results[0]
        images = first_char.get('images', {}).get('jpg', {})
        return {
            "image": images.get('large_image_url') or images.get('image_url'),
            "url": first_char.get('url', '#')
        }

    except Exception as e:
        print(f"Fetch Error: {e}")
        return {"image": "https://placehold.co/400x600?text=Spirit+Not+Found", "url": "#"}


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
