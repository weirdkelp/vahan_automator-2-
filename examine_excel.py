import pandas as pd
import os

# Examine one Excel file to understand its structure
file_path = 'outputs/Andaman & Nicobar Island(3)/JAN/vahan_data_20250618_113625.xlsx'

if os.path.exists(file_path):
    df = pd.read_excel(file_path)
    print("Columns:", df.columns.tolist())
    print("Shape:", df.shape)
    print("First few rows:")
    print(df.head().to_string())
    print("\nData types:")
    print(df.dtypes.to_string())
else:
    print(f"File not found: {file_path}") 