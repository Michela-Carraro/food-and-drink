
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Paris F&D Last-Mile Control Tower",
    page_icon="🚚",
    layout="wide"
)

# Initialize Session State for Multi-Round Simulation
if "round_num" not in st.session_state:
    st.session_state.round_num = 1

if "ledger" not in st.session_state:
    st.session_state.ledger = []

if "validated" not in st.session_state:
    st.session_state.validated = False

if "track_lock" not in st.session_state:
    st.session_state.track_lock = (
        "MarchéFrais Paris: Mass E-Grocery (15,000 orders/wk)"
    )

# Header
st.title("🚚🍾 Paris E-Grocery & Gastronomy Last-Mile Control Tower")

st.markdown(
    "**NEOMA Business School — Master's in Food & Drink Retailing and Logistics**"
)

# Market Scenario Banner
round_events = {
    1: (
        "☀️ Round 1: Baseline Parisian Demand",
        "Standard operating conditions across Greater Paris (Île-de-France). "
        "Establish a profitable fulfilment baseline."
    ),
    2: (
        "🌡️ Round 2: Summer Heatwave & Chilled Surge (+20% Demand)",
        "Extreme heat increases chilled/wine order volume by 20%, "
        "but unconditioned in-store picking suffers double spoilage (+4% waste)!"
    ),
    3: (
        "🌱 Round 3: Paris ZFE Low-Emission Zone Surcharge (+25% Courier Cost)",
        "New municipal traffic restrictions in central Paris raise "
        "hourly van/driver costs by 25% unless drop density is maximized."
    )
}

event_title, event_desc = round_events[st.session_state.round_num]

st.info(f"**{event_title}:** {event_desc}")

st.divider()

col_left, col_right = st.columns([1.05, 1.95])

# ==============================================================================
# LEFT PANEL: EXECUTIVE DECISION CONSOLE
# ==============================================================================

with col_left:

    st.header(f"🎛️ Round {st.session_state.round_num} Decisions")

    track_options = [
        "MarchéFrais Paris: Mass E-Grocery (15,000 orders/wk)",
        "Caves & Terroirs Paris: Fine Wine & Gastronomy (3,500 orders/wk)"
    ]

    selected_track = st.selectbox(
        "1. Business Track",
        options=track_options,
        index=track_options.index(st.session_state.track_lock),
        disabled=(len(st.session_state.ledger) > 0),
        help="Reset simulation to switch business tracks."
    )

    st.session_state.track_lock = selected_track
    is_grocery = selected_track.startswith("MarchéFrais")

    fulfillment_model = st.selectbox(
        "2. Fulfilment Node Architecture",
        options=[
            "In-Store / Backroom Picking (Low CAPEX | 70 UPH)",
            "Manual Climate-Controlled Dark Store (Medium CAPEX | 180 UPH)",
            "Automated Robotic CFC - Ocado Style (High CAPEX | 550 UPH)"
        ]
    )

    delivery_window = st.radio(
        "3. Last-Mile Routing & Delivery Window",
        options=[
            "1-Hour On-Demand Express (Scattered drops: 3.0 drops/hr)",
            "Picnic-Style Scheduled Milk-Run (Clustered routes: 10.5 drops/hr)"
        ]
    )

    min_basket = st.slider(
        "4. Minimum Order Threshold (€)",
        min_value=40 if is_grocery else 80,
        max_value=120 if is_grocery else 250,
        value=60 if is_grocery else 120,
        step=10
    )

    delivery_fee = st.slider(
        "5. Customer Delivery Fee (€)",
        min_value=0.0,
        max_value=15.0,
        value=4.0 if is_grocery else 9.0,
        step=0.5
    )

    st.markdown("---")

    run_btn = st.button(
        "🚀 Validate & Run Round Simulation",
        use_container_width=True,
        type="primary"
    )


# ==============================================================================
# BACKEND SIMULATION ENGINE
# ==============================================================================

