
import streamlit as st
import pandas as pd
import io
from datetime import datetime, timezone

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Food and Drink Retailing and Logistics Simulation",
    page_icon="🍾",
    layout="wide"
)

# ============================================================
# GOOGLE SHEETS DATABASE
# ============================================================

TEAM_HEADERS = [
    "Team Name",
    "Created At"
]

ROUND_HEADERS = [
    "Timestamp",
    "Team Name",
    "Scenario",
    "Round",
    "Batch Size",
    "Delivery Frequency",
    "Days Between Deliveries",
    "Cold Chain",
    "Safety Stock Days",
    "Net Profit (€)",
    "Waste (%)",
    "Integrity (%)",
    "OOS (%)",
    "CO2 (kg)",
    "Production Cost (€)",
    "Transport Cost (€)",
    "Holding Cost (€)",
    "Waste Cost (€)",
    "Units Sold",
    "Base Transit Days"
]


@st.cache_resource
def connect_to_google_sheets():

    credentials = dict(st.secrets["gcp_service_account"])

    client = __import__("gspread").service_account_from_dict(
        credentials
    )

    spreadsheet_id = st.secrets["google_sheet"]["spreadsheet_id"]

    spreadsheet = client.open_by_key(spreadsheet_id)

    return spreadsheet


def get_or_create_worksheet(spreadsheet, name, headers):

    try:
        worksheet = spreadsheet.worksheet(name)

    except Exception:
        worksheet = spreadsheet.add_worksheet(
            title=name,
            rows=2000,
            cols=len(headers)
        )

    existing_headers = worksheet.row_values(1)

    if not existing_headers:
        worksheet.append_row(headers)
    elif existing_headers != headers:
        raise ValueError(
            f"The headers in the '{name}' worksheet do not match "
            "the expected application structure. "
            "Please check the spreadsheet."
        )

    return worksheet


def initialize_database():

    spreadsheet = connect_to_google_sheets()

    teams_sheet = get_or_create_worksheet(
        spreadsheet,
        "Teams",
        TEAM_HEADERS
    )

    rounds_sheet = get_or_create_worksheet(
        spreadsheet,
        "RoundData",
        ROUND_HEADERS
    )

    return teams_sheet, rounds_sheet


def load_teams(teams_sheet):

    return pd.DataFrame(
        teams_sheet.get_all_records()
    )


def load_rounds(rounds_sheet):

    return pd.DataFrame(
        rounds_sheet.get_all_records()
    )


def register_team(teams_sheet, team_name):

    existing_teams = load_teams(teams_sheet)

    if not existing_teams.empty:

        existing_names = (
            existing_teams["Team Name"]
            .astype(str)
            .str.strip()
            .str.casefold()
        )

        if team_name.casefold() in existing_names.values:
            return

    teams_sheet.append_row(
        [
            team_name,
            datetime.now(timezone.utc).isoformat()
        ],
        value_input_option="USER_ENTERED"
    )


def save_round(rounds_sheet, result):

    rounds_sheet.append_row(
        [result.get(header, "") for header in ROUND_HEADERS],
        value_input_option="USER_ENTERED"
    )


# ============================================================
# SIMULATION ENGINE
# ============================================================

