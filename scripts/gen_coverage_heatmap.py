#!/usr/bin/env python3
"""
Генератор тепловой карты покрытия тестами.

Создаёт coverage_heatmap/index.html — интерактивный Plotly-отчёт:
  • Treemap  — файлы как цветные плитки (площадь = строк кода, цвет = % покрытия)
  • Heatmap  — построчная карта для каждого файла (зелёный / красный / серый)
  • Bar-chart — стековые бары с покрытием по файлам
"""

import json
import math
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

COVERAGE_JSON = "coverage.json"
OUTPUT_DIR = Path("coverage_heatmap")
COLS = 80          # ширина сетки построчной карты (нормализованные позиции)
COLOR_COVERED   = "#22C55E"   # green-500
COLOR_MISSING   = "#EF4444"   # red-500
COLOR_NEUTRAL   = "#E2E8F0"   # slate-200  (не исполняемая строка)
BG              = "#F8FAFC"

# Плавная шкала красный → янтарный → зелёный
COVERAGE_COLORSCALE = [
    [0.00, "#EF4444"],
    [0.50, "#F59E0B"],
    [0.75, "#84CC16"],
    [1.00, "#22C55E"],
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def short_name(path: str) -> str:
    return path.lstrip("./").replace("\\", "/")


def line_grid(executed: list[int], missing: list[int]) -> list[float]:
    """Нормализует строки файла в массив из COLS ячеек."""
    executed_set = set(executed)
    missing_set  = set(missing)
    all_lines    = executed_set | missing_set
    if not all_lines:
        return [0.5] * COLS

    max_line = max(all_lines)
    grid = [0.5] * COLS   # 0.5 = не исполняемая
    for ln in executed_set:
        pos = min(int((ln - 1) / max_line * COLS), COLS - 1)
        grid[pos] = 1.0
    for ln in missing_set:
        pos = min(int((ln - 1) / max_line * COLS), COLS - 1)
        if grid[pos] < 1.0:
            grid[pos] = 0.0
    return grid


# ── Data loading ──────────────────────────────────────────────────────────────

def load_files(data: dict) -> list[dict]:
    rows = []
    for filepath, fdata in data["files"].items():
        s = fdata["summary"]
        rows.append({
            "path":     short_name(filepath),
            "pct":      round(s["percent_covered"], 1),
            "covered":  s["covered_lines"],
            "missing":  s["missing_lines"],
            "total":    s["num_statements"],
            "grid":     line_grid(fdata["executed_lines"], fdata["missing_lines"]),
        })
    rows.sort(key=lambda r: r["pct"])
    return rows


# ── Chart builders ────────────────────────────────────────────────────────────

def treemap_trace(files: list[dict]) -> go.Treemap:
    labels  = [f["path"] for f in files]
    values  = [max(f["total"], 1) for f in files]
    pcts    = [f["pct"] for f in files]
    hovers  = [
        f"<b>{f['path']}</b><br>"
        f"Покрытие: <b>{f['pct']}%</b><br>"
        f"Покрыто: {f['covered']} / {f['total']} строк"
        for f in files
    ]
    return go.Treemap(
        labels=labels,
        parents=[""] * len(labels),
        values=values,
        text=[f"{p}%" for p in pcts],
        textinfo="label+text",
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hovers,
        marker=dict(
            colors=pcts,
            colorscale=COVERAGE_COLORSCALE,
            cmin=0, cmax=100,
            showscale=True,
            colorbar=dict(
                title="Покрытие",
                tickvals=[0, 25, 50, 75, 100],
                ticktext=["0%", "25%", "50%", "75%", "100%"],
                len=0.45, y=0.78,
            ),
        ),
    )


def lineheatmap_trace(files: list[dict]) -> go.Heatmap:
    """Построчная тепловая карта: строки = файлы, столбцы = нормализованные позиции строк."""
    z        = [f["grid"] for f in reversed(files)]
    y_labels = [f["path"] for f in reversed(files)]
    return go.Heatmap(
        z=z,
        y=y_labels,
        colorscale=[
            [0.0,  COLOR_MISSING],
            [0.49, COLOR_MISSING],
            [0.50, COLOR_NEUTRAL],
            [0.51, COLOR_NEUTRAL],
            [0.99, COLOR_NEUTRAL],
            [1.0,  COLOR_COVERED],
        ],
        showscale=False,
        zmin=0, zmax=1,
        xgap=0.5, ygap=2,
        hovertemplate="Файл: <b>%{y}</b><br>Позиция: %{x}<extra></extra>",
    )


def bar_traces(files: list[dict]) -> tuple[go.Bar, go.Bar]:
    names   = [f["path"] for f in reversed(files)]
    covered = [f["covered"] for f in reversed(files)]
    missing = [f["missing"] for f in reversed(files)]
    pcts    = [f["pct"] for f in reversed(files)]

    bar_cov = go.Bar(
        name="Покрыто",
        y=names, x=covered,
        orientation="h",
        marker_color=[f"hsl({int(min(p * 1.2, 120))}, 60%, 45%)" for p in pcts],
        text=[f"{p}%" for p in pcts],
        textposition="inside",
        hovertemplate="%{y}<br>Покрыто: <b>%{x}</b> строк<extra></extra>",
    )
    bar_mis = go.Bar(
        name="Не покрыто",
        y=names, x=missing,
        orientation="h",
        marker_color="rgba(239,68,68,0.25)",
        hovertemplate="%{y}<br>Не покрыто: <b>%{x}</b> строк<extra></extra>",
    )
    return bar_cov, bar_mis


# ── Layout ────────────────────────────────────────────────────────────────────

def build_figure(files: list[dict], total_pct: float) -> go.Figure:
    n = len(files)
    bar_height   = max(260, n * 28)
    hmap_height  = max(180, n * 22)
    tree_height  = 380
    total_height = tree_height + hmap_height + bar_height + 120

    fig = make_subplots(
        rows=3, cols=1,
        specs=[
            [{"type": "treemap"}],
            [{"type": "heatmap"}],
            [{"type": "bar"}],
        ],
        subplot_titles=(
            "Treemap — площадь пропорциональна количеству строк",
            "Построчная карта покрытия (зелёный = покрыто, красный = нет)",
            "Строки по файлам",
        ),
        row_heights=[tree_height, hmap_height, bar_height],
        vertical_spacing=0.06,
    )

    fig.add_trace(treemap_trace(files), row=1, col=1)
    fig.add_trace(lineheatmap_trace(files), row=2, col=1)

    bar_cov, bar_mis = bar_traces(files)
    fig.add_trace(bar_cov, row=3, col=1)
    fig.add_trace(bar_mis, row=3, col=1)

    fig.update_layout(
        title=dict(
            text=f"Тепловая карта покрытия тестами — <b>{total_pct:.1f}%</b>",
            font=dict(size=20, family="system-ui, -apple-system, sans-serif"),
            x=0.5,
        ),
        height=total_height,
        paper_bgcolor=BG,
        plot_bgcolor="#FFFFFF",
        font=dict(family="system-ui, -apple-system, sans-serif", size=12, color="#0F172A"),
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=80, b=20),
    )

    fig.update_xaxes(showgrid=False, row=2, col=1,
                     ticktext=["0%", "25%", "50%", "75%", "100%"],
                     tickvals=[0, COLS * 0.25, COLS * 0.5, COLS * 0.75, COLS])
    fig.update_yaxes(tickfont=dict(size=10), row=2, col=1)
    fig.update_yaxes(tickfont=dict(size=10), row=3, col=1)
    fig.update_xaxes(title_text="Строк кода", row=3, col=1)

    for ann in fig.layout.annotations:
        ann.font.size = 13
        ann.font.color = "#475569"

    return fig


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    src = Path(COVERAGE_JSON)
    if not src.exists():
        print(f"ERROR: {COVERAGE_JSON} not found. Run pytest with --cov-report=json first.",
              file=sys.stderr)
        sys.exit(1)

    with open(src) as f:
        data = json.load(f)

    files     = load_files(data)
    total_pct = data["totals"]["percent_covered"]

    fig = build_figure(files, total_pct)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / "index.html"
    fig.write_html(
        out,
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": True, "displaylogo": False,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )
    print(f"✓ Тепловая карта сохранена: {out}  (покрытие: {total_pct:.1f}%)")


if __name__ == "__main__":
    main()
