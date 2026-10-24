
from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "data" / "NUE_survey_dataset_v2.csv"
OUTPUT_DIR = ROOT / "outputs"


# Configurable factors; verify them before claiming validated results.
RICE_N2O_FACTOR = 0.004
N2O_TO_N2O_RATIO = 44 / 28
N2O_GWP100 = 273
DIESEL_FACTOR = 2.68
ELECTRICITY_FACTOR = 0.7117

DIESEL_COLUMNS = [
    "diesel_l",
    "diesel_litres",
    "diesel_liters",
    "diesel_consumption_l",
]

ELECTRICITY_COLUMNS = [
    "electricity_kwh",
    "electricity_consumption_kwh",
    "electricity_used_kwh",
]


def load_farm_data():
    """Load the dataset from the data folder."""
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE, low_memory=False)

    print("Dataset loaded successfully!")
    print("Total records:", len(df))
    print("Total columns:", len(df.columns))

    return df


def find_column(df, candidates):
    """Find a matching column without depending on capitalization."""
    column_lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        if candidate.lower() in column_lookup:
            return column_lookup[candidate.lower()]

    return None


def get_numeric_data(df, column):
    """Convert valid numbers and preserve missing values as NaN."""
    if column is None:
        return pd.Series(float("nan"), index=df.index)

    values = pd.to_numeric(df[column], errors="coerce")
    return values.where(values >= 0)


def calculate_fertilizer_emissions(nitrogen):
    """
    Estimate direct soil N2O emissions as kg CO2e.

    Assumes nitrogen is measured in kg N and the selected
    rice-specific emission factor applies to the records.
    """
    n2o_n = nitrogen * RICE_N2O_FACTOR
    n2o = n2o_n * N2O_TO_N2O_RATIO
    return n2o * N2O_GWP100


def run_carbon_engine():
    """Calculate available source estimates and save outputs."""
    df = load_farm_data()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Identify available activity-data columns.
    nitrogen_column = "Total_N" if "Total_N" in df.columns else None
    diesel_column = find_column(df, DIESEL_COLUMNS)
    electricity_column = find_column(df, ELECTRICITY_COLUMNS)

    nitrogen = get_numeric_data(df, nitrogen_column)
    diesel = get_numeric_data(df, diesel_column)
    electricity = get_numeric_data(df, electricity_column)

    results = pd.DataFrame(index=df.index)

    if "Merged_ID" in df.columns:
        results["record_id"] = df["Merged_ID"]
    else:
        results["record_id"] = [
            f"record_{i + 1}" for i in range(len(df))
        ]

    # Source-wise emissions.
    results["fertilizer_direct_soil_n2o_kgco2e_estimate"] = (
        calculate_fertilizer_emissions(nitrogen)
    )
    results["diesel_kgco2e_estimate"] = diesel * DIESEL_FACTOR
    results["electricity_kgco2e_estimate"] = (
        electricity * ELECTRICITY_FACTOR
    )

    source_columns = [
        "fertilizer_direct_soil_n2o_kgco2e_estimate",
        "diesel_kgco2e_estimate",
        "electricity_kgco2e_estimate",
    ]

    # Calculate a total only when every source is available.
    complete = results[source_columns].notna().all(axis=1)

    results["total_emissions_kgco2e"] = (
        results[source_columns].sum(axis=1, min_count=3)
    )

    results["total_emissions_status"] = complete.map({
        True: "complete_for_three_sources",
        False: "incomplete_missing_source_data",
    })

    # Save row-level results.
    output_csv = OUTPUT_DIR / "carbon_emissions_results.csv"
    results.to_csv(output_csv, index=False)

    # Summarize what the dataset actually contains.
    summary = {
        "records_processed": len(df),
        "input_columns": len(df.columns),
        "nitrogen_column_found": nitrogen_column,
        "diesel_column_found": diesel_column,
        "electricity_column_found": electricity_column,
        "records_with_nitrogen": int(nitrogen.notna().sum()),
        "records_with_diesel": int(diesel.notna().sum()),
        "records_with_electricity": int(electricity.notna().sum()),
        "records_with_complete_totals": int(complete.sum()),
        "records_with_incomplete_totals": int((~complete).sum()),
        "emission_factors": {
            "rice_n2o_factor": RICE_N2O_FACTOR,
            "n2o_to_n2o_ratio": N2O_TO_N2O_RATIO,
            "n2o_gwp100": N2O_GWP100,
            "diesel_kg_co2_per_litre": DIESEL_FACTOR,
            "electricity_kg_co2_per_kwh": ELECTRICITY_FACTOR,
        },
        "limitations": [
            "Verify Total_N units before interpreting fertilizer estimates.",
            "Verify that the rice-specific factor applies to these records.",
            "Diesel and electricity require actual activity measurements.",
            "Missing sources are not treated as zero.",
            "The fertilizer estimate covers direct soil N2O only.",
        ],
    }

    summary_file = OUTPUT_DIR / "carbon_emissions_summary.json"
    summary_file.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    # Plot only sources with available measurements.
    labels = []
    totals = []

    for label, column in [
        ("Fertilizer: direct soil N2O", source_columns[0]),
        ("Diesel", source_columns[1]),
        ("Electricity", source_columns[2]),
    ]:
        available = results[column].dropna()

        if not available.empty:
            labels.append(label)
            totals.append(available.sum())

    graph_file = OUTPUT_DIR / "carbon_emissions_by_source.png"

    if labels:
        plt.figure(figsize=(9, 5))
        plt.bar(labels, totals)
        plt.ylabel("Estimated emissions (kg CO2e)")
        plt.title("AgroFlux AI: Available Emission Estimates")
        plt.xticks(rotation=15, ha="right")
        plt.tight_layout()
        plt.savefig(graph_file, dpi=160)
        plt.close()
        print("Graph saved:", graph_file)
    else:
        print("No available source values for the graph.")

    print("\nCarbon engine finished.")
    print("Diesel column:", diesel_column or "NOT FOUND")
    print("Electricity column:", electricity_column or "NOT FOUND")
    print("Complete totals:", int(complete.sum()))
    print("Results CSV:", output_csv)
    print("Summary JSON:", summary_file)

    return results, summary


if __name__ == "__main__":
    run_carbon_engine()
