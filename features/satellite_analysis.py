from pathlib import Path

import streamlit as st


def render_satellite_analysis(output_dir: Path):
    """Render a green/yellow/red vegetation-zone map from the Nawada NDVI raster."""
    import numpy as np
    import matplotlib.pyplot as plt
    import rasterio
    from matplotlib.colors import ListedColormap, BoundaryNorm

    output_dir = Path(output_dir)

    st.markdown('<div id="cn-satellite"></div>', unsafe_allow_html=True)
    st.header("🛰️ Satellite Vegetation Zone Map")
    st.caption(
        "Each pixel is colored by its NDVI value: green = good, yellow = moderate, "
        "red = critical. These are screening categories, not a crop-health diagnosis."
    )

    # Use the Nawada raster only. Do not silently fall back to ndvi.tif,
    # because that file may cover a different geographic area.
    raster_path = output_dir / "nawada_ndvi.tif"

    if not raster_path.is_file():
        st.error(
            f"Nawada NDVI raster not found: {raster_path}. "
            "Place nawada_ndvi.tif in the outputs folder."
        )
        return

    try:
        with rasterio.open(raster_path) as src:
            ndvi = src.read(1, masked=True).astype("float32")
            bounds = src.bounds
            crs = src.crs
            transform = src.transform
            values = ndvi.filled(np.nan)
            valid_mask = (
                ~np.ma.getmaskarray(ndvi)
                & np.isfinite(values)
            )

        if not valid_mask.any():
            st.error("The Nawada NDVI raster contains no valid pixels.")
            return

        # Critical < 0.30; moderate 0.30–0.50; good > 0.50.
        zones = np.full(values.shape, np.nan, dtype="float32")
        zones[valid_mask & (values < 0.30)] = 0
        zones[valid_mask & (values >= 0.30) & (values <= 0.50)] = 1
        zones[valid_mask & (values > 0.50)] = 2

        cmap = ListedColormap(["#e34b4b", "#f2cf45", "#2ca25f"])
        cmap.set_bad((0, 0, 0, 0))
        norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)

        fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
        ax.imshow(
            np.ma.masked_invalid(zones),
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
            extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
            origin="upper",
        )
        ax.set_title("Nawada Vegetation Zones from Sentinel-2 NDVI")
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")
        ax.set_aspect("equal")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        valid_values = values[valid_mask]
        total = int(valid_values.size)
        critical = int(np.sum(valid_values < 0.30))
        moderate = int(np.sum((valid_values >= 0.30) & (valid_values <= 0.50)))
        good = int(np.sum(valid_values > 0.50))

        a, b, c = st.columns(3)
        a.metric("🟢 Good vegetation", f"{good / total * 100:.1f}%", f"{good:,} pixels")
        b.metric("🟡 Moderate vegetation", f"{moderate / total * 100:.1f}%", f"{moderate:,} pixels")
        c.metric("🔴 Critical vegetation", f"{critical / total * 100:.1f}%", f"{critical:,} pixels")

        st.caption(
            f"Source: {raster_path.name} · CRS: {crs} · "
            f"Bounds: left={bounds.left:.5f}, bottom={bounds.bottom:.5f}, "
            f"right={bounds.right:.5f}, top={bounds.top:.5f}. "
            "Thresholds: red NDVI < 0.30; yellow 0.30–0.50; green > 0.50. "
            "This displays the classified raster, not a street map or district-boundary overlay."
        )

    except Exception as exc:
        st.error(
            f"Could not generate the vegetation-zone map: "
            f"{type(exc).__name__}: {exc}"
        )
