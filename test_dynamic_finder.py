import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dynamic_dropdown_finder import (
    find_dropdown_by_label, find_refresh_button, find_download_button,
    get_available_states_dynamic, get_available_months_dynamic
)

def test_dynamic_finder():
    """Test the dynamic dropdown finder functions"""
    print("[INFO] Starting dynamic dropdown finder test...")
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to VAHAN website
        driver.get("https://vahan.parivahan.gov.in/vahan4dashboard/vahan/view/reportview.xhtml")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("[INFO] Successfully loaded VAHAN website")
        
        # Test finding various dropdowns
        dropdown_labels_to_test = ["Y-Axis", "X-Axis", "Year Type", "Year", "Type", "RTO", "State", "Month"]
        
        print("\n=== Testing Dropdown Finding ===")
        for label in dropdown_labels_to_test:
            print(f"\n[TEST] Looking for dropdown with label: {label}")
            dropdown = find_dropdown_by_label(driver, label)
            if dropdown:
                print(f"[SUCCESS] Found dropdown for '{label}'")
                dropdown_id = dropdown.get_attribute("id")
                dropdown_class = dropdown.get_attribute("class")
                print(f"[INFO] Dropdown ID: {dropdown_id}")
                print(f"[INFO] Dropdown Class: {dropdown_class}")
            else:
                print(f"[FAILED] Could not find dropdown for '{label}'")
        
        # Test finding refresh button
        print("\n=== Testing Refresh Button Finding ===")
        refresh_button = find_refresh_button(driver)
        if refresh_button:
            print("[SUCCESS] Found refresh button")
            button_id = refresh_button.get_attribute("id")
            button_text = refresh_button.text
            print(f"[INFO] Refresh button ID: {button_id}")
            print(f"[INFO] Refresh button text: {button_text}")
        else:
            print("[FAILED] Could not find refresh button")
        
        # Test finding download button
        print("\n=== Testing Download Button Finding ===")
        download_button = find_download_button(driver)
        if download_button:
            print("[SUCCESS] Found download button")
            button_id = download_button.get_attribute("id")
            button_text = download_button.text
            print(f"[INFO] Download button ID: {button_id}")
            print(f"[INFO] Download button text: {button_text}")
        else:
            print("[FAILED] Could not find download button")
        
        # Test getting available states
        print("\n=== Testing State Dropdown ===")
        states = get_available_states_dynamic(driver)
        if states:
            print(f"[SUCCESS] Found {len(states)} states")
            print(f"[INFO] First 5 states: {states[:5]}")
        else:
            print("[FAILED] Could not get available states")
        
        # Test getting available months (this might not work without selecting a year first)
        print("\n=== Testing Month Dropdown ===")
        months = get_available_months_dynamic(driver)
        if months:
            print(f"[SUCCESS] Found {len(months)} months")
            print(f"[INFO] Available months: {months}")
        else:
            print("[INFO] No months available (this is normal if no year is selected)")
        
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_dynamic_finder() 