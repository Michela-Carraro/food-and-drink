import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Food and Drink Retailing and Logistics Simulation",
    page_icon="🍾",
    layout="wide"
)

# Initialize Session State for Round Management and History
if "round_number" not in st.session_state:
    st.session_state.round_number = 1

if "history" not in st.session_state:
    st.session_state.history = []

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "active_scenario" not in st.session_state:
    st.session_state.active_scenario = (
        "JuiceCo: Fresh Orange Juice (Mass Grocery Retail)"
    )

# Main title and course description
st.title("🍊🍾 Food and Drink Retailing and Logistics Simulation")
st.subheader(
    "Master's Programme in Food and Drink Retailing and Logistics (NEOMA BS)"
)

st.markdown("""
Welcome to the **Food and Drink Retailing and Logistics Simulation**,
an interactive turn-based supply chain optimization game.

### 🎮 How to Play:
1. **Select your F&D Product Track** on the left
   (Mass Grocery Fresh Juice vs. Luxury Champagne Export).
2. Formulate your logistics strategy using the four operational levers.
3. Click **'Validate & Run Simulation Round'** to lock in your choices
   and process the weekly P&L.
4. Advance through **4 Operational Rounds** to correct your strategy
   based on the audit feedback.
""")

st.divider()

# Input and output columns
col_input, col_output = st.columns([1, 2])

with col_input:

    st.header(f"🛠️ Round {st.session_state.round_number} Decisions")

    # Scenario Selector
    scenario_options = [
        "JuiceCo: Fresh Orange Juice (Mass Grocery Retail)",
        "Maison Reims: Vintage Champagne Export (Wine & Gastronomy)"
    ]

    selected_scenario = st.selectbox(
        "Select Supply Chain Scenario",
        options=scenario_options,
        index=scenario_options.index(st.session_state.active_scenario),
        disabled=(len(st.session_state.history) > 0),
        help="Reset simulation to switch product tracks."
    )

    st.session_state.active_scenario = selected_scenario
    is_juice = selected_scenario.startswith("JuiceCo")

    st.markdown("Adjust your logistics parameters for this period:")

    # 1. Shipment batch size
    batch_size = st.slider(
        "Shipment Batch Size (Bottles)",
        min_value=500,
        max_value=10000 if is_juice else 4000,
        value=2000 if is_juice else 1000,
        step=500 if is_juice else 250,
        help=(
            "Larger batches reduce unit transport costs and per-bottle CO2, "
            "but increase warehouse dwell time."
        )
    )

    # 2. Delivery frequency
    frequency_options = {
        "Daily": 1,
        "Twice a Week": 3,
        "Weekly": 7
    }

    frequency_label = st.selectbox(
        "Delivery Frequency to Retail DC / Export Hub",
        options=list(frequency_options.keys()),
        index=1,
        help=(
            "Frequent deliveries improve speed-to-market but increase "
            "fixed transport expenses."
        )
    )

    days_between_deliveries = frequency_options[frequency_label]

    # 3. Cold chain / Thermal quality
    cold_chain_level = st.radio(
        "Thermal & Handling Investment (IoT & Reefer Control)",
        options=[
            "Standard (Ambient/Basic Transport - Low Investment)",
            "Premium (Continuous IoT Telemetry & Climate/Anti-Vibration Reefer)"
        ],
        index=0,
        help=(
            "Premium protects JuiceCo against biological decay (+2°C) "
            "and protects Maison Reims against heat spikes (>22°C) "
            "and vibration."
        )
    )

    # 4. Safety stock
    safety_stock_days = st.slider(
        "Warehouse / Cellar Safety Stock (Days of Coverage)",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help=(
            "Higher buffer stock prevents Out-of-Stock (OOS), "
            "but consumes shelf life in fresh juice or increases "
            "working capital in fine wine."
        )
    )

    st.markdown("---")

    # Submit Button Trigger
    submit_btn = st.button(
        "🚀 Validate & Run Simulation Round",
        use_container_width=True
    )


