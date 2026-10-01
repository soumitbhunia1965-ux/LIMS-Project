import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Privilege & SoD Matrix"
ws.views.sheetView[0].showGridLines = True

# Title block
ws.merge_cells('A1:G1')
title_cell = ws['A1']
title_cell.value = "QC LIMS - 21 CFR PART 11 ROLE & PRIVILEGE MATRIX (SEGREGATION OF DUTIES)"
title_cell.font = Font(name='Arial', size=13, bold=True, color='FFFFFF')
title_cell.fill = PatternFill(start_color='071527', end_color='071527', fill_type='solid')
title_cell.alignment = Alignment(horizontal='center', vertical='center')
ws.row_dimensions[1].height = 36

# Headers
headers = [
    "Module / Functional Area",
    "Action / System Event",
    "QC Analyst (ANALYST)",
    "Peer Reviewer (REVIEWER)",
    "QA Manager (QA_MANAGER)",
    "System Admin (SYSTEM_ADMIN)",
    "Segregation of Duties (SoD) & Regulatory Control Rule"
]

header_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
header_font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
thin_border = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

ws.row_dimensions[2].height = 28
for col_idx, header in enumerate(headers, start=1):
    cell = ws.cell(row=2, column=col_idx, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell.border = thin_border

# Data Rows
matrix_data = [
    ["Authentication", "Sign-in & select database instance", "Allow", "Allow", "Allow", "Allow", "Role-based authentication with instance logging."],
    ["Authentication", "User profile & department setup", "Deny", "Deny", "Deny", "Allow", "Prevents lab staff from modifying user security profiles."],
    ["Master Data (MDM)", "Register Product / Material Master", "Deny", "Review Only", "Allow", "Master data entries require QA authorization prior to use."],
    ["Master Data (MDM)", "Create / Approve Specification Binders", "Deny", "Review Only", "Allow", "QA holds sole authority to commit acceptance limits."],
    ["Master Data (MDM)", "Author Standard Test Procedures (STP)", "Allow", "Allow", "Review Only", "Analysts draft methods; peer reviewers confirm technical scope."],
    ["Sample Management", "Accession / Log New Sample", "Allow", "Allow", "Deny", "Deny", "Bench accessioning role; segregated from release authority."],
    ["Sample Management", "Transfer Custody / Update Location", "Allow", "Allow", "Allow", "Deny", "Chain of custody requires dual user attribution."],
    ["Sample Management", "Place Quality Administrative Hold", "Allow", "Allow", "Allow", "Deny", "Any user can place a hold upon detecting deviations."],
    ["Sample Management", "Release Quality Administrative Hold", "Deny", "Deny", "Allow", "Deny", "Quality holds require QA e-signature with justification to release."],
    ["Analytical Testing", "Enter / Edit Analytical Results", "Allow", "Deny", "Deny", "Deny", "Raw data entry reserved for performing analyst."],
    ["Analytical Testing", "Technical Peer Review (e-Sign)", "Deny", "Allow", "Deny", "Deny", "Reviewer cannot be the same user who logged or tested the sample."],
    ["Analytical Testing", "QA Disposition & Release (e-Sign)", "Deny", "Deny", "Allow", "Deny", "QA release must be independent from Analyst and Reviewer."],
    ["OOS Investigations", "Initiate Phase I OOS Record", "Allow", "Allow", "Deny", "Deny", "Triggered upon numeric range breach."],
    ["OOS Investigations", "Conclude & Authorize OOS Record", "Deny", "Deny", "Allow", "Deny", "QA release manager holds final decision on invalidation."],
    ["Instruments", "Register Instrument / Calibration", "Allow", "Allow", "Review Only", "Deny", "Metrology/QC analysts execute calibrations; expired tools locked."],
    ["Instruments", "Configure Connector Interfaces / Ports", "Deny", "Deny", "Deny", "Allow", "Port configurations restricted to System Administrators."],
    ["Stability", "Register Study & Log Chamber Pulls", "Allow", "Allow", "Review Only", "Deny", "Protocol scheduled and pulled by stability coordinators."],
    ["Audit Trail", "View Audit Trail Records", "Allow", "Allow", "Allow", "Allow", "Read-only access available across all certified roles."],
    ["Audit Trail", "Modify / Delete Audit Records", "Deny", "Deny", "Deny", "Deny", "21 CFR Part 11 Rule: Records are immutable (hard lock)."]
]

allow_fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
allow_font = Font(name='Arial', size=9, bold=True, color='375623')

deny_fill = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')
deny_font = Font(name='Arial', size=9, bold=True, color='C65911')

review_fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
review_font = Font(name='Arial', size=9, bold=True, color='833C0C')

standard_font = Font(name='Arial', size=9)

for row_idx, row_values in enumerate(matrix_data, start=3):
    ws.row_dimensions[row_idx].height = 22
    for col_idx, value in enumerate(row_values, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.border = thin_border
        cell.font = standard_font
        
        if col_idx in [3, 4, 5, 6]:
            cell.alignment = Alignment(horizontal='center', vertical='center')
            if value == "Allow":
                cell.fill = allow_fill
                cell.font = allow_font
            elif value == "Deny":
                cell.fill = deny_fill
                cell.font = deny_font
            elif value == "Review Only":
                cell.fill = review_fill
                cell.font = review_font
        elif col_idx in [1, 2]:
            cell.alignment = Alignment(horizontal='left', vertical='center')
        else:
            cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

# Adjust column widths
col_widths = [22, 38, 18, 18, 18, 18, 48]
for i, width in enumerate(col_widths, start=1):
    col_letter = get_column_letter(i)
    ws.column_dimensions[col_letter].width = width

wb.save("D:/LIMS Project/QC_LIMS_Privilege_Matrix.xlsx")
print("Successfully generated D:/LIMS Project/QC_LIMS_Privilege_Matrix.xlsx")
