import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Food and Drink Retailing and Logistics Simulation",
    page_icon="🍊",
    layout="wide"
)

# Initialize Session State for Round Management and History
if "round_number" not in st.session_state:
    st.session_state.round_number = 1
if "history" not in st.session_state:
    st.session_state.history = []
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# Main title and course description
st.title("🍊 Food and Drink Retailing and Logistics Simulation")
st.subheader("Master's Programme in Food and Drink Retailing and Logistics")

st.markdown("""
Welcome to **The Fresh Connection Lite**, an interactive logistics optimization game for **JuiceCo**,
a premium fresh orange juice manufacturing company.

### 🎮 How to Play:
1. Formulate your logistics strategy using the sliders on the left.
2. Click **'Validate & Run Simulation Round'** to locks in your choices. 
3. The results will process dynamically for that period and lock into your **Corporate History Ledger**.
4. You can progress up to **4 Operational Rounds** to correct your strategy based on teacher feedback.
""")

st.divider()

# Input and output columns
col_input, col_output = st.columns([1, 2])

with col_input:
    st.header(f"🛠️ Round {st.session_state.round_number} Decisions")
    st.markdown("Adjust your logistics configuration parameters for this round:")

    # 1. Shipment batch size
    batch_size = st.slider(
        "Shipment Batch Size (Bottles)",
        min_value=500,
        max_value=10000,
        value=2000,
        step=500,
        help="Larger batches reduce transportation costs per unit but increase warehouse dwell time."
    )

    # 2. Delivery frequency
    frequency_options = {
        "Daily": 1,
        "Twice a Week": 3,
        "Weekly": 7
    }

    frequency_label = st.selectbox(
        "Delivery Frequency to the Retail Distribution Centre (DC)",
        options=list(frequency_options.keys()),
        index=1,
        help="Frequent deliveries ensure product freshness but significantly increase fixed transportation costs."
    )
    days_between_deliveries = frequency_options[frequency_label]

    # 3. Cold chain quality
    cold_chain_level = st.radio(
        "Cold Chain Investment (IoT & Refrigerated Vehicles)",
        options=[
            "Standard (Low Investment)",
            "Premium (High Investment - Sensors and Continuous Refrigeration)"
        ],
        index=0,
        help="The Premium option protects the juice's biological shelf life, reducing quality degradation during transportation."
    )

    # 4. Safety stock
    safety_stock_days = st.slider(
        "Warehouse Safety Stock (Days of Coverage)",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
        help="Higher safety stock protects against stockouts caused by demand variability, but increases the risk of product expiry."
    )

    st.markdown("---")
    
    # Submit Button Trigger
    submit_btn = st.button("🚀 Validate & Run Simulation Round", use_container_width=True)

