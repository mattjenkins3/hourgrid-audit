"""Dependency-free, accessible SVG completeness dashboard."""
from __future__ import annotations

from html import escape


def render_svg(report: dict) -> str:
    months = report["months"]
    width, height = 900, 490
    status = "PASS" if report["ok"] else "ISSUES DETECTED"
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">Hourly coverage audit — {report["year"]} — {status}</title>',
        '<desc id="desc">Twelve monthly cards show observed distinct UTC hourly slots versus expected slots. Amber highlights missing hours. Not a data quality or forecast accuracy score.</desc>',
        '<rect width="900" height="490" fill="#f8fafc"/>',
        '<text x="34" y="46" font-family="sans-serif" font-size="27" font-weight="bold" fill="#14263d">Hourly coverage audit</text>',
        f'<text x="34" y="75" font-family="sans-serif" font-size="15" fill="#475569">{report["year"]} · {escape(report["basis"])} · {escape(report["label"])} labels · {report["coverage_percent"]}% coverage</text>',
        f'<text x="34" y="100" font-family="sans-serif" font-size="14" fill="#475569">{report["observed_unique_hours"]:,} / {report["expected_hours"]:,} unique expected hours · {status}</text>',
    ]
    for i, m in enumerate(months):
        col, row = i % 4, i // 4
        x, y = 34 + col * 217, 130 + row * 114
        total = m["expected"]
        fraction = m["observed"] / total if total else 0
        filled = max(0, min(169, 169 * fraction))
        good = m["missing"] == 0
        pieces.extend([
            f'<rect x="{x}" y="{y}" width="202" height="98" rx="9" fill="#ffffff" stroke="#cbd5e1"/>',
            f'<text x="{x+14}" y="{y+26}" font-family="sans-serif" font-size="18" font-weight="bold" fill="#14263d">{m["month"]}</text>',
            f'<text x="{x+188}" y="{y+26}" text-anchor="end" font-family="sans-serif" font-size="12" fill="{ "#146c55" if good else "#99510a"}">{m["missing"]} missing</text>',
            f'<rect x="{x+14}" y="{y+43}" width="169" height="13" rx="3" fill="#f5c36d"/>',
            f'<rect x="{x+14}" y="{y+43}" width="{filled:.2f}" height="13" rx="3" fill="#17846a"/>',
            f'<text x="{x+14}" y="{y+77}" font-family="sans-serif" font-size="13" fill="#475569">{m["observed"]} / {total} hours</text>',
        ])
    pieces.extend([
        '<rect x="34" y="477" width="10" height="10" fill="#17846a"/>',
        '<text x="51" y="486" font-family="sans-serif" font-size="11" fill="#475569">Observed unique hours</text>',
        '<rect x="210" y="477" width="10" height="10" fill="#f5c36d"/>',
        '<text x="227" y="486" font-family="sans-serif" font-size="11" fill="#475569">Missing expected hours</text>',
        '</svg>',
    ])
    return "\n".join(pieces) + "\n"