if run_btn:

    r = st.session_state.round_num

    demand_surge = 1.20 if r == 2 else 1.0
    courier_cost_multiplier = 1.25 if r == 3 else 1.0
    heatwave_spoilage_penalty = 0.04 if r == 2 else 0.0

    if is_grocery:
        BASE_ORDERS = 15000 * demand_surge
        BASE_BASKET = 95.0
        GROSS_MARGIN_RATE = 0.26
        AVG_ITEM_PRICE = 2.0
        PACKAGING_PER_ORDER = 0.85
        VAN_HOURLY = 38.0 * courier_cost_multiplier
        REF_MIN = 60.0
        REF_FEE = 4.0

    else:
        BASE_ORDERS = 3500 * demand_surge
        BASE_BASKET = 185.0
        GROSS_MARGIN_RATE = 0.38
        AVG_ITEM_PRICE = 18.5
        PACKAGING_PER_ORDER = 4.80
        VAN_HOURLY = 46.0 * courier_cost_multiplier
        REF_MIN = 120.0
        REF_FEE = 9.0

    # Demand elasticity
    elasticity = (
        1.0
        - ((min_basket - REF_MIN) * 0.005)
        - ((delivery_fee - REF_FEE) * 0.03)
    )

    if delivery_window.startswith("Picnic"):
        elasticity -= 0.06

    weekly_orders = max(500, int(BASE_ORDERS * elasticity))

    avg_basket = max(
        BASE_BASKET,
        min_basket + (25.0 if is_grocery else 45.0)
    )

    items_per_order = max(4, int(avg_basket / AVG_ITEM_PRICE))

    # Financials per order
    gross_margin_per_order = avg_basket * GROSS_MARGIN_RATE

    if fulfillment_model.startswith("In-Store"):

        uph = 70
        weekly_capex = 5000 if is_grocery else 3500
        spoilage_rate = (
            (0.035 if is_grocery else 0.02)
            + heatwave_spoilage_penalty
        )
        hub_label = "Local Supermarkets (In-Store)"

    elif fulfillment_model.startswith("Manual"):

        uph = 180
        weekly_capex = 22000 if is_grocery else 14000
        spoilage_rate = (
            (0.015 if is_grocery else 0.008)
            + (heatwave_spoilage_penalty * 0.25)
        )
        hub_label = "Paris Urban Dark Store"

    else:

        uph = 550
        weekly_capex = 65000
        spoilage_rate = 0.004
        hub_label = "Fleury-Mérogis Robotic CFC"

    hourly_picker = 22.0

    picking_labor_per_order = (
        items_per_order / uph
    ) * hourly_picker

    drops_per_hr = (
        3.0 if delivery_window.startswith("1-Hour") else 10.5
    )

    last_mile_per_order = VAN_HOURLY / drops_per_hr

    spoilage_per_order = avg_basket * spoilage_rate

    capex_per_order = weekly_capex / weekly_orders

    net_contrib_per_order = (
        gross_margin_per_order
        + delivery_fee
        - picking_labor_per_order
        - PACKAGING_PER_ORDER
        - last_mile_per_order
        - spoilage_per_order
        - capex_per_order
    )

    weekly_net_profit = net_contrib_per_order * weekly_orders

    active_vans_needed = int(
        np.ceil((weekly_orders / drops_per_hr) / 40.0)
    )

    co2_per_order = (
        (1.8 if delivery_window.startswith("1-Hour") else 0.45)
        * (1.3 if not is_grocery else 1.0)
    )

    weekly_co2_tons = (
        weekly_orders * co2_per_order
    ) / 1000.0

    # Customer Satisfaction
    csat = (
        94.0
        - (max(0.0, delivery_fee - REF_FEE) * 1.8)
        - (max(0.0, min_basket - REF_MIN) * 0.12)
    )

    if fulfillment_model.startswith("In-Store"):
        csat -= 8.0 + (4.0 if r == 2 else 0.0)

    if delivery_window.startswith("Picnic"):
        csat -= 3.5

    csat = max(0.0, min(100.0, csat))

    # Save results in ledger
    st.session_state.ledger.append({
        "Round": f"Round {r}",
        "Architecture": hub_label,
        "Routing": (
            "1-Hr Express"
            if delivery_window.startswith("1-Hour")
            else "Milk-Run"
        ),
        "Orders/Wk": weekly_orders,
        "Avg Basket (€)": round(avg_basket, 1),
        "Net Profit (€)": round(weekly_net_profit, 0),
        "Unit Margin (€)": round(net_contrib_per_order, 2),
        "CSAT (%)": round(csat, 1),
        "Vans Fleet": active_vans_needed,
        "CO2 (Tons)": round(weekly_co2_tons, 2),

        # Waterfall components
        "wf_gm": gross_margin_per_order,
        "wf_fee": delivery_fee,
        "wf_pick": -picking_labor_per_order,
        "wf_pack": -PACKAGING_PER_ORDER,
        "wf_van": -last_mile_per_order,
        "wf_spoil": -spoilage_per_order,
        "wf_capex": -capex_per_order,

        "is_express": delivery_window.startswith("1-Hour"),
        "is_cfc": fulfillment_model.startswith("Automated")
    })

    st.session_state.validated = True


