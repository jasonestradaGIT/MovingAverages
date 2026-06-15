from __future__ import annotations

import math
from io import StringIO
from statistics import NormalDist

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from moving_averages import add_combined_moving_average, add_moving_average
from version import APP_VERSION


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
            groupclick="toggleitem",
        ),
    )
    figure.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,0.22)")
    figure.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,0.22)")
    return figure


def add_moving_average_reference_lines(
    figure: go.Figure,
    dates: pd.Series,
    values: pd.Series,
    label: str,
    color: str,
    legend_group: str,
) -> None:
    moving_average_values = values.dropna()
    if moving_average_values.empty:
        return

    mean = moving_average_values.mean()
    standard_deviation = moving_average_values.std(ddof=1) if len(moving_average_values) > 1 else 0.0
    x_range = [dates.min(), dates.max()]
    reference_lines = [
        ("mean", mean, "dot", 1.8),
        ("+1 SD", mean + standard_deviation, "dash", 1.4),
        ("-1 SD", mean - standard_deviation, "dash", 1.4),
        ("+2 SD", mean + (2 * standard_deviation), "dashdot", 1.4),
        ("-2 SD", mean - (2 * standard_deviation), "dashdot", 1.4),
    ]

    for statistic_name, y_value, dash_style, width in reference_lines:
        figure.add_trace(
            go.Scatter(
                x=x_range,
                y=[y_value, y_value],
                mode="lines",
                name=f"{label} {statistic_name}",
                line=dict(color=color, dash=dash_style, width=width),
                legendgroup=legend_group,
                opacity=0.8,
            )
        )


def moving_average_statistics(label: str, values: pd.Series, moving_average_points: int) -> dict[str, float | int | str]:
    moving_average_values = values.dropna()
    mean = moving_average_values.mean()
    standard_deviation = moving_average_values.std(ddof=1) if len(moving_average_values) > 1 else 0.0
    median = moving_average_values.median()
    return {
        "Line": label,
        "MA Points": moving_average_points,
        "MA Values": len(moving_average_values),
        "Mean": mean,
        "SD": standard_deviation,
        "Mean + SD": mean + standard_deviation,
        "Mean - SD": mean - standard_deviation,
        "Mean + 2 SD": mean + (2 * standard_deviation),
        "Mean - 2 SD": mean - (2 * standard_deviation),
        "Median": median,
    }


def render_statistics_table(rows: list[dict[str, float | int | str]]) -> None:
    stats = pd.DataFrame(rows)
    numeric_columns = [
        "Mean",
        "SD",
        "Mean + SD",
        "Mean - SD",
        "Mean + 2 SD",
        "Mean - 2 SD",
        "Median",
    ]
    st.dataframe(
        stats.style.format({column: "{:.6g}" for column in numeric_columns}),
        width="stretch",
        hide_index=True,
    )


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


def build_separate_instrument_chart(
    data: pd.DataFrame,
    analyte: str,
    instruments: list[str],
    show_reference_lines: bool,
    title: str | None = None,
    color_map: dict[str, str] | None = None,
) -> go.Figure:
    figure = go.Figure()
    filtered = data[data["instrument"].isin(instruments)]
    colors = color_map or instrument_colors(instruments)

    for instrument in instruments:
        instrument_data = filtered[filtered["instrument"] == instrument]
        color = colors[instrument]
        moving_average_group = f"{instrument}_moving_average"
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
                legendgroup=moving_average_group,
                legendgrouptitle_text=f"{instrument} moving average",
            )
        )
        if show_reference_lines:
            add_moving_average_reference_lines(
                figure,
                instrument_data["date"],
                instrument_data["moving_average"],
                instrument,
                color,
                moving_average_group,
            )

    figure.update_layout(
        title=title or f"{analyte} Results and Moving Average by Instrument",
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Result",
    )
    return style_chart(figure)


