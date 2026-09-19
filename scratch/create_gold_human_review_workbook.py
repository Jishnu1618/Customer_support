import json
import shutil
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

manifest_path = Path("gold_selection_manifest.jsonl")
eval_pool_path = Path("data/processed/v2/eval_pool_inputs.jsonl")
dev_path = Path("data/processed/v2/dev_inputs.jsonl")
cluster_path = Path("data/manifests/v2/cluster_membership.json")
out_xlsx_root = Path("gold_human_review.xlsx")
out_xlsx_results = Path("results/phase2_v2/gold_human_review.xlsx")

# 1. Load Data
with open(manifest_path, "r", encoding="utf-8") as f:
    manifest_records = [json.loads(line) for line in f]

with open(eval_pool_path, "r", encoding="utf-8") as f:
    eval_records = [json.loads(line) for line in f]

with open(dev_path, "r", encoding="utf-8") as f:
    dev_records = [json.loads(line) for line in f]

with open(cluster_path, "r", encoding="utf-8") as f:
    cluster_membership = json.load(f)

print(f"Loaded {len(manifest_records)} gold selection manifest records.")
print(f"Loaded {len(eval_records)} evaluation pool records.")

# 2. Join & Verification (1-to-1 match check)
eval_dict = {}
for r in eval_records:
    eid = r["example_id"]
    if eid in eval_dict:
        raise ValueError(f"CRITICAL: Duplicate example_id found in eval_pool_inputs: {eid}")
    eval_dict[eid] = r

matched_items = []
missing_ids = []

for m in manifest_records:
    eid = m["example_id"]
    if eid not in eval_dict:
        missing_ids.append(eid)
    else:
        eval_item = eval_dict[eid]
        matched_items.append((m, eval_item))

if missing_ids:
    raise ValueError(f"CRITICAL: {len(missing_ids)} manifest records missing from eval pool: {missing_ids}")

assert len(matched_items) == 200, f"Expected 200 matched items, got {len(matched_items)}"
print(f"Verification: All 200 manifest records matched exactly 1 evaluation pool record.")

# 3. Development Contamination Audit
dev_gids = {d["group_id"] for d in dev_records}
dev_clusters = {cluster_membership.get(gid) for gid in dev_gids if cluster_membership.get(gid)}

contam_dev_direct = []
contam_dev_cluster = []

for m, eval_item in matched_items:
    gid = eval_item["group_id"]
    if gid in dev_gids:
        contam_dev_direct.append(gid)
    cid = cluster_membership.get(gid)
    if cid and cid in dev_clusters:
        contam_dev_cluster.append(gid)

if contam_dev_direct or contam_dev_cluster:
    raise ValueError(
        f"CRITICAL: Contamination detected! Direct dev groups: {contam_dev_direct}, "
        f"Dev cluster groups: {contam_dev_cluster}"
    )

print("Contamination Audit: 0 direct dev groups, 0 dev duplicate cluster groups in gold set.")

# 4. Build Excel Workbook
wb = openpyxl.Workbook()

# Sheet 1: Gold Human Review
ws = wb.active
ws.title = "Gold_Human_Review"
ws.views.sheetView[0].showGridLines = True

# Sheet 2: Taxonomy Reference
ref_ws = wb.create_sheet(title="Taxonomy_Reference")
ref_ws.views.sheetView[0].showGridLines = True

# Define Lists in Taxonomy_Reference
intents_data = [
    ("content_availability", "Content Availability & Licensing", "Inquiries regarding missing, removed, unavailable, or upcoming songs, albums, artists, or podcasts."),
    ("technical_support", "Technical Support & App Performance", "Inquiries reporting software bugs, playback failures, crashes, audio glitches, sync issues, or update regressions."),
    ("account_access", "Account Access & Security", "Issues logging in, resetting passwords, recovering accounts after Facebook disconnection, or hacked accounts."),
    ("billing_and_payments", "Billing, Payments & Invoicing", "Disputes or questions about charges, payment methods, billing dates, missing premium status, grace periods, or cancellations."),
    ("subscription_and_plans", "Subscription & Plan Management", "Questions regarding plan types (Family, Student), member invites, address verification, multi-stream rules, or account deletion."),
    ("platform_and_regional", "Platform Compatibility & Regional", "Service availability in specific countries/regions, travel/roaming limits, or external hardware/assistant integrations (Sonos, Siri)."),
    ("product_feedback", "Product Feedback, Suggestions & UX", "Feature suggestions, UI/UX feedback, comments on recommendation algorithms, ad placement complaints, or general user discontent."),
    ("other_or_ambiguous", "Other, Social Banter & Ambiguous", "Messages lacking actionable support requests: compliments, praise, banter, jokes, vague complaints requiring external media, or spam.")
]