# ==============================================================================
# RIGHT PANEL: VISUAL CONTROL TOWER DASHBOARD
# ==============================================================================

with col_right:

    if not st.session_state.validated:

        st.warning(
            "👈 Configure your network parameters on the left and click "
            "**Validate & Run Round Simulation** to generate your visual "
            "P&L and network telemetry."
        )

        # Initial network diagram preview
        st.subheader("🗺️ Supply Chain Network Topology Preview")

        st.graphviz_chart("""
        digraph {
            rankdir=LR;
            node [shape=box, style="rounded,filled",
                  fontname="Helvetica", fontsize=10];

            Supplier [
                label="Producers / Vineyards\\n(Chilled & Cellar)",
                fillcolor="#EEE8F5",
                color="#562c80"
            ];

            Hub [
                label="Fulfilment Node\\n(Store / Dark Store / CFC)",
                fillcolor="#F7F5FA",
                color="#562c80"
            ];

            Fleet [
                label="Last-Mile Fleet\\n(Electric Vans)",
                fillcolor="#EEE8F5",
                color="#562c80"
            ];

            Customer [
                label="Paris Households\\n(1-Hr vs. Milk-Run)",
                fillcolor="#562c80",
                fontcolor="white"
            ];

            Supplier -> Hub [label="Primary Freight"];
            Hub -> Fleet [label="Multi-Temp Totes"];
            Fleet -> Customer [label="Last-Mile Drops"];
        }
        """)

    else:

        curr = st.session_state.ledger[-1]

        st.header(
            f"📊 {curr['Round']} Control Tower Telemetry"
        )

        # Top KPI Metrics Row
        k1, k2, k3, k4, k5 = st.columns(5)

        prof = curr["Net Profit (€)"]

        prof_str = (
            f"-€{abs(prof):,.0f}"
            if prof < 0
            else f"€{prof:,.0f}"
        )

        u_prof = curr["Unit Margin (€)"]

        u_str = (
            f"-€{abs(u_prof):.2f}"
            if u_prof < 0
            else f"+€{u_prof:.2f}"
        )

        k1.metric(
            "Weekly Net Profit",
            prof_str,
            delta=f"{u_str} / order"
        )

        k2.metric(
            "Weekly Orders",
            f"{curr['Orders/Wk']:,}",
            delta=f"€{curr['Avg Basket (€)']} avg basket"
        )

        k3.metric(
            "Customer CSAT",
            f"{curr['CSAT (%)']}%",
            delta="Target: >85%",
            delta_color=(
                "normal"
                if curr["CSAT (%)"] >= 85
                else "inverse"
            )
        )

        k4.metric(
            "Active Van Fleet",
            f"{curr['Vans Fleet']} vans",
            delta=curr["Routing"]
        )

        k5.metric(
            "Weekly CO₂",
            f"{curr['CO2 (Tons)']} t",
            delta="Scope 3 Last-Mile"
        )

        st.divider()

        # Visual Row 1
        v_col1, v_col2 = st.columns([1.3, 1.0])

        # Unit Economics Waterfall
        with v_col1:

            st.subheader(
                "💶 Per-Order Unit Economics Waterfall (€)"
            )

            fig_wf = go.Figure(
                go.Waterfall(
                    orientation="v",

                    measure=[
                        "relative", "relative", "relative",
                        "relative", "relative", "relative",
                        "relative", "total"
                    ],

                    x=[
                        "Product Margin",
                        "Delivery Fee",
                        "Picking Labor",
                        "Thermal Pack",
                        "Last-Mile Van",
                        "Spoilage",
                        "Facility CAPEX",
                        "Net / Order"
                    ],

                    textposition="outside",

                    text=[
                        f"+€{curr['wf_gm']:.1f}",
                        f"+€{curr['wf_fee']:.1f}",
                        f"-€{abs(curr['wf_pick']):.1f}",
                        f"-€{abs(curr['wf_pack']):.1f}",
                        f"-€{abs(curr['wf_van']):.1f}",
                        f"-€{abs(curr['wf_spoil']):.1f}",
                        f"-€{abs(curr['wf_capex']):.1f}",
                        f"€{curr['Unit Margin (€)']:.2f}"
                    ],

                    y=[
                        curr["wf_gm"],
                        curr["wf_fee"],
                        curr["wf_pick"],
                        curr["wf_pack"],
                        curr["wf_van"],
                        curr["wf_spoil"],
                        curr["wf_capex"],
                        0
                    ],

                    increasing={
                        "marker": {"color": "#2E7D32"}
                    },

                    decreasing={
                        "marker": {"color": "#C62828"}
                    },

                    totals={
                        "marker": {"color": "#562c80"}
                    }
                )
            )

            fig_wf.update_layout(
                height=340,
                margin=dict(l=10, r=10, t=20, b=20),
                showlegend=False
            )

            st.plotly_chart(
                fig_wf,
                use_container_width=True
            )

        # Paris Delivery Drop Density
        with v_col2:

            st.subheader("🗺️ Paris Delivery Drop Density")

            np.random.seed(
                42 + st.session_state.round_num
            )

            if curr["is_express"]:

                # Scattered Île-de-France deliveries
                lats = np.random.normal(
                    48.8566, 0.045, 80
                )

                lons = np.random.normal(
                    2.3522, 0.065, 80
                )

            else:

                # Clustered neighbourhood milk-run routes
                lats = np.concatenate([
                    np.random.normal(48.865, 0.008, 40),
                    np.random.normal(48.845, 0.008, 40)
                ])

                lons = np.concatenate([
                    np.random.normal(2.335, 0.010, 40),
                    np.random.normal(2.375, 0.010, 40)
                ])

            map_df = pd.DataFrame({
                "lat": lats,
                "lon": lons
            })

            st.map(
                map_df,
                zoom=10,
                use_container_width=True
            )

            st.caption(
                f"📍 **Hub:** {curr['Architecture']} | "
                f"**Fleet:** {curr['Vans Fleet']} refrigerated "
                "electric vans active."
            )

        # Diagnostic Executive Alert
        if (
            curr["Net Profit (€)"] > 0
            and curr["CSAT (%)"] >= 85.0
        ):

            st.success(
                f"💎 **Executive Target Achieved!** "
                f"Your {curr['Architecture']} + {curr['Routing']} "
                f"network generated "
                f"**€{curr['Net Profit (€)']:,.0f}/week** "
                f"with **{curr['CSAT (%)']}% CSAT**."
            )

        elif curr["Net Profit (€)"] <= 0:

            if not is_grocery and curr["is_cfc"]:

                st.error(
                    "🚨 **CAPEX Over-Investment Trap:** "
                    "At 3,500 fine wine/gourmet orders/week, "
                    "a €65k/wk robotic CFC costs €18+ per order "
                    "in fixed overhead alone! Switch to a Manual "
                    "Climate-Controlled Dark Store."
                )

            else:

                st.error(
                    "🚨 **Negative Unit Economics:** "
                    "Look at the red bars in the Waterfall Chart "
                    "above—your picking labor or last-mile van "
                    "cost per order is eating your entire gross margin!"
                )

        else:

            st.warning(
                "⚠️ **Profitable, but CSAT < 85%:** "
                "High fees, high minimum baskets, or in-store "
                "stockouts are hurting customer retention."
            )

        # Historical Multi-Round Ledger
        st.divider()

        st.subheader("📜 Multi-Round P&L Ledger")

        display_cols = [
            "Round",
            "Architecture",
            "Routing",
            "Orders/Wk",
            "Net Profit (€)",
            "Unit Margin (€)",
            "CSAT (%)",
            "Vans Fleet",
            "CO2 (Tons)"
        ]

        st.dataframe(
            pd.DataFrame(st.session_state.ledger)[display_cols],
            use_container_width=True,
            hide_index=True
        )

        # Round Progression Buttons
        b1, b2 = st.columns(2)

        with b1:

            if st.session_state.round_num < 3:

                if st.button(
                    f"➡️ Advance to Round "
                    f"{st.session_state.round_num + 1} "
                    "(Next Market Shock)"
                ):

                    st.session_state.round_num += 1
                    st.session_state.validated = False
                    st.rerun()

            else:

                st.success(
                    "🏆 **3-Round Simulation Complete!** "
                    "Export or screenshot your Multi-Round P&L Ledger."
                )

        with b2:

            if st.button("🔄 Reset Simulation / Switch Track"):

                st.session_state.round_num = 1
                st.session_state.ledger = []
                st.session_state.validated = False
                st.rerun()
