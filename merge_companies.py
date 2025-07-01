import pandas as pd
import sys
import os
from typing import Dict, List

def merge_companies(input_file: str, merge_map: Dict[str, List[str]], output_file: str = None):
    """
    For each group, for each unique (State, Month), sum the numeric values for all companies in the merge list (including the main company),
    and keep a single row for the main company for each (State, Month). Remove all other companies in the merge list from the file.
    """
    # Read with header=2 so row 3 is used as header (0-based index)
    df = pd.read_excel(input_file, header=2)
    # Rename columns: second column to 'Month', third to 'Maker'
    cols = list(df.columns)
    if len(cols) >= 3:
        cols[1] = 'Month'
        cols[2] = 'Maker'
        df.columns = cols
    state_col = df.columns[0]
    month_col = df.columns[1]
    maker_col = df.columns[2]
    class_cols = list(df.columns[3:])
    # Clean numeric columns
    for col in class_cols:
        df[col] = df[col].astype(str).str.replace(',', '').str.replace(' ', '').str.replace('\u00A0', '')
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    # For each group
    for main_company, merge_list in merge_map.items():
        companies_to_merge = set(merge_list + [main_company])
        # Find all (State, Month) pairs present for these companies
        pairs = df[df[maker_col].isin(companies_to_merge)][[state_col, month_col]].drop_duplicates().values.tolist()
        new_rows = []
        for state, month in pairs:
            mask = (df[state_col] == state) & (df[month_col] == month) & (df[maker_col].isin(companies_to_merge))
            sub = df.loc[mask]
            if not sub.empty:
                summed = sub[class_cols].sum(numeric_only=True)
                # Take the first row as a template
                row = sub.iloc[0].copy()
                row[maker_col] = main_company
                for col in class_cols:
                    row[col] = summed[col]
                new_rows.append(row)
        # Remove all rows for these companies
        df = df[~df[maker_col].isin(companies_to_merge)]
        # Add the new combined rows
        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    # Sort for neatness
    df = df.sort_values([state_col, month_col, maker_col]).reset_index(drop=True)
    # Ensure all original columns are present in the output (including class columns)
    df = df[[state_col, month_col, maker_col] + class_cols]
    if not output_file:
        input_base = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"merged_{input_base}.xlsx"
    df.to_excel(output_file, index=False)
    # Set all column widths to 30 for better visibility
    try:
        from openpyxl import load_workbook
        wb = load_workbook(output_file)
        ws = wb.active
        for col in ws.columns:
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = 30
        wb.save(output_file)
    except Exception as e:
        print(f"[WARN] Could not set column widths: {e}")
    print(f"[OK] Merged file saved as {output_file}")

if __name__ == "__main__":
    import json
    if len(sys.argv) < 3:
        print("Usage: python merge_companies.py <input_file> <merge_map_json> [output_file]")
        print("Example merge_map_json: '{\"Tata Motors Ltd\": [\"TATA HITACHI CONSTRUCTION MACHINERY COMP PVT LTD\", \"TATA MOTORS PASSENGER VEHICLES LTD\"]}'")
        sys.exit(1)
    input_file = sys.argv[1]
    merge_map = json.loads(sys.argv[2])
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    merge_companies(input_file, merge_map, output_file) 