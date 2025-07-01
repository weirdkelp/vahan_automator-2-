import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import itertools
from collections import defaultdict
from datetime import datetime
import re
from calendar import month_abbr
from dynamic_dropdown_finder import (
    select_dropdown_dynamic, select_state_dynamic, select_month_dynamic,
    get_available_states_dynamic, get_available_months_dynamic,
    click_refresh_dynamic, click_download_dynamic, select_type_dynamic
)
from flask import Flask, render_template, request
import sys
import unicodedata

# --- Begin: Copied from main.py ---
PROMPT_KEY_MAP = {
    "y-axis": "yaxis",
    "x-axis": "xaxis",
    "type": "type",
    "state": "state",
    "rto": "rto",
    "year type": "year_type",
    "year": "year",
    "month": "month"
}
BASE_DIR = os.getcwd()
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")

MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN']
ALL_MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

# Define dropdown order here so it's available in the main function
DROPDOWN_ORDER = [
    ("yaxis", "yaxisVar_label", False),
    ("xaxis", "xaxisVar_label", False),
    ("year_type", "selectedYearType_label", False),
    ("year", "selectedYear_label", False),
    ("type", "Type", True),
    ("rto", "selectedRto_label", True)
]

def read_prompt():
    filters = {}
    if not os.path.exists(PROMPT_FILE):
        print("[WARN] prompt.txt not found.")
        return filters
    with open(PROMPT_FILE, "r") as f:
        for line in f:
            if ':' in line:
                key, val = line.strip().split(":", 1)
                key_clean = key.strip().lower()
                key_mapped = PROMPT_KEY_MAP.get(key_clean, key_clean)
                filters[key_mapped] = [v.strip() for v in val.split(",")]
    return filters

def select_dropdown(driver, label_id, item_text, is_select=False):
    try:
        if is_select:
            visible_label_id = label_id.replace("_input", "_label")
            label = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, visible_label_id))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", label)
            label.click()
            time.sleep(0.1)
            # Try both _items and _panel for the list ID
            list_id = visible_label_id.replace("_label", "_items")
            try:
                menu = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.ID, list_id))
                )
            except Exception:
                list_id = visible_label_id.replace("_label", "_panel")
                menu = WebDriverWait(driver, 3).until(
                    EC.visibility_of_element_located((By.ID, list_id))
                )
            items = menu.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
            target_text = item_text.strip().lower()
            for item in items:
                item_text_actual = item.text.strip().lower()
                if target_text in item_text_actual or item_text_actual in target_text:
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable(item))
                    item.click()
                    time.sleep(0.1)
                    return True
            return False
        else:
            # Robust PrimeFaces dropdown logic
            label = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, label_id))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", label)
            label.click()
            time.sleep(0.3)  # Wait for panel to open
            # Try to get the parent div's aria-owns for the items panel
            parent_div = label.find_element(By.XPATH, "ancestor::div[contains(@class, 'ui-selectonemenu')]")
            items_id = parent_div.get_attribute("aria-owns")
            if items_id:
                try:
                    menu = WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.ID, items_id))
                    )
                except Exception:
                    print(f"[WARN] Could not find items panel with id {items_id}")
                    return False
            else:
                # Fallback to _items or _panel
                items_id = label_id.replace("_label", "_items")
                try:
                    menu = WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.ID, items_id))
                    )
                except Exception:
                    items_id = label_id.replace("_label", "_panel")
                    menu = WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.ID, items_id))
                    )
            items = menu.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
            print(f"[DEBUG] Available options in {items_id}: {[item.text.strip() for item in items]}")
            target_text = item_text.strip().lower()
            for item in items:
                item_text_actual = item.text.strip().lower()
                if target_text in item_text_actual or item_text_actual in target_text:
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable(item))
                    item.click()
                    time.sleep(0.1)
                    return True
            print(f"[ERROR] No match found for '{item_text}' in {items_id}. Tried: {[item.text.strip() for item in items]}")
            return False
    except Exception as e:
        print(f"[CRITICAL] Dropdown selection failed for {label_id}: {str(e).split('Stacktrace:')[0]}")
        return False

def latest_file(folder):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".xlsx")]
    return max(files, key=os.path.getctime) if files else None

