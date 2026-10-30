from pathlib import Path
import pandas as pd
import streamlit as st


def _find_dataset(base_dir: Path):
    candidates = [
        base_dir / "outputs" / "rice_cleaned.csv",
        base_dir / "data" / "rice_cleaned.csv",
        base_dir / "data" / "CSISA_IND_LDS_Rice_2018_Data.csv",
        base_dir / "CSISA_IND_LDS_Rice_2018_Data.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def render_state_coverage(base_dir: Path):
    st.markdown('<div id="cn-state-coverage"></div>', unsafe_allow_html=True)
    st.header("🗺️ State-wise Dataset Coverage")
    st.caption("Shows the geographical representation of the rice-yield dataset loaded by this app.")
    path = _find_dataset(base_dir)
    if path is None:
        st.info("Dataset not found. Place rice_cleaned.csv in outputs/ or data/, or place the original CSISA dataset in data/.")
        return
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        st.error(f"Could not read {path.name}: {exc}")
        return
    state_col = next((c for c in ["state", "A-q102_state", "State", "STATE"] if c in df.columns), None)
    if not state_col:
        st.warning(f"Loaded {path.name}, but no recognised state column was found.")
        return
    id_col = next((c for c in ["sample_id", "sampleid", "Sample_ID", "sample id", "record_id", "id", "ID", "Merged_ID"] if c in df.columns), None)
    data = df.copy()
    data[state_col] = data[state_col].astype("string").str.strip()
    data = data[data[state_col].notna() & data[state_col].ne("") & data[state_col].str.lower().ne("nan")]
    if data.empty:
        st.warning("The dataset has no usable state values.")
        return
    if id_col:
        data = data[data[id_col].notna()].copy()
        total_samples = int(data[id_col].nunique())
        grouped = data.groupby(state_col)[id_col].nunique().sort_values(ascending=False)
        count_label = f"Unique IDs ({id_col})"
    else:
        grouped = data.groupby(state_col).size().sort_values(ascending=False)
        total_samples = int(grouped.sum())
        count_label = "Sample records (no ID column found)"
    total_states = int(grouped.size)
    a, b, c = st.columns(3)
    a.metric("Total samples represented", f"{total_samples:,}")
    b.metric("States represented", f"{total_states:,}")
    c.metric("Dataset file", path.name)
    st.caption(f"Counts are calculated from the loaded file. Counting method: {count_label}.")
    # Responsive rounded state cards
    cols_per_row = 3
    states = list(grouped.items())
    for start in range(0, len(states), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (state, count) in zip(cols, states[start:start + cols_per_row]):
            pct = (int(count) / total_samples * 100) if total_samples else 0
            with col:
                with st.container(border=True):
                    st.markdown(f"### {str(state)}")
                    st.metric("Samples", f"{int(count):,}")
                    st.progress(min(max(pct / 100, 0.0), 1.0))
                    st.caption(f"{pct:.1f}% of represented samples")
    chart_df = grouped.rename("Samples").reset_index().rename(columns={state_col: "State"})
    st.subheader("Compare states")
    st.bar_chart(chart_df.set_index("State"), height=300)
    with st.expander("View exact state-wise counts"):
        table = chart_df.copy()
        table["Share (%)"] = (table["Samples"] / total_samples * 100).round(2) if total_samples else 0
        st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption("Coverage describes the dataset records available to this prototype; it does not prove that the dataset is nationally representative.")
