"""
analysis_tools.py
-----------------
Utility tools for the analysis agent in the Agentic Space Explorer project.

Each tool is implemented as a callable function that operates on a shared
`context` dictionary — the agent’s working memory — that holds:
    - `context["df"]`:      The base pandas DataFrame loaded from a CSV file.
    - `context["tables"]`:  A dictionary of derived tables created by tools.
    - `context["artifacts"]`: An artifact registry for outputs like plots or markdown files.

Each tool follows a standard signature and is described by a ToolSpec in the
REGISTRY below. These ToolSpecs allow the planning agent to discover, describe,
and call tools dynamically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.io as pio


# ---------------------------------------------------------------------
# ToolSpec definition
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class ToolSpec:
    """Metadata and reference wrapper for a tool function.

    Fields
    ------
    name : str
        The unique name of the tool (used in registry and plans).
    description : str
        Short human-readable description for planners or agent reasoning.
    args_schema : Dict[str, str]
        Simple argument schema hint (not enforced) used in planner prompts.
    fn : Callable[..., Any]
        The actual Python function implementing the tool.
    """
    name: str
    description: str
    args_schema: Dict[str, str]
    fn: Callable[..., Any]


# ---------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------

def t_select_base_df(*, context: Dict[str, Any]) -> None:
    """
    Assert that the base DataFrame already exists in the context.

    This acts as a no-op "sanity check" tool—useful for explicit planning steps
    to ensure `context["df"]` has been loaded before performing analysis.
    """
    if "df" not in context or context["df"] is None:
        raise ValueError(
            "context['df'] is missing. Load the dataframe before running analysis."
        )
    return None


def t_group_count(*, context: Dict[str, Any], input: str, group_by: List[str], save_as: str) -> None:
    """
    Group rows of a DataFrame (or prior table) by specified columns and count occurrences.

    Parameters
    ----------
    input : str
        Either "df" (the base dataset) or the name of a derived table in `context["tables"]`.
    group_by : List[str]
        Column names to group by.
    save_as : str
        Key under which to store the resulting summary table.

    Example
    -------
    Group launches per agency:
        t_group_count(context=ctx, input="df", group_by=["Agency"], save_as="launches_per_agency")
    """
    df = _resolve_input(context, input)

    # Resolve column names (allows semantic aliasing like Agency -> Company)
    resolved_group_by = [_resolve_column(df, c) for c in group_by]

    out = (
        df.groupby(resolved_group_by)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    context["tables"][save_as] = out



def t_group_success_rate(*, context: Dict[str, Any], input: str, group_by: List[str], success_col: str, save_as: str) -> None:
    """
    Group by columns and compute success rate (mean of boolean success_col).
    Saves a table into context["tables"][save_as].

    Output columns:
      - group_by columns
      - success_rate (float 0-1)
      - also an alias column named exactly like success_col (e.g., 'Success') for planner-friendliness
    """
    df = _resolve_input(context, input)

    success_col_resolved = _resolve_column(df, success_col)
    resolved_group_by = [_resolve_column(df, c) for c in group_by]

    if success_col not in df.columns:
        raise ValueError(f"success_col '{success_col}' not found in dataframe columns")

    out = (
        df.groupby(resolved_group_by)[success_col_resolved]
          .mean()
          .reset_index(name="success_rate")
          .sort_values(group_by)
    )

    # Planner-friendly alias: lets the LLM use y="Success" and still work
    out[success_col] = out["success_rate"]

    context["tables"][save_as] = out

def t_describe_schema(*, context: Dict[str, Any], save_as: str = "schema") -> None:
    """
    Capture dataframe schema (columns + dtypes + basic hints) for planners and reports.
    Saves a 2-col table into context["tables"][save_as]: column, dtype
    """
    df = context["df"]
    out = pd.DataFrame({
        "column": df.columns.astype(str),
        "dtype": [str(t) for t in df.dtypes],
    })
    context["tables"][save_as] = out

def t_eda_probe_suite(
    *,
    context: Dict[str, Any],
    input: str = "df",
    year_col: str = "Year",
    success_col: str = "Success",
    org_col: str = "Company",
    save_as: str = "eda_insights",
    top_k: int = 8,
) -> None:
    """
    Run a bounded, deterministic EDA probe suite to surface candidate 'surprising' insights.

    Outputs a table with columns:
      - insight_type
      - label
      - metric
      - value
      - note

    This is meant to generate candidates; the LLM/report can choose which to highlight.
    """
    df = _resolve_input(context, input)

    # Resolve columns robustly (uses your existing alias resolver if present)
    ycol = _resolve_column(df, year_col)
    scol = _resolve_column(df, success_col)
    ocol = _resolve_column(df, org_col)

    df[ycol] = pd.to_numeric(df[ycol], errors="coerce")
    df = df.dropna(subset=[ycol])
    df[ycol] = df[ycol].astype(int)

    insights: List[Dict[str, Any]] = []

    # --- Probe 1: launches per year + YoY spikes/drops
    launches = df.groupby(ycol).size().reset_index(name="launches").sort_values(ycol)
    launches["yoy_delta"] = launches["launches"].diff()

    # Biggest spikes
    spikes = launches.dropna(subset=["yoy_delta"]).sort_values("yoy_delta", ascending=False).head(top_k)
    for _, r in spikes.iterrows():
        insights.append({
            "insight_type": "launch_spike",
            "label": f"{int(r[ycol])}",
            "metric": "launches_yoy_delta",
            "value": float(r["yoy_delta"]),
            "note": f"Launches increased by {int(r['yoy_delta'])} vs prior year."
        })

    # Biggest drops
    drops = launches.dropna(subset=["yoy_delta"]).sort_values("yoy_delta", ascending=True).head(top_k)
    for _, r in drops.iterrows():
        insights.append({
            "insight_type": "launch_drop",
            "label": f"{int(r[ycol])}",
            "metric": "launches_yoy_delta",
            "value": float(r["yoy_delta"]),
            "note": f"Launches decreased by {abs(int(r['yoy_delta']))} vs prior year."
        })

    # --- Probe 2: success rate per year + YoY changes
    # Ensure success column is numeric-ish boolean
    succ = df.copy()
    succ[scol] = succ[scol].astype(bool)

    sr = succ.groupby(ycol)[scol].mean().reset_index(name="success_rate").sort_values(ycol)
    sr["yoy_delta"] = sr["success_rate"].diff()

    sr_up = sr.dropna(subset=["yoy_delta"]).sort_values("yoy_delta", ascending=False).head(top_k)
    for _, r in sr_up.iterrows():
        insights.append({
            "insight_type": "success_rate_jump",
            "label": f"{int(r[ycol])}",
            "metric": "success_rate_yoy_delta",
            "value": float(r["yoy_delta"]),
            "note": f"Success rate increased by {r['yoy_delta']:.2%} vs prior year."
        })

    sr_down = sr.dropna(subset=["yoy_delta"]).sort_values("yoy_delta", ascending=True).head(top_k)
    for _, r in sr_down.iterrows():
        insights.append({
            "insight_type": "success_rate_drop",
            "label": f"{int(r[ycol])}",
            "metric": "success_rate_yoy_delta",
            "value": float(r["yoy_delta"]),
            "note": f"Success rate decreased by {abs(r['yoy_delta']):.2%} vs prior year."
        })

    # --- Probe 3: top orgs overall (simple “who dominates?” lens)
    top_orgs = df.groupby(ocol).size().reset_index(name="missions").sort_values("missions", ascending=False).head(top_k)
    for _, r in top_orgs.iterrows():
        insights.append({
            "insight_type": "top_org_overall",
            "label": str(r[ocol]),
            "metric": "missions",
            "value": float(r["missions"]),
            "note": f"High overall mission volume."
        })

    out = pd.DataFrame(insights)

    # Keep deterministic ordering: group by type then highest abs value
    if not out.empty:
        out["abs_value"] = out["value"].abs()
        out = out.sort_values(["insight_type", "abs_value"], ascending=[True, False]).drop(columns=["abs_value"])

    context["tables"][save_as] = out



def t_plot_line(*, context: Dict[str, Any], table: str, x: str, y: str, title: str, out_path: str) -> None:
    """
    Render a simple line plot from one of the tables and save to disk as PNG.

    The resulting plot path is appended to `context["artifacts"]["plots"]`
    so that later reporting tools can reference it.

    Parameters
    ----------
    table : str
        Name of the table in `context["tables"]` to plot.
    x, y : str
        Column names for horizontal and vertical axes.
    title : str
        Title for the chart.
    out_path : str
        Destination file path for saving the image.
    """
    if table not in context["tables"]:
        raise ValueError(f"Table '{table}' not found in context['tables']")
    df = context["tables"][table]

    if x not in df.columns or y not in df.columns:
        raise ValueError(f"plot_line requires columns '{x}' and '{y}' in table '{table}'")

    plt.figure()
    plt.plot(df[x], df[y])
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

    # Plotly sidecar for interactive rendering
    pfig = px.line(df, x=x, y=y, title=title, template="plotly_dark")
    pfig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
    pio.write_json(pfig, out_path.replace(".png", ".plotly.json"))

    # Register output artifact
    context["artifacts"]["plots"].append(out_path)

def t_plot_bar(*, context: Dict[str, Any], table: str, x: str, y: str, title: str, out_path: str, top_n: Optional[int] = None) -> None:
    """
    Render a bar chart from a named table and save to PNG.
    If top_n is provided, takes the first top_n rows (assumes already sorted by relevance).
    """
    if table not in context["tables"]:
        raise ValueError(f"Table '{table}' not found in context['tables']")
    df = context["tables"][table]

    if x not in df.columns or y not in df.columns:
        raise ValueError(f"plot_bar requires columns '{x}' and '{y}' in table '{table}'")

    if top_n is not None:
        df = df.head(int(top_n))

    plt.figure(figsize=(10, 5))
    plt.bar(df[x].astype(str), df[y])
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

    # Plotly sidecar for interactive rendering
    pfig = px.bar(df, x=df[x].astype(str), y=y, title=title, template="plotly_dark")
    pfig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
    pio.write_json(pfig, out_path.replace(".png", ".plotly.json"))

    context["artifacts"]["plots"].append(out_path)


def t_plot_histogram(*, context: Dict[str, Any], input: str, column: str, bins: int, title: str, out_path: str) -> None:
    """
    Render a histogram of a numeric column from df or a named table.
    input: "df" or a table name in context["tables"]
    """
    df = _resolve_input(context, input)

    if column not in df.columns:
        raise ValueError(f"plot_histogram requires column '{column}' in input '{input}'")

    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"plot_histogram found no numeric values for column '{column}'")

    plt.figure(figsize=(10, 5))
    plt.hist(series, bins=int(bins))
    plt.title(title)
    plt.xlabel(column)
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

    # Plotly sidecar for interactive rendering
    pfig = px.histogram(series.to_frame(name=column), x=column, nbins=int(bins), title=title, template="plotly_dark")
    pfig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
    pio.write_json(pfig, out_path.replace(".png", ".plotly.json"))

    context["artifacts"]["plots"].append(out_path)


def t_plot_stacked_area(
    *,
    context: Dict[str, Any],
    table: str,
    x: str,
    category: str,
    value: str,
    title: str,
    out_path: str,
    top_n_categories: int = 8,
) -> None:
    """
    Render a stacked area chart from a "long" table with columns:
      - x (e.g., Year)
      - category (e.g., Agency)
      - value (e.g., count)

    The tool will:
      - pick top N categories by total value
      - group the rest into "Other"
      - pivot into wide form and plot stacked area
    """
    if table not in context["tables"]:
        raise ValueError(f"Table '{table}' not found in context['tables']")
    df = context["tables"][table]

    for col in (x, category, value):
        if col not in df.columns:
            raise ValueError(f"plot_stacked_area requires column '{col}' in table '{table}'")

    # Ensure types
    df = df.copy()
    df[x] = pd.to_numeric(df[x], errors="coerce")
    df[value] = pd.to_numeric(df[value], errors="coerce")
    df = df.dropna(subset=[x, category, value])

    if df.empty:
        raise ValueError("plot_stacked_area: no data after cleaning.")

    # Choose top categories by total contribution
    totals = df.groupby(category)[value].sum().sort_values(ascending=False)
    top_cats = set(totals.head(int(top_n_categories)).index.tolist())

    df[category] = df[category].astype(str)
    df["__cat__"] = df[category].apply(lambda c: c if c in top_cats else "Other")

    wide = (
        df.groupby([x, "__cat__"])[value]
          .sum()
          .reset_index()
          .pivot(index=x, columns="__cat__", values=value)
          .fillna(0)
          .sort_index()
    )

    # Plot stacked area
    plt.figure(figsize=(12, 6))
    plt.stackplot(wide.index.values, wide.T.values, labels=wide.columns.tolist())
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(value)
    plt.legend(loc="upper left", fontsize="small")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()

    # Plotly sidecar for interactive rendering
    wide_reset = wide.reset_index()
    cat_cols = [c for c in wide_reset.columns if c != x]
    pfig = px.area(wide_reset, x=x, y=cat_cols, title=title, template="plotly_dark")
    pfig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
    pio.write_json(pfig, out_path.replace(".png", ".plotly.json"))

    context["artifacts"]["plots"].append(out_path)


def t_write_markdown(
    *,
    context: Dict[str, Any],
    title: str,
    tables: List[str],
    plot_paths: List[str],
    out_path: str,
    highlights: Optional[List[str]] = None,
) -> None:
    """
    Generate a Markdown report summarizing selected tables and plots.

    This produces a lightweight, shareable text report suitable for rendering
    inside HTML viewers or uploading to GitHub Gists.

    Parameters
    ----------
    title : str
        Report title.
    tables : List[str]
        A list of table names to display.
    plot_paths : Optional[List[str]]
        Explicit list of plot files to reference; if None, uses all plots
        in context["artifacts"]["plots"].
    out_path : str
        Output Markdown file path.
    """
    lines: List[str] = []
    lines.append(f"# {title}\n")

    lines.append("")

    if highlights:
        lines.append("## Key highlights")
        for h in highlights:
            lines.append(f"- {h}")
        lines.append("")


    lines.append("## Tables\n")

    # Include first few rows of each requested table
    for tname in tables:
        if tname not in context["tables"]:
            lines.append(f"- (missing) `{tname}`")
            continue
        lines.append(f"### `{tname}`\n")
        lines.append(context["tables"][tname].head(15).to_markdown(index=False))
        lines.append("")

    lines.append("## Plots\n")
    for p in (plot_paths or context["artifacts"]["plots"]):
        lines.append(f"- `{p}`")
    lines.append("")

    # Write to file
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Register summary artifact
    context["artifacts"]["md"] = out_path


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def _resolve_input(context: Dict[str, Any], input_name: str) -> pd.DataFrame:
    """
    Resolve an input name ("df" or a stored table name) into a pandas DataFrame.

    Used internally by other tools to avoid repeated boilerplate code.
    """
    if input_name == "df":
        return context["df"]
    if input_name in context["tables"]:
        return context["tables"][input_name]
    raise ValueError(f"Unknown input '{input_name}'. Use 'df' or a table name in context['tables'].")

def _resolve_column(df: pd.DataFrame, requested: str) -> str:
    """
    Resolve a requested column name to an existing column in df.

    Supports:
    - exact match
    - case-insensitive match
    - common semantic aliases (e.g., "Agency" -> "Company")
    """
    # 1) Exact match
    if requested in df.columns:
        return requested

    # 2) Case-insensitive match
    lower_map = {c.lower(): c for c in df.columns}
    if requested.lower() in lower_map:
        return lower_map[requested.lower()]

    # 3) Semantic aliases (extend as needed)
    aliases = {
        "agency": ["Company", "Organisation", "Organization", "Operator", "Agency", "Provider"],
        "mission_status": ["MissionStatus", "Mission_Status"],
        "rocket_status": ["RocketStatus", "Rocket_Status"],
    }

    key = requested.lower()
    if key in aliases:
        for cand in aliases[key]:
            if cand in df.columns:
                return cand
            if cand.lower() in lower_map:
                return lower_map[cand.lower()]

    raise KeyError(f"Column '{requested}' not found. Available columns: {list(df.columns)}")

def t_filter_year_range(
    *,
    context: Dict[str, Any],
    input: str,
    year_col: str = "Year",
    start_year: int,
    end_year: int,
    save_as: str,
) -> None:
    """
    Filter rows to a year range [start_year, end_year] inclusive.
    Saves the filtered dataframe as a named table in context["tables"][save_as].
    """
    df = _resolve_input(context, input).copy()
    ycol = _resolve_column(df, year_col)

    df[ycol] = pd.to_numeric(df[ycol], errors="coerce")
    df = df.dropna(subset=[ycol])
    df[ycol] = df[ycol].astype(int)

    out = df[(df[ycol] >= int(start_year)) & (df[ycol] <= int(end_year))].copy()
    context["tables"][save_as] = out



# ---------------------------------------------------------------------
# Registry: discoverable tools for planner/runtime
# ---------------------------------------------------------------------

REGISTRY: Dict[str, ToolSpec] = {
    "select_base_df": ToolSpec(
        name="select_base_df",
        description="Assert base dataframe is loaded into context['df'].",
        args_schema={},
        fn=t_select_base_df,
    ),
    "group_count": ToolSpec(
        name="group_count",
        description="Group by columns and count rows; saves as a named table.",
        args_schema={
            "input": "str (use 'df' or a prior table name)",
            "group_by": "list[str]",
            "save_as": "str",
        },
        fn=t_group_count,
    ),
    "group_success_rate": ToolSpec(
        name="group_success_rate",
        description="Group by columns and compute success rate (mean of boolean col); saves as a named table. Outputs success_rate (alias also exists as {success_col})",
        args_schema={
            "input": "str (use 'df' or a prior table name)",
            "group_by": "list[str]",
            "success_col": "str (e.g., 'Success')",
            "save_as": "str",
        },
        fn=t_group_success_rate,
    ),
    "describe_schema": ToolSpec(
        name="describe_schema",
        description="List available dataframe columns and dtypes; saves as a table for planning/debugging.",
        args_schema={
            "save_as": "optional str (default 'schema')",
        },
        fn=t_describe_schema,
    ),
    "filter_year_range": ToolSpec(
        name="filter_year_range",
        description="Filter rows to a year range [start_year, end_year] (inclusive) and save as a named table.",
        args_schema={
            "input": "str (use 'df' or a table name)",
            "year_col": "optional str (default 'Year')",
            "start_year": "int",
            "end_year": "int",
            "save_as": "str (table name to save filtered df)",
        },
        fn=t_filter_year_range,
    ),
    "eda_probe_suite": ToolSpec(
        name="eda_probe_suite",
        description="Run a bounded EDA probe suite to surface candidate surprising insights (spikes, drops, success-rate jumps, top orgs).",
        args_schema={
            "input": "optional str (default 'df'; can be a filtered table name)",
            "year_col": "optional str (default 'Year')",
            "success_col": "optional str (default 'Success')",
            "org_col": "optional str (default 'Company')",
            "save_as": "optional str (default 'eda_insights')",
            "top_k": "optional int (default 8)",
        },
        fn=t_eda_probe_suite,
    ),
    "plot_line": ToolSpec(
        name="plot_line",
        description="Plot a line chart from a named table and save to PNG.",
        args_schema={
            "table": "str (table name)",
            "x": "str (column name)",
            "y": "str (column name)",
            "title": "str",
            "out_path": "str (e.g., 'reports/plots/launches_per_year.png')",
        },
        fn=t_plot_line,
    ),
    "plot_bar": ToolSpec(
        name="plot_bar",
        description="Plot a bar chart from a named table and save to PNG (great for top-N categories).",
        args_schema={
            "table": "str (table name)",
            "x": "str (column name for categories)",
            "y": "str (column name for values)",
            "title": "str",
            "out_path": "str (e.g., 'reports/plots/top_agencies.png')",
            "top_n": "optional int (take first N rows)",
        },
        fn=t_plot_bar,
    ),
    "plot_histogram": ToolSpec(
        name="plot_histogram",
        description="Plot a histogram of a numeric column from df or a named table and save to PNG.",
        args_schema={
            "input": "str (use 'df' or a prior table name)",
            "column": "str (numeric column)",
            "bins": "int",
            "title": "str",
            "out_path": "str (e.g., 'reports/plots/year_hist.png')",
        },
        fn=t_plot_histogram,
    ),
    "plot_stacked_area": ToolSpec(
        name="plot_stacked_area",
        description="Plot a stacked area chart showing composition over time (e.g., Year x Agency counts).",
        args_schema={
            "table": "str (table name in long format)",
            "x": "str (time column, e.g. 'Year')",
            "category": "str (category column, e.g. 'Agency')",
            "value": "str (value column, e.g. 'count')",
            "title": "str",
            "out_path": "str (e.g., 'reports/plots/agency_share_over_time.png')",
            "top_n_categories": "optional int (default 8)",
        },
        fn=t_plot_stacked_area,
    ),

    "write_markdown": ToolSpec(
        name="write_markdown",
        description="Write a markdown report referencing tables and plots.",
        args_schema={
            "title": "str",
            "tables": "list[str] (table names)",
            "plot_paths": "optional list[str] (if omitted, uses all generated plots)",
            "out_path": "str (e.g., 'reports/analysis_summary.md')",
            "highlights": "optional list[str] (bullet highlights for the report)"
        },
        fn=t_write_markdown,
    ),
}