ref_ws["A1"] = "Intent_Code"
ref_ws["B1"] = "Intent_Name"
ref_ws["C1"] = "Description"
ref_ws["A1"].font = Font(bold=True, color="FFFFFF")
ref_ws["B1"].font = Font(bold=True, color="FFFFFF")
ref_ws["C1"].font = Font(bold=True, color="FFFFFF")
ref_header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
ref_ws["A1"].fill = ref_header_fill
ref_ws["B1"].fill = ref_header_fill
ref_ws["C1"].fill = ref_header_fill

for row_idx, (code, name, desc) in enumerate(intents_data, 2):
    ref_ws[f"A{row_idx}"] = code
    ref_ws[f"B{row_idx}"] = name
    ref_ws[f"C{row_idx}"] = desc

# Handling decisions list
ref_ws["E1"] = "Handling_Decision"
ref_ws["F1"] = "Decision_Description"
ref_ws["E1"].font = Font(bold=True, color="FFFFFF")
ref_ws["F1"].font = Font(bold=True, color="FFFFFF")
ref_ws["E1"].fill = ref_header_fill
ref_ws["F1"].fill = ref_header_fill
decisions_data = [
    ("auto_handle", "Safe automated reply can be sent (troubleshooting, policy explanation, self-serve link, polite acknowledgement)."),
    ("escalate", "Requires confidential account data, financial transaction lookup, backend database edits, or human security authorization.")
]
for row_idx, (code, desc) in enumerate(decisions_data, 2):
    ref_ws[f"E{row_idx}"] = code
    ref_ws[f"F{row_idx}"] = desc

# Needs clarification list
ref_ws["H1"] = "Needs_Clarification"
ref_ws["H1"].font = Font(bold=True, color="FFFFFF")
ref_ws["H1"].fill = ref_header_fill
ref_ws["H2"] = "True"
ref_ws["H3"] = "False"

# Confidence list
ref_ws["J1"] = "Confidence_Tier"
ref_ws["J1"].font = Font(bold=True, color="FFFFFF")
ref_ws["J1"].fill = ref_header_fill
ref_ws["J2"] = "high"
ref_ws["J3"] = "medium"
ref_ws["J4"] = "low"

# Auto-adjust column widths on reference sheet
ref_ws.column_dimensions["A"].width = 25
ref_ws.column_dimensions["B"].width = 35
ref_ws.column_dimensions["C"].width = 75
ref_ws.column_dimensions["E"].width = 20
ref_ws.column_dimensions["F"].width = 65
ref_ws.column_dimensions["H"].width = 22
ref_ws.column_dimensions["J"].width = 18

# Define Headers for Sheet 1
headers = [
    ("Example_ID", 32, "context"),
    ("Evaluation_Subset", 16, "context"),
    ("Allowed_Prior_Context", 48, "context"),
    ("Target_Customer_Message", 52, "context"),
    ("Human_Intent", 24, "annotation"),
    ("Human_Handling_Decision", 22, "annotation"),
    ("Human_Handling_Reason", 30, "annotation"),
    ("Human_Required_Reply_Elements", 38, "annotation"),
    ("Human_Prohibited_Claims_Or_Actions", 38, "annotation"),
    ("Human_Needs_Clarification", 22, "annotation"),
    ("Human_Annotation_Confidence", 22, "annotation"),
    ("Annotator_ID", 18, "annotation"),
    ("Notes", 32, "annotation")
]

# Style Definitions
font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
font_data = Font(name="Segoe UI", size=10)
fill_context_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")     # Slate 800
fill_annotation_header = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")  # Teal 700
fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")              # Light gray

thin_border_side = Side(border_style="thin", color="CBD5E1")
cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

align_left_wrap = Alignment(horizontal="left", vertical="top", wrap_text=True)
align_center_top = Alignment(horizontal="center", vertical="top")
align_center_header = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Write Headers
ws.row_dimensions[1].height = 32
for col_idx, (header_name, width, group_type) in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col_idx, value=header_name)
    cell.font = font_header
    cell.alignment = align_center_header
    cell.border = cell_border
    if group_type == "context":
        cell.fill = fill_context_header
    else:
        cell.fill = fill_annotation_header
    col_letter = get_column_letter(col_idx)
    ws.column_dimensions[col_letter].width = width

