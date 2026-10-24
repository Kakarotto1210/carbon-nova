"""NDVI calculation from aligned Red and NIR GeoTIFF rasters."""

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio


def calculate_ndvi(red_path, nir_path, output_path=None):
    """
    Calculate NDVI from two aligned single-band GeoTIFFs.

    Input rasters must represent comparable Red and NIR reflectance values,
    use the same CRS/grid/resolution, and have appropriate cloud/invalid pixels
    masked before interpreting results.
    """
    red_path, nir_path = Path(red_path), Path(nir_path)

    with rasterio.open(red_path) as red_src, rasterio.open(nir_path) as nir_src:
        if red_src.count < 1 or nir_src.count < 1:
            raise ValueError("Both files must contain at least one raster band.")
        if red_src.width != nir_src.width or red_src.height != nir_src.height:
            raise ValueError("Red and NIR rasters must have the same dimensions.")
        if red_src.transform != nir_src.transform or red_src.crs != nir_src.crs:
            raise ValueError("Red and NIR rasters must have the same grid and CRS.")

        red = red_src.read(1, masked=True).astype("float32")
        nir = nir_src.read(1, masked=True).astype("float32")
        profile = red_src.profile.copy()

    invalid = np.ma.getmaskarray(red) | np.ma.getmaskarray(nir)
    red_data = np.asarray(red.filled(np.nan), dtype="float32")
    nir_data = np.asarray(nir.filled(np.nan), dtype="float32")
    denominator = nir_data + red_data

    invalid |= ~np.isfinite(red_data) | ~np.isfinite(nir_data)
    invalid |= np.isclose(denominator, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi_data = (nir_data - red_data) / denominator

    invalid |= ~np.isfinite(ndvi_data)
    ndvi_data = np.clip(ndvi_data, -1.0, 1.0).astype("float32")
    ndvi_data[invalid] = -9999.0

    valid = ndvi_data[~invalid]
    if valid.size == 0:
        raise ValueError("No valid pixels remain. Check nodata values and input rasters.")

    summary = {
        "valid_pixel_count": int(valid.size),
        "mean_ndvi": float(np.mean(valid)),
        "median_ndvi": float(np.median(valid)),
        "min_ndvi": float(np.min(valid)),
        "max_ndvi": float(np.max(valid)),
        "low_vegetation_pixel_percent": float(np.mean(valid < 0.30) * 100.0),
        "threshold_note": "NDVI < 0.30 is a rough screening threshold, not a diagnosis.",
    }
    if output_path:
        profile.update(
            driver="GTiff",
            count=1,
            dtype="float32",
            nodata=-9999.0,
            compress="deflate",
        )
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(ndvi_data, 1)
        summary["output_raster"] = str(output_path)

    return ndvi_data, summary


def main():
    parser = argparse.ArgumentParser(description="Calculate NDVI from Red/NIR GeoTIFFs.")
    parser.add_argument("--red", required=True, help="Path to aligned Red-band GeoTIFF")
    parser.add_argument("--nir", required=True, help="Path to aligned NIR-band GeoTIFF")
    parser.add_argument("--out", required=True, help="Output NDVI GeoTIFF path")
    args = parser.parse_args()

    _, summary = calculate_ndvi(args.red, args.nir, args.out)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":    main()