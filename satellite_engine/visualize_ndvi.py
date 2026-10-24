
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

input_file = "outputs/ndvi.tif"
output_dir = Path("outputs")
output_dir.mkdir(exist_ok=True)

with rasterio.open(input_file) as src:
    ndvi = src.read(1).astype("float32")
    nodata = src.nodata

    valid = np.isfinite(ndvi)

    if nodata is not None:
        valid &= ndvi != nodata

    values = ndvi[valid]

if values.size == 0:
    raise ValueError("No valid NDVI pixels found.")

# Colour-coded NDVI map
display = np.where(valid, ndvi, np.nan)

plt.figure(figsize=(10, 7))
image = plt.imshow(
    display,
    cmap="RdYlGn",
    vmin=-1,
    vmax=1
)
plt.colorbar(image, label="NDVI")
plt.title("AgroFlux AI - Vegetation Index Map")
plt.axis("off")
plt.tight_layout()
plt.savefig(output_dir / "ndvi_map.png", dpi=200)
plt.close()

# NDVI distribution histogram
plt.figure(figsize=(9, 5))
plt.hist(values, bins=40)
plt.axvline(0.30, linestyle="--",
            label="Screening threshold: 0.30")
plt.xlabel("NDVI")
plt.ylabel("Number of pixels")
plt.title("AgroFlux AI - NDVI Distribution")
plt.legend()
plt.tight_layout()
plt.savefig(output_dir / "ndvi_histogram.png", dpi=200)
plt.close()

print("Visualization complete.")
print("Valid pixels:", values.size)
print("Mean NDVI:", round(float(values.mean()), 4))
print("Saved: outputs/ndvi_map.png")
print("Saved: outputs/ndvi_histogram.png")