def get_month_folder(base_outputs_dir, state_name, year, month_name):
    state_dir = os.path.join(base_outputs_dir, state_name)
    year_dir = os.path.join(state_dir, str(year))
    month_dir = os.path.join(year_dir, month_name)
    os.makedirs(month_dir, exist_ok=True)
    return month_dir

def process_downloaded_file(file_path, base_outputs_dir, state_name, month_name, year):
    try:
        if not os.path.exists(file_path):
            print(f"[ERROR] File does not exist: {file_path}")
            return False
        # Ensure all folders exist before saving
        state_dir = os.path.join(base_outputs_dir, state_name)
        year_dir = os.path.join(state_dir, str(year))
        month_dir = os.path.join(year_dir, month_name)
        os.makedirs(month_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(month_dir, f"vahan_data_{timestamp}.xlsx")
        import shutil
        shutil.copy2(file_path, output_file)
        print(f"[INFO] Saved downloaded file to: {output_file}")
        os.remove(file_path)
        print(f"[INFO] Removed original downloaded file: {file_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to process Excel file: {e}")
        return False

def click_refresh_and_download(driver, xaxis_value=None, filters=None, month_name=None, state_name=None):
    if not month_name:
        print("[INFO] Clicking Refresh...")
        try:
            refresh_button = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "j_idt71"))
            )
            if refresh_button.is_displayed() and refresh_button.is_enabled():
                try:
                    refresh_button.click()
                    print("[INFO] Clicked Refresh button directly.")
                except:
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).move_to_element(refresh_button).pause(0.1).click().perform()
                    print("[INFO] Clicked Refresh button using ActionChains.")
                time.sleep(1)
            else:
                print("[ERROR] Refresh button is not interactable (not displayed or not enabled).")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to click refresh button: {e}")
            return False
        # Do not require month selection if just refreshing
        return True
    # Only require/select month if month_name is provided
    if xaxis_value and xaxis_value.lower() in ["vehicle category", "vehicle class", "norms", "fuel"]:
        if month_name:
            if not select_month(driver, month_name):
                return False
        else:
            print("[WARN] Month selection required but no month specified (download phase)")
            return False
    print("[INFO] Waiting for Excel download image/button...")
    for attempt in range(3):
        try:
            download_img = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "groupingTable:j_idt85"))
            )
            if download_img.is_displayed() and download_img.is_enabled():
                try:
                    download_img.click()
                    print(f"[INFO] Clicked Excel download image/button directly on attempt {attempt+1}.")
                    break
                except Exception as e:
                    print(f"[WARN] Direct click failed on attempt {attempt+1}: {e}")
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).move_to_element(download_img).pause(0.1).click().perform()
                    print(f"[INFO] Clicked Excel download image/button using ActionChains on attempt {attempt+1}.")
                    break
            else:
                print(f"[WARN] Download button not interactable on attempt {attempt+1}.")
        except Exception as e:
            print(f"[WARN] Could not find or click Excel download image/button on attempt {attempt+1}: {e}")
            time.sleep(0.5)
    else:
        print(f"[ERROR] Could not click Excel download image/button after 3 attempts.")
        return False
    time.sleep(0.5)
    return True

def select_month(driver, month_name):
    try:
        month_dropdown = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "groupingTable:selectMonth_label"))
        )
        month_dropdown.click()
        time.sleep(0.1)
        month_items = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.ID, "groupingTable:selectMonth_items"))
        )
        month_options = month_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        print("[DEBUG] Available months in dropdown:", [m.text.strip() for m in month_options])
        with open("month_debug.txt", "a", encoding="utf-8") as f:
            f.write("[DEBUG] Available months in dropdown: " + str([m.text.strip() for m in month_options]) + "\n")
        for month_opt in month_options:
            if month_opt.text.strip().lower().startswith(month_name.lower()):
                print(f"[INFO] Selecting month: {month_opt.text.strip()}")
                month_opt.click()
                time.sleep(0.1)
                return True
        print(f"[WARN] Month '{month_name}' not found in dropdown")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to select month {month_name}: {e}")
        return False
# --- End: Copied from main.py ---

def normalize_name(name):
    name = unicodedata.normalize('NFKC', name)
    name = re.sub(r'\s+', '', name)
    name = re.sub(r'[^\w\d]', '', name)
    return name.lower()

