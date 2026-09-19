import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Review"

ref_ws = wb.create_sheet(title="Taxonomy_Reference")
ref_ws["A1"] = "Intent"
intents = [
    "content_availability", "technical_support", "account_access",
    "billing_and_payments", "subscription_and_plans", "platform_and_regional",
    "product_feedback", "other_or_ambiguous"
]
for idx, it in enumerate(intents, 2):
    ref_ws[f"A{idx}"] = it

dv_intent = DataValidation(type="list", formula1="=Taxonomy_Reference!$A$2:$A$9", allow_blank=True)
ws.add_data_validation(dv_intent)
dv_intent.add("E2:E201")

wb.save("scratch/test_dv.xlsx")
print("Successfully saved test_dv.xlsx")
