from pathlib import Path
import streamlit as st


def render_yield_prediction(base_dir: Path):
    st.markdown('<div id="cn-yield"></div>', unsafe_allow_html=True)
    st.header("🤖 Crop Yield Prediction")
    st.caption("Prototype prediction using the saved model and its matching demo input. The output is an estimate, not a guaranteed yield.")
    model_candidates = [base_dir / "models" / "rice_yield_model.joblib", base_dir / "models" / "yield_model.joblib", base_dir / "yield_model.joblib"]
    model_path = next((p for p in model_candidates if p.exists()), None)
    input_candidates = [base_dir / "data" / "prediction_input.example.json", base_dir / "data" / "prediction_input.json"]
    input_path = next((p for p in input_candidates if p.exists()), None)
    if model_path is None:
        st.error("Model not found. Add yield_model.joblib to models/.")
        return
    st.caption(f"Model: {model_path.name}")
    if input_path is None:
        st.warning("The saved model expects 135 input features. Add its matching prediction_input.example.json to data/ to run a prediction safely; the app will not invent farm inputs.")
        return
    if st.button("Run demo yield prediction", key="cn_run_yield_prediction", type="primary"):
        try:
            from ml_engine.predict import predict_records
            with st.spinner("Running prediction..."):
                prediction = predict_records(model_path, input_path)
            results = prediction.get("results", [])
            if not results:
                st.warning("The prediction returned no results.")
            else:
                for item in results:
                    value = item.get("prediction")
                    if isinstance(value, (int, float)):
                        target = str(prediction.get("target", "")).lower()
                        unit = "kg/ha" if "kg_ha" in target or "kg/ha" in target else ("tonnes/ha" if "ton" in target else "target units")
                        st.metric("Estimated crop yield", f"{value:,.2f} {unit}")
                    else:
                        st.metric("Model output", str(value))
                metrics = prediction.get("metrics", {})
                if metrics:
                    st.subheader("Saved model evaluation metrics")
                    metric_cols = st.columns(min(3, len(metrics)))
                    for col, (name, value) in zip(metric_cols, metrics.items()):
                        if isinstance(value, (int, float)):
                            col.metric(name.upper(), f"{value:.3f}")
                st.info(prediction.get("warning", "Prototype estimate: validate against measured harvest data."))
                with st.expander("Technical details"):
                    st.json(prediction)
        except Exception as exc:
            st.error(f"Prediction failed: {exc}")