def get_all_states_from_vahan(driver):
    """Get list of all available states from the VAHAN dropdown using Selenium."""
    try:
        state_label = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "j_idt39_label"))
        )
        state_label.click()
        time.sleep(0.5)
        state_items = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "j_idt39_items"))
        )
        state_options = state_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        states = [opt.text.strip() for opt in state_options if opt.text.strip() and "All Vahan4 Running States" not in opt.text.strip()]
        state_label.click()
        time.sleep(0.2)
        return states
    except Exception as e:
        print(f"[ERROR] Failed to get available states from VAHAN: {e}")
        return []

def scan_existing_outputs(months):
    existing_by_folder = {}
    base_dir = os.getcwd()
    output_folders = [f for f in os.listdir(base_dir) if f.startswith('outputs') and os.path.isdir(os.path.join(base_dir, f))]
    print(f"\n[SCAN] Found output folders to scan: {output_folders}\n")
    for folder in output_folders:
        print(f"\n--- [SCAN] Now scanning folder: [{folder}] ---")
        existing_by_folder[folder] = set()
        outputs_dir = os.path.join(base_dir, folder)
        for state_dir in os.listdir(outputs_dir):
            state_path = os.path.join(outputs_dir, state_dir)
            if os.path.isdir(state_path):
                normalized_state = normalize_name(state_dir)
                for month in months:
                    month_path = os.path.join(state_path, month)
                    if os.path.isdir(month_path):
                        if any(fname.endswith('.xlsx') for fname in os.listdir(month_path)):
                            print(f"    [SCAN] FOUND: {folder}/{state_dir}/{month}")
                            existing_by_folder[folder].add((normalized_state, normalize_name(month)))
    return existing_by_folder

def generate_year_month_range(start_year, start_month, end_year, end_month):
    months = [m.upper() for m in month_abbr if m]
    month_to_num = {m: i+1 for i, m in enumerate(months)}
    num_to_month = {i+1: m for i, m in enumerate(months)}
    try:
        sy, sm = int(start_year), month_to_num[start_month.upper()]
        ey, em = int(end_year), month_to_num[end_month.upper()]
    except Exception as e:
        print(f"[ERROR] Invalid year/month in prompt.txt: {e}")
        return []
    result = []
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        result.append((y, num_to_month[m]))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return result

def get_available_months_for_year(driver):
    try:
        month_dropdown = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "groupingTable:selectMonth_label"))
        )
        month_dropdown.click()
        time.sleep(0.1)
        month_items = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.ID, "groupingTable:selectMonth_items"))
        )
        month_options = month_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        months = [m.text.strip().upper() for m in month_options if m.text.strip() and m.text.strip().upper() not in ("SELECT MONTH", "2025")]
        month_dropdown.click()
        time.sleep(0.1)
        print("[DEBUG] Available months for selected year:", months)
        with open("month_debug.txt", "a", encoding="utf-8") as f:
            f.write("[DEBUG] Available months for selected year: " + str(months) + "\n")
        return months
    except Exception as e:
        print(f"[ERROR] Failed to get available months for year: {e}")
        return []

def is_session_alive(driver):
    try:
        _ = driver.title
        return True
    except Exception as e:
        print(f"[ERROR] Selenium session lost: {e}")
        return False

def setup_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True
    })
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "yaxisVar_label"))
    )
    return driver

def wait_for_dropdown(driver, label_id, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.ID, label_id))
        )
    except Exception as e:
        print(f"[DEBUG] wait_for_dropdown: Could not find {label_id} within {timeout}s: {e}")