# --- SIMULATION ENGINE (CALCULATED ONLY UPON EXPLICIT SUBMISSION) ---
if submit_btn:
    # Fixed market parameters
    WEEKLY_POTENTIAL_DEMAND = 10000
    RETAIL_SELLING_PRICE = 5.00
    WHOLESALE_SELLING_PRICE = 3.50
    UNIT_PRODUCTION_COST = 2.00
    TOTAL_SHELF_LIFE_DAYS = 24
    CONTRACTUAL_RSL_THRESHOLD = 70.0  

    # Transit time and degradation calculation
    base_transit_days = 2 if days_between_deliveries == 1 else (4 if days_between_deliveries == 3 else 7)
    if batch_size > 5000:
        base_transit_days += 1  

    # Cold chain impact on accelerated degradation
    degradation_multiplier = 1.0 if cold_chain_level.startswith("Premium") else 1.3
    shelf_life_lost_in_transit = base_transit_days * degradation_multiplier

    # Remaining Shelf Life (RSL) upon arrival
    remaining_shelf_life_days = TOTAL_SHELF_LIFE_DAYS - shelf_life_lost_in_transit - safety_stock_days
    rsl_percentage = max(0.0, min(100.0, (remaining_shelf_life_days / TOTAL_SHELF_LIFE_DAYS) * 100))

    # Food Waste calculation
    shelf_saturation_risk = (batch_size / 2000) * (days_between_deliveries / 2)
    food_waste_percent = 2.0 + (safety_stock_days * 3.5) + (shelf_saturation_risk * 1.5)
    if rsl_percentage < CONTRACTUAL_RSL_THRESHOLD:
        food_waste_percent += 40.0  

    food_waste_percent = max(0.0, min(100.0, food_waste_percent))

    # Out-of-Stock (OOS) calculation
    oos_percent = 15.0 - (safety_stock_days * 3.0) + (days_between_deliveries * 2.0)
    if batch_size < 1000 and days_between_deliveries > 3:
        oos_percent += 25.0  
    oos_percent = max(0.0, min(100.0, oos_percent))

    # --- FINANCIAL PERFORMANCE ---
    requested_units = WEEKLY_POTENTIAL_DEMAND
    units_lost_to_oos = requested_units * (oos_percent / 100)
    potentially_delivered_units = requested_units - units_lost_to_oos
    expired_wasted_units = potentially_delivered_units * (food_waste_percent / 100)
    healthy_units_sold = potentially_delivered_units - expired_wasted_units

    # Cost items
    total_production_cost = potentially_delivered_units * UNIT_PRODUCTION_COST
    base_trip_cost = 300 if days_between_deliveries == 1 else (600 if days_between_deliveries == 3 else 1200)
    if cold_chain_level.startswith("Premium"):
        base_trip_cost *= 1.4  

    weekly_number_of_trips = 7 / days_between_deliveries
    total_transportation_cost = base_trip_cost * weekly_number_of_trips
    inventory_holding_cost = safety_stock_days * 250
    contractual_penalties = expired_wasted_units * WHOLESALE_SELLING_PRICE
    total_revenue = healthy_units_sold * WHOLESALE_SELLING_PRICE

    net_profit = total_revenue - total_production_cost - total_transportation_cost - inventory_holding_cost - contractual_penalties

    # Environmental calculation
    transportation_co2 = (weekly_number_of_trips * 120) / (batch_size / 2000)
    refrigeration_co2 = 450 if cold_chain_level.startswith("Premium") else 200
    total_co2_kg = transportation_co2 + refrigeration_co2 + (expired_wasted_units * 0.1)

    # Store results in the history dictionary
    round_results = {
        "Round": f"Round {st.session_state.round_number}",
        "Net Profit (€)": round(net_profit, 2),
        "Food Waste (%)": round(food_waste_percent, 1),
        "RSL (%)": round(rsl_percentage, 1),
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

# --- OUTPUT RENDERING ---
with col_output:
    if not st.session_state.submitted:
        st.info("💡 **Awaiting Strategy Decision:** Configure your logistics parameters on the left and click the submit validation button to calculate results.")
    else:
        # Fetch current active round results from session history
        current_data = st.session_state.history[-1]
        
        st.header(f"📊 Performance Dashboard ({current_data['Round']} Verified Results)")

        # Main metrics row
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric(
            label="Net Profit",
            value=f"€ {current_data['Net Profit (€)']:,.2f}",
            delta=f"Unit margin: € {((current_data['Net Profit (€)'] / current_data['Units Sold']) if current_data['Units Sold'] > 0 else 0):.2f}"
        )
        kpi2.metric(label="Food Waste", value=f"{current_data['Food Waste (%)']}%")
        kpi3.metric(label="Remaining Shelf Life", value=f"{current_data['RSL (%)']}%")
        kpi4.metric(label="Out-of-Stock (OOS)", value=f"{current_data['OOS (%)']}%")

        st.divider()

        # Graphs breakdown
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("**Operating Cost Breakdown (€)**")
            cost_df = pd.DataFrame({
                "Cost Category": ["Production", "Transportation", "Inventory Holding", "Waste Penalties"],
                "Value (€)": [current_data["Prod Cost"], current_data["Trans Cost"], current_data["Hold Cost"], current_data["Waste Cost"]]
            })
            st.bar_chart(data=cost_df, x="Cost Category", y="Value (€)", use_container_width=True)
            
        with col_chart2:
            st.markdown("**Carbon Footprint Ledger**")
            st.metric(label="Total Carbon Footprint emissions", value=f"{current_data['CO2 Emitted (kg)']} kg CO₂e")
            st.progress(min(1.0, max(0.0, current_data['CO2 Emitted (kg)'] / 3000.0)))

        # Automated strategic diagnostic feedback block
        st.subheader("🧠 Corporate Logistics Audit & Feedback")
        if current_data["RSL (%)"] < 70.0:
            st.error(f"🚨 **Retailer Rejection Action Taken:** Your RSL dropped to {current_data['RSL (%)']}%, which is below the 70% contractual barrier. The supermarket rejected your entire delivery batch, triggering massive waste and monetary damage. You must decrease warehouse safety stock days or deploy Premium Cold Chain assets immediately!")
        elif current_data["OOS (%)"] > 12.0:
            st.warning("⚠️ **Severe Out-of-Stock Alert:** Your OOS rate is too high. You are leaving free profit on the table because store shelves are sitting empty during high-demand peak days. Boost your safety stock coverage or increase your shipment frequency.")
        elif current_data["Food Waste (%)"] > 15.0:
            st.warning("🪰 **Unsustainable Product Disposal:** Food waste is cutting deep into your margins. In the F&B sector, excessive batch sizes combined with low transport frequencies kill your speed-to-market loop.")
        else:
