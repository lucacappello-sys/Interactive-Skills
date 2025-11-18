import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# =========================================================
# 1. CONFIGURAZIONE PAGINA
# =========================================================
st.set_page_config(
    page_title="Skills – As Is vs To Be",
    layout="wide"
)

# =========================================================
# 2. COSTANTI E MAPPING
# =========================================================

FIXED_CATEGORIES = [
    "analytical",
    "collaboration",
    "interaction / ux",
    "management",
    "operational",
    "personal / soft",
    "technical",
]

TO_BE_CAT_MAP = {
    "technical":      "technical",
    "operational":    "operational",
    "analytical":     "analytical",
    "collaboration":  "collaboration",
    "management":     "management",
    "soft":           "personal / soft",
    "personal/soft":  "personal / soft",
    "personal / soft": "personal / soft",
    "interaction/ux": "interaction / ux",
    "interaction / ux": "interaction / ux"
}

AS_IS_CAT_MAP = {
    "operational":    "operational",
    "collaboration":  "collaboration",
    "personal/soft":  "personal / soft",
    "personal / soft": "personal / soft",
    "soft":           "personal / soft",
    "analytical":     "analytical",
    "technical":      "technical",
    "management":     "management",
    "interaction/ux": "interaction / ux",
    "interaction / ux": "interaction / ux"
}

# Palette colori personalizzata
COLOR_MAP = {
    "AS-IS": "#EF553B", 
    "TO-BE": "#636EFA"
}
# Font personalizzato
CUSTOM_FONT = dict(family="Verdana, sans-serif", size=12, color="#2c3e50")

# =========================================================
# 3. FUNZIONI DI UTILITÀ
# =========================================================

def pretty_category(cat_canon: str) -> str:
    return cat_canon.title()

