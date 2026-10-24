"""Train and evaluate a scikit-learn model from a labeled CSV."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def train_model(csv_path, target, task, model_out, test_size=0.2, random_state=42):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Training CSV not found: {csv_path}")
    if not 0.1 <= test_size <= 0.5:
        raise ValueError("test_size must be between 0.1 and 0.5")

    df = pd.read_csv(csv_path)
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' was not found in the CSV.")

    rows_before = len(df)
    df = df.dropna(subset=[target]).copy()
    if len(df) < 10:
        raise ValueError("At least 10 labeled rows are required for a basic train/test split.")

    y = df.pop(target)
    # Remove obvious identifier columns, but keep real predictive measurements.
    ignored = [
        c for c in df.columns
        if c.lower() in {"id", "farm_id", "farmer_name", "farm_name", "record_id"}
    ]
    X = df.drop(columns=ignored)

    if X.shape[1] == 0:
        raise ValueError("No usable feature columns remain after removing ID columns.")

    if task == "regression":
        y = pd.to_numeric(y, errors="coerce").replace([np.inf, -np.inf], np.nan)
        valid_rows = y.notna()
        X = X.loc[valid_rows].copy()
        y = y.loc[valid_rows].copy()
        if len(y) < 10:
            raise ValueError("Fewer than 10 rows have a valid numeric regression target.")
    elif task == "classification":
        if y.nunique() < 2:
            raise ValueError("Classification requires at least two target classes.")
    else:
        raise ValueError("task must be 'classification' or 'regression'.")

    # Clean infinite numeric inputs; pipeline imputers handle missing values.
    X = X.replace([np.inf, -np.inf], np.nan)
    numeric_cols = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [c for c in X.columns if c not in numeric_cols]

    transformers = []
    if numeric_cols:
        transformers.append((
            "numeric",
            Pipeline([("imputer", SimpleImputer(strategy="median"))]),
            numeric_cols,
        ))
    if categorical_cols:
        transformers.append((
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical_cols,
        ))
    if not transformers:
        raise ValueError("No numeric or categorical input features were found.")

    preprocessor = ColumnTransformer(transformers)

    if task == "classification":
        estimator = RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=random_state, n_jobs=-1
        )
    else:
        estimator = RandomForestRegressor(
            n_estimators=200, random_state=random_state, n_jobs=-1
        )

    stratify = y if task == "classification" and y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    pipeline = Pipeline([("preprocessor", preprocessor), ("model", estimator)])
    pipeline.fit(X_train, y_train)
    predictions = pipeline.predict(X_test)

    if task == "classification":
        metrics = {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "classification_report": classification_report(
                y_test, predictions, output_dict=True, zero_division=0
            ),
        }
    else:
        mse = mean_squared_error(y_test, predictions)
        metrics = {
            "mae": float(mean_absolute_error(y_test, predictions)),
            "rmse": float(mse ** 0.5),
            "r2": float(r2_score(y_test, predictions)),
        }

    model_out = Path(model_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    warning = (
        "Baseline metrics need validation. Random row splits may overestimate performance "
        "when nearby or related farms appear in both train and test sets."
    )
    artifact = {
        "pipeline": pipeline,
        "task": task,
        "target": target,
        "features": X.columns.tolist(),
        "metrics": metrics,
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "source_rows": int(rows_before),
        "usable_labeled_rows": int(len(X)),
        "warning": warning,
    }
    joblib.dump(artifact, model_out, compress=3)

    return {
        "model_path": str(model_out),
        "task": task,
        "target": target,
        "features": X.columns.tolist(),
        "source_rows": int(rows_before),
        "usable_labeled_rows": int(len(X)),
        "dropped_or_invalid_target_rows": int(rows_before - len(X)),
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "metrics": metrics,
        "warning": warning,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="CSV with features and a real labeled target")
    parser.add_argument("--target", required=True, help="Target column to predict")
    parser.add_argument("--task", choices=["classification", "regression"], required=True)
    parser.add_argument("--model-out", default="models/agroflux_model.joblib")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    result = train_model(args.csv, args.target, args.task, args.model_out, args.test_size)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
