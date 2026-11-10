
import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Food and Drink Retailing and Logistics Simulation",
    page_icon="🍊",
    layout="wide"
)

# Main title and course description
st.title("🍊 Food and Drink Retailing and Logistics Simulation")
st.subheader("Master's Programme in Food and Drink Retailing and Logistics")

st.markdown("""
Welcome to the interactive logistics optimization simulation for **JuiceCo**,
a premium fresh orange juice manufacturing company.

Your objective as the Logistics Management Team is to maximize **Net Profit**
while minimizing **Food Waste**, finding the optimal balance between
transportation costs, biological cold chain constraints, and contractual
penalties imposed by large-scale retailers.
""")

st.divider()

# Input and output columns
col_input, col_output = st.columns([1, 2])

with col_input:
    st.header("🛠️ Strategic Decisions")
    st.markdown("Adjust the logistics parameters for the next operational round:")

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


# --- SIMULATION ENGINE (BACKEND LOGIC) ---

# Fixed market parameters
WEEKLY_POTENTIAL_DEMAND = 10000
RETAIL_SELLING_PRICE = 5.00
WHOLESALE_SELLING_PRICE = 3.50
UNIT_PRODUCTION_COST = 2.00
TOTAL_SHELF_LIFE_DAYS = 24
CONTRACTUAL_RSL_THRESHOLD = 70.0  # Carrefour rejects products below 70%

# Transit time and degradation calculation
base_transit_days = (
    2 if days_between_deliveries == 1
    else (4 if days_between_deliveries == 3 else 7)
)

if batch_size > 5000:
    base_transit_days += 1  # Delays caused by consolidating larger batches

# Cold chain impact on accelerated degradation
degradation_multiplier = (
    1.0 if cold_chain_level.startswith("Premium") else 1.3
)

shelf_life_lost_in_transit = base_transit_days * degradation_multiplier

# Remaining Shelf Life (RSL) upon arrival
remaining_shelf_life_days = (
    TOTAL_SHELF_LIFE_DAYS
    - shelf_life_lost_in_transit
    - safety_stock_days
)

rsl_percentage = (
    remaining_shelf_life_days / TOTAL_SHELF_LIFE_DAYS
) * 100

rsl_percentage = max(0.0, min(100.0, rsl_percentage))

# Food Waste calculation
shelf_saturation_risk = (
    batch_size / 2000
) * (
    days_between_deliveries / 2
)

food_waste_percent = (
    2.0
    + (safety_stock_days * 3.5)
    + (shelf_saturation_risk * 1.5)
)

if rsl_percentage < CONTRACTUAL_RSL_THRESHOLD:
    food_waste_percent += 40.0  # Major penalty if products arrive below retailer requirements

food_waste_percent = max(0.0, min(100.0, food_waste_percent))

# Out-of-Stock (OOS) calculation
oos_percent = (
    15.0
    - (safety_stock_days * 3.0)
    + (days_between_deliveries * 2.0)
)

if batch_size < 1000 and days_between_deliveries > 3:
    oos_percent += 25.0  # Critical understocking

oos_percent = max(0.0, min(100.0, oos_percent))


# --- FINANCIAL PERFORMANCE ---

requested_units = WEEKLY_POTENTIAL_DEMAND

units_lost_to_oos = requested_units * (oos_percent / 100)

potentially_delivered_units = requested_units - units_lost_to_oos

expired_wasted_units = (
    potentially_delivered_units * (food_waste_percent / 100)
)

healthy_units_sold = potentially_delivered_units - expired_wasted_units

# Cost items
total_production_cost = (
    potentially_delivered_units * UNIT_PRODUCTION_COST
)

# Transportation costs influenced by strategic decisions
base_trip_cost = (
    300 if days_between_deliveries == 1
    else (600 if days_between_deliveries == 3 else 1200)
)

if cold_chain_level.startswith("Premium"):
    base_trip_cost *= 1.4  # Additional cost for advanced refrigerated vehicles and energy

weekly_number_of_trips = 7 / days_between_deliveries

total_transportation_cost = (
    base_trip_cost * weekly_number_of_trips
)

inventory_holding_cost = safety_stock_days * 250

contractual_penalties = (
    expired_wasted_units * WHOLESALE_SELLING_PRICE
)

# Revenue and net profit
total_revenue = healthy_units_sold * WHOLESALE_SELLING_PRICE

net_profit = (
    total_revenue
    - total_production_cost
    - total_transportation_cost
    - inventory_holding_cost
    - contractual_penalties
)

# Indicative carbon footprint calculation
transportation_co2 = (
    weekly_number_of_trips * 120
) / (batch_size / 2000)

refrigeration_co2 = (
    450 if cold_chain_level.startswith("Premium") else 200
)

total_co2_kg = (
    transportation_co2
    + refrigeration_co2
    + (expired_wasted_units * 0.1)
)


# --- RESULTS DASHBOARD ---

with col_output:
    st.header("📊 Performance Dashboard (Weekly Results)")

    # Main KPIs
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    kpi1.metric(
        label="Net Profit",
        value=f"€ {net_profit:,.2f}",
        delta=(
            f"Actual unit margin: € "
            f"{((net_profit / healthy_units_sold) if healthy_units_sold > 0 else 0):.2f}"
        ),
        delta_color="normal" if net_profit > 0 else "inverse"
    )

    kpi2.metric(
        label="Food Waste",
        value=f"{food_waste_percent:.1f}%",
        delta="CRITICAL" if food_waste_percent > 20 else "Acceptable",
        delta_color="inverse" if food_waste_percent > 20 else "normal"
    )

    kpi3.metric(
        label="Remaining Shelf Life (RSL)",
        value=f"{rsl_percentage:.1f}%",
        delta=(
            "Retailer Rejection (<70%)"
            if rsl_percentage < CONTRACTUAL_RSL_THRESHOLD
            else "Compliant"
        ),
        delta_color=(
            "normal"
            if rsl_percentage >= CONTRACTUAL_RSL_THRESHOLD
            else "inverse"
        )
    )

    kpi4.metric(
        label="Out-of-Stock (OOS)",
        value=f"{oos_percent:.1f}%",
        delta="Empty Shelves" if oos_percent > 10 else "Optimal",
        delta_color="inverse" if oos_percent > 10 else "normal"
    )

    st.divider()

    # Cost charts and trade-off analysis
    st.subheader("📉 Cost Structure and Sustainability")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**Operating Cost Breakdown (€)**")

        cost_data = {
            "Cost Category": [
                "Production",
                "Refrigerated Transportation",
                "Inventory Holding",
                "Expired / Rejected Goods Penalties"
            ],
            "Value (€)": [
                float(total_production_cost),
                float(total_transportation_cost),
                float(inventory_holding_cost),
                float(contractual_penalties)
            ]
        }

        df_costs = pd.DataFrame(cost_data)

        st.bar_chart(
            data=df_costs,
            x="Cost Category",
            y="Value (€)",
            use_container_width=True
        )

    with col_chart2:
        st.markdown("**Environmental Impact of the Strategy**")

        st.metric(
            label="Total CO₂ Equivalent Emissions",
            value=f"{total_co2_kg:.1f} kg CO₂e"
        )

        st.progress(
            min(1.0, max(0.0, total_co2_kg / 3000.0)),
            text="Supply Chain Environmental Capacity Utilization"
        )

    st.divider()

    # Automatic instructor feedback
    st.subheader("🧠 Logistics Consulting Report (Student Feedback)")

    if rsl_percentage < CONTRACTUAL_RSL_THRESHOLD:

        st.error(
            f"🚨 **Distribution Centre Load Rejection:** "
            f"Your Remaining Shelf Life (RSL) has fallen to "
            f"{rsl_percentage:.1f}%, below the contractual threshold of "
            f"{CONTRACTUAL_RSL_THRESHOLD}%. "
            f"The retailer has rejected the shipment and applied contractual penalties. "
            f"You should reduce inventory holding time or invest in a Premium Cold Chain "
            f"solution to slow down biological degradation!"
        )

    elif oos_percent > 12.0:

        st.warning(
            f"⚠️ **Empty Shelves at Retail Stores:** "
            f"You have a very high Out-of-Stock rate ({oos_percent:.1f}%). "
            f"You are losing market share and valuable profits because safety stock "
            f"is too low or deliveries are too infrequent to meet customer demand."
        )

    elif food_waste_percent > 15.0:

        st.warning(
            f"🪰 **Excessive Food Waste:** "
            f"You are discarding too much orange juice due to oversized shipment batches "
            f"or excessive inventory holding time. Remember: in the food industry, "
            f"inventory that does not move eventually expires and destroys profit margins."
        )

    else:

        st.success(
            "💎 **Excellent Operational Balance!** "
            "You have successfully maintained contractual compliance with the retailer, "
            "controlled food waste, and protected retail shelves against stockouts. "
            "You are ready to present your logistics strategy!"
        )