def run_simulation(
    is_juice,
    batch_size,
    days_between_deliveries,
    cold_chain_level,
    safety_stock_days
):

    if is_juice:

        demand = 10000
        selling_price = 3.50
        production_cost = 2.00
        shelf_life = 24
        threshold = 70.0

        glass_multiplier = 1.0
        holding_cost_per_day = 250.0

    else:

        demand = 3000
        selling_price = 28.00
        production_cost = 14.00
        shelf_life = 100
        threshold = 85.0

        glass_multiplier = 1.85
        holding_cost_per_day = 450.0

    # Transit time

    base_transit_days = (
        2 if days_between_deliveries == 1
        else 4 if days_between_deliveries == 3
        else 7
    )

    if (
        (is_juice and batch_size > 5000)
        or (not is_juice and batch_size > 2000)
    ):
        base_transit_days += 1

    # Product integrity

    if is_juice:

        degradation_multiplier = (
            1.0
            if cold_chain_level.startswith("Premium")
            else 1.35
        )

        shelf_life_lost = (
            base_transit_days * degradation_multiplier
        )

        remaining_days = (
            shelf_life
            - shelf_life_lost
            - safety_stock_days
        )

        integrity = max(
            0.0,
            min(
                100.0,
                remaining_days / shelf_life * 100
            )
        )

    else:

        thermal_loss = (
            1.2
            if cold_chain_level.startswith("Premium")
            else 4.5
        )

        quality_lost = (
            base_transit_days * thermal_loss
            + safety_stock_days * 0.4
        )

        integrity = max(
            0.0,
            min(100.0, 100.0 - quality_lost)
        )

    # Waste and rejection

    if is_juice:

        saturation_risk = (
            (batch_size / 2000)
            * (days_between_deliveries / 2)
        )

        waste = (
            2.0
            + safety_stock_days * 3.5
            + saturation_risk * 1.5
        )

        if integrity < threshold:
            waste += 45.0

    else:

        waste = 0.5 + base_transit_days * 0.3

        if integrity < threshold:
            waste += 35.0

    waste = max(0.0, min(100.0, waste))

    # Out of stock

    batch_ratio = batch_size / (
        2000 if is_juice else 600
    )

    oos = (
        15.0
        - safety_stock_days * 3.0
        + days_between_deliveries * 2.0
    )

    if batch_ratio < 0.5 and days_between_deliveries > 3:
        oos += 25.0

    oos = max(0.0, min(100.0, oos))

    # Financial performance

    lost_units = demand * oos / 100

    delivered_units = demand - lost_units

    rejected_units = delivered_units * waste / 100

    sold_units = delivered_units - rejected_units

    total_production_cost = (
        delivered_units * production_cost
    )

    trip_cost = (
        300 if days_between_deliveries == 1
        else 600 if days_between_deliveries == 3
        else 1200
    )

    if not is_juice:
        trip_cost *= 1.3

    if cold_chain_level.startswith("Premium"):
        trip_cost *= 1.4

    number_of_trips = 7 / days_between_deliveries

    transport_cost = trip_cost * number_of_trips

    inventory_cost = (
        safety_stock_days * holding_cost_per_day
    )

    waste_cost = rejected_units * selling_price

    revenue = sold_units * selling_price

    net_profit = (
        revenue
        - total_production_cost
        - transport_cost
        - inventory_cost
        - waste_cost
    )

    # Environmental performance

    normalized_batch = batch_size / (
        2000 if is_juice else 800
    )

    transport_co2 = (
        (number_of_trips * 120) / normalized_batch
    ) * glass_multiplier

    refrigeration_co2 = (
        450
        if cold_chain_level.startswith("Premium")
        else 180
    )

    total_co2 = (
        transport_co2
        + refrigeration_co2
        + rejected_units * 0.15
    )

    return {
        "Net Profit (€)": round(net_profit, 2),
        "Waste (%)": round(waste, 1),
        "Integrity (%)": round(integrity, 1),
        "OOS (%)": round(oos, 1),
        "CO2 (kg)": round(total_co2, 1),
        "Production Cost (€)": round(total_production_cost, 2),
        "Transport Cost (€)": round(transport_cost, 2),
        "Holding Cost (€)": round(inventory_cost, 2),
        "Waste Cost (€)": round(waste_cost, 2),
        "Units Sold": round(sold_units, 2),
        "Base Transit Days": base_transit_days
    }


# ============================================================
# DATABASE CONNECTION
# ============================================================

try:

    teams_sheet, rounds_sheet = initialize_database()

except Exception as error:

    st.error(
        "Unable to connect to Google Sheets. "
        "Please check your Google credentials and spreadsheet access."
    )

    st.exception(error)
    st.stop()


# ============================================================
# APPLICATION TITLE
# ============================================================

st.title("🍊🍾 Food and Drink Retailing and Logistics Simulation")

st.subheader(
    "Master's Programme in Food and Drink Retailing and Logistics "
    "(NEOMA BS)"
)

st.markdown("""
Welcome to the **Food and Drink Retailing and Logistics Simulation**.

A four-round supply chain strategy competition.
""")

st.divider()


# ============================================================
# NAVIGATION
# ============================================================

mode = st.sidebar.radio(
    "Application Access",
    [
        "Student Simulation",
        "Lecturer Dashboard"
    ]
)


# ============================================================
# LECTURER DASHBOARD
# ============================================================

