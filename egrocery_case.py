import streamlit as st
import pandas as pd

st.set_page_config(page_title="Paris E-Grocery Last-Mile Case", page_icon="🚚", layout="wide")

st.title("🚚 Case Study Simulator: Paris E-Grocery Fulfillment")
st.subheader("Master's Consulting Challenge: Fixing Negative Last-Mile Unit Economics")

st.markdown("""
**Case Context:** *MarchéFrais Paris* processes **15,000 online grocery orders per week** (Average Basket: **€95**, Gross Product Margin: **26%**). 
Currently, the company loses money on every delivery due to slow manual in-store picking and inefficient 1-hour delivery windows. 
**Your Mission:** Configure the fulfillment network below to achieve a **positive Weekly Net Profit** while maintaining **Customer Satisfaction > 85%**.
""")

st.divider()

col_left, col_right = st.columns([1, 2])

with col_left:
    st.header("🎛️ Network Decisions")
    
    fulfillment_model = st.selectbox(
        "1. Fulfillment Facility Architecture",
        options=[
            "In-Store Picking (Low CAPEX, 70 UPH)",
            "Manual Urban Dark Store (Medium CAPEX, 180 UPH)",
            "Automated Robotic MFC - Ocado Style (High CAPEX, 550 UPH)"
        ]
    )
    
    delivery_window = st.radio(
        "2. Customer Delivery Window Promise",
        options=[
            "1-Hour On-Demand Slots (High customer appeal, 3 drops/hr)",
            "Picnic Milk-Run Fixed Routes (Next-day 20-min window, 10 drops/hr)"
        ]
    )
    
    min_basket = st.slider(
        "3. Minimum Order Basket Threshold (€)",
        min_value=40, max_value=100, value=60, step=10,
        help="Higher minimums boost margin per order, but reduce total weekly order volume."
    )
    
    delivery_fee = st.slider(
        "4. Customer Delivery Fee Charged (€)",
        min_value=0.0, max_value=8.0, value=4.0, step=0.5
    )

# --- BACKEND ECONOMICS ENGINE ---
# Demand elasticity based on minimum basket and delivery fee
demand_factor = 1.0 - ((min_basket - 60) * 0.008) - ((delivery_fee - 4.0) * 0.04)
if delivery_window.startswith("Picnic"):
    demand_factor -= 0.08  # Slight demand drop for next-day vs instant

weekly_orders = max(2000, int(15000 * demand_factor))
avg_basket_value = max(95.0, min_basket + 25.0)
items_per_order = int(avg_basket_value / 2.0)

# Revenue & Gross Product Margin
gross_merchandise_value = weekly_orders * avg_basket_value
product_gross_margin = gross_merchandise_value * 0.26
fee_revenue = weekly_orders * delivery_fee

# Picking Labor & Facility CAPEX (Weekly amortized)
if fulfillment_model.startswith("In-Store"):
    uph = 70
    weekly_capex_rent = 5000
    spoilage_rate = 0.04
elif fulfillment_model.startswith("Manual"):
    uph = 180
    weekly_capex_rent = 22000
    spoilage_rate = 0.015
else:
    uph = 550
    weekly_capex_rent = 65000
    spoilage_rate = 0.004

hourly_picker_wage = 22.0
picking_cost_per_order = (items_per_order / uph) * hourly_picker_wage
total_picking_cost = weekly_orders * picking_cost_per_order

# Last-Mile Van & Driver Costs
drops_per_hour = 3.0 if delivery_window.startswith("1-Hour") else 10.0
hourly_van_driver_cost = 38.0  # Refrigerated electric van + driver
last_mile_cost_per_order = hourly_van_driver_cost / drops_per_hour
total_last_mile_cost = weekly_orders * last_mile_cost_per_order

# Spoilage & Stockout Substitutions
total_spoilage_cost = gross_merchandise_value * spoilage_rate

# Net Weekly Profit
weekly_net_profit = (
    product_gross_margin
    + fee_revenue
    - weekly_capex_rent
    - total_picking_cost
    - total_last_mile_cost
    - total_spoilage_cost
)

# Customer Satisfaction Score
csat = 92.0 - (delivery_fee * 1.5) - ((min_basket - 50) * 0.15)
if fulfillment_model.startswith("In-Store"):
    csat -= 8.0  # Frequent out-of-stocks from store shelf competition
if delivery_window.startswith("Picnic"):
    csat -= 4.0
csat = max(0.0, min(100.0, csat))

# --- DASHBOARD OUTPUT ---
with col_right:
    st.header("📊 Weekly E-Grocery P&L & KPIs")
    
    m1, m2, m3, m4 = st.columns(4)
    profit_str = f"-€{abs(weekly_net_profit):,.0f}" if weekly_net_profit < 0 else f"€{weekly_net_profit:,.0f}"
    m1.metric("Weekly Net Profit", profit_str)
    m2.metric("Active Weekly Orders", f"{weekly_orders:,}")
    m3.metric("Fulfillment Cost / Order", f"€{(picking_cost_per_order + last_mile_cost_per_order):.2f}")
    m4.metric("Customer Satisfaction", f"{csat:.1f}%")
    
    st.divider()
    
    cost_df = pd.DataFrame({
        "Cost Driver": ["Facility & Robotics CAPEX", "Picking Labor", "Last-Mile Vans", "Fresh Spoilage"],
        "Weekly Cost (€)": [weekly_capex_rent, total_picking_cost, total_last_mile_cost, total_spoilage_cost]
    })
    st.bar_chart(cost_df, x="Cost Driver", y="Weekly Cost (€)", use_container_width=True)
    
    if weekly_net_profit > 0 and csat >= 85.0:
        st.success("✅ **Profitable & Customer-Approved!** You solved the Parisian e-grocery equation.")
    elif weekly_net_profit <= 0:
        st.error("🚨 **Negative Unit Economics:** Your picking and last-mile costs exceed your basket margin. Look at drop density (drops/hr) or facility CAPEX vs. order volume!")
    else:
        st.warning("⚠️ **Profitable, but Low Satisfaction (<85%):** Your high minimum basket or delivery fees are driving customers to competitors.")