def build_single_instrument_chart(
    data: pd.DataFrame,
    analyte: str,
    instrument: str,
    show_reference_lines: bool,
    color_map: dict[str, str] | None = None,
) -> go.Figure:
    return build_separate_instrument_chart(
        data,
        analyte,
        [instrument],
        show_reference_lines,
        title=f"{analyte} Moving Average - {instrument}",
        color_map=color_map,
    )


def build_raw_result_chart(
    data: pd.DataFrame,
    analyte: str,
    instrument: str,
    show_reference_lines: bool,
    color: str,
) -> go.Figure:
    figure = go.Figure()
    legend_group = f"{instrument}_raw_results"
    figure.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["result"],
            mode="lines+markers",
            name=f"{instrument} raw results",
            line=dict(color=color, width=2.5),
            marker=dict(color=color, size=7),
            legendgroup=legend_group,
            legendgrouptitle_text=f"{instrument} raw results",
        )
    )
    if show_reference_lines:
        add_moving_average_reference_lines(
            figure,
            data["date"],
            data["result"],
            instrument,
            color,
            legend_group,
        )

    figure.update_layout(
        title=f"{analyte} Raw Results - {instrument}",
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Result",
    )
    return style_chart(figure)


def raw_result_statistics(label: str, values: pd.Series) -> dict[str, float | int | str]:
    result_values = values.dropna()
    mean = result_values.mean()
    standard_deviation = result_values.std(ddof=1) if len(result_values) > 1 else 0.0
    return {
        "Line": label,
        "Result Values": len(result_values),
        "Mean": mean,
        "SD": standard_deviation,
        "Mean + SD": mean + standard_deviation,
        "Mean - SD": mean - standard_deviation,
        "Mean + 2 SD": mean + (2 * standard_deviation),
        "Mean - 2 SD": mean - (2 * standard_deviation),
        "Median": result_values.median(),
    }


def render_raw_result_statistics(rows: list[dict[str, float | int | str]]) -> None:
    stats = pd.DataFrame(rows)
    numeric_columns = [
        "Mean",
        "SD",
        "Mean + SD",
        "Mean - SD",
        "Mean + 2 SD",
        "Mean - 2 SD",
        "Median",
    ]
    st.dataframe(
        stats.style.format({column: "{:.6g}" for column in numeric_columns}),
        width="stretch",
        hide_index=True,
    )


def normal_distribution_statistics(
    values: pd.Series,
    confidence_level: float = 0.95,
) -> dict[str, float | int]:
    moving_average_values = values.dropna()
    mean = moving_average_values.mean()
    standard_deviation = moving_average_values.std(ddof=1) if len(moving_average_values) > 1 else 0.0
    alpha = 1 - confidence_level
    tail_alpha = alpha / 2
    z_value = NormalDist().inv_cdf(1 - tail_alpha)
    margin = z_value * standard_deviation
    return {
        "Value Count": len(moving_average_values),
        "Confidence Level": confidence_level,
        "Alpha": alpha,
        "Alpha per Tail": tail_alpha,
        "Z Value": z_value,
        "Mean": mean,
        "Sample SD": standard_deviation,
        "Margin": margin,
        "Lower Cutoff": mean - margin,
        "Upper Cutoff": mean + margin,
    }


def confidence_level_label(confidence_level: float) -> str:
    return f"{confidence_level * 100:.6g}%"


def render_normal_distribution_statistics(
    statistics_sets: list[dict[str, float | int]],
    value_count_label: str,
) -> None:
    statistic_fields = [
        (value_count_label, "Value Count", 1),
        ("Confidence level (%)", "Confidence Level", 100),
        ("Alpha", "Alpha", 1),
        ("Alpha per tail", "Alpha per Tail", 1),
        ("Z value", "Z Value", 1),
        ("Mean", "Mean", 1),
        ("Sample SD", "Sample SD", 1),
        ("Margin (Z x SD)", "Margin", 1),
        ("Lower cutoff", "Lower Cutoff", 1),
        ("Upper cutoff", "Upper Cutoff", 1),
    ]
    rows = [{"Statistic": label} for label, _, _ in statistic_fields]
    value_columns = []
    for index, statistics in enumerate(statistics_sets):
        interval_label = confidence_level_label(statistics["Confidence Level"])
        column = f"{interval_label} Interval" if index == 0 else f"{interval_label} Custom Interval"
        value_columns.append(column)
        for row, (_, field, multiplier) in zip(rows, statistic_fields):
            row[column] = statistics[field] * multiplier

    table = pd.DataFrame(rows)
    st.dataframe(
        table.style.format({column: "{:.6g}" for column in value_columns}),
        width="stretch",
        hide_index=True,
    )


