
from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parent
input_file = ROOT / "outputs" / "nawada_ndvi.tif"
output_dir = ROOT / "outputs"

if not input_file.exists():
    raise FileNotFoundError(f"NDVI raster not found: {input_file}")

with rasterio.open(input_file) as src:
    band = src.read(1, masked=True).astype("float32")
    values = np.asarray(band.data)
    valid = (
        ~np.ma.getmaskarray(band)
        & np.isfinite(values)
        & (values >= -1)
        & (values <= 1)
    )

if not valid.any():
    raise ValueError("No valid NDVI pixels found.")

# Three simple screening zones
zones = np.zeros(values.shape, dtype=np.uint8)
zones[valid & (values < 0.30)] = 1
zones[valid & (values >= 0.30) & (values < 0.60)] = 2
zones[valid & (values >= 0.60)] = 3

labels = ["Low (< 0.30)", "Moderate (0.30–0.60)", "High (>= 0.60)"]
colors = ["#c96b47", "#e9c46a", "#319b69"]

percentages = [
    np.mean(zones[valid] == zone) * 100
    for zone in (1, 2, 3)
]

# Vegetation-zone map
masked_zones = np.ma.masked_where(~valid, zones)

plt.figure(figsize=(10, 7))
plt.imshow(
    masked_zones,
    cmap=ListedColormap(colors),
    vmin=0.5,
    vmax=3.5,
    interpolation="nearest"
)
colorbar = plt.colorbar(ticks=[1, 2, 3])
colorbar.ax.set_yticklabels(labels)
plt.title("Vegetation Zones — Nawada AOI")
plt.axis("off")
plt.tight_layout()
plt.savefig(output_dir / "vegetation_zones.png", dpi=200)
plt.close()

# Vegetation percentage chart
plt.figure(figsize=(8, 5))
bars = plt.bar(labels, percentages, color=colors)
plt.ylabel("Valid pixels (%)")
plt.title("Vegetation Zone Distribution — Nawada AOI")
plt.ylim(0, 100)

for bar, percentage in zip(bars, percentages):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{percentage:.1f}%",
        ha="center",
        va="bottom"
    )

plt.tight_layout()
plt.savefig(output_dir / "vegetation_percentage.png", dpi=200)
plt.close()

print("\nNAWADA VEGETATION ANALYSIS COMPLETE")
print("Valid pixels:", int(valid.sum()))

for label, percentage in zip(labels, percentages):
    print(f"{label}: {percentage:.2f}%")

print("Saved:", output_dir / "vegetation_zones.png")
print("Saved:", output_dir / "vegetation_percentage.png")
