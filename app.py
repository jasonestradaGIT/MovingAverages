from __future__ import annotations

from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from moving_averages import add_combined_moving_average, add_moving_average


SAMPLE_CSV = """date,analyte,instrument,result
2026-01-02 08:14:03.125,Glucose,Architect c8000,96.2
2026-01-02 09:02:41.384,Glucose,Architect c8000,97.1
2026-01-02 09:58:22.019,Glucose,Architect c8000,95.8
2026-01-02 10:43:10.773,Glucose,Architect c8000,98.4
2026-01-02 11:37:55.640,Glucose,Architect c8000,99.2
2026-01-02 08:19:48.502,Glucose,Atellica CH,94.8
2026-01-02 09:10:16.094,Glucose,Atellica CH,95.6
2026-01-02 10:04:39.811,Glucose,Atellica CH,96.9
2026-01-02 10:51:07.236,Glucose,Atellica CH,96.4
2026-01-02 11:45:28.957,Glucose,Atellica CH,97.8
2026-01-02 08:11:29.411,Creatinine,Architect c8000,0.91
2026-01-02 09:05:13.004,Creatinine,Architect c8000,0.93
2026-01-02 09:54:58.672,Creatinine,Architect c8000,0.92
2026-01-02 10:48:31.290,Creatinine,Architect c8000,0.94
2026-01-02 11:39:49.518,Creatinine,Architect c8000,0.95
2026-01-02 08:16:44.207,Creatinine,Atellica CH,0.88
2026-01-02 09:12:30.563,Creatinine,Atellica CH,0.90
2026-01-02 10:01:22.148,Creatinine,Atellica CH,0.91
2026-01-02 10:57:04.731,Creatinine,Atellica CH,0.89
2026-01-02 11:50:36.409,Creatinine,Atellica CH,0.92
2026-01-02 08:23:02.010,Sodium,Dimension EXL,139.4
2026-01-02 09:17:50.306,Sodium,Dimension EXL,140.1
2026-01-02 10:08:15.887,Sodium,Dimension EXL,139.8
2026-01-02 10:59:42.064,Sodium,Dimension EXL,140.3
2026-01-02 11:53:11.942,Sodium,Dimension EXL,141.0
2026-01-02 08:28:38.716,Sodium,Atellica CH,138.8
2026-01-02 09:21:19.345,Sodium,Atellica CH,139.2
2026-01-02 10:13:44.120,Sodium,Atellica CH,139.7
2026-01-02 11:05:21.699,Sodium,Atellica CH,140.0
2026-01-02 11:58:59.033,Sodium,Atellica CH,140.5
"""

REQUIRED_COLUMNS = {"date", "analyte", "instrument", "result"}
DISPLAY_COLUMNS = ["date", "analyte", "instrument", "result", "moving_average"]
CHART_COLORS = [
    "#38bdf8",
    "#fb7185",
    "#a3e635",
    "#fbbf24",
    "#c084fc",
    "#2dd4bf",
    "#f97316",
    "#818cf8",
    "#f472b6",
    "#22c55e",
]
COMBINED_LINE_COLOR = "#facc15"


def load_default_data() -> pd.DataFrame:
    return pd.read_csv(StringIO(SAMPLE_CSV), parse_dates=["date"])


def load_uploaded_data(uploaded_file) -> pd.DataFrame:
    return pd.read_csv(uploaded_file, parse_dates=["date"])


def validate_data(data: pd.DataFrame) -> pd.DataFrame:
    missing_columns = REQUIRED_COLUMNS - set(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required column(s): {missing}")

    clean_data = data.copy()
    clean_data["date"] = pd.to_datetime(clean_data["date"], errors="coerce")
    clean_data["result"] = pd.to_numeric(clean_data["result"], errors="coerce")
    clean_data["analyte"] = clean_data["analyte"].astype(str).str.strip()
    clean_data["instrument"] = clean_data["instrument"].astype(str).str.strip()
    clean_data = clean_data.dropna(subset=["date", "analyte", "instrument", "result"])
    clean_data = clean_data[
        (clean_data["analyte"] != "")
        & (clean_data["instrument"] != "")
        & (clean_data["analyte"].str.lower() != "nan")
        & (clean_data["instrument"].str.lower() != "nan")
    ]

    if clean_data.empty:
        raise ValueError("No valid lab rows found after cleaning the data.")

    return clean_data.sort_values(["analyte", "instrument", "date"]).reset_index(drop=True)


def instrument_colors(instruments: list[str]) -> dict[str, str]:
    return {instrument: CHART_COLORS[index % len(CHART_COLORS)] for index, instrument in enumerate(instruments)}


def style_chart(figure: go.Figure) -> go.Figure:
    figure.update_layout(
        colorway=CHART_COLORS,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=70, b=110),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    figure.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.22)")
    figure.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.22)")
    return figure