def build_normal_distribution_chart(
    values: pd.Series,
    analyte: str,
    instrument: str,
    color: str,
    value_label: str,
    title_value_label: str,
    custom_statistics: dict[str, float | int] | None = None,
) -> go.Figure:
    moving_average_values = values.dropna()
    statistics = normal_distribution_statistics(moving_average_values)
    mean = statistics["Mean"]
    standard_deviation = statistics["Sample SD"]
    figure = go.Figure()

    figure.add_trace(
        go.Histogram(
            x=moving_average_values,
            histnorm="probability density",
            name=value_label,
            marker=dict(color=color, opacity=0.58, line=dict(color=color, width=1)),
        )
    )

    maximum_density = 1.0
    if len(moving_average_values) > 1 and standard_deviation > 0:
        minimum = moving_average_values.min()
        maximum = moving_average_values.max()
        padding = (maximum - minimum) * 0.15
        if padding == 0:
            padding = standard_deviation

        x_start = minimum - padding
        x_end = maximum + padding
        x_values = [
            x_start + (x_end - x_start) * index / 119
            for index in range(120)
        ]
        normal_density = [
            (1 / (standard_deviation * math.sqrt(2 * math.pi)))
            * math.exp(-0.5 * ((value - mean) / standard_deviation) ** 2)
            for value in x_values
        ]
        maximum_density = max(normal_density) * 1.12
        figure.add_trace(
            go.Scatter(
                x=x_values,
                y=normal_density,
                mode="lines",
                name="Normal fit",
                line=dict(color=color, width=3),
            )
        )

    reference_lines = [
        ("Mean", statistics["Mean"], "#facc15", "solid", 3),
        ("Lower 95% cutoff", statistics["Lower Cutoff"], "#fb7185", "dash", 2),
        ("Upper 95% cutoff", statistics["Upper Cutoff"], "#fb7185", "dash", 2),
    ]
    if custom_statistics is not None:
        custom_label = confidence_level_label(custom_statistics["Confidence Level"])
        reference_lines.extend(
            [
                (
                    f"Lower {custom_label} cutoff",
                    custom_statistics["Lower Cutoff"],
                    "#a3e635",
                    "dashdot",
                    2,
                ),
                (
                    f"Upper {custom_label} cutoff",
                    custom_statistics["Upper Cutoff"],
                    "#a3e635",
                    "dashdot",
                    2,
                ),
            ]
        )
    for label, x_value, line_color, dash_style, width in reference_lines:
        figure.add_trace(
            go.Scatter(
                x=[x_value, x_value],
                y=[0, maximum_density],
                mode="lines",
                name=f"{label}: {x_value:.6g}",
                line=dict(color=line_color, dash=dash_style, width=width),
            )
        )

    figure.update_layout(
        title=f"{analyte} {title_value_label} Distribution - {instrument}",
        bargap=0.08,
        xaxis_title=title_value_label,
        yaxis_title="Density",
    )
    return style_chart(figure)