def main():
    # Setup Selenium first to get all possible states
    driver = setup_driver()
    filters = read_prompt()
    # --- Add initial dropdown selection as in main.py ---
    # Select all global filters (except state, year, month) ONCE
    for k, label, is_select in DROPDOWN_ORDER:
        if k in filters and k not in ("state", "year", "month"):
            v = filters[k][0]
            print(f"[INFO] (initial) Selecting {k}: {v}")
            if k == "type":
                select_type_dynamic(driver, v)
            else:
                select_dropdown(driver, label, v, is_select)
            time.sleep(0.5)
    type_value = filters.get('type', [None])[0]
    year_value = filters.get('year', [None])[0]
    # (year_value selection is handled per month below)
    try:
        all_states = get_available_states_dynamic(driver)
        if not all_states:
            print("[CRITICAL] Could not retrieve list of states from VAHAN. Aborting check.")
            return
        print(f"[INFO] All available states from VAHAN: {all_states}")
        
        start_year = filters.get('start_year', [None])[0]
        start_month = filters.get('start_month', [None])[0]
        end_year = filters.get('end_year', [None])[0]
        end_month = filters.get('end_month', [None])[0]
        if not all([start_year, start_month, end_year, end_month]):
            print("[ERROR] Start/end year/month not set in prompt.txt. Using default 12 months.")
            year_month_seq = [(datetime.now().year, m) for m in ALL_MONTHS]
        else:
            year_month_seq = generate_year_month_range(start_year, start_month, end_year, end_month)
        print(f"[INFO] Year/month sequence to process: {year_month_seq}")
        
        # Now scan outputs/ for existing data
        months_in_range = list({m for y, m in year_month_seq})
        existing_by_folder = scan_existing_outputs(months_in_range)
        all_missing_by_folder = {}
        for folder, existing in existing_by_folder.items():
            print(f"\n=== Checking missing files in {folder} ===")
            print(f"[INFO] Found {len(existing)} existing (state, month) pairs in {folder}")
            missing = []
            for state in all_states:
                for y, month in year_month_seq:
                    key = (normalize_name(state), normalize_name(month))
                    if key not in existing:
                        missing.append((state, f"{month} {y}"))
            if missing:
                print(f"[INFO] Missing {len(missing)} (state, month) pairs in {folder}:")
                for state, month in missing:
                    print(f"  - {state} / {month}")
                all_missing_by_folder[folder] = missing
            else:
                print(f"[INFO] No missing data in {folder}. All (state, month) pairs have at least one .xlsx file.")
        if not all_missing_by_folder:
            print("\n[INFO] All folders are complete. No missing data anywhere.")
            return
        for folder, missing in all_missing_by_folder.items():
            print(f"\n=== Processing missing data for {folder} ===")
        missing_by_state = defaultdict(list)
        for state, month in missing:
            missing_by_state[state].append(month)
        for state, months in missing_by_state.items():
            print(f"[INFO] Downloading missing data for {state} (months: {months})")
            failed_dropdowns = []
            # Session health check and browser restart logic
            if not is_session_alive(driver):
                print("[INFO] Restarting browser session...")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = setup_driver()
                # Re-select all global filters (except state, year, month)
                for k, label, is_select in DROPDOWN_ORDER:
                    if k in filters and k not in ("state", "year", "month"):
                        v = filters[k][0]
                        print(f"[INFO] (re)Selecting {k}: {v}")
                        if k == "type":
                            select_type_dynamic(driver, v)
                        else:
                            select_dropdown(driver, label, v, is_select)
                        time.sleep(0.5)
            # Print all element IDs on the page for debugging
            ids = [e.get_attribute('id') for e in driver.find_elements(By.XPATH, '//*[@id]')]
            print("[DEBUG] All element IDs on page:", ids)
            # Only select state here
            if not select_state_dynamic(driver, state):
                print(f"[WARN] Could not select state {state}")
                continue
            xaxis_value = filters.get("xaxis", [None])[0]
            time.sleep(1)
            for m in months:
                if not is_session_alive(driver):
                    print("[INFO] Restarting browser session (inside month loop)...")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = setup_driver()
                    # Re-select all global filters (except state, year, month)
                    for k, label, is_select in DROPDOWN_ORDER:
                        if k in filters and k not in ("state", "year", "month"):
                            v = filters[k][0]
                            print(f"[INFO] (re)Selecting {k}: {v}")
                            if k == "type":
                                select_type_dynamic(driver, v)
                            else:
                                select_dropdown(driver, label, v, is_select)
                            time.sleep(0.5)
                    if not select_state_dynamic(driver, state):
                        print(f"[WARN] Could not select state {state} after browser restart")
                        continue
                if ' ' in m:
                    month, year = m.split()
                else:
                    month, year = m, str(datetime.now().year)
                print(f"[INFO] Processing year: {year}, month: {month} for state: {state}")
                # Select year using main.py approach
                if not select_dropdown(driver, "selectedYear_label", str(year)):
                    print(f"[ERROR] Failed to select year: {year}")
                    continue
                if not click_refresh_dynamic(driver):
                    print(f"[ERROR] Failed to click refresh after selecting year {year}")
                    continue
                available_months = get_available_months_for_year(driver)
                print(f"[DEBUG] Available months for selected year: {available_months}")
                if month.upper() not in available_months:
                    print(f"[WARN] Month '{month}' not available for year {year}, skipping.")
                    continue
                if not select_month(driver, month):
                    print(f"[ERROR] Failed to select month: {month}")
                    continue
                time.sleep(2)
                if click_download_dynamic(driver):
                    print("[INFO] Waiting for file download to complete...")
                    if wait_for_download(DOWNLOAD_DIR, timeout=15):
                        file_path = latest_file(DOWNLOAD_DIR)
                        if file_path:
                            if process_downloaded_file(file_path, folder, state, month, year):
                                print(f"[INFO] Successfully processed data for {state} - {month} {year}")
                            else:
                                print(f"[ERROR] Failed to process data for {state} - {month} {year}")
                        else:
                            print(f"[ERROR] No Excel file found for {state} - {month} {year}")
                    else:
                        print(f"[ERROR] Download did not complete in time for {state} - {month} {year}")
                else:
                    print(f"[ERROR] Failed to download data for {state} - {month} {year}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

def parse_folder_range(folder_name):
    import re
    m = re.search(r'_(\d{4})([A-Z]{3})_to_(\d{4})([A-Z]{3})', folder_name)
    if m:
        start_year, start_month, end_year, end_month = m.groups()
        return start_year, start_month, end_year, end_month
    return None, None, None, None

def get_all_outputs_folders():
    base_dir = os.getcwd()
    return [f for f in os.listdir(base_dir) if f.startswith('outputs') and os.path.isdir(os.path.join(base_dir, f))]

def scan_existing_outputs_for_folder(folder, months):
    existing = set()
    outputs_dir = os.path.join(os.getcwd(), folder)
    for state_dir in os.listdir(outputs_dir):
        state_path = os.path.join(outputs_dir, state_dir)
        if os.path.isdir(state_path):
            normalized_state = normalize_name(state_dir)
            for year_dir in os.listdir(state_path):
                year_path = os.path.join(state_path, year_dir)
                if os.path.isdir(year_path):
                    for month in months:
                        month_path = os.path.join(year_path, month)
                        if os.path.isdir(month_path):
                            if any(fname.endswith('.xlsx') for fname in os.listdir(month_path)):
                                existing.add((normalized_state, year_dir, normalize_name(month)))
    return existing

def download_missing_for_folder(folder):
    # Parse range from folder name
    start_year, start_month, end_year, end_month = parse_folder_range(folder)
    if not all([start_year, start_month, end_year, end_month]):
        print(f"[ERROR] Could not parse date range from folder: {folder}")
        return
    # Build year/month sequence
    months = [m.upper() for m in month_abbr if m]
    month_to_num = {m: i+1 for i, m in enumerate(months)}
    num_to_month = {i+1: m for i, m in enumerate(months)}
    try:
        sy, sm = int(start_year), month_to_num[start_month.upper()]
        ey, em = int(end_year), month_to_num[end_month.upper()]
    except Exception as e:
        print(f"[ERROR] Invalid year/month in folder name: {e}")
        return
    year_month_seq = []
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        year_month_seq.append((y, num_to_month[m]))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    months_in_range = list({m for y, m in year_month_seq})
    outputs_dir = os.path.join(os.getcwd(), folder)
    # Always use master state list
    raw_state_folders = [d for d in os.listdir(outputs_dir) if os.path.isdir(os.path.join(outputs_dir, d))]
    normalized_folder_states = [normalize_name(d) for d in raw_state_folders]
    normalized_master_states = [normalize_name(s) for s in MASTER_STATES]
    missing_pairs = []
    for state, norm_state in zip(MASTER_STATES, normalized_master_states):
        if norm_state not in normalized_folder_states:
            for y, month in year_month_seq:
                missing_pairs.append((state, y, month))
        else:
            state_path = os.path.join(outputs_dir, state)
            for y, month in year_month_seq:
                month_path = os.path.join(state_path, str(y), month)
                if not os.path.isdir(month_path) or not any(fname.endswith('.xlsx') for fname in os.listdir(month_path)):
                    missing_pairs.append((state, y, month))
    if not missing_pairs:
        print(f"[INFO] No missing data for {folder}")
        return
    print(f"[INFO] Downloading missing data for {folder}: {len(missing_pairs)} items")
    driver = setup_driver()
    try:
        filters = read_prompt()
        # Select all global filters (except state, year, month) ONCE
        for k, label, is_select in DROPDOWN_ORDER:
            if k in filters and k not in ("state", "year", "month"):
                v = filters[k][0]
                print(f"[INFO] (initial) Selecting {k}: {v}")
                if k == "type":
                    select_type_dynamic(driver, v)
                else:
                    select_dropdown(driver, label, v, is_select)
                time.sleep(0.5)
        for state, y, month in missing_pairs:
            print(f"[DEBUG] Attempting to download for state: {state}, year: {y}, month: {month}")
            # Session health check and browser restart logic
            if not is_session_alive(driver):
                print("[INFO] Restarting browser session...")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = setup_driver()
                # Re-select all global filters (except state, year, month)
                for k, label, is_select in DROPDOWN_ORDER:
                    if k in filters and k not in ("state", "year", "month"):
                        v = filters[k][0]
                        print(f"[INFO] (re)Selecting {k}: {v}")
                        if k == "type":
                            select_type_dynamic(driver, v)
                        else:
                            select_dropdown(driver, label, v, is_select)
                        time.sleep(0.5)
            if not select_state_dynamic(driver, state):
                print(f"[WARN] Could not select state {state}")
                continue
            if not select_dropdown(driver, "selectedYear_label", str(y)):
                print(f"[ERROR] Failed to select year: {y}")
                continue
            if not click_refresh_dynamic(driver):
                print(f"[ERROR] Failed to click refresh after selecting year {y}")
                continue
            available_months = get_available_months_for_year(driver)
            if month.upper() not in available_months:
                print(f"[WARN] Month '{month}' not available for year {y}, skipping.")
                continue
            if not select_month(driver, month):
                print(f"[ERROR] Failed to select month: {month}")
                continue
            time.sleep(2)
            if click_download_dynamic(driver):
                print("[INFO] Waiting for file download to complete...")
                if wait_for_download(DOWNLOAD_DIR, timeout=15):
                    file_path = latest_file(DOWNLOAD_DIR)
                    if file_path:
                        if process_downloaded_file(file_path, folder, state, month, y):
                            print(f"[INFO] Successfully processed data for {state} - {month} {y}")
                        else:
                            print(f"[ERROR] Failed to process data for {state} - {month} {y}")
                    else:
                        print(f"[ERROR] No Excel file found for {state} - {month} {y}")
                else:
                    print(f"[ERROR] Download did not complete in time for {state} - {month} {y}")
            else:
                print(f"[ERROR] Failed to download data for {state} - {month} {y}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

app = Flask(__name__)

# Add master state list at the top (if not already present)
MASTER_STATES = [
    "Andaman & Nicobar Island(3)",
    "Andhra Pradesh(83)",
    "Arunachal Pradesh(29)",
    "Assam(33)",
    "Bihar(48)",
    "Chhattisgarh(31)",
    "Chandigarh(1)",
    "UT of DNH and DD(3)",
    "Delhi(16)",
    "Goa(13)",
    "Gujarat(37)",
    "Himachal Pradesh(96)",
    "Haryana(98)",
    "Jharkhand(25)",
    "Jammu and Kashmir(21)",
    "Karnataka(68)",
    "Kerala(87)",
    "Ladakh(3)",
    "Lakshadweep(6)",
    "Maharashtra(59)",
    "Meghalaya(15)",
    "Manipur(13)",
    "Madhya Pradesh(53)",
    "Mizoram(10)",
    "Nagaland(9)",
    "Odisha(39)",
    "Punjab(96)",
    "Puducherry(8)",
    "Rajasthan(59)",
    "Sikkim(9)",
    "Tamil Nadu(148)",
    "Tripura(9)",
    "Uttarakhand(21)",
    "Uttar Pradesh(77)",
    "West Bengal(59)"
]

@app.route('/', methods=['GET', 'POST'])
def missing_check_dashboard():
    import sys
    import os
    print("[DEBUG] CWD:", os.getcwd())
    debug_lines = []
    debug_lines.append("[DEBUG] Flask route called (top of function)\n")
    selected_folder = request.form.get('folder') if request.method == 'POST' else None
    debug_lines.append(f"[DEBUG] selected_folder: {selected_folder}\n")
    try:
        with open("flask_debug.log", "a", encoding="utf-8") as f:
            f.writelines(debug_lines)
    except Exception as e:
        print("[DEBUG] Exception writing flask_debug.log:", e)
    output_folders = get_all_outputs_folders()
    selected_folder = request.form.get('folder') if request.method == 'POST' else None
    missing = []
    folder_range = None
    all_states = []
    months_in_range = []
    year_month_seq = []
    download_log = ""
    if selected_folder:
        start_year, start_month, end_year, end_month = parse_folder_range(selected_folder)
        folder_range = (start_year, start_month, end_year, end_month)
        if all(folder_range):
            months = [m.upper() for m in month_abbr if m]
            month_to_num = {m: i+1 for i, m in enumerate(months)}
            num_to_month = {i+1: m for i, m in enumerate(months)}
            try:
                sy, sm = int(start_year), month_to_num[start_month.upper()]
                ey, em = int(end_year), month_to_num[end_month.upper()]
            except Exception as e:
                sy, sm, ey, em = None, None, None, None
            y, m = sy, sm
            while (y < ey) or (y == ey and m <= em):
                year_month_seq.append((y, num_to_month[m]))
                if m == 12:
                    y += 1
                    m = 1
                else:
                    m += 1
            months_in_range = list({m for y, m in year_month_seq})
            outputs_dir = os.path.join(os.getcwd(), selected_folder)
            raw_state_folders = [d for d in os.listdir(outputs_dir) if os.path.isdir(os.path.join(outputs_dir, d))]
            normalized_folder_states = [normalize_name(d) for d in raw_state_folders]
            normalized_master_states = [normalize_name(s) for s in MASTER_STATES]
            debug_lines.append(f"[DEBUG] Normalized folder states: {normalized_folder_states}\n")
            debug_lines.append(f"[DEBUG] Normalized master states: {normalized_master_states}\n")
            for state, norm_state in zip(MASTER_STATES, normalized_master_states):
                if norm_state not in normalized_folder_states:
                    for y, month in year_month_seq:
                        missing.append(f"{state} / {y} / {month}")
                else:
                    state_path = os.path.join(outputs_dir, state)
                    for y, month in year_month_seq:
                        month_path = os.path.join(state_path, str(y), month)
                        if not os.path.isdir(month_path) or not any(fname.endswith('.xlsx') for fname in os.listdir(month_path)):
                            missing.append(f"{state} / {y} / {month}")
            debug_lines.append(f"[DEBUG] Missing states: {[s for s, norm_s in zip(MASTER_STATES, normalized_master_states) if norm_s not in normalized_folder_states]}\n")
            with open("flask_debug.log", "a", encoding="utf-8") as f:
                f.writelines(debug_lines)
        # Immediately start download for selected folder and capture log
        import io
        import sys
        log_stream = io.StringIO()
        sys_stdout = sys.stdout
        sys.stdout = log_stream
        try:
            download_missing_for_folder(selected_folder)
        finally:
            sys.stdout = sys_stdout
        download_log = log_stream.getvalue()
    return render_template('missing_check_dashboard.html', folders=output_folders, selected=selected_folder, missing=missing, folder_range=folder_range, download_log=download_log)

def wait_for_download(download_dir, timeout=15):
    import time, os
    start = time.time()
    while time.time() - start < timeout:
        files = [f for f in os.listdir(download_dir) if f.endswith('.xlsx')]
        if files:
            return True
        time.sleep(0.5)
    return False

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == "--download-missing" and sys.argv[2] == "--folder":
        folder = sys.argv[3]
        download_missing_for_folder(folder)
    else:
        main() 