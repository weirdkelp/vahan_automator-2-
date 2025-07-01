import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import unicodedata
import re
from dynamic_dropdown_finder import select_type_dynamic, select_dropdown, select_state_dynamic, get_available_months

BASE_DIR = os.getcwd()
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

# MASTER LIST OF STATES (as per user request)
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

# Helper functions from main.py (copy as needed)
def get_available_states(driver):
    state_label = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "j_idt41_label"))
    )
    state_label.click()
    time.sleep(0.5)
    state_items = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.ID, "j_idt41_items"))
    )
    state_options = state_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
    states = [opt.text.strip() for opt in state_options if opt.text.strip() and "All Vahan4 Running States" not in opt.text.strip()]
    state_label.click()
    time.sleep(0.2)
    return states

def normalize_name(name):
    # Normalize unicode, remove all whitespace and punctuation, and lowercase
    name = unicodedata.normalize('NFKC', name)
    name = re.sub(r'\s+', '', name)  # Remove all whitespace
    name = re.sub(r'[^\w\d]', '', name)  # Remove all non-alphanumeric
    return name.lower()

def scan_existing_outputs():
    existing = set()
    if not os.path.exists(OUTPUTS_DIR):
        return existing
    for state in os.listdir(OUTPUTS_DIR):
        state_path = os.path.join(OUTPUTS_DIR, state)
        if not os.path.isdir(state_path):
            continue
        for month in os.listdir(state_path):
            month_path = os.path.join(state_path, month)
            if not os.path.isdir(month_path):
                continue
            # Check for at least one .xlsx file in the month folder
            if any(fname.endswith('.xlsx') for fname in os.listdir(month_path)):
                existing.add((normalize_name(state), normalize_name(month)))
    return existing

def download_missing(driver, state, month):
    # Implement the logic to select state and month, refresh, and download as in main.py
    # This is a simplified version; you may want to copy more robust logic from main.py
    from selenium.webdriver.common.action_chains import ActionChains
    def select_state():
        state_label = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "j_idt41_label"))
        )
        state_label.click()
        time.sleep(0.2)
        state_items = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "j_idt41_items"))
        )
        state_options = state_items.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        for state_opt in state_options:
            if state_opt.text.strip() == state:
                state_opt.click()
                time.sleep(0.2)
                return True
        return False
    def select_month():
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
            if month_opt.text.strip() == month:
                month_opt.click()
                time.sleep(0.1)
                return True
        return False
    def click_refresh_and_download():
        refresh_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "j_idt72"))
        )
        refresh_button.click()
        time.sleep(1.5)
        download_img = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "groupingTable:j_idt91"))
        )
        download_img.click()
        time.sleep(3)
    # Select state and month, then download
    if not select_state():
        print(f"[WARN] Could not select state {state}")
        return False
    click_refresh_and_download()
    if not select_month():
        print(f"[WARN] Could not select month {month}")
        return False
    click_refresh_and_download()
    # Move the downloaded file to the correct folder
    files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.xlsx')]
    if not files:
        print(f"[WARN] No file downloaded for {state} - {month}")
        return False
    latest = max([os.path.join(DOWNLOAD_DIR, f) for f in files], key=os.path.getctime)
    month_dir = os.path.join(OUTPUTS_DIR, state, month)
    os.makedirs(month_dir, exist_ok=True)
    import shutil
    dest = os.path.join(month_dir, os.path.basename(latest))
    shutil.move(latest, dest)
    print(f"[INFO] Downloaded and moved file for {state} - {month}")
    return True

def main():
    print("[DEBUG] Script started")
    if len(sys.argv) > 1:
        outputs_folder = sys.argv[1]
    else:
        outputs_folder = input("Enter the outputs folder to check (e.g. outputs_Maker_Vehicle_Class_2024JAN_to_2025JAN_20250626_103509): ").strip()
    global OUTPUTS_DIR
    OUTPUTS_DIR = os.path.join(BASE_DIR, outputs_folder)
    if not os.path.exists(OUTPUTS_DIR):
        print(f"[ERROR] Specified outputs folder does not exist: {OUTPUTS_DIR}")
        return
    # Calculate folder and state normalization info before the state loop
    raw_state_folders = [d for d in os.listdir(OUTPUTS_DIR) if os.path.isdir(os.path.join(OUTPUTS_DIR, d))]
    normalized_master_states = [normalize_name(s) for s in MASTER_STATES]
    output_folder_states = [normalize_name(d) for d in raw_state_folders]
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
    try:
        driver.get("https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "yaxisVar_label"))
        )
        all_states = MASTER_STATES  # Use master list
        # For each state, select all required dropdowns before checking months
        for state in all_states:
            print(f"[INFO] Processing state: {state}")
            # Select type, year type, year, state in order
            try:
                select_type_dynamic(driver, "Actual Value")
                select_dropdown(driver, "selectedYearType_label", "Calendar Year")
                select_dropdown(driver, "selectedYear_label", "2024")
                select_state_dynamic(driver, state)
                # Now the month dropdown should be present
                all_months = get_available_months(driver)
                print(f"[INFO] Available months for {state}: {all_months}")
            except Exception as e:
                print(f"[ERROR] Could not select dropdowns for {state}: {e}")
                continue
            # Now check for missing months for this state
            raw_state_folders = [d for d in os.listdir(OUTPUTS_DIR) if os.path.isdir(os.path.join(OUTPUTS_DIR, d))]
            normalized_master_states = [normalize_name(s) for s in MASTER_STATES]
            output_folder_states = [normalize_name(d) for d in raw_state_folders]
            norm_state = normalize_name(state)
            missing_months = []
            if norm_state not in output_folder_states:
                print(f"[ALERT] State '{state}' is missing as a folder. Will attempt to download all months.")
                missing_months = all_months
            else:
                # Check which months are missing for this state
                state_path = os.path.join(OUTPUTS_DIR, state)
                existing_months = [normalize_name(m) for m in os.listdir(state_path) if os.path.isdir(os.path.join(state_path, m))]
                for month in all_months:
                    if normalize_name(month) not in existing_months:
                        missing_months.append(month)
            print(f"[INFO] Missing months for {state}: {missing_months}")
            for month in missing_months:
                print(f"[INFO] Downloading missing data for {state} - {month}")
                download_missing(driver, state, month)
        # Print normalization debug table at the end
        print("[DEBUG] About to print state presence debug table")
        print("=== State Presence Debug Table ===")
        for master, norm_master in zip(MASTER_STATES, normalized_master_states):
            found = norm_master in output_folder_states
            print(f"Master: '{master}' | Normalized: '{norm_master}' | Present in outputs: {found}")
        print("=== End State Presence Debug Table ===")
        print("=== Folder vs Master State Normalization Table ===")
        for folder in raw_state_folders:
            norm_folder = normalize_name(folder)
            print(f"Folder: '{folder}' | Normalized: '{norm_folder}'")
        print("---")
        for master, norm_master in zip(MASTER_STATES, normalized_master_states):
            print(f"Master: '{master}' | Normalized: '{norm_master}'")
        print("=== End Table ===")
    finally:
        driver.quit()

if __name__ == "__main__":
    main() 