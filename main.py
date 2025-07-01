import os
import time
import sys
import pandas as pd
import schedule
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import itertools
from selenium.webdriver.common.action_chains import ActionChains
from calendar import month_abbr
from dynamic_dropdown_finder import (
    select_dropdown_dynamic, select_state_dynamic, select_month_dynamic,
    get_available_states_dynamic, get_available_months_dynamic,
    click_refresh_dynamic, click_download_dynamic, select_type_dynamic
)

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
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt.txt")

# Create base directories
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

ALL_MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

# Define dropdown order here so it's available throughout the script
DROPDOWN_ORDER = [
    ("yaxis", "yaxisVar_label", False),
    ("xaxis", "xaxisVar_label", False),
    ("year_type", "selectedYearType_label", False),
    ("year", "selectedYear_label", False),
    ("type", "Type", True),
    ("rto", "selectedRto_label", True)
]

def get_state_folder(state_name):
    """Create and return path to state-specific folder"""
    state_dir = os.path.join(OUTPUT_DIR, state_name)
    os.makedirs(state_dir, exist_ok=True)
    return state_dir

def get_month_folder(state_name, month_name):
    """Create and return path to month-specific folder within state folder"""
    state_dir = get_state_folder(state_name)
    month_dir = os.path.join(state_dir, month_name)
    os.makedirs(month_dir, exist_ok=True)
    return month_dir

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

def latest_file(folder):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".xlsx")]
    return max(files, key=os.path.getctime) if files else None

def get_available_states(driver):
    """Get list of available states from the dropdown"""
    try:
        print("[DEBUG] Attempting to find state dropdown...")
        # Click on the state dropdown label to open it
        state_label = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "j_idt39_label"))
        )
        state_label.click()
        time.sleep(0.5)

        # Find the dropdown items container
        state_items = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "j_idt39_items"))
        )
        
        # Get all visible li elements
        state_options = state_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        print(f"[DEBUG] Found {len(state_options)} state options")
        
        # Show all options for debugging
        all_options = [opt.text.strip() for opt in state_options]
        print(f"[DEBUG] All state options: {all_options}")
        
        # Filter out empty options and the "All" option, but keep individual states
        states = [opt.text.strip() for opt in state_options if opt.text.strip() and "All Vahan4 Running States" not in opt.text.strip()]
        print(f"[DEBUG] Filtered states: {states}")
        
        # Close the dropdown
        state_label.click()
        time.sleep(0.2)
        
        return states
    except Exception as e:
        print(f"[ERROR] Failed to get available states: {e}")
        return []

def wait_for_ui_blocker(driver, timeout=5):
    """Wait for UI blocker overlay to disappear - only if one is detected"""
    try:
        # Check if there's a blocker present first
        blockers = driver.find_elements(By.CSS_SELECTOR, "div.ui-blockui.ui-widget-overlay")
        if not blockers:
            return True  # No blocker found, continue immediately
        
        # Only wait if a blocker is actually present
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ui-blockui.ui-widget-overlay"))
        )
        time.sleep(0.2)  # Small delay after blocker disappears
        return True
    except:
        # If timeout or error, continue anyway
        return True

def get_available_months(driver):
    """Get list of available months from the dropdown"""
    try:
        month_dropdown = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "groupingTable:selectMonth_label"))
        )
        month_dropdown.click()
        time.sleep(0.1)  # Reduced wait time

        month_items = WebDriverWait(driver, 3).until(
            EC.visibility_of_element_located((By.ID, "groupingTable:selectMonth_items"))
        )
        
        month_options = month_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        months = [opt.text.strip() for opt in month_options if opt.text.strip() != "2025"]
        
        # Close the dropdown
        month_dropdown.click()
        time.sleep(0.1)  # Reduced wait time
        
        return months
    except Exception as e:
        # If there's a click interception error, wait for UI blocker and retry once
        if "element click intercepted" in str(e).lower():
            print("[INFO] UI blocker detected, waiting for it to disappear...")
            wait_for_ui_blocker(driver)
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
                months = [opt.text.strip() for opt in month_options if opt.text.strip() != "2025"]
                
                month_dropdown.click()
                time.sleep(0.1)
                
                return months
            except Exception as e2:
                print(f"[ERROR] Failed to get available months after retry: {e2}")
                return []
        else:
            print(f"[ERROR] Failed to get available months: {e}")
            return []