if mode == "Lecturer Dashboard":

    st.header("🎓 Lecturer Administration")

    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:

        admin_password = st.text_input(
            "Lecturer Password",
            type="password"
        )

        if st.button("Access Lecturer Dashboard"):

            if admin_password == st.secrets["admin"]["password"]:

                st.session_state.admin_authenticated = True
                st.rerun()

            else:

                st.error("Incorrect password.")

    else:

        if st.button("Logout Lecturer"):
            st.session_state.admin_authenticated = False
            st.rerun()

        teams_df = load_teams(teams_sheet)
        data = load_rounds(rounds_sheet)

        st.subheader("📊 Overall Classroom Performance")

        if data.empty:

            st.info("No student submissions have been recorded yet.")

        else:

            # Data cleaning

            numeric_columns = [
                "Round",
                "Net Profit (€)",
                "Waste (%)",
                "Integrity (%)",
                "OOS (%)",
                "CO2 (kg)",
                "Units Sold",
                "Batch Size",
                "Days Between Deliveries",
                "Safety Stock Days"
            ]

            for column in numeric_columns:
                data[column] = pd.to_numeric(
                    data[column],
                    errors="coerce"
                )

            total_teams = (
                teams_df["Team Name"].nunique()
                if not teams_df.empty
                else data["Team Name"].nunique()
            )

            total_submissions = len(data)

            average_profit = data["Net Profit (€)"].mean()

            total_emissions = data["CO2 (kg)"].sum()

            k1, k2, k3, k4 = st.columns(4)

            k1.metric(
                "Participating Teams",
                total_teams
            )

            k2.metric(
                "Round Submissions",
                total_submissions
            )

            k3.metric(
                "Average Round Profit",
                f"€{average_profit:,.2f}"
            )

            k4.metric(
                "Total CO₂ Emissions",
                f"{total_emissions:,.1f} kg"
            )

            st.divider()

            # Team leaderboard

            st.subheader("🏆 Team Leaderboard")

            leaderboard = (
                data.groupby("Team Name")
                .agg(
                    Rounds_Completed=("Round", "nunique"),
                    Total_Profit=("Net Profit (€)", "sum"),
                    Average_Waste=("Waste (%)", "mean"),
                    Average_OOS=("OOS (%)", "mean"),
                    Average_Integrity=("Integrity (%)", "mean"),
                    Total_CO2=("CO2 (kg)", "sum")
                )
                .reset_index()
                .sort_values(
                    "Total_Profit",
                    ascending=False
                )
            )

            leaderboard.insert(
                0,
                "Rank",
                range(1, len(leaderboard) + 1)
            )

            leaderboard_display = leaderboard.rename(
                columns={
                    "Rounds_Completed": "Rounds",
                    "Total_Profit": "Total Profit (€)",
                    "Average_Waste": "Average Waste (%)",
                    "Average_OOS": "Average OOS (%)",
                    "Average_Integrity": "Average Integrity (%)",
                    "Total_CO2": "Total CO2 (kg)"
                }
            )

            st.dataframe(
                leaderboard_display,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            # Profitability chart

            st.subheader("💰 Profitability by Team")

            profit_chart = leaderboard[
                ["Team Name", "Total_Profit"]
            ].set_index("Team Name")

            st.bar_chart(profit_chart)

            # Round-by-round performance

            st.subheader("📈 Round-by-Round Profit Evolution")

            profit_evolution = data.pivot_table(
                index="Round",
                columns="Team Name",
                values="Net Profit (€)",
                aggfunc="sum"
            )

            st.line_chart(profit_evolution)

            st.divider()

            # Sustainability analysis

            st.subheader("🌱 Sustainability Comparison")

            sustainability = leaderboard[
                ["Team Name", "Total_CO2"]
            ].set_index("Team Name")

            st.bar_chart(sustainability)

            # Waste comparison

            st.subheader("📦 Waste and Rejection Comparison")

            waste_chart = leaderboard[
                ["Team Name", "Average_Waste"]
            ].set_index("Team Name")

            st.bar_chart(waste_chart)

            st.divider()

            # Team filtering

            st.subheader("🔍 Detailed Team Analysis")

            selected_team = st.selectbox(
                "Select a team",
                sorted(data["Team Name"].unique())
            )

            team_data = data[
                data["Team Name"] == selected_team
            ].sort_values("Round")

            st.markdown(f"### Team: {selected_team}")

            st.dataframe(
                team_data,
                use_container_width=True,
                hide_index=True
            )

            # Decisions analysis

            st.subheader("⚙️ Historical Logistics Decisions")

            decision_columns = [
                "Round",
                "Scenario",
                "Batch Size",
                "Delivery Frequency",
                "Cold Chain",
                "Safety Stock Days"
            ]

            st.dataframe(
                team_data[decision_columns],
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            # Download data

            st.subheader("📥 Export Classroom Data")

            csv_data = data.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "Download All Round Data (CSV)",
                data=csv_data,
                file_name="classroom_simulation_data.csv",
                mime="text/csv"
            )

            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(
                excel_buffer,
                engine="openpyxl"
            ) as writer:

                data.to_excel(
                    writer,
                    sheet_name="Round Data",
                    index=False
                )

                leaderboard_display.to_excel(
                    writer,
                    sheet_name="Leaderboard",
                    index=False
                )

                teams_df.to_excel(
                    writer,
                    sheet_name="Teams",
                    index=False
                )

            st.download_button(
                "Download Complete Excel Report",
                data=excel_buffer.getvalue(),
                file_name="food_drink_simulation.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )


# ============================================================
# STUDENT SIMULATION
# ============================================================

else:

    st.header("👥 Student Team Access")

    # Login

    if "team_name" not in st.session_state:

        with st.form("team_login"):

            team_name_input = st.text_input(
                "Enter your team name",
                max_chars=40,
                placeholder="e.g. Team Champagne"
            )

            login_button = st.form_submit_button(
                "🚀 Enter Simulation",
                use_container_width=True
            )

        if login_button:

            team_name_input = team_name_input.strip()

            if len(team_name_input) < 2:

                st.error("Please enter a valid team name.")

            else:

                register_team(
                    teams_sheet,
                    team_name_input
                )

                st.session_state.team_name = team_name_input

                st.rerun()

        st.stop()

    # Logged-in team

    team_name = st.session_state.team_name

    st.sidebar.success(f"Logged in: {team_name}")

    if st.sidebar.button("Logout Team"):

        del st.session_state.team_name
        st.rerun()

    st.header(f"🏁 Welcome, {team_name}!")

    # Load shared team history

    all_data = load_rounds(rounds_sheet)

    if all_data.empty:

        team_data = pd.DataFrame()

    else:

        team_data = all_data[
            all_data["Team Name"].astype(str).str.casefold()
            == team_name.casefold()
        ].copy()

        if not team_data.empty:

            team_data["Round"] = pd.to_numeric(
                team_data["Round"],
                errors="coerce"
            )

            team_data = team_data.sort_values("Round")

    # Scenario selection

    scenario_options = [
        "JuiceCo: Fresh Orange Juice (Mass Grocery Retail)",
        "Maison Reims: Vintage Champagne Export (Wine & Gastronomy)"
    ]

    if not team_data.empty:

        active_scenario = team_data.iloc[0]["Scenario"]

        st.info(
            f"Selected product track: **{active_scenario}**"
        )

    else:

        active_scenario = st.selectbox(
            "Select your Supply Chain Scenario",
            scenario_options
        )

    is_juice = active_scenario.startswith("JuiceCo")

    # Determine current round

    completed_rounds = (
        team_data["Round"].dropna().astype(int).tolist()
        if not team_data.empty
        else []
    )

    if completed_rounds:

        current_round = max(completed_rounds) + 1

    else:

        current_round = 1

    # ========================================================
    # DECISION INTERFACE
    # ========================================================

    if current_round <= 4:

        st.divider()

        st.header(
            f"🛠️ Round {current_round} Decisions"
        )

        st.markdown("""
        Configure your logistics strategy and submit your decisions.
        Each round is saved automatically to the shared database.
        """)

        with st.form(
            f"decision_form_{team_name}_{current_round}"
        ):

            # Shipment batch

            batch_size = st.slider(
                "Shipment Batch Size (Bottles)",
                min_value=500,
                max_value=10000 if is_juice else 4000,
                value=2000 if is_juice else 1000,
                step=500 if is_juice else 250
            )

            # Delivery frequency

            frequency_options = {
                "Daily": 1,
                "Twice a Week": 3,
                "Weekly": 7
            }

            frequency_label = st.selectbox(
                "Delivery Frequency to Retail DC / Export Hub",
                list(frequency_options.keys()),
                index=1
            )

            days_between = frequency_options[frequency_label]

            # Cold chain

            cold_chain = st.radio(
                "Thermal & Handling Investment",
                [
                    "Standard (Ambient/Basic Transport - Low Investment)",
                    "Premium (Continuous IoT Telemetry & Climate/Anti-Vibration Reefer)"
                ]
            )

            # Safety stock

            safety_stock = st.slider(
                "Warehouse / Cellar Safety Stock (Days)",
                min_value=1,
                max_value=10,
                value=3
            )

            submit = st.form_submit_button(
                "🚀 Validate & Run Simulation Round",
                use_container_width=True
            )

        if submit:

            # Recheck database before writing

            latest_data = load_rounds(rounds_sheet)

            if not latest_data.empty:

                already_submitted = latest_data[
                    (
                        latest_data["Team Name"]
                        .astype(str)
                        .str.casefold()
                        == team_name.casefold()
                    )
                    &
                    (
                        pd.to_numeric(
                            latest_data["Round"],
                            errors="coerce"
                        ) == current_round
                    )
                ]

            else:

                already_submitted = pd.DataFrame()

            if not already_submitted.empty:

                st.warning(
                    "This team has already submitted this round. "
                    "Please refresh the application."
                )

                st.rerun()

            else:

                results = run_simulation(
                    is_juice,
                    batch_size,
                    days_between,
                    cold_chain,
                    safety_stock
                )

                row = {
                    "Timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),

                    "Team Name": team_name,
                    "Scenario": active_scenario,
                    "Round": current_round,
                    "Batch Size": batch_size,
                    "Delivery Frequency": frequency_label,
                    "Days Between Deliveries": days_between,
                    "Cold Chain": cold_chain,
                    "Safety Stock Days": safety_stock
                }

                row.update(results)

                save_round(
                    rounds_sheet,
                    row
                )

                st.success(
                    f"Round {current_round} successfully saved!"
                )

                st.rerun()

    else:

        st.success(
            "🏆 Congratulations! Your team has completed all four rounds."
        )

    # ========================================================
    # TEAM PERFORMANCE DASHBOARD
    # ========================================================

    if not team_data.empty:

        st.divider()

        st.header("📊 Your Team Performance")

        latest = team_data.iloc[-1]

        profit = float(latest["Net Profit (€)"])

        k1, k2, k3, k4 = st.columns(4)

        k1.metric(
            "Latest Net Profit",
            f"€{profit:,.2f}"
        )

        k2.metric(
            "Waste / Rejection",
            f"{float(latest['Waste (%)']):.1f}%"
        )

        integrity_label = (
            "Remaining Shelf Life"
            if is_juice
            else "Thermal Integrity"
        )

        k3.metric(
            integrity_label,
            f"{float(latest['Integrity (%)']):.1f}%"
        )

        k4.metric(
            "Out-of-Stock",
            f"{float(latest['OOS (%)']):.1f}%"
        )

        st.metric(
            "Latest CO₂ Emissions",
            f"{float(latest['CO2 (kg)']):,.1f} kg CO₂e"
        )

        # Feedback

        st.subheader("🧠 Corporate Logistics Audit")

        threshold = 70.0 if is_juice else 85.0

        if float(latest["Integrity (%)"]) < threshold:

            st.error(
                "Product integrity is below the contractual threshold. "
                "Your delivery faces a retailer or importer rejection risk."
            )

        elif float(latest["OOS (%)"]) > 12:

            st.warning(
                "Your stockout rate is high. Consider increasing "
                "safety stock or delivery frequency."
            )

        elif float(latest["Waste (%)"]) > 15:

            st.warning(
                "Your waste and rejection rate is excessive. "
                "Review batch sizes and inventory buffers."
            )

        else:

            st.success(
                "Strong operational balance achieved!"
            )

        # Historical table

        st.subheader("📜 Your Historical Performance")

        display_columns = [
            "Round",
            "Net Profit (€)",
            "Waste (%)",
            "Integrity (%)",
            "OOS (%)",
            "CO2 (kg)"
        ]

        st.dataframe(
            team_data[display_columns],
            use_container_width=True,
            hide_index=True
        )

        # Profit evolution

        st.subheader("📈 Profit Evolution")

        profit_history = team_data[
            ["Round", "Net Profit (€)"]
        ].copy()

        profit_history["Round"] = (
            "Round "
            + profit_history["Round"].astype(str)
        )

        profit_history = profit_history.set_index("Round")

        st.line_chart(profit_history)

        # Decision history

        with st.expander("View all historical logistics decisions"):

            st.dataframe(
                team_data[
                    [
                        "Round",
                        "Batch Size",
                        "Delivery Frequency",
                        "Cold Chain",
                        "Safety Stock Days"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

    st.divider()

    st.caption(
        "Food and Drink Retailing and Logistics Simulation | NEOMA BS"
    )
