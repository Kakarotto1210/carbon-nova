
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent

input_file = ROOT / "Emissions_Agriculture_Energy_E_All_Data_(Normalized).csv"
output_csv = ROOT / "outputs" / "india_emissions_trends.csv"
output_png = ROOT / "outputs" / "india_emissions_trends.png"

df = pd.read_csv(input_file, encoding="latin1")

# Select India's total-energy emissions, avoiding double-counting
india = df[
    (df["Area"].astype(str).str.strip() == "India")
    & (df["Item"] == "Total Energy")
    & (df["Element"].astype(str).str.startswith("Emissions"))
].copy()

if india.empty:
    raise ValueError("No matching India Total Energy emissions records found.")

# Keep only the columns needed for the graph
india = india[["Year", "Element", "Unit", "Value"]]
india["Value"] = pd.to_numeric(india["Value"], errors="coerce")
india = india.dropna(subset=["Year", "Value"])

# Save the filtered historical data
india.to_csv(output_csv, index=False)

# Arrange the data so each gas becomes a separate line
chart_data = india.pivot_table(
    index="Year",
    columns="Element",
    values="Value",
    aggfunc="first"
).sort_index()

chart_data.plot(figsize=(10, 5), marker=".")
plt.title("India: Agricultural Energy-Related Emissions")
plt.xlabel("Year")
plt.ylabel("Emissions (kilotonnes)")
plt.grid(True, alpha=0.3)
plt.legend(title="Gas")
plt.tight_layout()
plt.savefig(output_png, dpi=150)
plt.close()

print("Records saved:", len(india))
print("Year range:", int(india["Year"].min()), "-", int(india["Year"].max()))
print("CSV saved:", output_csv)
print("Graph saved:", output_png)