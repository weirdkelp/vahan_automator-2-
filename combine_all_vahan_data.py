import os
import pandas as pd
import sys

if len(sys.argv) > 1:
    OUTPUTS_DIR = sys.argv[1]
else:
    OUTPUTS_DIR = 'outputs'

if not os.path.isdir(OUTPUTS_DIR):
    print(f"[ERROR] The specified folder '{OUTPUTS_DIR}' does not exist.")
    sys.exit(1)

print(f"[INFO] Combining data from folder: {OUTPUTS_DIR}")

COMBINED_FILE_XLSX = f'combined_data_{os.path.basename(OUTPUTS_DIR)}.xlsx'
COMBINED_FILE_CSV = f'combined_data_{os.path.basename(OUTPUTS_DIR)}.csv'

all_data = []

for state in os.listdir(OUTPUTS_DIR):
    state_path = os.path.join(OUTPUTS_DIR, state)
    if not os.path.isdir(state_path):
        continue
    for year in os.listdir(state_path):
        year_path = os.path.join(state_path, year)
        if not os.path.isdir(year_path):
            continue
        for month in os.listdir(year_path):
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue
            for fname in os.listdir(month_path):
                if fname.endswith('.xlsx'):
                    fpath = os.path.join(month_path, fname)
                    try:
                        # Read the file without header to find the real header row
                        preview = pd.read_excel(fpath, header=None, nrows=10)
                        header_row_idx = None
                        for i, row in preview.iterrows():
                            row_str = row.astype(str).str.lower().str.replace(' ', '')
                            if ('sno' in row_str.values or 's.no.' in row_str.values) and any('maker' in v for v in row_str.values):
                                header_row_idx = i
                                break
                        if header_row_idx is None:
                            print(f"Could not find real header in {fpath}, skipping.")
                            continue
                        df = pd.read_excel(fpath, header=header_row_idx)
                        # Standardize column names and remove 'Unnamed' from column names
                        df.columns = [str(col).replace('Unnamed', '').strip() for col in df.columns]
                        # If there are multiple S.No. columns, keep only the last one
                        sno_cols = [col for col in df.columns if str(col).strip().replace(' ', '').lower() in ['s.no.', 'sno', 's.no']]
                        if len(sno_cols) > 1:
                            for col in sno_cols[:-1]:
                                df = df.drop(columns=col)
                        # Rename the last S.No. column to 'S.No.'
                        if sno_cols:
                            df = df.rename(columns={sno_cols[-1]: 'S.No.'})
                        df['State'] = state
                        df['Year'] = year
                        df['Month'] = month
                        all_data.append(df)
                        print(f"Loaded: {fpath} ({df.shape[0]} rows, header at row {header_row_idx})")
                    except Exception as e:
                        print(f"Failed to load {fpath}: {e}")

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True, join='outer')
    # Convert all columns that look like numbers but are stored as text to numeric type
    for col in combined_df.columns:
        combined_df[col] = pd.to_numeric(combined_df[col], errors='ignore')
    # Drop all columns whose names start with 'S.No.' (including all variants)
    sno_cols = [col for col in combined_df.columns if str(col).strip().replace(' ', '').lower().startswith('s.no.') or str(col).strip().replace(' ', '').lower() == 'sno']
    if sno_cols:
        combined_df = combined_df.drop(columns=sno_cols)
    print('All columns in combined DataFrame:')
    print(combined_df.columns.tolist())
    # --- Combine Month and Year into YYYYMM format ---
    month_map = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}
    if 'Month' in combined_df.columns and 'Year' in combined_df.columns:
        combined_df['Month'] = combined_df.apply(lambda row: f"{row['Year']}{month_map.get(str(row['Month']).upper(), '??')}", axis=1)
        combined_df = combined_df.drop(columns=['Year'])
    # Find Maker and Vehicle Class columns (case-insensitive, ignore spaces)
    def find_col(df, target):
        return next((col for col in df.columns if col.strip().replace(' ', '').lower() == target), None)
    maker_col = find_col(combined_df, 'maker')
    vehicle_class_col = find_col(combined_df, 'vehicleclass')
    # Remove State, Month, Maker, Vehicle Class if already present
    cols = combined_df.columns.tolist()
    for col in ['State', 'Month', maker_col, vehicle_class_col]:
        if col in cols:
            cols.remove(col)
    # Insert in desired order, but only if the column exists
    new_order = []
    for col in ['State', 'Month', maker_col, vehicle_class_col]:
        if col and col in combined_df.columns:
            new_order.append(col)
    new_order += cols
    combined_df = combined_df[new_order]
    print(f"Combined DataFrame shape: {combined_df.shape}")
    print(f"Columns: {combined_df.columns.tolist()}")
    try:
        with pd.ExcelWriter(COMBINED_FILE_XLSX, engine='openpyxl') as writer:
            combined_df.to_excel(writer, index=False)
            worksheet = writer.sheets['Sheet1']
            for col in worksheet.columns:
                max_length = 32
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max_length
        print(f"Combined file saved as {COMBINED_FILE_XLSX} with column width 32.")
    except Exception as e:
        print(f"Failed to save as Excel: {e}")
    try:
        combined_df.to_csv(COMBINED_FILE_CSV, index=False)
        print(f"Combined file also saved as {COMBINED_FILE_CSV}.")
    except Exception as e:
        print(f"Failed to save as CSV: {e}")
else:
    print("No data found to combine.") 