def select_state(driver, state_name):
    """Select a specific state from the dropdown"""
    try:
        # Click on the state dropdown label to open it
        state_label = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "j_idt39_label"))
        )
        state_label.click()
        time.sleep(0.2)

        # Find the dropdown items container
        state_items = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "j_idt39_items"))
        )
        
        # Get all visible li elements
        state_options = state_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        
        for state_opt in state_options:
            if state_opt.text.strip() == state_name:
                print(f"[INFO] Selecting state: {state_name}")
                state_opt.click()
                time.sleep(0.2)
                return True
                
        print(f"[WARN] State '{state_name}' not found in dropdown")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to select state {state_name}: {e}")
        return False

def select_month(driver, month_name):
    """Select a specific month from the dropdown"""
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
        for month_opt in month_options:
            if month_opt.text.strip().lower().startswith(month_name.lower()):
                print(f"[INFO] Selecting month: {month_opt.text.strip()}")
                month_opt.click()
                time.sleep(0.1)
                return True
        print(f"[WARN] Month '{month_name}' not found in dropdown")
        return False
    except Exception as e:
        # If there's a click interception error, wait for UI blocker and retry once
        if "element click intercepted" in str(e).lower():
            print(f"[INFO] UI blocker detected while selecting month {month_name}, waiting for it to disappear...")
            wait_for_ui_blocker(driver)
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
                
                for month_opt in month_options:
                    if month_opt.text.strip() == month_name:
                        print(f"[INFO] Selecting month: {month_name}")
                        month_opt.click()
                        time.sleep(0.1)
                        return True
                        
                print(f"[WARN] Month '{month_name}' not found in dropdown after retry")
                return False
            except Exception as e2:
                print(f"[ERROR] Failed to select month {month_name} after retry: {e2}")
                return False
        else:
            print(f"[ERROR] Failed to select month {month_name}: {e}")
            return False

def select_dropdown(driver, label_id, item_text, is_select=False):
    try:
        # For PrimeFaces/JSF dropdowns, always use the visible label and <li> menu
        if is_select:
            visible_label_id = label_id.replace("_input", "_label")
            label = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, visible_label_id))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", label)
            label.click()
            time.sleep(0.1)  # Reduced wait time

            list_id = visible_label_id.replace("_label", "_items")
            menu = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.ID, list_id))
            )
            items = menu.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
            print(f"[DEBUG] Visible options ({len(items)}) in {list_id}: {[item.text.strip() for item in items]}")

            target_text = item_text.strip().lower()
            
            # Special handling for RTO selection
            if "rto" in label_id.lower():
                # For RTO, we'll select the first option that contains "All Vahan4 Running Office"
                for item in items:
                    if "all vahan4 running office" in item.text.strip().lower():
                        print(f"[INFO] Matched RTO option: {item.text.strip()}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", item)
                        WebDriverWait(driver, 2).until(EC.element_to_be_clickable(item))
                        item.click()
                        print(f"[INFO] Selected RTO option: {item.text.strip()}")
                        time.sleep(0.1)  # Reduced wait time
                        return True
            else:
                # Normal selection for other dropdowns
                for item in items:
                    item_text_actual = item.text.strip().lower()
                    if target_text in item_text_actual or item_text_actual in target_text:
                        print(f"[INFO] Matched '{item.text.strip()}' for target '{item_text}'")
                        driver.execute_script("arguments[0].scrollIntoView(true);", item)
                        WebDriverWait(driver, 2).until(EC.element_to_be_clickable(item))
                        item.click()
                        print(f"[INFO] Selected '{item.text.strip()}' in {visible_label_id} via UI click")
                        time.sleep(0.1)  # Reduced wait time
                        return True
            
            print(f"[ERROR] '{item_text}' not found in {list_id}. Options: {[item.text.strip() for item in items]}")
            return False
        else:
            print(f"\n[DEBUG] Attempting to select '{item_text}' in dropdown {label_id}")
            dropdown = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, label_id))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
            dropdown.click()
            time.sleep(0.1)  # Reduced wait time
            list_id = label_id.replace("_label", "_items")
            menu = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.ID, list_id))
            )
            items = menu.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
            print(f"[DEBUG] Available options ({len(items)}) in {label_id}: {[item.text.strip() for item in items]}")
            target_text = item_text.strip().lower()
            for item in items:
                item_text_actual = item.text.strip().lower()
                if target_text in item_text_actual or item_text_actual in target_text:
                    print(f"[INFO] Matched '{item.text.strip()}' for target '{item_text}'")
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable(item))
                    item.click()
                    print(f"[INFO] Selected '{item.text.strip()}' in {label_id} via UI click")
                    time.sleep(0.1)  # Reduced wait time
                    return True
            print(f"[ERROR] No match found for '{item_text}' in {label_id}. Tried: {[item.text.strip() for item in items]}")
            return False

    except Exception as e:
        print(f"[CRITICAL] Dropdown selection failed for {label_id}: {str(e).split('Stacktrace:')[0]}")
        return False