def build_combined_instrument_chart(
    data: pd.DataFrame,
    analyte: str,
    instruments: list[str],
    moving_average_points: int,
    show_reference_lines: bool,
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
            legendgroup="combined_moving_average",
            legendgrouptitle_text="Combined moving average",
        )
    )
    if show_reference_lines:
        add_moving_average_reference_lines(
            figure,
            combined_data["date"],
            combined_data["combined_moving_average"],
            "Combined",
            COMBINED_LINE_COLOR,
            "combined_moving_average",
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
    st.markdown(
        f"""
        <div style="position: fixed; bottom: 0.75rem; left: 1rem; text-align: left;
                    font-size: 0.72rem; opacity: 0.65; line-height: 1.3;">
            Version {APP_VERSION}<br>
            Copyright &copy; 2026 Jason Estrada<br>
            Licensed under the BSD 3-Clause License.
        </div>
        """,
        unsafe_allow_html=True,
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
        show_reference_lines = st.checkbox(
            "Show mean and SD reference lines",
            value=True,
            key=f"show_reference_lines_{analyte}",
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

        selected_instrument_colors = instrument_colors(selected_instruments)

        if display_mode == "Separate instruments":
            overview_stats = [
                moving_average_statistics(
                    instrument,
                    analyte_data[analyte_data["instrument"] == instrument]["moving_average"],
                    moving_average_points,
                )
                for instrument in selected_instruments
            ]
            render_statistics_table(overview_stats)
            chart = build_separate_instrument_chart(
                analyte_data,
                analyte,
                selected_instruments,
                show_reference_lines,
                color_map=selected_instrument_colors,
            )
            st.plotly_chart(
                apply_axis_settings(chart, y_axis_mode, y_min, y_max, x_axis_mode, x_start, x_end),
                width="stretch",
            )
        else:
            combined_data = add_combined_moving_average(filtered_data, moving_average_points)
            render_statistics_table(
                [
                    moving_average_statistics(
                        "Combined",
                        combined_data["combined_moving_average"],
                        moving_average_points,
                    )
                ]
            )
            chart = build_combined_instrument_chart(
                analyte_data,
                analyte,
                selected_instruments,
                moving_average_points,
                show_reference_lines,
            )
            st.plotly_chart(
                apply_axis_settings(chart, y_axis_mode, y_min, y_max, x_axis_mode, x_start, x_end),
                width="stretch",
            )

        with st.expander("Instrument charts", expanded=True):
            for instrument in selected_instruments:
                instrument_data = analyte_data[analyte_data["instrument"] == instrument]
                instrument_reference_lines = st.checkbox(
                    f"Show mean and SD reference lines for {instrument}",
                    value=True,
                    key=f"show_reference_lines_{analyte}_{instrument}",
                )
                render_statistics_table(
                    [
                        moving_average_statistics(
                            instrument,
                            instrument_data["moving_average"],
                            moving_average_points,
                        )
                    ]
                )
                instrument_chart = build_single_instrument_chart(
                    instrument_data,
                    analyte,
                    instrument,
                    instrument_reference_lines,
                    color_map=selected_instrument_colors,
                )
                st.plotly_chart(
                    apply_axis_settings(
                        instrument_chart,
                        y_axis_mode,
                        y_min,
                        y_max,
                        x_axis_mode,
                        x_start,
                        x_end,
                    ),
                    width="stretch",
                )
                with st.container(border=True):
                    show_additional_graphs = st.toggle(
                        f"Additional graphs for {instrument}",
                        value=False,
                        key=f"show_additional_graphs_{analyte}_{instrument}",
                    )
                    if show_additional_graphs:
                        st.markdown(f"#### Raw Result Chart - {instrument}")
                        raw_result_reference_lines = st.checkbox(
                            "Show mean and SD reference lines for raw results",
                            value=True,
                            key=f"raw_result_reference_lines_{analyte}_{instrument}",
                        )
                        render_raw_result_statistics(
                            [raw_result_statistics(instrument, instrument_data["result"])]
                        )
                        raw_result_chart = build_raw_result_chart(
                            instrument_data,
                            analyte,
                            instrument,
                            raw_result_reference_lines,
                            selected_instrument_colors[instrument],
                        )
                        st.plotly_chart(
                            apply_axis_settings(
                                raw_result_chart,
                                y_axis_mode,
                                y_min,
                                y_max,
                                x_axis_mode,
                                x_start,
                                x_end,
                            ),
                            width="stretch",
                        )

                        st.markdown(f"#### MA Value Distribution - {instrument}")
                        ma_distribution_statistics = normal_distribution_statistics(
                            instrument_data["moving_average"]
                        )
                        ma_custom_interval_enabled = st.toggle(
                            "Add custom confidence interval for MA values",
                            value=False,
                            key=f"ma_custom_interval_enabled_{analyte}_{instrument}",
                        )
                        ma_custom_confidence_percent = st.number_input(
                            "MA custom confidence level (%)",
                            min_value=0.1,
                            max_value=99.9,
                            value=99.0,
                            step=0.1,
                            format="%.3f",
                            disabled=not ma_custom_interval_enabled,
                            key=f"ma_custom_confidence_percent_{analyte}_{instrument}",
                        )
                        ma_custom_distribution_statistics = None
                        if ma_custom_interval_enabled:
                            ma_custom_distribution_statistics = normal_distribution_statistics(
                                instrument_data["moving_average"],
                                ma_custom_confidence_percent / 100,
                            )
                        st.caption(
                            "Fitted-normal intervals = mean +/- z x sample SD. "
                            "They describe the distribution of MA values, not the confidence interval of the estimated mean."
                        )
                        ma_statistics_sets = [ma_distribution_statistics]
                        if ma_custom_distribution_statistics is not None:
                            ma_statistics_sets.append(ma_custom_distribution_statistics)
                        render_normal_distribution_statistics(
                            ma_statistics_sets,
                            "MA values",
                        )
                        st.plotly_chart(
                            build_normal_distribution_chart(
                                instrument_data["moving_average"],
                                analyte,
                                instrument,
                                selected_instrument_colors[instrument],
                                "MA values",
                                "MA Value",
                                ma_custom_distribution_statistics,
                            ),
                            width="stretch",
                        )

                        st.markdown(f"#### Raw Result Distribution - {instrument}")
                        raw_distribution_statistics = normal_distribution_statistics(
                            instrument_data["result"]
                        )
                        raw_custom_interval_enabled = st.toggle(
                            "Add custom confidence interval for raw results",
                            value=False,
                            key=f"raw_custom_interval_enabled_{analyte}_{instrument}",
                        )
                        raw_custom_confidence_percent = st.number_input(
                            "Raw result custom confidence level (%)",
                            min_value=0.1,
                            max_value=99.9,
                            value=99.0,
                            step=0.1,
                            format="%.3f",
                            disabled=not raw_custom_interval_enabled,
                            key=f"raw_custom_confidence_percent_{analyte}_{instrument}",
                        )
                        raw_custom_distribution_statistics = None
                        if raw_custom_interval_enabled:
                            raw_custom_distribution_statistics = normal_distribution_statistics(
                                instrument_data["result"],
                                raw_custom_confidence_percent / 100,
                            )
                        st.caption(
                            "Fitted-normal intervals = mean +/- z x sample SD. "
                            "They describe the distribution of raw results, not the confidence interval of the estimated mean."
                        )
                        raw_statistics_sets = [raw_distribution_statistics]
                        if raw_custom_distribution_statistics is not None:
                            raw_statistics_sets.append(raw_custom_distribution_statistics)
                        render_normal_distribution_statistics(
                            raw_statistics_sets,
                            "Raw result values",
                        )
                        st.plotly_chart(
                            build_normal_distribution_chart(
                                instrument_data["result"],
                                analyte,
                                instrument,
                                selected_instrument_colors[instrument],
                                "Raw results",
                                "Raw Result",
                                raw_custom_distribution_statistics,
                            ),
                            width="stretch",
                        )

        with st.expander("View analyte data"):
            st.dataframe(filtered_data[DISPLAY_COLUMNS], width="stretch")

with st.expander("View all cleaned data"):
    st.dataframe(lab_data[DISPLAY_COLUMNS], width="stretch")