def normalize_string(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower()

def normalize_role_name(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.replace("_", "", regex=False)
    )

# =========================================================
# 4. GESTIONE STATO (SESSION STATE)
# =========================================================
if "selected_category" not in st.session_state:
    st.session_state["selected_category"] = pretty_category(FIXED_CATEGORIES[0])

# =========================================================
# 5. CARICAMENTO DATI
# =========================================================
#commmented
st.title("Confronto Skills: As-Is vs To-Be")
st.markdown("""
**Dashboard interattiva**
1. Carica il file Excel.
2. Seleziona i ruoli.
3. Clicca sui grafici per cambiare la categoria di skills a destra.
""")

uploaded_file = st.file_uploader("Carica il file Excel (.xlsx)", type=["xlsx"])

if not uploaded_file:
    st.info("Carica il file Excel per iniziare.")
    st.stop()

try:
    df_tobe_raw = pd.read_excel(uploaded_file, sheet_name="Skills To Be")
    df_asis_raw = pd.read_excel(uploaded_file, sheet_name="Skills As Is")
except Exception as e:
    st.error(f"Errore nel caricamento del file: {e}")
    st.stop()

# Pulizia
df_tobe_raw.columns = [c.strip().lower() for c in df_tobe_raw.columns]
df_asis_raw.columns = [c.strip().lower() for c in df_asis_raw.columns]
df_tobe = df_tobe_raw.dropna(subset=["skill"]).copy()
df_asis = df_asis_raw.dropna(subset=["skill"]).copy()

# Mapping
df_tobe["cat_norm"] = normalize_string(df_tobe["skill category"]).map(TO_BE_CAT_MAP)
df_asis["cat_norm"] = normalize_string(df_asis["skill category"]).map(AS_IS_CAT_MAP)
df_tobe["role_clean"] = normalize_role_name(df_tobe["role"])
df_asis["role_clean"] = normalize_role_name(df_asis["role as is"])
df_asis["role_tobe_target_clean"] = normalize_role_name(df_asis["role to be"].fillna(""))

as_is_roles_display = sorted(df_asis["role as is"].unique())
to_be_roles_display = sorted(df_tobe["role"].unique())
clean_to_display_tobe = df_tobe.set_index("role_clean")["role"].to_dict()

# =========================================================
# 6. SELEZIONE RUOLI
# =========================================================

col_sel1, col_sel2 = st.columns(2)

with col_sel1:
    selected_asis = st.selectbox("Ruolo AS-IS", as_is_roles_display)

suggested_target_clean = df_asis[df_asis["role as is"] == selected_asis]["role_tobe_target_clean"].unique()
suggested_options = sorted(list(set([
    clean_to_display_tobe[r] for r in suggested_target_clean if r in clean_to_display_tobe
])))
final_options = suggested_options if suggested_options else to_be_roles_display

with col_sel2:
    selected_tobe = st.selectbox("Ruolo TO-BE", final_options)

# =========================================================
# 7. PREPARAZIONE DATI
# =========================================================

sel_asis_clean = normalize_role_name(pd.Series([selected_asis]))[0]
sel_tobe_clean = normalize_role_name(pd.Series([selected_tobe]))[0]

subset_asis = df_asis[df_asis["role_clean"] == sel_asis_clean]
subset_tobe = df_tobe[df_tobe["role_clean"] == sel_tobe_clean]

counts_asis = subset_asis.groupby("cat_norm")["skill"].count()
counts_tobe = subset_tobe.groupby("cat_norm")["skill"].count()

categories_list = []
values_asis_list = []
values_tobe_list = []

for cat in FIXED_CATEGORIES:
    cat_display = pretty_category(cat)
    val_a = counts_asis.get(cat, 0)
    val_t = counts_tobe.get(cat, 0)
    categories_list.append(cat_display)
    values_asis_list.append(val_a)
    values_tobe_list.append(val_t)

df_chart = pd.DataFrame({
    "Categoria": categories_list * 2,
    "Valore": values_asis_list + values_tobe_list,
    "Tipo": ["AS-IS"] * len(categories_list) + ["TO-BE"] * len(categories_list)
})

# =========================================================
# 8. VISUALIZZAZIONE GRAFICI
# =========================================================

left_col, right_col = st.columns([2, 1])

with left_col:
    chart_types = st.multiselect(
        "Visualizza grafici:",
        ["Radar", "Barre", "Bolle"],
        default=["Radar", "Barre"]
    )

    # --- RADAR CHART ---
    if "Radar" in chart_types:
        st.subheader("Radar Chart")
        
        # Dati "chiusi" per il radar
        r_a = values_asis_list + [values_asis_list[0]]
        r_t = values_tobe_list + [values_tobe_list[0]]
        theta = categories_list + [categories_list[0]]
        max_val = max(max(r_a), max(r_t)) + 1
        
        fig_radar = go.Figure()
        
        # AS-IS Trace
        fig_radar.add_trace(go.Scatterpolar(
            r=r_a, theta=theta, fill='toself', name=f'AS-IS: {selected_asis}',
            line_color=COLOR_MAP["AS-IS"],
            mode='lines+markers',
            marker=dict(size=14, line=dict(width=2, color='white')) 
        ))
        
        # TO-BE Trace
        fig_radar.add_trace(go.Scatterpolar(
            r=r_t, theta=theta, fill='toself', name=f'TO-BE: {selected_tobe}',
            line_color=COLOR_MAP["TO-BE"],
            mode='lines+markers',
            marker=dict(size=14, line=dict(width=2, color='white'))
        ))
        
        fig_radar.update_layout(
            font=CUSTOM_FONT,
            legend=dict(orientation="h", y=1.1, x=1),
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max_val], tickfont=dict(size=10), gridcolor="lightgray"),
                angularaxis=dict(tickfont=dict(size=12, color="black"))
            ),
            height=500,
            margin=dict(t=50, b=40, l=60, r=60),
            clickmode='event+select'
        )
        
        event_radar = st.plotly_chart(
            fig_radar, 
            use_container_width=True, 
            on_select="rerun", 
            selection_mode="points",
            key="radar_chart"
        )
        
        if event_radar and event_radar.selection["points"]:
            point = event_radar.selection["points"][0]
            if "theta" in point:
                st.session_state["selected_category"] = point["theta"]
            elif "point_index" in point:
                idx = point["point_index"]
                real_idx = idx % len(categories_list)
                selected_cat = categories_list[real_idx]
                st.session_state["selected_category"] = selected_cat

    # --- BARRE ---
    if "Barre" in chart_types:
        st.subheader("Bar Chart")
        fig_bar = px.bar(
            df_chart, x="Categoria", y="Valore", color="Tipo", barmode="group", text_auto=True,
            color_discrete_map=COLOR_MAP
        )
        fig_bar.update_layout(
            font=CUSTOM_FONT,
            xaxis=dict(title=None, tickfont=dict(size=12)),
            yaxis=dict(title=None, showgrid=True, gridcolor="#eee"),
            legend=dict(title=None, orientation="h", y=1.1, x=1),
            height=450,
            margin=dict(t=40),
            clickmode='event+select'
        )
        event_bar = st.plotly_chart(
            fig_bar, use_container_width=True, on_select="rerun", selection_mode="points", key="bar_chart"
        )
        if event_bar and event_bar.selection["points"]:
            point = event_bar.selection["points"][0]
            if "x" in point:
                st.session_state["selected_category"] = point["x"]

    # --- BOLLE (CON NUMERI) ---
    if "Bolle" in chart_types:
        st.subheader("Bubble Chart")
        
        # Filtriamo i dati: solo valori > 0
        df_bubble = df_chart[df_chart["Valore"] > 0].copy()
        
        fig_bubble = px.scatter(
            df_bubble, 
            x="Categoria", 
            y="Tipo", 
            size="Valore", 
            color="Tipo",
            size_max=60, 
            hover_data={"Valore": True},
            color_discrete_map=COLOR_MAP,
            text="Valore"  # <--- NUOVO: Indica che il testo è la colonna Valore
        )
        fig_bubble.update_xaxes(categoryorder='array', categoryarray=categories_list)
        fig_bubble.update_layout(
            font=CUSTOM_FONT,
            xaxis=dict(title=None, gridcolor="#eee"),
            yaxis=dict(title=None, type='category'),
            legend=dict(title=None, orientation="h", y=1.1, x=1),
            height=450,
            plot_bgcolor="rgba(240, 242, 246, 0.5)",
            clickmode='event+select'
        )
        # Stile del testo dentro le bolle (Bianco e Grassetto)
        fig_bubble.update_traces(
            textposition='middle center',
            textfont=dict(color='white', weight='bold')
        )

        event_bubble = st.plotly_chart(
            fig_bubble, use_container_width=True, on_select="rerun", selection_mode="points", key="bubble_chart"
        )
        if event_bubble and event_bubble.selection["points"]:
            point = event_bubble.selection["points"][0]
            if "x" in point:
                st.session_state["selected_category"] = point["x"]