# Populate Rows (200 records)
for row_num, (m, eval_item) in enumerate(matched_items, 2):
    ex_id = m["example_id"]
    subset = m.get("subset", "evaluation")
    
    # Extract allowed prior context (all turns in ancestor path before target customer message)
    ancestor_turns = eval_item.get("ancestor_turns", [])
    if len(ancestor_turns) <= 1:
        prior_context_text = "None (Initial Root Inquiry)"
    else:
        prior_turns = ancestor_turns[:-1]
        lines = []
        for t in prior_turns:
            role = "Customer" if t.get("inbound") else "Brand (SpotifyCares)"
            lines.append(f"[{role} - Tweet {t.get('tweet_id')}]: {t.get('text', '')}")
        prior_context_text = "\n\n".join(lines)
        
    # Extract target customer message (last turn in ancestor path)
    if ancestor_turns:
        target_msg = ancestor_turns[-1].get("text", "")
    else:
        target_msg = eval_item.get("model_input_text", "")
        
    # Write context columns
    ws.cell(row=row_num, column=1, value=ex_id).alignment = align_center_top
    ws.cell(row=row_num, column=2, value=subset).alignment = align_center_top
    ws.cell(row=row_num, column=3, value=prior_context_text).alignment = align_left_wrap
    ws.cell(row=row_num, column=4, value=target_msg).alignment = align_left_wrap
    
    # Write blank annotation columns (Cols 5 to 13)
    for col_idx in range(5, 14):
        c = ws.cell(row=row_num, column=col_idx, value="")
        if col_idx in [5, 6, 10, 11, 12]:  # Dropdowns & ID
            c.alignment = align_center_top
        else:
            c.alignment = align_left_wrap

    # Apply styling & borders
    ws.row_dimensions[row_num].height = 65
    is_even = (row_num % 2 == 0)
    for col_idx in range(1, 14):
        c = ws.cell(row=row_num, column=col_idx)
        c.font = font_data
        c.border = cell_border
        if is_even and col_idx <= 4:
            c.fill = fill_zebra

# Add Data Validation Dropdowns
# 1. Intent (Col E)
dv_intent = DataValidation(
    type="list",
    formula1="=Taxonomy_Reference!$A$2:$A$9",
    allow_blank=True
)
dv_intent.error = "Please select a valid intent from the taxonomy."
dv_intent.errorTitle = "Invalid Intent"
dv_intent.prompt = "Select intent from dropdown."
dv_intent.promptTitle = "Intent Selection"
ws.add_data_validation(dv_intent)
dv_intent.add("E2:E201")

# 2. Handling Decision (Col F)
dv_decision = DataValidation(
    type="list",
    formula1="=Taxonomy_Reference!$E$2:$E$3",
    allow_blank=True
)
dv_decision.error = "Select either auto_handle or escalate."
dv_decision.errorTitle = "Invalid Decision"
dv_decision.prompt = "Select auto_handle or escalate."
dv_decision.promptTitle = "Handling Decision"
ws.add_data_validation(dv_decision)
dv_decision.add("F2:F201")

# 3. Needs Clarification (Col J)
dv_clarification = DataValidation(
    type="list",
    formula1="=Taxonomy_Reference!$H$2:$H$3",
    allow_blank=True
)
dv_clarification.error = "Select True or False."
dv_clarification.errorTitle = "Invalid Value"
dv_clarification.prompt = "Select True or False."
dv_clarification.promptTitle = "Needs Clarification"
ws.add_data_validation(dv_clarification)
dv_clarification.add("J2:J201")

# 4. Confidence (Col K)
dv_confidence = DataValidation(
    type="list",
    formula1="=Taxonomy_Reference!$J$2:$J$4",
    allow_blank=True
)
dv_confidence.error = "Select high, medium, or low."
dv_confidence.errorTitle = "Invalid Confidence"
dv_confidence.prompt = "Select high, medium, or low."
dv_confidence.promptTitle = "Annotation Confidence"
ws.add_data_validation(dv_confidence)
dv_confidence.add("K2:K201")

# Freeze panes at row 2, column E (columns A-D visible while scrolling across annotation fields)
ws.freeze_panes = "E2"

# Save workbook
wb.save(out_xlsx_root)
print(f"Successfully created: {out_xlsx_root}")

# Mirror to results directory
shutil.copyfile(out_xlsx_root, out_xlsx_results)
print(f"Successfully copied to: {out_xlsx_results}")
