from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Iterable

import xlsxwriter


FIELDS = [
    "id",
    "title",
    "severity",
    "service",
    "source",
    "status",
    "count",
    "first_seen",
    "last_seen",
    "recovered_at",
    "acknowledged_at",
    "sample_message",
]


def incidents_to_csv(rows: Iterable[dict]) -> bytes:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def incidents_to_xlsx(rows: list[dict]) -> bytes:
    stream = BytesIO()
    workbook = xlsxwriter.Workbook(stream, {"in_memory": True})
    sheet = workbook.add_worksheet("Incidents")
    summary = workbook.add_worksheet("Summary")

    header = workbook.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#172033",
            "border": 1,
            "align": "center",
        }
    )
    critical = workbook.add_format({"bg_color": "#FDE8E7", "font_color": "#B42318"})
    high = workbook.add_format({"bg_color": "#FFF3DC", "font_color": "#9A5700"})
    recovered = workbook.add_format({"bg_color": "#E8F7EE", "font_color": "#157347"})
    wrap = workbook.add_format({"text_wrap": True, "valign": "top"})
    title = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#172033"})
    metric = workbook.add_format({"bold": True, "font_size": 22, "align": "center"})

    for col, field in enumerate(FIELDS):
        sheet.write(0, col, field.replace("_", " ").title(), header)

    for row_index, row in enumerate(rows, start=1):
        for col, field in enumerate(FIELDS):
            value = row.get(field)
            fmt = wrap if field in {"sample_message", "source"} else None
            sheet.write(row_index, col, value if value is not None else "", fmt)
        severity = row.get("severity")
        status = row.get("status")
        if severity == "critical":
            sheet.set_row(row_index, None, critical)
        elif severity == "high":
            sheet.set_row(row_index, None, high)
        if status in {"recovered", "resolved"}:
            sheet.set_row(row_index, None, recovered)

    sheet.freeze_panes(1, 0)
    sheet.autofilter(0, 0, max(len(rows), 1), len(FIELDS) - 1)
    sheet.set_column(0, 0, 8)
    sheet.set_column(1, 1, 31)
    sheet.set_column(2, 5, 16)
    sheet.set_column(6, 6, 10)
    sheet.set_column(7, 10, 23)
    sheet.set_column(11, 11, 70)

    total = len(rows)
    open_count = sum(row.get("status") in {"open", "acknowledged"} for row in rows)
    critical_count = sum(
        row.get("severity") == "critical"
        and row.get("status") in {"open", "acknowledged"}
        for row in rows
    )
    recovered_count = sum(row.get("status") in {"recovered", "resolved"} for row in rows)

    summary.write("A1", "LogPulse Sentinel Incident Report", title)
    labels = ["Total incidents", "Open incidents", "Open critical", "Recovered / resolved"]
    values = [total, open_count, critical_count, recovered_count]
    for index, (label, value) in enumerate(zip(labels, values), start=3):
        summary.write(index, 0, label, header)
        summary.write(index, 1, value, metric)
    summary.set_column("A:A", 28)
    summary.set_column("B:B", 20)

    workbook.close()
    return stream.getvalue()
