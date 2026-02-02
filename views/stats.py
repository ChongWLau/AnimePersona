import streamlit as st
import pandas as pd
import plotly.express as px

def show_stats_tab(supabase):
    st.header("📊 Global Anime Leaderboard")
    st.write("Every anime listed by users, ranked by frequency.")

    # 1. Fetch data
    res = supabase.table("anime_list").select("anime_list").execute()
    
    if not res.data:
        st.info("No data yet!")
        return

    # 2. Process ALL titles
    all_titles = []
    for entry in res.data:
        titles = [t.strip() for t in entry['anime_list'].split(',') if t.strip()]
        all_titles.extend(titles)

    df = pd.DataFrame(all_titles, columns=["Anime Title"])
    df["Anime Title"] = df["Anime Title"].str.title()
    
    # Create the full count list (No .nlargest() limit here)
    full_counts = df["Anime Title"].value_counts().reset_index()
    full_counts.columns = ["Anime Title", "Count"]

    # 3. Visual Highlight: Top 20 Chart
    # We still show a chart, but expanded to 20 for better visibility
    top_20 = full_counts.head(20)
    
    fig = px.bar(
        top_20, 
        x="Count", 
        y="Anime Title", 
        orientation='h',
        color="Count",
        color_continuous_scale="Agsunset",
        template="plotly_dark",
        title="Top 20 Most Frequent Appearances"
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
    st.plotly_chart(fig, width='content')

    # 4. THE FULL LIST (Searchable & Sortable)
    st.divider()
    st.subheader("📋 Full Global Rankings")
    st.write("Search for a specific anime to see how many people have it in their list:")
    
    # st.dataframe provides a built-in search bar and sorting
    st.dataframe(
        full_counts, 
        width='content',
        hide_index=True,
        column_config={
            "Anime Title": st.column_config.TextColumn("Series Name"),
            "Count": st.column_config.NumberColumn("Total Users", help="How many users included this in their top 9")
        }
    )

    # 5. Fun Metrics
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Judgments", len(res.data))
    c2.metric("Total Votes Cast", len(all_titles))
    c3.metric("Unique Series", len(full_counts))