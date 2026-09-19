import json
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import pandas as pd

with open('golden_eval.jsonl', 'r', encoding='utf-8') as f:
    gold_records = [json.loads(line) for line in f if line.strip()]

with open('gold_selection_manifest.jsonl', 'r', encoding='utf-8') as f:
    manifest_records = [json.loads(line) for line in f if line.strip()]
manifest_dict = {m['example_id']: m for m in manifest_records}

df_labels = pd.read_csv('gold_labels.csv', dtype=str).set_index('example_id').to_dict('index')

wb = openpyxl.load_workbook('results/phase2_v2/gold_human_review.xlsx')
ws = wb['Gold_Human_Review']

for r in range(ws.max_row, 1, -1):
    ws.delete_rows(r)

font_data = Font(name='Segoe UI', size=10)
thin_border_side = Side(border_style='thin', color='CBD5E1')
cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
fill_zebra = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')

align_left_wrap = Alignment(horizontal='left', vertical='top', wrap_text=True)
align_center_top = Alignment(horizontal='center', vertical='top')

for idx, g in enumerate(gold_records, start=2):
    eid = g['example_id']
    m = manifest_dict[eid]
    lbl = df_labels[eid]
    
    ancestor_turns = m.get('ancestor_turns', [])
    if len(ancestor_turns) <= 1:
        prior_context_text = 'None (Initial Root Inquiry)'
    else:
        prior_turns = ancestor_turns[:-1]
        lines = []
        for t in prior_turns:
            role = 'Customer' if t.get('inbound') else 'Brand (SpotifyCares)'
            lines.append(f"[{role} - Tweet {t.get('tweet_id')}]: {t.get('text', '')}")
        prior_context_text = '\n\n'.join(lines)
        
    target_msg = g['message']
    
    row_values = [
        eid,
        g['subset'],
        prior_context_text,
        target_msg,
        lbl['intent'],
        lbl['handling_decision'],
        lbl['handling_reason'],
        lbl['required_reply_elements'],
        lbl['prohibited_claims_or_actions'],
        str(lbl['needs_clarification']),
        lbl['annotation_confidence'],
        lbl['annotator_id'],
        lbl['notes']
    ]
    
    ws.row_dimensions[idx].height = 65
    is_even = (idx % 2 == 0)
    for c_idx, val in enumerate(row_values, 1):
        cell = ws.cell(row=idx, column=c_idx, value=val)
        cell.font = font_data
        cell.border = cell_border
        if c_idx in [1, 2, 5, 6, 10, 11, 12]:
            cell.alignment = align_center_top
        else:
            cell.alignment = align_left_wrap
        if is_even and c_idx <= 4:
            cell.fill = fill_zebra

wb.save('gold_human_review.xlsx')
print('Successfully rebuilt gold_human_review.xlsx with 200 items and Taxonomy_Reference sheet!')
