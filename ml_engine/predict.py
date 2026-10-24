"""Run predictions from a saved AgroFlux ML pipeline."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def predict_records(model_path, input_path):
    model_path = Path(model_path)
    input_path = Path(input_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not input_path.exists():
        raise FileNotFoundError(f"Prediction input not found: {input_path}")

    artifact = joblib.load(model_path)
    records = json.loads(input_path.read_text(encoding="utf-8-sig"))
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list) or not records:
        raise ValueError("Input JSON must be an object or a non-empty list of objects.")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("Every item in the input JSON list must be an object.")

    expected = artifact["features"]
    frame = pd.DataFrame(records)
    missing = [column for column in expected if column not in frame.columns]
    if missing:
        raise ValueError(
            "Input JSON is missing features required by this model: " + ", ".join(missing)
        )

    # Model imputers handle missing values; replace infinite values with missing first.
    features = frame[expected].replace([np.inf, -np.inf], np.nan)
    predictions = artifact["pipeline"].predict(features)

    results = []
    for index, value in enumerate(predictions):
        item = {
            "row": index,
            "prediction": value.item() if hasattr(value, "item") else value,
        }
        if artifact["task"] == "classification" and hasattr(artifact["pipeline"], "predict_proba"):
            probabilities = artifact["pipeline"].predict_proba(features.iloc[[index]])[0]
            classes = artifact["pipeline"].named_steps["model"].classes_
            item["class_probabilities"] = {
                str(label): float(prob) for label, prob in zip(classes, probabilities)
            }
        results.append(item)

    return {
        "task": artifact["task"],
        "target": artifact["target"],
        "results": results,
        "metrics": artifact.get("metrics", {}),
        "warning": artifact.get(
            "warning", "Validate model performance before operational use."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to model artifact .joblib")
    parser.add_argument("--input", required=True, help="JSON file with feature records")
    args = parser.parse_args()
    print(json.dumps(predict_records(args.model, args.input), indent=2, default=str))


if __name__ == "__main__":
    main()