def click_refresh_and_download(driver, xaxis_value=None, filters=None, month_name=None, state_name=None):
    # Only click Refresh if no month is specified (month selection happens after refresh)
    if not month_name:
        print("[INFO] Clicking Refresh...")
        try:
            refresh_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "j_idt71"))
            )
            driver.execute_script("arguments[0].click();", refresh_button)
            print("[INFO] Clicked Refresh button.")
            time.sleep(1.5)
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

def get_new_output_dir(filters):
    def get_val(key):
        v = filters.get(key, [None])[0]
        return v.replace(' ', '_') if v else 'unknown'
    year_start = get_val('start_year')
    month_start = get_val('start_month')
    year_end = get_val('end_year')
    month_end = get_val('end_month')
    yaxis = get_val('yaxis')
    xaxis = get_val('xaxis')
    run_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    folder_name = f"outputs_{yaxis}_{xaxis}_{year_start}{month_start}_to_{year_end}{month_end}_{run_time}"
    return os.path.join(BASE_DIR, folder_name)

def process_downloaded_file(file_path, state_name, month_name, year):
    """Process the downloaded Excel file and save to the correct outputs folder, creating a new outputs folder if needed"""
    try:
        if not os.path.exists(file_path):
            print(f"[ERROR] File does not exist: {file_path}")
            return False
        global OUTPUT_DIR
        # New structure: OUTPUT_DIR/state/year/month/file.xlsx
        year_str = str(year)
        state_dir = os.path.join(OUTPUT_DIR, state_name)
        year_dir = os.path.join(state_dir, year_str)
        os.makedirs(year_dir, exist_ok=True)
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
        "download.default_directory": DOWNLOAD_DIR,
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
    time.sleep(4)
    return driver