# =========================================================
# 9. DETTAGLIO SKILL
# =========================================================

with right_col:
    curr_cat = st.session_state["selected_category"]
    
    st.subheader(f"Dettaglio: {curr_cat}")
    
    try:
        idx = categories_list.index(curr_cat)
        cat_canon = FIXED_CATEGORIES[idx]
    except:
        cat_canon = FIXED_CATEGORIES[0]

    skills_asis_list = subset_asis[subset_asis["cat_norm"] == cat_canon]["skill"].tolist()
    skills_tobe_list = subset_tobe[subset_tobe["cat_norm"] == cat_canon]["skill"].tolist()

    with st.container(border=True):
        st.markdown(f"**AS-IS ({len(skills_asis_list)})**")
        if skills_asis_list:
            for s in skills_asis_list:
                st.markdown(f"• {s}")
        else:
            st.caption("Nessuna skill")

    with st.container(border=True):
        st.markdown(f"**TO-BE ({len(skills_tobe_list)})**")
        if skills_tobe_list:
            for s in skills_tobe_list:
                st.markdown(f"• {s}")
        else:
            st.caption("Nessuna skill")
            
    delta = len(skills_tobe_list) - len(skills_asis_list)
    
    if delta > 0:
        st.success(f"Gap: +{delta} (Skill aggiunte)")
    elif delta < 0:
        st.error(f"Gap: {delta} (Skill perse)")
    else:
        st.info("Gap: 0 (Invariato)")