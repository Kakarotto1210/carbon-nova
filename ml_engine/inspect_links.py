

from pathlib import Path
import csv
import math

ROOT = Path(__file__).resolve().parent.parent

input_file = ROOT / "data" / "CSISA_IND_LDS_Rice_2018_Data.csv"
output_file = ROOT / "outputs" / "rice_cleaned.csv"

ACRE_TO_HECTARE = 0.40468564224

# Fertilizer selection field, DAP quantity field, Urea quantity field
stages = [
    ("F-basalFerts", "F-q5202_basalDAP", "F-q5204_basalUrea"),
    ("F-firstTopDressFert", "F-q5212_1tdDAP", "F-q5216_1tdUrea"),
    ("F-secondTopDressFert", "F-q5233_2tdDAP", "F-q5237_2tdUrea"),
    ("F-thirdTopDressFert", "F-q5253_3tdDAP", "F-q5257_3tdUrea"),
]


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def stage_amount(row, selector_index, amount_index, fertilizer):
    raw_amount = row[amount_index].strip()

    # A recorded quantity takes priority.
    if raw_amount:
        return number(raw_amount)

    selected_value = row[selector_index].strip().lower()

    # A blank selection is unknown, not zero.
    if not selected_value:
        return None

    # Only explicit no-fertilizer responses count as zero.
    if selected_value in {
        "none", "no", "no fertilizer", "not applied", "not used"
    }:
        return 0.0

    # Handle common separators in multiple-selection answers.
    for separator in [",", ";", "/", "|", "+"]:
        selected_value = selected_value.replace(separator, " ")

    selected = selected_value.split()

    # Selected but quantity missing: keep it unknown.
    if fertilizer.lower() in selected:
        return None

    # Another fertilizer was selected at this stage.
    return 0.0


def total_for_fertilizer(row, indexes, fertilizer_position, fertilizer):
    values = []

    for selector, dap_column, urea_column in stages:
        if fertilizer_position == "DAP":
            amount_column = dap_column
        else:
            amount_column = urea_column

        amount = stage_amount(
            row,
            indexes[selector],
            indexes[amount_column],
            fertilizer,
        )

        if amount is None or amount < 0:
            return None

        values.append(amount)

    return sum(values)


if not input_file.exists():
    raise FileNotFoundError(f"Input file not found: {input_file}")

output_file.parent.mkdir(parents=True, exist_ok=True)

with input_file.open(
    "r", newline="", encoding="utf-8-sig"
) as source:

    reader = csv.reader(source)
    headers = next(reader)

    required = {
        "A-q102_state",
        "C-q306_cropLarestAreaAcre",
        "L-tonPerHectare",
        "O-largestPlotGPS-Accuracy",
    }

    for selector, dap_column, urea_column in stages:
        required.update([selector, dap_column, urea_column])

    missing = required - set(headers)
    if missing:
        raise ValueError(f"Required columns missing: {sorted(missing)}")

    indexes = {name: headers.index(name) for name in required}

    # These CSV columns have blank headers; positions were checked
    # during the previous dataset audit.
    latitude_index = 214
    longitude_index = 215

    if len(headers) <= longitude_index:
        raise ValueError("Coordinate columns were not found.")

    if headers[latitude_index].strip() or headers[longitude_index].strip():
        raise ValueError("Coordinate positions changed; recheck the CSV.")

    output_headers = [
        "state",
        "plot_area_acres",
        "plot_area_hectares",
        "urea_kg_per_plot",
        "dap_kg_per_plot",
        "urea_kg_per_ha",
        "dap_kg_per_ha",
        "urea_dap_product_kg_per_ha",
        "yield_ton_per_hectare",
        "latitude",
        "longitude",
        "gps_accuracy_m",
        "fertilizer_rate_status",
    ]

    total_rows = 0
    complete_rates = 0
    incomplete_rows = 0
    coordinate_rows = 0

    with output_file.open(
        "w", newline="", encoding="utf-8-sig"
    ) as target:

        writer = csv.DictWriter(target, fieldnames=output_headers)
        writer.writeheader()

        for row in reader:
            if not row or all(not value.strip() for value in row):
                continue

            area_acres = number(
                row[indexes["C-q306_cropLarestAreaAcre"]]
            )

            area_hectares = (
                area_acres * ACRE_TO_HECTARE
                if area_acres is not None and area_acres > 0
                else None
            )

            urea_plot = total_for_fertilizer(
                row, indexes, "Urea", "Urea"
            )
            dap_plot = total_for_fertilizer(
                row, indexes, "DAP", "DAP"
            )

            urea_rate = (
                urea_plot / area_hectares
                if urea_plot is not None and area_hectares
                else None
            )

            dap_rate = (
                dap_plot / area_hectares
                if dap_plot is not None and area_hectares
                else None
            )

            combined_rate = (
                urea_rate + dap_rate
                if urea_rate is not None and dap_rate is not None
                else None
            )

            if area_hectares is None:
                status = "invalid_plot_area"
            elif urea_plot is None or dap_plot is None:
                status = "fertilizer_amount_unknown"
                incomplete_rows += 1
            else:
                status = "complete_urea_dap_only"
                complete_rates += 1

            latitude = row[latitude_index].strip()
            longitude = row[longitude_index].strip()

            if number(latitude) is not None and number(longitude) is not None:
                coordinate_rows += 1

            writer.writerow({
                "state": row[indexes["A-q102_state"]].strip(),
                "plot_area_acres": area_acres,
                "plot_area_hectares": area_hectares,
                "urea_kg_per_plot": urea_plot,
                "dap_kg_per_plot": dap_plot,
                "urea_kg_per_ha": urea_rate,
                "dap_kg_per_ha": dap_rate,
                "urea_dap_product_kg_per_ha": combined_rate,
                "yield_ton_per_hectare":
                    row[indexes["L-tonPerHectare"]].strip(),
                "latitude": latitude,
                "longitude": longitude,
                "gps_accuracy_m":
                    row[indexes["O-largestPlotGPS-Accuracy"]].strip(),
                "fertilizer_rate_status": status,
            })

            total_rows += 1

print("\nFERTILIZER RATE CALCULATION COMPLETE")
print("Rows processed:", total_rows)
print("Rows with complete Urea/DAP rates:", complete_rates)
print("Rows with unknown fertilizer quantities:", incomplete_rows)
print("Rows with coordinates:", coordinate_rows)
print("Output:", output_file)
print("Only Urea and DAP are included.")
print("Original source CSV was not modified.")
