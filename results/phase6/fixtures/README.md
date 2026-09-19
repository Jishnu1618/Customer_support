# Synthetic Evaluation Fixtures

These files are **strictly synthetic test fixtures** preserved from early pipeline development:
- `synthetic_ratings_fixture.csv`
- `synthetic_ratings_90_fixture.jsonl`

### Provenance & Purpose
- These values were originally copied from LLM Judge predictions solely to verify calculation code, data loaders, and statistical helper routines (such as linear-weighted Cohen's Kappa unit tests).
- **They are NOT human ratings.** No human annotator reviewed or scored these rows.
- They are decoupled from the authoritative evaluation pipeline and must **never** be used to claim inter-rater agreement or human alignment.
- Genuine human review is conducted via `results/phase6/reply_human_review_task.xlsx` and `human_ratings.csv`, where all human rating fields are kept empty until an independent human annotator completes and signs them.
