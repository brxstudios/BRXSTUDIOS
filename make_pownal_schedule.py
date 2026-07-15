#!/usr/bin/env python3
"""Generate the Pownal Security Schedule as a print-ready xlsx (portrait letter, 1 page).

Layout: title bar, then each day stacked top-to-bottom (Aug 11 -> 17), each with
Shift | Volunteer 1 | Volunteer 2 columns and blank fill-in cells.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.page import PageMargins

YELLOW = PatternFill("solid", fgColor="F6C445")
GREEN_HDR = PatternFill("solid", fgColor="93C47D")
GREEN = PatternFill("solid", fgColor="A9D08E")
BLUE_HDR = PatternFill("solid", fgColor="6D9EEB")
BLUE = PatternFill("solid", fgColor="CFE2F3")

thin = Side(style="thin", color="666666")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

DAYS = [
    ("August 11th  TUESDAY",   ["5pm - 10pm", "10pm - 3am", "3am - 8am (when volunteers arrive)"]),
    ("August 12th  WEDNESDAY", ["5pm - 10pm", "10pm - 3am", "3am - 8am (when volunteers arrive)"]),
    ("August 13th  THURSDAY",  ["5pm - 10pm", "10pm - 3am", "3am - 8am (when volunteers arrive)"]),
    ("August 14th  FRIDAY",    ["5pm - 10pm", "10pm - 3am", "3am - 8am (when volunteers arrive)"]),
    ("August 15th  SATURDAY",  ["5pm - 10pm", "10pm - 3am", "3am - 8am (when volunteers arrive)"]),
    ("August 16th  SUNDAY",    ["7am - 12pm", "12pm - 5pm", "5pm - 10pm", "10pm - 3am", "3am - 8am"]),
    ("August 17th  MONDAY",    ["7am - 12pm", "12pm - 5pm", "5pm - 10pm", "10pm - 3am", "3am - 8am (when volunteers arrive)"]),
]

wb = Workbook()
ws = wb.active
ws.title = "Security Schedule"

ws.column_dimensions["A"].width = 40  # shift
ws.column_dimensions["B"].width = 37  # volunteer 1
ws.column_dimensions["C"].width = 37  # volunteer 2

# Title bar
ws.merge_cells("A1:C1")
t = ws.cell(row=1, column=1, value="POWNAL SECURITY SCHEDULE")
t.font = Font(bold=True, size=20)
t.alignment = Alignment(horizontal="center", vertical="center")
for c in range(1, 4):
    ws.cell(row=1, column=c).fill = YELLOW
    ws.cell(row=1, column=c).border = BORDER
ws.row_dimensions[1].height = 34
ws.row_dimensions[2].height = 5

# Column labels (once, under the title)
for col, (label, fill, color) in enumerate([
    ("Shift", GREEN_HDR, "000000"),
    ("Volunteer 1", BLUE_HDR, "FFFFFF"),
    ("Volunteer 2", BLUE_HDR, "FFFFFF"),
], start=1):
    cell = ws.cell(row=3, column=col, value=label)
    cell.font = Font(bold=True, size=11, color=color)
    cell.fill = fill
    cell.border = BORDER
    cell.alignment = Alignment(horizontal="center" if col > 1 else "left", vertical="center")
ws.row_dimensions[3].height = 18

# Days stacked top to bottom
row = 4
for title, shifts in DAYS:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    h = ws.cell(row=row, column=1, value=title)
    h.font = Font(bold=True, size=12)
    h.alignment = Alignment(horizontal="left", vertical="center")
    for c in range(1, 4):
        ws.cell(row=row, column=c).fill = GREEN_HDR
        ws.cell(row=row, column=c).border = BORDER
    ws.row_dimensions[row].height = 20
    row += 1

    for shift in shifts:
        s = ws.cell(row=row, column=1, value=shift)
        s.font = Font(bold=True, size=10)
        s.fill = GREEN
        s.border = BORDER
        s.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        for col in (2, 3):
            v = ws.cell(row=row, column=col)
            v.fill = BLUE
            v.border = BORDER
        ws.row_dimensions[row].height = 36
        row += 1

# Footnote (from the original sheet)
NOTE = ("Please note that shifts are organized by calendar day. Even if a shift extends "
        "into the early morning hours, it is recorded under the day it begins to maintain "
        "scheduling consistency.")
ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
n = ws.cell(row=row, column=1, value=NOTE)
n.font = Font(italic=True, size=9)
n.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
ws.row_dimensions[row].height = 30
row += 1

# Print setup: one portrait letter page
ws.page_setup.orientation = "portrait"
ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
ws.page_setup.fitToPage = True
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 1
ws.page_margins = PageMargins(left=0.4, right=0.4, top=0.4, bottom=0.4)
ws.print_area = f"A1:C{row - 1}"
ws.sheet_view.showGridLines = False

wb.save("/home/user/BRXSTUDIOS/Pownal Security Schedule.xlsx")
print(f"Saved. Last row: {row - 1}")
