"""AgroFlux AI Streamlit dashboard."""

import json
import math
import os
import hmac
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

st.set_page_config(page_title="AgroFlux AI", page_icon="🌱", layout="wide")


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
.stApp { background: linear-gradient(135deg, #07110d 0%, #0b1d15 55%, #10291c 100%); color: #e6f4ea; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1450px; }
h1, h2, h3 { color: #e6f4ea !important; letter-spacing: -0.5px; }
h1 { font-size: 2.5rem !important; }
[data-testid="stMetric"] { background: linear-gradient(145deg, #11291d, #0b1c14); padding: 20px; border-radius: 16px; border: 1px solid #24583a; box-shadow: 0 0 18px rgba(46, 204, 113, 0.09); }
[data-testid="stMetricLabel"] { color: #a8c9b3 !important; }
[data-testid="stMetricValue"] { color: #55ed9b !important; font-weight: 700; }
[data-testid="stSidebar"] { background: #08150f; border-right: 1px solid #1e4930; }
[data-testid="stSidebar"] * { color: #e0f0e5; }
.stTextInput input, .stNumberInput input { background-color: #10251a; color: #e6f4ea; border: 1px solid #326746; border-radius: 9px; }
.stButton > button { background: linear-gradient(90deg, #147a45, #20b765); color: white; border: 1px solid #38d982; border-radius: 10px; padding: 0.55rem 1.2rem; font-weight: 700; }
.stButton > button:hover { background: #26c971; color: #06140b; border-color: #55ed9b; }
[data-testid="stDataFrame"] { border: 1px solid #24583a; border-radius: 12px; overflow: hidden; }
hr { border-color: #244a33; }
[data-testid="stImage"] img { border-radius: 12px; border: 1px solid #244a33; }
</style>
""", unsafe_allow_html=True)

st.title("🌱 AgroFlux AI")
st.caption("Agricultural yield, fertilizer and vegetation intelligence prototype")


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

# 1. Satellite vegetation analysis
st.header("🛰️ Satellite Vegetation Analysis — Nawada AOI")
ndvi_path = OUTPUT_DIR / "nawada_ndvi.tif"
if ndvi_path.exists():
    try:
        import numpy as np
        import rasterio

        with rasterio.open(ndvi_path) as src:
            ndvi = src.read(1, masked=True)
            valid = ndvi.compressed()
            valid = valid[np.isfinite(valid)]

        if len(valid):
            c1, c2, c3 = st.columns(3)
            c1.metric("Valid pixels", f"{len(valid):,}")
            c2.metric("Mean NDVI", f"{float(np.mean(valid)):.4f}")
            c3.metric("Pixels below 0.30", f"{float(np.mean(valid < 0.30) * 100):.2f}%")
            st.caption("NDVI below 0.30 is a rough screening threshold, not a diagnosis. This raster covers the approximate Nawada area of interest (AOI); it has not yet been clipped to the exact district boundary.")
        else:
            st.warning("No valid NDVI pixels found.")
    except Exception as error:
        st.warning(f"Could not read NDVI raster: {error}")
else:
    st.info("NDVI raster not found. Run the satellite analysis first.")

col1, col2 = st.columns(2)
for container, filename, caption in [
    (col1, "vegetation_zones.png", "Nawada AOI Vegetation Zones"),
    (col2, "vegetation_percentage.png", "Nawada AOI Vegetation Distribution"),
]:
    with container:
        image_path = OUTPUT_DIR / filename
        if image_path.exists():
            st.image(str(image_path), caption=caption, width="stretch")
        else:
            st.caption(f"{filename} not found.")

st.divider()

# 2. Fertilizer emission estimates
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

# 4.5 Manual farm-emissions scenario calculator
st.subheader("🧮 Farm Emissions Scenario Calculator")
st.caption(
    "The survey files do not contain verified diesel-litre and electricity-kWh quantities. "
    "Enter activity data for one farm below to calculate a separate scenario estimate; "
    "these values are not pulled from the survey dataset."
)

with st.form("farm_emissions_scenario_form"):
    st.write("Enter total seasonal activity for one farm. If a source was genuinely unused, enter 0; leave nothing blank.")
    f1, f2 = st.columns(2)
    with f1:
        scenario_area_ha_text = st.text_input("Farm area (hectares)", placeholder="e.g. 1.2")
        scenario_urea_kg_text = st.text_input("Urea used (kg)", placeholder="e.g. 80")
        scenario_dap_kg_text = st.text_input("DAP used (kg)", placeholder="e.g. 25")
    with f2:
        scenario_diesel_l_text = st.text_input("Diesel consumed (litres)", placeholder="e.g. 35")
        scenario_electricity_kwh_text = st.text_input("Grid electricity consumed (kWh)", placeholder="e.g. 120")
        st.caption("Factors used: diesel 2.68 kg CO₂/L; Indian grid electricity 0.710 kg CO₂/kWh (CEA FY 2024–25).")
    calculate_scenario = st.form_submit_button("Calculate Scenario Estimate")

if calculate_scenario:
    raw_inputs = {
        "farm area (hectares)": scenario_area_ha_text,
        "urea (kg)": scenario_urea_kg_text,
        "DAP (kg)": scenario_dap_kg_text,
        "diesel (litres)": scenario_diesel_l_text,
        "electricity (kWh)": scenario_electricity_kwh_text,
    }
    parsed = {}
    bad_inputs = []
    for label, raw in raw_inputs.items():
        try:
            value = float(raw)
            if not math.isfinite(value) or value < 0:
                bad_inputs.append(label)
            else:
                parsed[label] = value
        except (TypeError, ValueError):
            bad_inputs.append(label)

    if bad_inputs:
        st.error("Enter a valid non-negative number for: " + ", ".join(bad_inputs) + ". Unknown usage must not be entered as zero.")
    elif parsed["farm area (hectares)"] <= 0:
        st.error("Farm area must be greater than zero.")
    else:
        # Illustrative screening factors. Urea assumes 46% N; DAP assumes 18% N.
        # Direct N2O-N factor = 0.01 kg N2O-N per kg N; GWP100 N2O = 273.
        urea_kg = parsed["urea (kg)"]
        dap_kg = parsed["DAP (kg)"]
        diesel_l = parsed["diesel (litres)"]
        electricity_kwh = parsed["electricity (kWh)"]
        area_ha = parsed["farm area (hectares)"]

        urea_application_co2 = urea_kg * (0.20 * 44.0 / 12.0)
        nitrogen_kg = urea_kg * 0.46 + dap_kg * 0.18
        direct_n2o_co2e = nitrogen_kg * 0.01 * (44.0 / 28.0) * 273.0
        diesel_co2 = diesel_l * 2.68
        electricity_co2 = electricity_kwh * 0.710
        total_kg_co2e = urea_application_co2 + direct_n2o_co2e + diesel_co2 + electricity_co2

        c1, c2, c3 = st.columns(3)
        c1.metric("Scenario emissions", f"{total_kg_co2e:,.1f} kg CO₂e")
        c2.metric("Per hectare", f"{total_kg_co2e / area_ha:,.1f} kg CO₂e/ha")
        c3.metric("Nitrogen applied", f"{nitrogen_kg:,.1f} kg N")

        components = pd.DataFrame([
            {"Source": "Urea application CO₂", "Estimated emissions (kg CO₂e)": urea_application_co2},
            {"Source": "Direct soil N₂O from Urea + DAP nitrogen", "Estimated emissions (kg CO₂e)": direct_n2o_co2e},
            {"Source": "Diesel combustion", "Estimated emissions (kg CO₂e)": diesel_co2},
            {"Source": "Grid electricity", "Estimated emissions (kg CO₂e)": electricity_co2},
        ])
        st.dataframe(components, width="stretch", hide_index=True)
        st.warning(
            "This is a manual-input screening estimate, not a dataset-observed farm total. "
            "It covers only urea application CO₂, direct soil N₂O from Urea/DAP nitrogen, diesel combustion, "
            "and grid electricity. It excludes rice-paddy methane, fertilizer manufacture, other fertilizers, "
            "indirect N₂O and other farm activities; therefore it is not a complete lifecycle carbon footprint."
        )
        st.caption(
            "Emission-factor references: CEA, CO₂ Baseline Database for the Indian Power Sector, Version 21.0 (FY 2024–25 grid average: 0.710 tCO₂/MWh): "
            "https://cea.nic.in/wp-content/uploads/baseline/2025/12/User_Guide_V_21.0.pdf ; "
            "diesel direct CO₂ factor approximation: 2.68 kg CO₂/L as referenced in Indian government documentation."
        )

# National trend chart
st.header("🇮🇳 India Agricultural Emissions Trend")
image_path = OUTPUT_DIR / "india_emissions_trends.png"
if image_path.exists():
    st.image(str(image_path), caption="Agricultural emissions trend", width="stretch")
else:
    st.info("India emissions trend chart not found.")

st.divider()

# 4. Yield prediction
st.header("🤖 ML Yield Prediction")
st.caption("Runs the saved model with a synthetic demo input. This is not a real farmer record.")

model_candidates = [MODEL_DIR / "rice_yield_model.joblib", MODEL_DIR / "yield_model.joblib"]
model_path = next((path for path in model_candidates if path.exists()), None)
input_path = DATA_DIR / "prediction_input.example.json"

if model_path is None:
    st.error("Yield model not found. Expected models/rice_yield_model.joblib. Train the model first.")
elif not input_path.exists():
    st.error("Synthetic demo input not found: data/prediction_input.example.json")
else:
    st.caption(f"Model file: {model_path.name}")
    st.caption(f"Input file: {input_path.name}")
    if st.button("Run Yield Prediction", key="run_yield_prediction"):
        try:
            # Call the same function as the CLI. This avoids subprocess path/stdout issues.
            from ml_engine.predict import predict_records

            with st.spinner("Running yield prediction..."):
                prediction = predict_records(model_path, input_path)

            results = prediction.get("results", [])
            if not results:
                st.warning("Prediction ran but returned no results.")
            else:
                for item in results:
                    value = item.get("prediction")
                    if isinstance(value, (int, float)) and "yield" in prediction.get("target", "").lower():
                        st.metric(f"Predicted yield — row {item.get('row', 0)}", f"{value:.2f} tonnes/hectare")
                    else:
                        st.metric(f"Prediction — row {item.get('row', 0)}", str(value))

                metrics = prediction.get("metrics", {})
                if metrics:
                    st.subheader("Model test metrics")
                    metric_cols = st.columns(min(3, len(metrics)))
                    for column, (name, value) in zip(metric_cols, metrics.items()):
                        if isinstance(value, (int, float)):
                            column.metric(name.upper(), f"{value:.3f}")
                st.info(prediction.get("warning", "Validate predictions before real-world use."))
                with st.expander("Prediction details"):
                    st.json(prediction)
        except Exception as error:
            st.error(f"Prediction failed: {error}")
            st.caption("Check the model file and the synthetic data/prediction_input.example.json feature names.")

st.divider()
st.caption(
    "Academic prototype. NDVI zones are screening indicators; fertilizer emissions may be partial estimates; "
    "yield predictions need validation. Existing satellite imagery is not automatically matched to a selected farm."
)