# ============================================================
# SIMULATION ENGINE
# CALCULATED ONLY UPON EXPLICIT SUBMISSION
# ============================================================

if submit_btn:

    if is_juice:

        # Scenario A: Mass Grocery Fresh Orange Juice
        WEEKLY_POTENTIAL_DEMAND = 10000
        WHOLESALE_SELLING_PRICE = 3.50
        UNIT_PRODUCTION_COST = 2.00
        TOTAL_SHELF_LIFE_DAYS = 24
        CONTRACTUAL_THRESHOLD = 70.0

        glass_weight_multiplier = 1.0
        holding_cost_per_day = 250.0

    else:

        # Scenario B: Luxury Vintage Champagne Export
        WEEKLY_POTENTIAL_DEMAND = 3000
        WHOLESALE_SELLING_PRICE = 28.00
        UNIT_PRODUCTION_COST = 14.00
        TOTAL_SHELF_LIFE_DAYS = 100

        CONTRACTUAL_THRESHOLD = 85.0
        glass_weight_multiplier = 1.85
        holding_cost_per_day = 450.0

    # Transit time calculation
    base_transit_days = (
        2 if days_between_deliveries == 1
        else 4 if days_between_deliveries == 3
        else 7
    )

    if (is_juice and batch_size > 5000) or (
        not is_juice and batch_size > 2000
    ):
        base_transit_days += 1

    # Thermal & biological degradation calculation
    if is_juice:

        degradation_multiplier = (
            1.0 if cold_chain_level.startswith("Premium") else 1.35
        )

        shelf_life_lost = base_transit_days * degradation_multiplier

        remaining_days = (
            TOTAL_SHELF_LIFE_DAYS
            - shelf_life_lost
            - safety_stock_days
        )

        integrity_metric = max(
            0.0,
            min(
                100.0,
                (remaining_days / TOTAL_SHELF_LIFE_DAYS) * 100
            )
        )

    else:

        # Champagne thermal degradation
        thermal_loss_per_day = (
            1.2 if cold_chain_level.startswith("Premium") else 4.5
        )

        total_quality_lost = (
            base_transit_days * thermal_loss_per_day
            + safety_stock_days * 0.4
        )

        integrity_metric = max(
            0.0,
            min(100.0, 100.0 - total_quality_lost)
        )

    # Waste / Gate Rejection calculation
    if is_juice:

        shelf_saturation_risk = (
            (batch_size / 2000)
            * (days_between_deliveries / 2)
        )

        waste_percent = (
            2.0
            + (safety_stock_days * 3.5)
            + (shelf_saturation_risk * 1.5)
        )

        if integrity_metric < CONTRACTUAL_THRESHOLD:
            waste_percent += 45.0

    else:

        waste_percent = 0.5 + (base_transit_days * 0.3)

        if integrity_metric < CONTRACTUAL_THRESHOLD:
            waste_percent += 35.0

    waste_percent = max(0.0, min(100.0, waste_percent))

    # Out-of-Stock (OOS) calculation
    batch_ratio = batch_size / (2000 if is_juice else 600)

    oos_percent = (
        15.0
        - (safety_stock_days * 3.0)
        + (days_between_deliveries * 2.0)
    )

    if batch_ratio < 0.5 and days_between_deliveries > 3:
        oos_percent += 25.0

    oos_percent = max(0.0, min(100.0, oos_percent))

    # ========================================================
    # FINANCIAL PERFORMANCE
    # ========================================================

    requested_units = WEEKLY_POTENTIAL_DEMAND

    units_lost_to_oos = (
        requested_units * (oos_percent / 100)
    )

    potentially_delivered_units = (
        requested_units - units_lost_to_oos
    )

    wasted_rejected_units = (
        potentially_delivered_units * (waste_percent / 100)
    )

    healthy_units_sold = (
        potentially_delivered_units - wasted_rejected_units
    )

    # Cost items
    total_production_cost = (
        potentially_delivered_units * UNIT_PRODUCTION_COST
    )

    base_trip_cost = (
        300 if days_between_deliveries == 1
        else 600 if days_between_deliveries == 3
        else 1200
    )

    if not is_juice:
        base_trip_cost *= 1.3

    if cold_chain_level.startswith("Premium"):
        base_trip_cost *= 1.4

    weekly_number_of_trips = 7 / days_between_deliveries

    total_transportation_cost = (
        base_trip_cost * weekly_number_of_trips
    )

    inventory_holding_cost = (
        safety_stock_days * holding_cost_per_day
    )

    contractual_penalties = (
        wasted_rejected_units * WHOLESALE_SELLING_PRICE
    )

    total_revenue = (
        healthy_units_sold * WHOLESALE_SELLING_PRICE
    )

    net_profit = (
        total_revenue
        - total_production_cost
        - total_transportation_cost
        - inventory_holding_cost
        - contractual_penalties
    )

    # ========================================================
    # ENVIRONMENTAL CALCULATION (SCOPE 3 CO2)
    # ========================================================

    normalized_batch = (
        batch_size / (2000 if is_juice else 800)
    )

    transportation_co2 = (
        (weekly_number_of_trips * 120) / normalized_batch
    ) * glass_weight_multiplier

    refrigeration_co2 = (
        450 if cold_chain_level.startswith("Premium") else 180
    )

    total_co2_kg = (
        transportation_co2
        + refrigeration_co2
        + (wasted_rejected_units * 0.15)
    )

    # Store results in history dictionary
    round_results = {
        "Round": f"Round {st.session_state.round_number}",
        "Net Profit (€)": round(net_profit, 2),
        "Waste / Rejection (%)": round(waste_percent, 1),
        "RSL / Thermal Integrity (%)": round(integrity_metric, 1),
        "OOS (%)": round(oos_percent, 1),
        "CO2 Emitted (kg)": round(total_co2_kg, 1),
        "Prod Cost": total_production_cost,
        "Trans Cost": total_transportation_cost,
        "Hold Cost": inventory_holding_cost,
        "Waste Cost": contractual_penalties,
        "Units Sold": healthy_units_sold
    }

    st.session_state.history.append(round_results)
    st.session_state.submitted = True