def run_vahan_automation():
    print(f"\n[INFO] Starting VAHAN automation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    filters = read_prompt()
    global OUTPUT_DIR
    OUTPUT_DIR = get_new_output_dir(filters)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"[INFO] Output directory for this run: {OUTPUT_DIR}")

    driver = setup_driver()

    try:
        # Select 'Type' and 'Year' first to populate the state dropdown
        type_value = filters.get('type', [None])[0]
        year_value = filters.get('year', [None])[0]
        if type_value:
            select_type_dynamic(driver, type_value)
            time.sleep(1)
        if year_value:
            select_dropdown(driver, "selectedYear_label", year_value)
            time.sleep(1)

        # Now get all available states using dynamic approach
        available_states = get_available_states_dynamic(driver)
        print(f"[INFO] Found {len(available_states)} states: {available_states}")
        if not available_states and 'state' in filters:
            available_states = filters['state']
            print(f"[INFO] Using state from prompt.txt: {available_states}")

        filter_keys = [k for k, _, _ in DROPDOWN_ORDER if k in filters]
        filter_values = [filters[k] for k in filter_keys]
        if not filter_keys:
            filter_combinations = [()]
        else:
            filter_combinations = list(itertools.product(*filter_values))

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

        for combo in filter_combinations:
            print(f"\n[INFO] Processing filter combination: {dict(zip(filter_keys, combo))}")
            xaxis_value = None

            # Session health check and browser restart logic for each filter combo
            if not is_session_alive(driver):
                print("[INFO] Restarting browser session...")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = setup_driver()
                # Re-select all dropdowns up to this point
                for (k, label_id, is_select), v in zip(DROPDOWN_ORDER, combo):
                    if k in filters and k != "state":
                        print(f"[INFO] (re)Selecting {k}: {v}")
                        if k == "type":
                            select_type_dynamic(driver, v)
                        else:
                            select_dropdown(driver, label_id, v, is_select)
                        time.sleep(0.5)

            for (k, label_id, is_select), v in zip(DROPDOWN_ORDER, combo):
                if k in filters:
                    print(f"[INFO] Selecting {k}: {v}")
                    if k == "type":
                        success = select_type_dynamic(driver, v)
                    elif k == "state":
                        success = select_state_dynamic(driver, v)
                    else:
                        success = select_dropdown(driver, label_id, v, is_select)
                    if k == "xaxis":
                        xaxis_value = v
                    if not success:
                        print(f"[WARN] Skipping combination due to selection failure: {dict(zip(filter_keys, combo))}")
                        break
                    time.sleep(0.5)
            else:
                for state_name in available_states:
                    print(f"\n[INFO] Processing state: {state_name}")
                    # Always select the state before downloading for it
                    if not select_state_dynamic(driver, state_name):
                        print(f"[ERROR] Failed to select state: {state_name}. Skipping to next state.")
                        continue
                    print(f"[INFO] Now downloading for state: {state_name}")
                    # Session health check and browser restart logic for each state
                    if not is_session_alive(driver):
                        print("[INFO] Restarting browser session (inside state loop)...")
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = setup_driver()
                        # Re-select all dropdowns up to this point
                        for (k, label_id, is_select), v in zip(DROPDOWN_ORDER, combo):
                            if k in filters and k != "state":
                                print(f"[INFO] (re)Selecting {k}: {v}")
                                if k == "type":
                                    select_type_dynamic(driver, v)
                                else:
                                    select_dropdown(driver, label_id, v, is_select)
                                time.sleep(0.5)
                        # Always select the state after browser restart
                        if not select_state_dynamic(driver, state_name):
                            print(f"[WARN] Could not select state {state_name} after browser restart")
                            continue
                    # Click refresh after state selection using dynamic finder
                    print("[INFO] Clicking refresh after state selection...")
                    if not click_refresh_dynamic(driver):
                        print(f"[ERROR] Failed to click refresh after state selection")
                        continue
                    time.sleep(2)
                    for y, month in year_month_seq:
                        # Session health check and browser restart logic for each year/month
                        if not is_session_alive(driver):
                            print("[INFO] Restarting browser session (inside month loop)...")
                            try:
                                driver.quit()
                            except Exception:
                                pass
                            driver = setup_driver()
                            # Re-select all dropdowns up to this point
                            for (k, label_id, is_select), v in zip(DROPDOWN_ORDER, combo):
                                if k in filters and k != "state":
                                    print(f"[INFO] (re)Selecting {k}: {v}")
                                    if k == "type":
                                        select_type_dynamic(driver, v)
                                    else:
                                        select_dropdown(driver, label_id, v, is_select)
                                    time.sleep(0.5)
                            if not select_state_dynamic(driver, state_name):
                                print(f"[WARN] Could not select state {state_name} after browser restart (month loop)")
                                continue
                        print(f"\n[INFO] Processing year: {y}, month: {month} for state: {state_name}")
                        if not select_dropdown(driver, "selectedYear_label", str(y)):
                            print(f"[ERROR] Failed to select year: {y}")
                            continue
                        if not click_refresh_dynamic(driver):
                            print(f"[ERROR] Failed to click refresh after selecting year {y}")
                            continue
                        available_months = get_available_months_for_year(driver)
                        print(f"[DEBUG] Available months for selected year: {available_months}")
                        if month.upper() not in available_months:
                            print(f"[WARN] Month '{month}' not available for year {y}, skipping.")
                            continue
                        if not select_month(driver, month):
                            print(f"[ERROR] Failed to select month: {month}")
                            continue
                        time.sleep(2)
                        if click_download_dynamic(driver):
                            print("[INFO] Waiting for file download to complete...")
                            time.sleep(3)
                            file_path = latest_file(DOWNLOAD_DIR)
                            if file_path:
                                if process_downloaded_file(file_path, state_name, month, y):
                                    print(f"[INFO] Successfully processed data for {state_name} - {month} {y}")
                                else:
                                    print(f"[ERROR] Failed to process data for {state_name} - {month} {y}")
                            else:
                                print(f"[ERROR] No Excel file found for {state_name} - {month} {y}")
                        else:
                            print(f"[ERROR] Failed to download data for {state_name} - {month} {y}")

    except Exception as e:
        print(f"[ERROR] Automation failed: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run-now":
        run_vahan_automation()
    else:
        print("[INFO] Scheduler started. Will run every hour.")
        schedule.every().hour.do(run_vahan_automation)
        while True:
            schedule.run_pending()
            time.sleep(1)
