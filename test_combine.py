import os
import pandas as pd

OUTPUTS_DIR = 'outputs'
COMBINED_FILE_XLSX = 'test_combined_data.xlsx'
COMBINED_FILE_CSV = 'test_combined_data.csv'

all_data = []
file_count = 0
max_files = 5  # Only process first 5 files for testing

print("Starting to process files...")

for state in os.listdir(OUTPUTS_DIR):
    if file_count >= max_files:
        break
    state_path = os.path.join(OUTPUTS_DIR, state)
    if not os.path.isdir(state_path):
        continue
    print(f"Processing state: {state}")
    
    for month in os.listdir(state_path):
        if file_count >= max_files:
            break
        month_path = os.path.join(state_path, month)
        if not os.path.isdir(month_path):
            continue
        
        for fname in os.listdir(month_path):
            if file_count >= max_files:
                break
            if fname.endswith('.xlsx'):
                fpath = os.path.join(month_path, fname)
                try:
                    print(f"Loading file {file_count + 1}: {fpath}")
                    df = pd.read_excel(fpath)
                    df['State'] = state
                    df['Month'] = month
                    all_data.append(df)
                    print(f"Successfully loaded: {fpath} ({df.shape[0]} rows)")
                    file_count += 1
                except Exception as e:
                    print(f"Failed to load {fpath}: {e}")

print(f"Processed {file_count} files")

if all_data:
    print("Combining data...")
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Combined DataFrame shape: {combined_df.shape}")
    print(f"Columns: {combined_df.columns.tolist()}")
    
    try:
        combined_df.to_excel(COMBINED_FILE_XLSX, index=False)
        print(f"Test file saved as {COMBINED_FILE_XLSX}")
    except Exception as e:
        print(f"Failed to save as Excel: {e}")
    
    try:
        combined_df.to_csv(COMBINED_FILE_CSV, index=False)
        print(f"Test file also saved as {COMBINED_FILE_CSV}")
    except Exception as e:
        print(f"Failed to save as CSV: {e}")
else:
    print("No data found to combine.") 