"""AgroFlux AI Streamlit dashboard."""

import json
import math
import os
import hmac
from pathlib import Path

import pandas as pd
import streamlit as st

from features.state_coverage import render_state_coverage
from features.satellite_analysis import render_satellite_analysis
from features.yield_prediction import render_yield_prediction
from features.carbon_simulator import render_carbon_simulator


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"


st.set_page_config(page_title="Carbon Nova AI | Agriculture Intelligence", page_icon="🌿", layout="wide")


def require_password():
    """Require a password from an environment variable before showing app data."""
    expected_password = os.environ.get("APP_PASSWORD", "")
    if not expected_password:
        st.error(
            "Dashboard access is not configured. Set the APP_PASSWORD environment "
            "variable locally or in Render before starting the app."
        )
        st.stop()

    if st.session_state.get("agroflux_authenticated"):
        return

    st.title("🔐 AgroFlux AI — Protected Access")
    with st.form("agroflux_login_form"):
        entered_password = st.text_input("Dashboard password", type="password")
        submitted = st.form_submit_button("Unlock dashboard", width="stretch")

    if submitted:
        if hmac.compare_digest(entered_password, expected_password):
            st.session_state["agroflux_authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()


require_password()


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --cn-bg:#07130e; --cn-panel:#10251a; --cn-border:rgba(144,202,164,.20); --cn-text:#edf8f0; --cn-muted:#a8c6b2; --cn-accent:#75efaa; }
html { scroll-behavior:smooth; }
.stApp {
 background:radial-gradient(ellipse at 8% 0%,rgba(30,132,77,.25),transparent 34%),radial-gradient(ellipse at 95% 12%,rgba(40,112,75,.18),transparent 30%),linear-gradient(145deg,#07130e 0%,#0a1a12 48%,#08140e 100%);
 color:var(--cn-text);font-family:'DM Sans',sans-serif;
}
.block-container { max-width:1500px;padding-top:1.2rem;padding-bottom:4rem; }
h1,h2,h3 { color:var(--cn-text)!important;font-family:'Manrope',sans-serif!important;letter-spacing:-.55px; }
h1 { font-size:2.25rem!important;font-weight:800!important; } h2 { font-weight:800!important; } h3 { font-weight:750!important; }
p,label,.stMarkdown { color:#d6e7db; } [data-testid="stCaptionContainer"] p { color:var(--cn-muted)!important; }
[data-testid="stMetric"] {
 background:linear-gradient(145deg,rgba(23,54,37,.96),rgba(12,31,21,.96));border:1px solid var(--cn-border);
 border-radius:22px;padding:19px 21px;box-shadow:0 12px 30px rgba(0,0,0,.16);
 transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease;
}
[data-testid="stMetric"]:hover { transform:translateY(-3px);border-color:rgba(117,239,170,.55);box-shadow:0 16px 35px rgba(0,0,0,.22); }
[data-testid="stMetricLabel"] { color:#b5d1bf!important;font-weight:600; }
[data-testid="stMetricValue"] { color:var(--cn-accent)!important;font-weight:800!important; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#081710,#0e2418);border-right:1px solid var(--cn-border); }
[data-testid="stSidebar"] * { color:var(--cn-text); }
[data-testid="stSidebar"] a { color:#b6f6ce!important;text-decoration:none!important;font-weight:600; }
[data-testid="stSidebar"] a:hover { color:#fff!important; }
.stTextInput input,.stNumberInput input,.stTextArea textarea { background:#10251a;color:var(--cn-text);border:1px solid #315b42;border-radius:12px; }
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button {
 background:linear-gradient(135deg,#16804a,#20ad65);color:white;border:1px solid #3cbd7a;border-radius:12px;
 padding:.68rem 1.1rem;font-weight:750;transition:all .18s ease;
}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"] button:hover {
 background:linear-gradient(135deg,#28b96c,#43d987);color:#06140c;border-color:#8cf4b5;transform:translateY(-2px);box-shadow:0 8px 22px rgba(32,173,101,.18);
}
[data-testid="stDataFrame"],[data-testid="stTable"] { border:1px solid var(--cn-border);border-radius:14px;overflow:hidden; }
[data-testid="stImage"] img { border-radius:22px;border:1px solid var(--cn-border);transition:transform .2s ease; }
[data-testid="stImage"] img:hover { transform:scale(1.01); }
[data-testid="stAlert"] { border-radius:20px;border:1px solid rgba(104,220,157,.28);box-shadow:0 8px 24px rgba(0,0,0,.12); }
div[data-testid="stProgressBar"]>div>div,.stProgress>div>div { background:linear-gradient(90deg,#20ad65,#8af4b6); }
hr { border-color:rgba(137,207,160,.18);margin:1.8rem 0; }
div[data-testid="stForm"] { background:linear-gradient(145deg,rgba(20,49,34,.88),rgba(9,27,18,.92));border:1px solid rgba(117,239,170,.24);border-radius:24px;padding:22px;box-shadow:0 12px 30px rgba(0,0,0,.13); }
/* Rounded panels around Streamlit bordered containers and data areas */
div[data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(145deg,rgba(20,48,33,.76),rgba(9,25,17,.88));border:1px solid rgba(128,211,157,.25);border-radius:22px;padding:8px 10px;box-shadow:0 12px 28px rgba(0,0,0,.13);transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease; }
div[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color:rgba(117,239,170,.5);box-shadow:0 16px 34px rgba(0,0,0,.2); }
[data-testid="stDataFrame"], [data-testid="stTable"] { background:rgba(13,34,23,.72);border:1px solid rgba(117,239,170,.22);border-radius:20px;overflow:hidden;padding:5px; }
[data-testid="stTabs"] [role="tablist"] { gap:8px;background:rgba(7,23,15,.65);padding:7px;border:1px solid var(--cn-border);border-radius:18px; }
[data-testid="stTabs"] button[role="tab"] { border-radius:13px;padding:8px 16px; }
[data-testid="stTabs"] button[aria-selected="true"] { background:linear-gradient(135deg,#176b40,#23975a); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a { display:block;background:linear-gradient(135deg,rgba(25,67,45,.92),rgba(12,38,25,.95));border:1px solid rgba(117,239,170,.19);border-radius:15px;padding:11px 13px;margin:8px 0;box-shadow:0 5px 14px rgba(0,0,0,.12);transition:all .18s ease; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a:hover { background:linear-gradient(135deg,#1b7748,#164b31);border-color:rgba(117,239,170,.6);transform:translateX(3px); }
[data-testid="stSidebar"] h3 { padding:12px 13px;background:rgba(117,239,170,.07);border:1px solid rgba(117,239,170,.14);border-radius:16px; }
.cn-hero {
 position:relative;overflow:hidden;padding:34px 36px;border-radius:30px;margin:0 0 26px 0;
 background:linear-gradient(115deg,rgba(17,75,45,.98),rgba(16,48,32,.98) 58%,rgba(25,95,58,.95));
 border:1px solid rgba(143,241,179,.28);box-shadow:0 20px 55px rgba(0,0,0,.22);
}
.cn-hero:after { content:"🌿";position:absolute;right:35px;top:5px;font-size:100px;opacity:.13;transform:rotate(-14deg); }
.cn-eyebrow { color:#a7f4c2;font-size:.76rem;font-weight:800;letter-spacing:2px; }
.cn-title { color:#f3fff6;font-family:Manrope,sans-serif;font-size:2.25rem;font-weight:800;line-height:1.15;margin:9px 0; }
.cn-subtitle { color:#d0efdc;font-size:1rem;max-width:750px;line-height:1.6; }
.cn-chip { display:inline-block;margin-top:16px;margin-right:7px;padding:6px 11px;border-radius:99px;background:rgba(7,28,17,.38);border:1px solid rgba(173,255,201,.25);color:#dfffea;font-size:.78rem;font-weight:700; }
/* Dedicated action-plan cards: stronger hierarchy, rounded corners, accent rail */
.cn-action-card { display:flex;gap:18px;align-items:flex-start;margin:14px 0;padding:21px 23px;border-radius:22px;background:linear-gradient(120deg,rgba(19,58,38,.96),rgba(10,31,21,.98));border:1px solid rgba(124,221,157,.28);border-left:5px solid #42cf82;box-shadow:0 12px 28px rgba(0,0,0,.19);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease; }
.cn-action-card:hover { transform:translateY(-2px);border-color:rgba(117,239,170,.65);box-shadow:0 16px 32px rgba(0,0,0,.24); }
.cn-action-number { flex:0 0 48px;height:48px;display:flex;align-items:center;justify-content:center;border-radius:15px;background:linear-gradient(145deg,#1e9b5c,#145c39);border:1px solid rgba(159,255,193,.34);color:#f2fff6;font-size:1rem;font-weight:800; }
.cn-action-title { color:#9ff4bd;font-size:.78rem;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;margin:1px 0 8px; }
.cn-action-copy { color:#e4f5e9;font-size:1rem;line-height:1.65;margin:0; }
.cn-section-intro { color:#a9cbb5;font-size:.94rem;margin-top:-8px;margin-bottom:18px; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a { scroll-margin-top:20px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="cn-hero">
  <div class="cn-eyebrow">AGRICULTURE • CLIMATE INTELLIGENCE</div>
  <div class="cn-title">Carbon Nova AI</div>
  <div class="cn-subtitle">A smarter view of vegetation, farm emissions and crop-yield insights — bringing your agricultural analytics into one workspace.</div>
  <span class="cn-chip">🛰️ Satellite insights</span>
  <span class="cn-chip">🌾 Fertilizer analysis</span>
  <span class="cn-chip">♻️ Carbon estimates</span>
  <span class="cn-chip">🤖 ML predictions</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🌿 Carbon Nova")
    st.caption("AGRICULTURE INTELLIGENCE")
    st.markdown("---")
    st.markdown("### Quick navigation")
    st.caption("Jump to a workspace")
    st.markdown("[🛰️ Satellite vegetation](#cn-satellite)")
    st.markdown("[🌾 Fertilizer emissions](#cn-fertilizer)")
    st.markdown("[🏭 Farm carbon emissions](#cn-carbon)")
    st.markdown("[🧮 Scenario calculator](#cn-scenario)")
    st.markdown("[🇮🇳 India emissions trend](#cn-india-trend)")
    st.markdown("[🤖 Yield prediction](#cn-yield)")
    st.markdown("[🌱 Farm action plan](#cn-action-plan)")
    st.markdown("---")
    st.markdown("**Workspace status**")
    st.caption("Dashboard connected to local project files.")
    st.caption("Explore each section using quick navigation.")


def read_json(path):
    """Read a JSON file; return an empty dict if it's absent or invalid."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as error:
        st.warning(f"Could not read {path.name}: {error}")
        return {}


# Carbon summary is optional. Its absence should never break the dashboard.
summary = read_json(OUTPUT_DIR / "carbon_emissions_summary.json")

# 1. State-wise dataset coverage (calculated from the rice dataset)
render_state_coverage(BASE_DIR)
st.divider()

# 2. Satellite vegetation analysis (separate module)
render_satellite_analysis(OUTPUT_DIR)
st.divider()

# 2. Fertilizer emission estimates
st.markdown('<div id="cn-fertilizer"></div>', unsafe_allow_html=True)
st.header("🌾 Fertilizer Emissions")
fertilizer_path = OUTPUT_DIR / "fertilizer_emissions_summary.csv"
if fertilizer_path.exists():
    try:
        fertilizer_df = pd.read_csv(fertilizer_path)
        if fertilizer_df.empty:
            st.info("Fertilizer summary exists but contains no rows.")
        else:
            st.dataframe(fertilizer_df, width="stretch")
    except Exception as error:
        st.warning(f"Could not read fertilizer summary: {error}")
else:
    st.warning("Fertilizer summary CSV is missing. Run the fertilizer-emissions calculation to generate it.")

image_path = OUTPUT_DIR / "fertilizer_emissions_by_type.png"
if image_path.exists():
    st.image(str(image_path), caption="Estimated Emissions by Fertilizer Type", width="stretch")

st.divider()

# 3. Carbon emissions: show detailed/partial rows if available
st.markdown('<div id="cn-carbon"></div>', unsafe_allow_html=True)
st.header("🏭 Farm Carbon Emissions")
carbon_results_path = OUTPUT_DIR / "carbon_emissions_results.csv"

diesel_found = bool(summary.get("diesel_column_found", False))
electricity_found = bool(summary.get("electricity_column_found", False))
complete_records = int(summary.get("records_with_complete_totals", 0) or 0)
processed = int(summary.get("records_processed", 0) or 0)

m1, m2, m3 = st.columns(3)
m1.metric("Records processed", f"{processed:,}" if processed else "Not reported")
m2.metric("Diesel quantity data", "Found" if diesel_found else "Missing")
m3.metric("Electricity quantity data", "Found" if electricity_found else "Missing")

if carbon_results_path.exists():
    try:
        carbon_df = pd.read_csv(carbon_results_path)
        st.subheader("Available carbon calculation results")
        total_col = "total_emissions_kgco2e"
        if total_col in carbon_df.columns:
            totals = pd.to_numeric(carbon_df[total_col], errors="coerce")
            complete_totals = totals.dropna()
            if not complete_totals.empty:
                c1, c2 = st.columns(2)
                c1.metric("Records with complete totals", f"{len(complete_totals):,}")
                c2.metric("Sum of complete record totals", f"{complete_totals.sum():,.2f} kg CO₂e")
            else:
                st.warning(
                    "Detailed calculation file exists, but it contains no complete farm totals. "
                    "Diesel/electricity quantities may be missing; missing sources are not treated as zero."
                )
        # Display the table even when total emissions are incomplete so partial outputs are visible.
        st.dataframe(carbon_df.head(100), width="stretch")
        if len(carbon_df) > 100:
            st.caption("Showing first 100 rows of the detailed output.")
    except Exception as error:
        st.warning(f"Could not read carbon results: {error}")
else:
    st.info("Detailed carbon results file not found. Run the carbon-emissions calculation first.")

if not diesel_found or not electricity_found or complete_records == 0:
    st.warning(
        f"Complete farm-level carbon totals are not currently available. "
        f"Reported complete records: {complete_records}. The existing inputs support only partial estimates. "
        "Do not interpret missing diesel/electricity data as zero emissions."
    )

image_path = OUTPUT_DIR / "carbon_emissions_by_source.png"
if image_path.exists():
    st.image(str(image_path), caption="Carbon engine outputs — interpret as partial estimates where sources are missing", width="stretch")

# Carbon reduction simulator (separate module)
render_carbon_simulator()
st.divider()

# National trend chart
st.markdown('<div id="cn-india-trend"></div>', unsafe_allow_html=True)
st.header("🇮🇳 India Agricultural Emissions Trend")
image_path = OUTPUT_DIR / "india_emissions_trends.png"
if image_path.exists():
    st.image(str(image_path), caption="Agricultural emissions trend", width="stretch")
else:
    st.info("India emissions trend chart not found.")

st.divider()

# Yield prediction (separate module)
render_yield_prediction(BASE_DIR)

st.divider()
st.caption(
    "Academic prototype. NDVI zones are screening indicators; fertilizer emissions may be partial estimates; "
    "yield predictions need validation. Existing satellite imagery is not automatically matched to a selected farm."
)

# ==============================
# SMART FARM HEALTH & ACTION PLAN
# ==============================

import numpy as np

st.markdown("---")
st.markdown('<div id="cn-action-plan"></div>', unsafe_allow_html=True)
st.header("🌿 Smart Farm Health & Action Plan")
st.caption(
    "A vegetation screening indicator and practical next steps based on the "
    "available satellite data. This is not a crop diagnosis."
)

ndvi_candidates = [
    OUTPUT_DIR / "nawada_ndvi.tif",
    OUTPUT_DIR / "ndvi.tif",
]
ndvi_file = next((file for file in ndvi_candidates if file.exists()), None)

mean_ndvi = None
low_vegetation = None
data_note = ""

if ndvi_file:
    try:
        import rasterio

        with rasterio.open(ndvi_file) as src:
            ndvi_data = src.read(1, masked=True).astype("float32")
            valid = np.asarray(ndvi_data.compressed())
            valid = valid[np.isfinite(valid)]

        if valid.size:
            mean_ndvi = float(np.mean(valid))
            low_vegetation = float(np.mean(valid < 0.30) * 100)
        else:
            data_note = "The NDVI raster contains no valid pixels."
    except Exception as error:
        data_note = f"Could not read NDVI data: {type(error).__name__}"
else:
    data_note = "No supported NDVI raster was found in the outputs folder."

if mean_ndvi is not None:
    # Transparent, heuristic score based only on mean NDVI.
    # It is not a validated whole-farm health score.
    if mean_ndvi < 0.20:
        score, category = 35, "Low vegetation greenness"
    elif mean_ndvi < 0.30:
        score, category = 50, "Below-moderate vegetation greenness"
    elif mean_ndvi < 0.40:
        score, category = 65, "Moderate vegetation greenness"
    elif mean_ndvi < 0.50:
        score, category = 78, "Good vegetation greenness"
    else:
        score, category = 88, "High vegetation greenness"

    st.subheader("Farm vegetation snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Vegetation Screening Score", f"{score}/100")
    c2.metric("Mean NDVI", f"{mean_ndvi:.3f}")
    c3.metric("Pixels below NDVI 0.30", f"{low_vegetation:.1f}%")
    st.progress(score / 100)
    st.info(
        f"**Screening result: {category}.** NDVI measures vegetation greenness, "
        "not overall farm health. Scores are heuristic indicators, not validated diagnoses."
    )

    recommendations = []
    if low_vegetation >= 40:
        recommendations.append(
            "Inspect low-NDVI zones in the field. Check crop stage, soil moisture, "
            "weeds, pests and nutrient availability before choosing a treatment."
        )
    elif low_vegetation >= 20:
        recommendations.append(
            "Inspect lower-NDVI patches and compare them with healthier-looking "
            "areas before deciding whether intervention is needed."
        )
    else:
        recommendations.append(
            "Vegetation greenness is relatively consistent against the selected "
            "threshold. Continue monitoring and verify crop conditions in the field."
        )

    recommendations.append(
        "Do not apply extra fertilizer based on NDVI alone. Use soil testing, "
        "crop requirements and local agronomic advice."
    )
    recommendations.append(
        "Review fertilizer-emissions estimates separately. They are estimates and "
        "do not represent a complete measurement of farm carbon emissions."
    )

    st.subheader("Your farm action plan")
    st.markdown('<div class="cn-section-intro">Practical next steps based on the current vegetation screening. Confirm findings in the field before making farm-management decisions.</div>', unsafe_allow_html=True)
    from html import escape as html_escape
    for number, recommendation in enumerate(recommendations, 1):
        st.markdown(
            f'<div class="cn-action-card">'
            f'<div class="cn-action-number">{number:02d}</div>'
            f'<div><div class="cn-action-title">Recommended action</div>'
            f'<p class="cn-action-copy">{html_escape(recommendation)}</p></div></div>',
            unsafe_allow_html=True,
        )

    # Build the PDF in memory; no report file is written to the project directory.
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    pdf_buffer = BytesIO()
    pdf_doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Carbon Nova AI - Farm Action Plan",
        author="Carbon Nova AI",
    )

    pdf_styles = getSampleStyleSheet()
    pdf_styles.add(ParagraphStyle(
        name="CNTitle", parent=pdf_styles["Title"], fontName="Helvetica-Bold",
        fontSize=23, leading=28, textColor=colors.HexColor("#166534"),
        alignment=TA_LEFT, spaceAfter=6,
    ))
    pdf_styles.add(ParagraphStyle(
        name="CNSubtitle", parent=pdf_styles["Normal"], fontSize=10,
        leading=15, textColor=colors.HexColor("#64748b"), spaceAfter=18,
    ))
    pdf_styles.add(ParagraphStyle(
        name="CNHeading", parent=pdf_styles["Heading2"], fontSize=14,
        leading=18, textColor=colors.HexColor("#166534"),
        spaceBefore=14, spaceAfter=8,
    ))
    pdf_styles.add(ParagraphStyle(
        name="CNBody", parent=pdf_styles["BodyText"], fontSize=10,
        leading=15, spaceAfter=8,
    ))

    story = [
        Paragraph("CARBON NOVA AI", pdf_styles["CNTitle"]),
        Paragraph("Farm Health Screening &amp; Action Plan", pdf_styles["CNSubtitle"]),
    ]
    metrics_table = Table(
        [
            ["SCREENING SCORE", "MEAN NDVI", "LOW-NDVI PIXELS"],
            [f"{score}/100", f"{mean_ndvi:.3f}", f"{low_vegetation:.1f}%"],
        ],
        colWidths=[2.2 * inch] * 3,
    )
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14532d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0fdf4")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#166534")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1fae5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([
        metrics_table,
        Spacer(1, 14),
        Paragraph("Screening Assessment", pdf_styles["CNHeading"]),
        Paragraph(escape(category), pdf_styles["CNBody"]),
        Paragraph("Recommended Actions", pdf_styles["CNHeading"]),
    ])
    for number, recommendation in enumerate(recommendations, 1):
        story.append(Paragraph(
            f"<b>{number}.</b> {escape(recommendation)}",
            pdf_styles["CNBody"],
        ))
    story.extend([
        Spacer(1, 10),
        Paragraph("Limitations", pdf_styles["CNHeading"]),
        Paragraph(
            "This heuristic screening score uses mean NDVI only. NDVI indicates "
            "vegetation greenness and does not diagnose crop health or measure total "
            "farm sustainability. Verify findings with field inspection and appropriate "
            "agricultural measurements. Emissions estimates may not cover every source.",
            pdf_styles["CNBody"],
        ),
        Spacer(1, 12),
        Paragraph("Generated by Carbon Nova AI | Agricultural intelligence prototype",
                  pdf_styles["Italic"]),
    ])
    pdf_doc.build(story)
    pdf_bytes = pdf_buffer.getvalue()

    st.download_button(
        "⬇️ Download Farm Action Plan (PDF)",
        data=pdf_bytes,
        file_name="Carbon_Nova_Farm_Action_Plan.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
else:
    st.warning(data_note)
    st.caption(
        "Place your NDVI raster at outputs/ndvi.tif or "
        "outputs/nawada_ndvi.tif, then refresh the dashboard."
    )
