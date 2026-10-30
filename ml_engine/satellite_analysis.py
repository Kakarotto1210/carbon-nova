from pathlib import Path
import streamlit as st


def render_satellite_analysis(output_dir: Path):
    st.markdown('<div id="cn-satellite"></div>', unsafe_allow_html=True)
    st.header("🛰️ Satellite Vegetation Analysis — Nawada AOI")
    ndvi_path = output_dir / "nawada_ndvi.tif"
    if not ndvi_path.exists():
        ndvi_path = output_dir / "ndvi.tif"
    if ndvi_path.exists():
        try:
            import numpy as np
            import rasterio
            with rasterio.open(ndvi_path) as src:
                ndvi = src.read(1, masked=True)
                valid = ndvi.compressed()
                valid = valid[np.isfinite(valid)]
            if len(valid):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Valid pixels", f"{len(valid):,}")
                c2.metric("Mean NDVI", f"{float(np.mean(valid)):.3f}")
                c3.metric("Median NDVI", f"{float(np.median(valid)):.3f}")
                c4.metric("Pixels below 0.30", f"{float(np.mean(valid < 0.30) * 100):.1f}%")
                st.caption("NDVI < 0.30 is a rough screening threshold, not a crop diagnosis. The raster may not be clipped to an exact district boundary.")
            else:
                st.warning("No valid NDVI pixels found in the raster.")
        except Exception as exc:
            st.warning(f"Could not read NDVI raster: {exc}")
    else:
        st.info("NDVI raster not found. Place ndvi.tif or nawada_ndvi.tif in outputs/.")
    left, right = st.columns(2)
    for col, filename, caption in [
        (left, "vegetation_zones.png", "Vegetation zones"),
        (right, "vegetation_percentage.png", "Vegetation distribution"),
    ]:
        with col:
            image_path = output_dir / filename
            with st.container(border=True):
                st.subheader(caption)
                if image_path.exists():
                    st.image(str(image_path), use_container_width=True)
                else:
                    st.caption(f"{filename} not found in outputs/.")
