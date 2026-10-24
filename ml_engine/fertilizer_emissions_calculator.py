"""
AgroFlux AI - Fertilizer Emissions Calculator
Processes the cleaned CIMMYT fertilizer survey CSV, including 50,000+ rows.

Important:
- This calculates estimates for supported fertilizer types only.
- It is not a trained ML model or a complete farm carbon footprint.
- Unsupported fertilizer types are left uncalculated, never treated as zero emissions.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "outputs" / "fertilizer_cleaned.csv"
OUTPUT_FILE = ROOT / "outputs" / "fertilizer_emissions_estimated.csv"
SUMMARY_FILE = ROOT / "outputs" / "fertilizer_emissions_summary.csv"
GRAPH_FILE = ROOT / "outputs" / "fertilizer_emissions_by_type.png"

# Approximate nitrogen mass fractions by common fertilizer product.
# Only map products when the product identity is sufficiently clear.
NITROGEN_FRACTION = {
    "urea": 0.46,  # 46% nitrogen by mass
    "dap": 0.18,   # standard DAP grade 18-46-0: 18% nitrogen by mass
}

# IPCC Tier 1-style defaults / stated conversion choices:
DIRECT_N2O_N_PER_N = 0.010  # kg N2O-N per kg N added (aggregated default)
N2O_TO_N2O_N = 44 / 28
N2O_GWP100 = 273  # IPCC AR6 100-year GWP
UREA_C_TO_CO2 = 44 / 12
UREA_C_FRACTION = 0.20  # kg C per kg urea, IPCC default

def normalize_fertilizer_name(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().split())

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input not found: {INPUT_FILE}\n"
            "Run prepare_fertilizer_data.py first so fertilizer_cleaned.csv exists."
        )

    # Read the file once. Pandas vectorized calculations are suitable for 50,000 rows.
    df = pd.read_csv(INPUT_FILE)

    required = {"Chem_fert_nm_kh", "quantity_kg", "conversion_status"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    df["fertilizer_name_normalized"] = df["Chem_fert_nm_kh"].map(normalize_fertilizer_name)
    df["nitrogen_fraction"] = df["fertilizer_name_normalized"].map(NITROGEN_FRACTION)

    quantity = pd.to_numeric(df["quantity_kg"], errors="coerce")
    valid_quantity = quantity.notna() & (quantity >= 0)
    converted = df["conversion_status"].astype(str).str.lower().eq("converted")
    supported = df["nitrogen_fraction"].notna() & valid_quantity & converted

    # Default to missing values. Unsupported records must not look like zero emissions.
    df["nitrogen_kg_estimated"] = pd.NA
    df["direct_n2o_kg_co2e_estimated"] = pd.NA
    df["urea_application_co2_kg_estimated"] = pd.NA
    df["fertilizer_emissions_kg_co2e_estimated"] = pd.NA
    df["calculation_status"] = "unsupported_fertilizer_or_invalid_quantity"

    # Nitrogen-derived direct soil N2O estimate for supported products.
    n_kg = quantity.loc[supported] * df.loc[supported, "nitrogen_fraction"]
    direct_n2o_co2e = n_kg * DIRECT_N2O_N_PER_N * N2O_TO_N2O_N * N2O_GWP100

    df.loc[supported, "nitrogen_kg_estimated"] = n_kg
    df.loc[supported, "direct_n2o_kg_co2e_estimated"] = direct_n2o_co2e

    # CO2 from urea carbon is a separate source; do not apply it to DAP.
    is_urea = supported & df["fertilizer_name_normalized"].eq("urea")
    urea_co2 = quantity.loc[is_urea] * UREA_C_FRACTION * UREA_C_TO_CO2
    df.loc[is_urea, "urea_application_co2_kg_estimated"] = urea_co2

    # For supported non-urea products, the urea-specific CO2 component is zero;
    # this is not a claim that their full lifecycle emissions are zero.
    is_supported_non_urea = supported & ~df["fertilizer_name_normalized"].eq("urea")
    df.loc[is_supported_non_urea, "urea_application_co2_kg_estimated"] = 0.0

    df.loc[supported, "fertilizer_emissions_kg_co2e_estimated"] = (
        df.loc[supported, "direct_n2o_kg_co2e_estimated"].astype(float)
        + df.loc[supported, "urea_application_co2_kg_estimated"].astype(float)
    )
    df.loc[supported, "calculation_status"] = "estimated_ipcc_default_factors"

    # Keep every source record in the detailed output for auditability.
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    # Summary includes only rows where a calculation was actually made.
    valid = df.loc[supported].copy()
    if not valid.empty:
        summary = (
            valid.groupby("Chem_fert_nm_kh", dropna=False)
            .agg(
                records_calculated=("fertilizer_emissions_kg_co2e_estimated", "count"),
                fertilizer_quantity_kg=("quantity_kg", "sum"),
                nitrogen_kg_estimated=("nitrogen_kg_estimated", "sum"),
                direct_n2o_kg_co2e_estimated=("direct_n2o_kg_co2e_estimated", "sum"),
                urea_application_co2_kg_estimated=("urea_application_co2_kg_estimated", "sum"),
                fertilizer_emissions_kg_co2e_estimated=("fertilizer_emissions_kg_co2e_estimated", "sum"),
            )
            .reset_index()
        )
    else:
        summary = pd.DataFrame(columns=[
            "Chem_fert_nm_kh", "records_calculated", "fertilizer_quantity_kg",
            "nitrogen_kg_estimated", "direct_n2o_kg_co2e_estimated",
            "urea_application_co2_kg_estimated", "fertilizer_emissions_kg_co2e_estimated"
        ])
    summary.to_csv(SUMMARY_FILE, index=False)

    # Optional visualization. If matplotlib is unavailable, the CSV results are still saved.
    if not summary.empty:
        try:
            import matplotlib.pyplot as plt
            chart_data = summary.sort_values(
                "fertilizer_emissions_kg_co2e_estimated", ascending=False
            )
            plt.figure(figsize=(9, 5))
            plt.bar(
                chart_data["Chem_fert_nm_kh"].astype(str),
                chart_data["fertilizer_emissions_kg_co2e_estimated"].astype(float),
            )
            plt.xlabel("Fertilizer type")
            plt.ylabel("Estimated emissions (kg CO2e)")
            plt.title("Estimated fertilizer-related emissions by supported type")
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            plt.savefig(GRAPH_FILE, dpi=150)
            plt.close()
            print(f"Graph: {GRAPH_FILE}")
        except ImportError:
            print("Graph skipped: matplotlib is not installed. CSV outputs were still saved.")

    print(f"Input rows: {len(df):,}")
    print(f"Rows with estimates: {int(supported.sum()):,}")
    print(f"Rows not calculated: {int((~supported).sum()):,}")
    print(f"Detailed results: {OUTPUT_FILE}")
    print(f"Fertilizer summary: {SUMMARY_FILE}")
    print("\nIMPORTANT: These are partial estimates using default factors, not validated predictions")
    print("or a complete farm carbon footprint. Review unsupported fertilizer names before reporting.")

if __name__ == "__main__":
    main()
