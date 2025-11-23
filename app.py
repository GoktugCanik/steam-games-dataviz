import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(page_title="Data Visualation of Best Selling Games on Steam", layout="wide")

# Load Data
def load_data():
    data = pd.read_csv("data/bestSelling_games.csv")
    data["price"] = pd.to_numeric(data["price"], errors="coerce")
    data["reviews_like_rate"] = pd.to_numeric(data["reviews_like_rate"], errors="coerce")
    data["rating"] = pd.to_numeric(data["rating"], errors="coerce")
    data["estimated_downloads"] = pd.to_numeric(data["estimated_downloads"], errors="coerce")
    data["release_date"] = pd.to_datetime(data["release_date"], errors="coerce")
    data["user_defined_tags"] = data["user_defined_tags"].fillna("")
    data = data.drop_duplicates(subset=["game_name","developer"]) 
    release_year = data["release_date"].dt.year
    data["release_year"] = release_year
    data["is_free"] = (data["price"].fillna(0) == 0).astype(int)

    return data

data = load_data()

# Side Bar for Filters
st.sidebar.header("Filters")

min_downloads = st.sidebar.number_input("Minimum Downloads", 0, int(data["estimated_downloads"].max()), 0, step=100000)
year_range = st.sidebar.slider("Release Year Range", int(data["release_year"].min()), int(data["release_year"].max()), (int(data["release_year"].min()), int(data["release_year"].max())))
developers = data["developer"].value_counts().index.tolist()
selected_developers = st.sidebar.multiselect("Developers", options=developers, default=[])
os = (data["supported_os"].dropna().str.replace(" ", "").str.split(",").explode().unique())
os_options = sorted([o for o in os if o != ""]) 
selected_os = st.sidebar.multiselect("Supported OS", options=os_options, default=[])
free_only = st.sidebar.checkbox("Free Only", value=False)

filtered = data.copy()  
if selected_developers:
    filtered = filtered[filtered["developer"].isin(selected_developers)]
if selected_os:
    pattern = "|".join(selected_os)
    filtered = filtered[filtered["supported_os"].fillna("").str.replace(" ", "").str.contains(pattern)]
filtered = filtered[(filtered["estimated_downloads"] >= min_downloads)]
filtered = filtered[(filtered["release_year"] >= year_range[0]) & (filtered["release_year"] <= year_range[1])]
if free_only:
    filtered = filtered[filtered["price"] == 0]

st.title("Google Play Store Data Visualization")

#Bar Graph
st.header("📊 Games by Estimated Downloads")
top_games = filtered.sort_values("estimated_downloads", ascending=False).head(20)
fig_bar = px.bar(
    top_games,
    x="game_name",
    y="estimated_downloads",
    title="Games by Estimated Downloads",
    template="plotly_white",
    labels={"game_name": "Game", "estimated_downloads": "Downloads"}
)
fig_bar.update_traces(hovertemplate="Game Name: %{x}<br>Estimated Downloads: %{y:,}<extra></extra>")
st.plotly_chart(fig_bar, use_container_width=True)

# Treemap
st.header("🌳 Treemap: Downloads by Developer and Reviews Like Rate")
treemap_data = filtered.copy()
treemap_data["is_free_label"] = np.where(treemap_data["is_free"] == 0, "Paid", "Free")

fig_treemap = px.treemap(treemap_data, path=["developer", "is_free_label", "game_name"], values="estimated_downloads", 
                                    color="reviews_like_rate", color_continuous_scale="Viridis", title="Downloads Hierarchy",
                                    labels={"developer":"Developer","is_free_label":"Free","game_name":"Game"})
st.plotly_chart(fig_treemap, use_container_width=True)


# Parallel Coordinates
st.header("🧭 Parallel Coordinates: Numeric Features")
pc_cols = ["estimated_downloads", "rating", "price", "length", "difficulty"]
pc_data = filtered[pc_cols + ["game_name", "developer"]].dropna()
pc_data = pc_data.sort_values("estimated_downloads", ascending=False).head(200)
fig_pc = px.parallel_coordinates(pc_data, dimensions=pc_cols, color="estimated_downloads", color_continuous_scale=px.colors.sequential.Plasma,
                               labels={"estimated_downloads": "Downloads", "rating": "Rating", "price": "Price", "length": "Length", "difficulty": "Difficulty"})   
st.plotly_chart(fig_pc, use_container_width=True)