def format_timestamp(value: pd.Timestamp) -> str:
    return f"{value:%Y-%m-%d %H:%M:%S.%f}"[:-3]


def parse_axis_timestamp(value: str, label: str) -> pd.Timestamp:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        raise ValueError(f"{label} must be a valid date/time.")
    return timestamp


def apply_axis_settings(
    figure: go.Figure,
    y_axis_mode: str,
    y_min: float,
    y_max: float,
    x_axis_mode: str,
    x_start: pd.Timestamp,
    x_end: pd.Timestamp,
) -> go.Figure:
    if y_axis_mode == "Manual":
        figure.update_yaxes(range=[y_min, y_max])

    if x_axis_mode == "Manual":
        figure.update_xaxes(range=[x_start, x_end])

    return figure


def build_separate_instrument_chart(data: pd.DataFrame, analyte: str, instruments: list[str]) -> go.Figure:
    figure = go.Figure()
    filtered = data[data["instrument"].isin(instruments)]
    colors = instrument_colors(instruments)

    for instrument in instruments:
        instrument_data = filtered[filtered["instrument"] == instrument]
        color = colors[instrument]
        figure.add_trace(
            go.Scatter(
                x=instrument_data["date"],
                y=instrument_data["result"],
                mode="markers",
                name=f"{instrument} result",
                marker=dict(color=color, size=8, symbol="circle-open", line=dict(width=1.6)),
                opacity=0.55,
                visible="legendonly",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=instrument_data["date"],
                y=instrument_data["moving_average"],
                mode="lines",
                name=f"{instrument} moving average",
                line=dict(color=color, width=3),
            )
        )

    figure.update_layout(
        title=f"{analyte} Results and Moving Average by Instrument",
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Result",
    )
    return style_chart(figure)


def build_combined_instrument_chart(
    data: pd.DataFrame,
    analyte: str,
    instruments: list[str],
    moving_average_points: int,
) -> go.Figure:
    figure = go.Figure()
    filtered = data[data["instrument"].isin(instruments)]
    combined_data = add_combined_moving_average(filtered, moving_average_points)
    colors = instrument_colors(instruments)

    for instrument in instruments:
        instrument_data = combined_data[combined_data["instrument"] == instrument]
        color = colors[instrument]
        figure.add_trace(
            go.Scatter(
                x=instrument_data["date"],
                y=instrument_data["result"],
                mode="markers",
                name=f"{instrument} result",
                marker=dict(color=color, size=8, symbol="circle-open", line=dict(width=1.6)),
                opacity=0.55,
                visible="legendonly",
            )
        )

    figure.add_trace(
        go.Scatter(
            x=combined_data["date"],
            y=combined_data["combined_moving_average"],
            mode="lines",
            name="Combined moving average",
            line=dict(color=COMBINED_LINE_COLOR, width=4),
        )
    )

    figure.update_layout(
        title=f"{analyte} Combined Moving Average",
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Result",
    )
    return style_chart(figure)


st.set_page_config(page_title="Laboratory Moving Averages", page_icon=":microscope:", layout="wide")

st.title("Laboratory Moving Averages")
st.caption("Analyze lab results by analyte, instrument, and rolling point count.")

with st.sidebar:
    st.header("Data")
    uploaded_file = st.file_uploader("CSV file", type=["csv"])
    st.caption("Expected columns: date, analyte, instrument, result")
    st.caption("The date column can include time down to milliseconds.")

    st.header("Moving Average")
    moving_average_points = st.slider(
        "Points to include",
        min_value=2,
        max_value=100,
        value=5,
        help="Number of recent results per analyte and instrument used in the rolling average.",
    )

try:
    raw_data = load_uploaded_data(uploaded_file) if uploaded_file else load_default_data()
    lab_data = validate_data(raw_data)
except Exception as error:
    st.error(f"Could not load the laboratory data: {error}")
    st.stop()

lab_data = add_moving_average(lab_data, moving_average_points)
analytes = sorted(lab_data["analyte"].unique())

