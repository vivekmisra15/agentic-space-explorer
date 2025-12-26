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
    out = (
        df.groupby(group_by)
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
    if success_col not in df.columns:
        raise ValueError(f"success_col '{success_col}' not found in dataframe columns")

    out = (
        df.groupby(group_by)[success_col]
          .mean()
          .reset_index(name="success_rate")
          .sort_values(group_by)
    )

    # Planner-friendly alias: lets the LLM use y="Success" and still work
    out[success_col] = out["success_rate"]

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

    # Register output artifact
    context["artifacts"]["plots"].append(out_path)


def t_write_markdown(*, context: Dict[str, Any], title: str, tables: List[str], plot_paths: Optional[List[str]], out_path: str) -> None:
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
    "write_markdown": ToolSpec(
        name="write_markdown",
        description="Write a markdown report referencing tables and plots.",
        args_schema={
            "title": "str",
            "tables": "list[str] (table names)",
            "plot_paths": "optional list[str] (if omitted, uses all generated plots)",
            "out_path": "str (e.g., 'reports/analysis_summary.md')",
        },
        fn=t_write_markdown,
    ),
}