# ============================================================
# OUTPUT RENDERING
# ============================================================

with col_output:

    if not st.session_state.submitted:

        st.info(
            "💡 **Awaiting Strategy Decision:** Select your scenario "
            "and configure your logistics parameters on the left, "
            "then click **Validate & Run Simulation Round**."
        )

    else:

        current_data = st.session_state.history[-1]

        st.header(
            f"📊 Performance Dashboard "
            f"({current_data['Round']} Verified Results)"
        )

        # Main metrics row
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        profit_val = current_data["Net Profit (€)"]

        formatted_profit = (
            f"-€{abs(profit_val):,.2f}"
            if profit_val < 0
            else f"€{profit_val:,.2f}"
        )

        unit_margin = (
            profit_val / current_data["Units Sold"]
            if current_data["Units Sold"] > 0
            else 0.0
        )

        formatted_margin = (
            f"-€{abs(unit_margin):.2f}"
            if unit_margin < 0
            else f"€{unit_margin:.2f}"
        )

        kpi1.metric(
            label="Net Profit",
            value=formatted_profit,
            delta=f"Net unit margin: {formatted_margin}"
        )

        kpi2.metric(
            label="Spoilage / Rejection",
            value=f"{current_data['Waste / Rejection (%)']}%"
        )

        kpi3.metric(
            label=(
                "Remaining Shelf Life"
                if is_juice
                else "Thermal Integrity"
            ),
            value=f"{current_data['RSL / Thermal Integrity (%)']}%"
        )

        kpi4.metric(
            label="Out-of-Stock (OOS)",
            value=f"{current_data['OOS (%)']}%"
        )

        st.divider()

        # Graphs breakdown
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:

            st.markdown("Operating Cost Breakdown (€)")

            cost_df = pd.DataFrame({
                "Cost Category": [
                    "Production",
                    "Transportation",
                    "Inventory Holding",
                    "Spoilage / Penalties"
                ],
                "Value (€)": [
                    current_data["Prod Cost"],
                    current_data["Trans Cost"],
                    current_data["Hold Cost"],
                    current_data["Waste Cost"]
                ]
            })

            st.bar_chart(
                data=cost_df,
                x="Cost Category",
                y="Value (€)",
                use_container_width=True
            )

        with col_chart2:

            st.markdown("Scope 3 Carbon Footprint Ledger")

            st.metric(
                label="Total Weekly Emissions",
                value=f"{current_data['CO2 Emitted (kg)']:,.1f} kg CO₂e"
            )

            st.progress(
                min(
                    1.0,
                    max(
                        0.0,
                        current_data["CO2 Emitted (kg)"] / 3500.0
                    )
                )
            )

            if not is_juice:
                st.caption(
                    "🍾 Note: Heavy Champagne glass bottles amplify "
                    "transport CO₂ emissions per trip."
                )

        # ====================================================
        # STRATEGIC DIAGNOSTIC FEEDBACK
        # ====================================================

        st.subheader("🧠 Corporate Logistics Audit & Feedback")

        threshold = 70.0 if is_juice else 85.0

        if current_data["RSL / Thermal Integrity (%)"] < threshold:

            if is_juice:

                st.error(
                    f"🚨 Retailer Gate Rejection (<70% RSL): "
                    f"Your Remaining Shelf Life dropped to "
                    f"{current_data['RSL / Thermal Integrity (%)']}%. "
                    "The supermarket rejected the delivery at the DC gate! "
                    "Reduce safety stock days, ship more frequently, "
                    "or upgrade to Premium Cold Chain."
                )

            else:

                st.error(
                    f"🚨 Thermal Shock Rejection (<85% Integrity): "
                    "Without continuous climate-controlled reefer protection, "
                    "transit heat spikes (>22°C) and vibration damaged "
                    "your vintage Champagne! Importers rejected the batch. "
                    "Upgrade to Premium IoT Reefer transport or shorten "
                    "transit dwell time."
                )

        elif current_data["OOS (%)"] > 12.0:

            st.warning(
                f"⚠️ Severe Out-of-Stock Alert "
                f"({current_data['OOS (%)']}%): "
                "Shelves and restaurant cellars are running empty "
                "during peak demand. Increase safety stock coverage "
                "or ship more frequently."
            )

        elif current_data["Waste / Rejection (%)"] > 15.0:

            st.warning(
                f"⚠️ Excessive Spoilage & Holding Loss "
                f"({current_data['Waste / Rejection (%)']}%): "
                "Your batch sizes or safety stock buffers are too high "
                "relative to weekly demand."
            )

        else:

            st.success(
                "💎 Optimal Supply Chain Balance Achieved! "
                "You protected product integrity, satisfied buyer "
                "thresholds, prevented stockouts, and delivered "
                "strong net profitability."
            )

        # ====================================================
        # MULTI-ROUND LEDGER HISTORY TABLE
        # ====================================================

        st.divider()

        st.subheader("📜 Historical Performance Ledger")

        history_df = pd.DataFrame(
            st.session_state.history
        )[
            [
                "Round",
                "Net Profit (€)",
                "Waste / Rejection (%)",
                "RSL / Thermal Integrity (%)",
                "OOS (%)",
                "CO2 Emitted (kg)"
            ]
        ]

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True
        )

        # ====================================================
        # ROUND ADVANCEMENT CONTROLS
        # ====================================================

        col_btn1, col_btn2 = st.columns([1, 3])

        with col_btn1:

            if st.session_state.round_number < 4:

                if st.button(
                    f"➡️ Next: Round "
                    f"{st.session_state.round_number + 1}"
                ):

                    st.session_state.round_number += 1
                    st.session_state.submitted = False
                    st.rerun()

            else:

                st.success("🏆 All 4 Rounds Complete!")

        with col_btn2:

            if st.button("🔄 Reset Simulation / Switch Product Track"):

                st.session_state.round_number = 1
                st.session_state.history = []
                st.session_state.submitted = False
                st.rerun()
