import csv
import json
import pandas as pd
from pathlib import Path

# Load user uploaded CSV
user_csv_path = Path("scratch/user_annotated_gold.csv")
# We will save the user's input text to this path