# Scatter/bubble
st.header("💸 Price vs Rating (Bubble by Downloads)")
scatter_data = filtered.sort_values("estimated_downloads", ascending=False).head(100)
fig_scatter = px.scatter(scatter_data, x="price", y="rating", size="estimated_downloads", color="developer", hover_name="game_name", labels={"price": "Price", "rating": "Rating"}, template="plotly_white", title="Price vs Rating")
fig_scatter.update_traces(hovertemplate="Game Name: %{hovertext}<br>Price: %{x:.2f}<br>Rating: %{y:.2f}<br>Downloads: %{marker.size:,}<extra></extra>")
st.plotly_chart(fig_scatter, use_container_width=True)  

# Sunburst Chart
st.header("🌞 Sunburst: Genre → Developer → Game")
sb = filtered.sort_values("estimated_downloads", ascending=False).head(10).copy()
sb["tags_list"] = sb["user_defined_tags"].astype(str).str.split(",")
sb = sb.explode("tags_list")
sb["tags_list"] = sb["tags_list"].str.strip()
sb = sb[sb["tags_list"] != ""]
sb["downloads_weight"] = sb["estimated_downloads"] / sb.groupby("game_name")["tags_list"].transform("count").replace(0, 1)
fig_sunburst = px.sunburst(sb, path=["tags_list", "developer", "game_name"], values="downloads_weight", color="rating", color_continuous_scale="RdBu", title="Sunburst by Genre, Developer, and Game")
st.plotly_chart(fig_sunburst, use_container_width=True)

# Heatmap
st.header("🔥 Heatmap: Correlation Matrix")
heatmap_data = filtered[["estimated_downloads", "rating", "price", "length", "reviews_like_rate"]].dropna()
fig_heatmap = px.imshow(heatmap_data.corr(), text_auto=".4f", title="Correlation Matrix", color_continuous_scale="Viridis",)
st.plotly_chart(fig_heatmap, use_container_width=True)

# Line Chart
st.header("📈 Downloads Per Year")
line_data = filtered.groupby("release_year", as_index=False)["estimated_downloads"].sum()
fig_line = px.line(line_data, x="release_year", y="estimated_downloads", markers=True, template="plotly_white", labels={"release_year": "Year", "estimated_downloads": "Downloads"}, title="Total Downloads per Year")
st.plotly_chart(fig_line, use_container_width=True)

#Icicle Chart
st.header("🌳 Icicle: Age Restriction → Genre → Game")
max_tags = st.slider("Max genres", 3, 30, 8)
max_games = st.slider("Max games per genre", 3, 50, 10)
icicle_data = filtered.copy()
icicle_data["primary_tag"] = icicle_data["user_defined_tags"].astype(str).str.split(",").str[0].str.strip()
icicle_data["primary_tag"] = icicle_data["primary_tag"].replace({"": "Unknown"})
icicle_data["age_val"] = pd.to_numeric(icicle_data["age_restriction"], errors="coerce").fillna(0).astype(int)
icicle_data["age_label"] = icicle_data["age_val"].map({0: "All Ages", 13: "Teen 13+", 17: "Mature 17+"})
icicle_data["age_label"] = icicle_data["age_label"].fillna(icicle_data["age_val"].astype(str))
tag_downloads = icicle_data.groupby("primary_tag", as_index=False)["estimated_downloads"].sum().sort_values("estimated_downloads", ascending=False)
top_tags = tag_downloads["primary_tag"].head(max_tags)
icicle_data = icicle_data[icicle_data["primary_tag"].isin(top_tags)]
icicle_data = icicle_data.sort_values(["primary_tag", "estimated_downloads"], ascending=False).groupby("primary_tag", as_index=False).head(max_games)
icicle_view = icicle_data.sort_values("estimated_downloads", ascending=False)
fig_icicle = px.icicle(icicle_view, path=["age_label", "primary_tag", "game_name"], values="estimated_downloads", color="rating", color_continuous_scale="Viridis", title=f"Icicle: Age → Genre → Game (Top {max_tags} genres, Top {max_games} games)")
st.plotly_chart(fig_icicle, use_container_width=True)

# 3D Game Design Profile
st.header("🧊 3D Game Design Profile: Difficulty vs Length vs Rating")
td_data = data[["difficulty", "length", "rating", "game_name", "developer"]].dropna()
td_data = td_data.sort_values("rating", ascending=False).head(200)
fig_td = px.scatter_3d(td_data, x="difficulty", y="length", z="rating", color="developer",
    hover_name="game_name", title="3D: Difficulty vs Length vs Rating", template="plotly_white",)
st.plotly_chart(fig_td, width='stretch')

