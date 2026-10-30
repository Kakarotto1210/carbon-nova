# Carbon Nova AI — Satellite Engine + ML Engine

This package contains **only** the two engines requested. No frontend, Flask API, or database.

## Folder structure
- `satellite_engine/ndvi.py` — calculate NDVI from real red/NIR raster bands and summarize vegetation health.
- `ml_engine/train.py` — train/evaluate/save a model from a labeled CSV dataset.
- `ml_engine/predict.py` — load a saved model and predict on new farm records.
- `requirements.txt` — dependencies.

## Setup
Use Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 1) Satellite engine: NDVI from GeoTIFF files

You need actual satellite imagery with separate **Red** and **Near Infrared (NIR)** bands, aligned to the same grid.
For Landsat 8/9 surface-reflectance products, Red is commonly band 4 and NIR band 5; for Sentinel-2, Red is commonly B04 and NIR B08. Confirm the product and scaling/quality-mask requirements before use.

```bash
python -m satellite_engine.ndvi --red data/red.tif --nir data/nir.tif --out outputs/ndvi.tif
```

The script writes an NDVI GeoTIFF and prints summary statistics. It masks invalid/no-data pixels. It does **not** download imagery, identify farm boundaries, apply cloud masks, or automatically correct satellite scaling.

NDVI formula:
`NDVI = (NIR - Red) / (NIR + Red)`

The NDVI thresholds in the code are only rough screening categories, not universal agronomic diagnoses. Crop, growth stage, sensor, and local calibration matter.

## 2) ML engine: train using labeled data

The ML model needs a CSV containing measured input features and a **real labeled target**. Do not train on invented labels or use NDVI alone as proof of crop stress/yield.

Example command:
```bash
python -m ml_engine.train --csv data/farm_training.csv --target crop_stress --task classification --model-out models/crop_stress.joblib
```

For a numeric target such as measured yield:
```bash
python -m ml_engine.train --csv data/farm_training.csv --target yield_t_ha --task regression --model-out models/yield.joblib
```

- Classification targets should be category labels (e.g. `low`, `moderate`, `high`) verified by ground observations.
- Regression targets should be numeric measurements (e.g. measured yield in tonnes/hectare).
- Do not include IDs, names, post-outcome information, or target-derived columns as features.
- The trainer uses a held-out test split and saves the fitted preprocessing + model pipeline.

## 3) Make predictions

Create a JSON file containing a list of records whose feature columns match the training CSV:
```json
[
  {"ndvi_mean": 0.62, "rainfall_mm": 18.0, "temperature_c": 29.0, "soil_moisture": 0.24}
]
```

Then run:
```bash
python -m ml_engine.predict --model models/crop_stress.joblib --input data/new_farms.json
```

The example feature names are illustrative only. Use the exact features in your own training CSV.

## Important
This starter does not ship a trained model or real labeled dataset. Training and prediction will only be meaningful after you provide representative, validated data for your target crops and region. The satellite engine computes NDVI only when supplied real, compatible red/NIR rasters.
