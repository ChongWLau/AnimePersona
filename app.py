import streamlit as st
from google import genai

from supabase import create_client, Client

from views.hall import show_hall_of_fame
from views.judge import show_judge_tab
from views.lookup import show_lookup_tab

# --- 1. INITIALIZATION ---
GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

client = genai.Client(api_key=GEMINI_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

tab1, tab2, tab3 = st.tabs(["🔥 Get Judged", "🏆 Hall of Fame", "🔍 Find Result"])

with tab1:
    show_judge_tab(supabase, client)
with tab2:
    show_hall_of_fame(supabase)
with tab3:
    show_lookup_tab(supabase)
