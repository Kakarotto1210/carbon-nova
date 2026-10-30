
from pathlib import Path

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.warp import reproject, Resampling
from matplotlib.colors import ListedColormap


def render_satellite_analysis(output_dir: Path):
    output_dir = Path(output_dir)
    project_dir = output_dir.parent
    data_dir = project_dir / "data"

    st.header("Satellite Vegetation Analysis — Nawada AOI")
    st.caption(
        "Satellite-derived vegetation zones. Green = good, "
        "yellow = moderate, red = critical."
    )

    ndvi_candidates = [
        output_dir / "nawada_ndvi.tif",
        output_dir / "ndvi.tif",
        data_dir / (
            "2026-06-24-00_00_2026-06-24-23_59_"
            "Sentinel-2_L2A_NDVI.tiff"
        ),
    ]

    red_candidates = [
        data_dir / (
            "2026-06-24-00_00_2026-06-24-23_59_"
            "Sentinel-2_L2A_B04_(Raw).tiff"
        ),
        data_dir / "red.tif",
    ]

    nir_candidates = [
        data_dir / (
            "2026-06-24-00_00_2026-06-24-23_59_"
            "Sentinel-2_L2A_B08_(Raw).tiff"
        ),
        data_dir / "nir.tif",
    ]

    ndvi_path = next((p for p in ndvi_candidates if p.exists()), None)
    red_path = next((p for p in red_candidates if p.exists()), None)
    nir_path = next((p for p in nir_candidates if p.exists()), None)

    if ndvi_path is None:
        st.error("NDVI TIFF not found. Check your data/ and outputs/ folders.")
        return

    try:
        with rasterio.open(ndvi_path) as src:
            ndvi = src.read(1, masked=True).astype("float32")
            ndvi_transform = src.transform
            ndvi_crs = src.crs
            ndvi_profile = src.profile.copy()

        values = np.asarray(ndvi.filled(np.nan), dtype="float32")
        valid = np.isfinite(values)

        if ndvi_profile.get("nodata") is not None:
            valid &= values != ndvi_profile["nodata"]

        if not valid.any():
            st.error("The NDVI raster contains no valid pixels.")
            return

        # Classify actual NDVI pixels.
        zones = np.full(values.shape, -1, dtype=np.int8)
        zones[valid & (values < 0.30)] = 0
        zones[valid & (values >= 0.30) & (values <= 0.50)] = 1
        zones[valid & (values > 0.50)] = 2

        total = int(valid.sum())
        critical = int((zones == 0).sum())
        moderate = int((zones == 1).sum())
        good = int((zones == 2).sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valid pixels", f"{total:,}")
        c2.metric("Mean NDVI", f"{np.nanmean(values[valid]):.3f}")
        c3.metric("Median NDVI", f"{np.nanmedian(values[valid]):.3f}")
        c4.metric("Critical vegetation", f"{critical / total:.1%}")

        # Create a satellite-band background aligned to the NDVI grid.
        background = None
        source_path = nir_path or red_path

        if source_path is not None:
            with rasterio.open(source_path) as src:
                band = src.read(1).astype("float32")
                aligned = np.full(values.shape, np.nan, dtype="float32")

                reproject(
                    source=band,
                    destination=aligned,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=ndvi_transform,
                    dst_crs=ndvi_crs,
                    resampling=Resampling.bilinear,
                    src_nodata=src.nodata,
                    dst_nodata=np.nan,
                )

            finite = np.isfinite(aligned)
            if finite.any():
                low, high = np.nanpercentile(aligned[finite], [2, 98])
                if high > low:
                    background = np.clip(
                        (aligned - low) / (high - low), 0, 1
                    )

        st.subheader("Vegetation Zones Over Satellite Data")

        fig, ax = plt.subplots(figsize=(11, 7))

        if background is not None:
            ax.imshow(
                background,
                cmap="gray",
                origin="upper",
                alpha=0.95,
            )
            overlay = np.ma.masked_where(zones < 0, zones)
            cmap = ListedColormap(["#E53935", "#FDD835", "#20A44B"])
            ax.imshow(
                overlay,
                cmap=cmap,
                vmin=0,
                vmax=2,
                alpha=0.58,
                origin="upper",
            )
            title = "Vegetation Zones — Satellite Band Overlay"
        else:
            overlay = np.ma.masked_where(zones < 0, zones)
            cmap = ListedColormap(["#E53935", "#FDD835", "#20A44B"])
            ax.imshow(overlay, cmap=cmap, vmin=0, vmax=2)
            title = "Vegetation Zones — NDVI Classification"

        ax.set_title(title)
        ax.set_xlabel("Raster column (pixel)")
        ax.set_ylabel("Raster row (pixel)")
        ax.set_xticks([])
        ax.set_yticks([])

        from matplotlib.patches import Patch
        ax.legend(
            handles=[
                Patch(color="#20A44B", label="Good (> 0.50)"),
                Patch(color="#FDD835", label="Moderate (0.30–0.50)"),
                Patch(color="#E53935", label="Critical (< 0.30)"),
            ],
            loc="lower center",
            bbox_to_anchor=(0.5, -0.10),
            ncol=3,
            frameon=True,
        )

        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        st.subheader("Vegetation Distribution")

        names = ["Critical", "Moderate", "Good"]
        counts = [critical, moderate, good]
        percentages = [count / total * 100 for count in counts]

        fig, ax = plt.subplots(figsize=(8, 3.5))
        bars = ax.bar(
            names,
            percentages,
            color=["#E53935", "#FDD835", "#20A44B"],
        )
        ax.set_ylabel("Valid pixels (%)")
        ax.set_ylim(0, 100)
        ax.bar_label(bars, fmt="%.1f%%")
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        st.caption(
            f"NDVI source: {ndvi_path.name}. "
            "Zones use NDVI thresholds of 0.30 and 0.50. "
            "The overlay is aligned to the NDVI raster grid; "
            "it is not a district-boundary map."
        )

    except Exception as exc:
        st.error(f"Satellite visualization failed: {type(exc).__name__}: {exc}")