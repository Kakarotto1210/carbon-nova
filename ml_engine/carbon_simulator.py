import streamlit as st


def _estimate(urea_kg, dap_kg, diesel_l, electricity_kwh):
    # Screening estimate only; intentionally limited to these sources.
    urea_application_co2 = urea_kg * (0.20 * 44.0 / 12.0)
    nitrogen_kg = urea_kg * 0.46 + dap_kg * 0.18
    direct_n2o_co2e = nitrogen_kg * 0.01 * (44.0 / 28.0) * 273.0
    diesel_co2 = diesel_l * 2.68
    electricity_co2 = electricity_kwh * 0.710
    return urea_application_co2 + direct_n2o_co2e + diesel_co2 + electricity_co2


def render_carbon_simulator():
    st.markdown('<div id="cn-scenario"></div>', unsafe_allow_html=True)
    st.header("♻️ Carbon Reduction Simulator")
    st.caption("Compare a baseline with a hypothetical reduction in urea/DAP use. This is a scenario estimate, not a measured emissions reduction or an agronomic recommendation.")
    with st.form("cn_carbon_reduction_form"):
        left, right = st.columns(2)
        with left:
            area = st.number_input("Farm area (hectares)", min_value=0.01, value=1.0, step=0.1)
            urea = st.number_input("Baseline urea (kg)", min_value=0.0, value=80.0, step=5.0)
            dap = st.number_input("Baseline DAP (kg)", min_value=0.0, value=25.0, step=5.0)
        with right:
            diesel = st.number_input("Diesel (litres)", min_value=0.0, value=20.0, step=5.0)
            electricity = st.number_input("Electricity (kWh)", min_value=0.0, value=80.0, step=10.0)
            reduction = st.slider("Hypothetical fertilizer reduction", min_value=0, max_value=40, value=10, step=5, format="%d%%")
        submitted = st.form_submit_button("Compare baseline vs scenario", type="primary")
    if submitted:
        baseline = _estimate(urea, dap, diesel, electricity)
        scenario = _estimate(urea * (1 - reduction / 100), dap * (1 - reduction / 100), diesel, electricity)
        delta = baseline - scenario
        a, b, c = st.columns(3)
        a.metric("Baseline estimate", f"{baseline:,.1f} kg CO₂e", f"{baseline / area:,.1f} kg/ha")
        b.metric("Scenario estimate", f"{scenario:,.1f} kg CO₂e", f"{scenario / area:,.1f} kg/ha")
        c.metric("Estimated difference", f"{delta:,.1f} kg CO₂e", f"{(delta / baseline * 100 if baseline else 0):.1f}% lower")
        st.progress(min(max((delta / baseline if baseline else 0), 0.0), 1.0))
        st.warning("This demo assumes fertilizer can be reduced by the selected percentage without modelling crop response. Do not reduce fertilizer in real fields without soil/crop guidance. Estimates omit rice-paddy methane, fertilizer manufacture and several other emissions sources.")