summary_cols = st.columns(4)
summary_cols[0].metric("Analytes", len(analytes))
summary_cols[1].metric("Instruments", lab_data["instrument"].nunique())
summary_cols[2].metric("Results", f"{len(lab_data):,}")
summary_cols[3].metric("MA Points", moving_average_points)

tabs = st.tabs(analytes)
for tab, analyte in zip(tabs, analytes):
    analyte_data = lab_data[lab_data["analyte"] == analyte]
    available_instruments = sorted(analyte_data["instrument"].unique())

    with tab:
        selected_instruments = st.multiselect(
            "Instruments",
            options=available_instruments,
            default=available_instruments,
            key=f"instruments_{analyte}",
        )
        display_mode = st.radio(
            "Visualization",
            options=["Separate instruments", "Combined instruments"],
            horizontal=True,
            key=f"display_mode_{analyte}",
        )

        if not selected_instruments:
            st.info("Select at least one instrument to visualize this analyte.")
            continue

        filtered_data = analyte_data[analyte_data["instrument"].isin(selected_instruments)]
        st.markdown(
            "**Date/Time Range:** "
            f"`{format_timestamp(filtered_data['date'].min())}` to "
            f"`{format_timestamp(filtered_data['date'].max())}`"
        )

        metric_cols = st.columns(2)
        metric_cols[0].metric("Included Instruments", len(selected_instruments))
        metric_cols[1].metric("Included Results", f"{len(filtered_data):,}")

        data_y_min = float(filtered_data["result"].min())
        data_y_max = float(filtered_data["result"].max())
        y_padding = max((data_y_max - data_y_min) * 0.05, 0.01)

        with st.expander("Axis controls"):
            axis_cols = st.columns(2)
            with axis_cols[0]:
                y_axis_mode = st.radio(
                    "Y-axis scale",
                    options=["Auto", "Manual"],
                    horizontal=True,
                    key=f"y_axis_mode_{analyte}",
                )
                y_min = st.number_input(
                    "Y minimum",
                    value=data_y_min - y_padding,
                    format="%.6f",
                    disabled=y_axis_mode == "Auto",
                    key=f"y_min_{analyte}",
                )
                y_max = st.number_input(
                    "Y maximum",
                    value=data_y_max + y_padding,
                    format="%.6f",
                    disabled=y_axis_mode == "Auto",
                    key=f"y_max_{analyte}",
                )

            with axis_cols[1]:
                x_axis_mode = st.radio(
                    "X-axis range",
                    options=["Full range", "Manual"],
                    horizontal=True,
                    key=f"x_axis_mode_{analyte}",
                )
                x_start_text = st.text_input(
                    "X start",
                    value=format_timestamp(filtered_data["date"].min()),
                    disabled=x_axis_mode == "Full range",
                    key=f"x_start_{analyte}",
                )
                x_end_text = st.text_input(
                    "X end",
                    value=format_timestamp(filtered_data["date"].max()),
                    disabled=x_axis_mode == "Full range",
                    key=f"x_end_{analyte}",
                )

        if y_axis_mode == "Manual" and y_min >= y_max:
            st.warning("Y minimum must be less than Y maximum.")
            continue

        try:
            x_start = parse_axis_timestamp(x_start_text, "X start")
            x_end = parse_axis_timestamp(x_end_text, "X end")
        except ValueError as error:
            st.warning(str(error))
            continue

        if x_axis_mode == "Manual" and x_start >= x_end:
            st.warning("X start must be before X end.")
            continue

        if display_mode == "Separate instruments":
            chart = build_separate_instrument_chart(analyte_data, analyte, selected_instruments)
            st.plotly_chart(
                apply_axis_settings(chart, y_axis_mode, y_min, y_max, x_axis_mode, x_start, x_end),
                width="stretch",
            )
        else:
            chart = build_combined_instrument_chart(
                analyte_data,
                analyte,
                selected_instruments,
                moving_average_points,
            )
            st.plotly_chart(
                apply_axis_settings(chart, y_axis_mode, y_min, y_max, x_axis_mode, x_start, x_end),
                width="stretch",
            )

        with st.expander("View analyte data"):
            st.dataframe(filtered_data[DISPLAY_COLUMNS], width="stretch")

with st.expander("View all cleaned data"):
    st.dataframe(lab_data[DISPLAY_COLUMNS], width="stretch")
