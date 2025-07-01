import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def find_dropdown_by_label(driver, label_text, dropdown_type="select"):
    """
    Dynamically find dropdown by its label text instead of hardcoded ID.
    dropdown_type: "select" for PrimeFaces selectOneMenu, "dropdown" for regular dropdown
    """
    try:
        # Strategy 1: Find the actual dropdown elements by common patterns
        dropdown_selectors = [
            ".ui-selectonemenu",
            ".ui-selectonemenu-label",
            ".ui-selectonemenu-trigger",
            "select",
            "[role='combobox']"
        ]
        
        for selector in dropdown_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        # Check if this dropdown is associated with our label
                        try:
                            # Look for the label in the same form group or nearby
                            parent = element.find_element(By.XPATH, "./..")
                            grandparent = parent.find_element(By.XPATH, "./..")
                            
                            # Check if label text is in the parent or grandparent
                            parent_text = parent.text.lower()
                            grandparent_text = grandparent.text.lower()
                            label_lower = label_text.lower()
                            
                            if (label_lower in parent_text or 
                                label_lower in grandparent_text or
                                any(label_lower in sibling.text.lower() for sibling in parent.find_elements(By.XPATH, "./*"))):
                                print(f"[DEBUG] Found dropdown with label '{label_text}' using selector: {selector}")
                                return element
                        except Exception:
                            continue
            except Exception:
                continue
        
        # Strategy 2: Find by label text and then find the associated dropdown
        label_strategies = [
            f"//label[contains(text(), '{label_text}')]",
            f"//span[contains(text(), '{label_text}')]",
            f"//div[contains(text(), '{label_text}')]",
            f"//*[@aria-label='{label_text}' or @title='{label_text}']",
        ]
        
        for strategy in label_strategies:
            try:
                label_elements = driver.find_elements(By.XPATH, strategy)
                for label_element in label_elements:
                    if label_element.is_displayed():
                        # Try to find the associated dropdown
                        try:
                            # Look for dropdown in the same container
                            parent = label_element.find_element(By.XPATH, "./..")
                            dropdown = parent.find_element(By.CSS_SELECTOR, ".ui-selectonemenu, .ui-selectonemenu-label, select")
                            if dropdown.is_displayed() and dropdown.is_enabled():
                                print(f"[DEBUG] Found dropdown with label '{label_text}' using label strategy: {strategy}")
                                return dropdown
                        except Exception:
                            # Try looking in the grandparent
                            try:
                                grandparent = parent.find_element(By.XPATH, "./..")
                                dropdown = grandparent.find_element(By.CSS_SELECTOR, ".ui-selectonemenu, .ui-selectonemenu-label, select")
                                if dropdown.is_displayed() and dropdown.is_enabled():
                                    print(f"[DEBUG] Found dropdown with label '{label_text}' using grandparent strategy: {strategy}")
                                    return dropdown
                            except Exception:
                                continue
            except Exception:
                continue
        
        # Strategy 3: Find by form field patterns
        form_selectors = [
            f"//*[contains(@id, '{label_text.lower().replace(' ', '')}')]",
            f"//*[contains(@id, '{label_text.lower().replace('-', '')}')]",
            f"//*[contains(@name, '{label_text.lower().replace(' ', '')}')]",
        ]
        
        for selector in form_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[DEBUG] Found dropdown with label '{label_text}' using form selector: {selector}")
                        return element
            except Exception:
                continue
        
        print(f"[WARN] Could not find dropdown with label '{label_text}' using any strategy")
        return None
        
    except Exception as e:
        print(f"[ERROR] Error finding dropdown with label '{label_text}': {e}")
        return None

def find_dropdown_items_container(driver, dropdown_element):
    try:
        # Strategy 1: Look for the items container by ID pattern
        dropdown_id = dropdown_element.get_attribute("id")
        if dropdown_id:
            # Try common ID patterns for items containers
            possible_item_ids = [
                dropdown_id.replace("_label", "_items"),
                dropdown_id.replace("_input", "_items"),
                dropdown_id + "_items",
                dropdown_id.replace("label", "items"),
                dropdown_id.replace("Var", "_items"),
                dropdown_id.replace("Type", "_items")
            ]
            
            for item_id in possible_item_ids:
                try:
                    items_container = driver.find_element(By.ID, item_id)
                    if items_container.is_displayed():
                        print(f"[DEBUG] Found items container with ID: {item_id}")
                        return items_container
                except Exception:
                    continue
        
        # Strategy 2: Look for items container by class and proximity
        items_containers = driver.find_elements(By.CSS_SELECTOR, ".ui-selectonemenu-items-wrapper, .ui-selectonemenu-panel, .ui-selectonemenu-items")
        for container in items_containers:
            if container.is_displayed():
                # Check if this container is near our dropdown
                try:
                    dropdown_location = dropdown_element.location
                    container_location = container.location
                    distance = abs(dropdown_location['x'] - container_location['x']) + abs(dropdown_location['y'] - container_location['y'])
                    if distance < 500:  # Within reasonable distance
                        print(f"[DEBUG] Found items container by proximity")
                        return container
                except Exception:
                    continue
        
        # Strategy 3: Look for any visible list with items
        lists = driver.find_elements(By.CSS_SELECTOR, "ul.ui-selectonemenu-items, ul.ui-selectonemenu-list, .ui-selectonemenu-items ul")
        for list_elem in lists:
            if list_elem.is_displayed():
                print(f"[DEBUG] Found items list by CSS selector")
                return list_elem
        
        # Strategy 4: Look for the dropdown panel that appears when clicked
        panels = driver.find_elements(By.CSS_SELECTOR, ".ui-selectonemenu-panel, .ui-selectonemenu-items-wrapper")
        for panel in panels:
            if panel.is_displayed():
                print(f"[DEBUG] Found dropdown panel")
                return panel
        
        print(f"[WARN] Could not find items container for dropdown")
        return None
        
    except Exception as e:
        print(f"[ERROR] Error finding items container: {e}")
        return None

def find_refresh_button(driver):
    """
    Find refresh button using stable selectors based on the HTML provided.
    Uses button text "Refresh" and icon class "ui-icon-refresh".
    """
    try:
        # Primary strategy: Find button by visible text "Refresh" and icon
        refresh_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[.//span[contains(@class, 'ui-button-text') and normalize-space(text())='Refresh']]"
            ))
        )
        print("[DEBUG] Found refresh button using stable text selector")
        return refresh_button
    except Exception as e:
        print(f"[DEBUG] Primary refresh button strategy failed: {e}")
        
        # Fallback strategies
        refresh_selectors = [
            "//button[contains(text(), 'Refresh')]",
            "//input[@value='Refresh']",
            "//a[contains(text(), 'Refresh')]",
            "//span[contains(text(), 'Refresh')]",
            "//*[@title='Refresh']",
            "//*[@aria-label='Refresh']"
        ]
        for selector in refresh_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[DEBUG] Found refresh button using selector: {selector}")
                        return element
            except Exception:
                continue
        refresh_patterns = [
            ".ui-button[onclick*='refresh']",
            ".ui-button[onclick*='Refresh']",
            "button[onclick*='refresh']",
            "input[onclick*='refresh']",
            ".ui-commandbutton[onclick*='refresh']"
        ]
        for pattern in refresh_patterns:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, pattern)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[DEBUG] Found refresh button using pattern: {pattern}")
                        return element
            except Exception:
                continue
        button_classes = [
            ".ui-button.ui-widget.ui-state-default",
            ".ui-commandbutton.ui-widget.ui-state-default",
            "button.ui-button"
        ]
        for class_selector in button_classes:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, class_selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        button_text = element.text.lower()
                        button_attrs = element.get_attribute("outerHTML").lower()
                        if "refresh" in button_text or "refresh" in button_attrs:
                            print(f"[DEBUG] Found refresh button by class and text analysis")
                            return element
            except Exception:
                continue
        print(f"[WARN] Could not find refresh button using any strategy")
        return None
    except Exception as e:
        print(f"[ERROR] Error finding refresh button: {e}")
        return None

def find_download_button(driver):
    """
    Find download button using robust strategies:
    1. Prefer the <a> tag with id 'groupingTable:xls' or class 'ui-commandlink' containing the download <img>.
    2. Fallback to previous strategies (img with src/title, etc).
    """
    try:
        # Strategy 1: Find <a> with id 'groupingTable:xls' or class 'ui-commandlink' containing the download image
        try:
            a_elem = driver.find_element(By.XPATH, "//a[@id='groupingTable:xls' and .//img[contains(@src, 'csv.png') and contains(@title, 'Download EXCEL file')]]")
            if a_elem.is_displayed() and a_elem.is_enabled():
                print("[DEBUG] Found download <a> by id and image.")
                return a_elem
        except Exception:
            pass
        try:
            a_elems = driver.find_elements(By.XPATH, "//a[contains(@class, 'ui-commandlink') and .//img[contains(@src, 'csv.png') and contains(@title, 'Download EXCEL file')]]")
            for a_elem in a_elems:
                if a_elem.is_displayed() and a_elem.is_enabled():
                    print("[DEBUG] Found download <a> by class and image.")
                    return a_elem
        except Exception:
            pass
        # Strategy 2: Fallback to previous strategies (img with src/title, etc)
        try:
            download_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//img[@src='/vahan4dashboard/resources/images/csv.png' and @title='Download EXCEL file']"
                ))
            )
            print("[DEBUG] Found download button using stable image source and title selector")
            return download_button
        except Exception as e:
            print(f"[DEBUG] Primary download button strategy failed: {e}")
        download_selectors = [
            "//img[@alt='Excel']",
            "//img[@title='Excel']",
            "//img[contains(@src, 'excel')]",
            "//img[contains(@src, 'download')]",
            "//*[@title='Download Excel']",
            "//*[@aria-label='Download Excel']",
            "//*[contains(text(), 'Excel')]",
            "//*[contains(text(), 'Download')]"
        ]
        for selector in download_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[DEBUG] Found download button using selector: {selector}")
                        return element
            except Exception:
                continue
        download_patterns = [
            ".ui-commandlink[onclick*='excel']",
            ".ui-commandlink[onclick*='download']",
            "a[onclick*='excel']",
            "a[onclick*='download']",
            ".ui-button[onclick*='excel']",
            ".ui-button[onclick*='download']"
        ]
        for pattern in download_patterns:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, pattern)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[DEBUG] Found download button using pattern: {pattern}")
                        return element
            except Exception:
                continue
        table_download_selectors = [
            "//*[contains(@id, 'groupingTable')]//img[contains(@src, 'excel')]",
            "//*[contains(@id, 'groupingTable')]//a[contains(@onclick, 'excel')]",
            "//*[contains(@id, 'groupingTable')]//*[contains(@onclick, 'download')]"
        ]
        for selector in table_download_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        print(f"[DEBUG] Found download button in table using selector: {selector}")
                        return element
            except Exception:
                continue
        print(f"[WARN] Could not find download button using any strategy")
        return None
    except Exception as e:
        print(f"[ERROR] Error finding download button: {e}")
        return None

def robust_dropdown_click(driver, dropdown_element):
    """
    Try to click the dropdown label if present and visible, otherwise click the main dropdown div, otherwise click the <select> element, otherwise use JavaScript click. Logs HTML and saves a screenshot on failure.
    """
    # Wait for overlays to disappear
    try:
        WebDriverWait(driver, 5).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-blockui, .ui-widget-overlay"))
        )
    except Exception:
        pass

    # Log outer HTML for debugging
    try:
        print("[DEBUG] Dropdown outer HTML:", dropdown_element.get_attribute("outerHTML"))
    except Exception:
        pass

    # Try to click the label if present and visible
    try:
        label = dropdown_element.find_element(By.CSS_SELECTOR, ".ui-selectonemenu-label")
        if label.is_displayed() and label.is_enabled():
            label.click()
            return True
        else:
            print("[DEBUG] Label found but not visible/enabled, falling back to main div.")
    except Exception:
        print("[DEBUG] No label found, falling back to main div.")

    # Fallback: click the main dropdown div
    try:
        if dropdown_element.is_displayed() and dropdown_element.is_enabled():
            dropdown_element.click()
            return True
    except Exception:
        pass
    # Fallback: click the <select> element inside
    try:
        select_elem = dropdown_element.find_element(By.TAG_NAME, "select")
        driver.execute_script("arguments[0].click();", select_elem)
        return True
    except Exception:
        pass
    # Fallback: use JavaScript click on the main div
    try:
        driver.execute_script("arguments[0].click();", dropdown_element)
        return True
    except Exception:
        pass
    # Take a screenshot for debugging
    try:
        driver.save_screenshot("dropdown_click_failure.png")
        print("[DEBUG] Saved screenshot as dropdown_click_failure.png")
    except Exception:
        pass
    return False

def select_dropdown_dynamic(driver, dropdown_label, item_text, is_select=False):
    try:
        print(f"[DEBUG] Attempting to select '{item_text}' from dropdown with label '{dropdown_label}'")
        dropdown_element = find_dropdown_by_label(driver, dropdown_label, "select" if is_select else "dropdown")
        if not dropdown_element:
            print(f"[ERROR] Could not find dropdown with label '{dropdown_label}'")
            return False
        
        # First, try to close any open dropdowns to avoid click interception
        try:
            # Look for any open dropdown panels and close them
            open_panels = driver.find_elements(By.CSS_SELECTOR, ".ui-selectonemenu-panel, .ui-selectonemenu-items-wrapper")
            for panel in open_panels:
                if panel.is_displayed():
                    # Click outside to close
                    driver.execute_script("arguments[0].style.display = 'none';", panel)
                    time.sleep(0.1)
        except Exception:
            pass
        
        # Scroll to the dropdown and click it
        driver.execute_script("arguments[0].scrollIntoView(true);", dropdown_element)
        time.sleep(0.2)
        
        # Try multiple click strategies
        click_success = False
        try:
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable(dropdown_element))
            dropdown_element.click()
            click_success = True
        except Exception as e:
            print(f"[DEBUG] Direct click failed: {e}")
            try:
                # Try JavaScript click
                driver.execute_script("arguments[0].click();", dropdown_element)
                click_success = True
            except Exception as e2:
                print(f"[DEBUG] JavaScript click failed: {e2}")
                try:
                    # Try ActionChains click
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(driver).move_to_element(dropdown_element).click().perform()
                    click_success = True
                except Exception as e3:
                    print(f"[DEBUG] ActionChains click failed: {e3}")
        
        if not click_success:
            print(f"[ERROR] Could not click dropdown '{dropdown_label}'")
            return False
        
        time.sleep(0.3)  # Wait for dropdown to open
        
        # Find the items container
        items_container = find_dropdown_items_container(driver, dropdown_element)
        if not items_container:
            print(f"[ERROR] Could not find items container for dropdown '{dropdown_label}'")
            return False
        
        # Get all visible items
        items = items_container.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none']), .ui-selectonemenu-item:not([style*='display: none'])")
        print(f"[DEBUG] Found {len(items)} items in dropdown '{dropdown_label}': {[item.text.strip() for item in items]}")
        
        target_text = item_text.strip().lower()
        
        # Special handling for RTO selection
        if "rto" in dropdown_label.lower():
            for item in items:
                if "all vahan4 running office" in item.text.strip().lower():
                    print(f"[INFO] Selecting RTO option: {item.text.strip()}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable(item))
                    item.click()
                    time.sleep(0.1)
                    return True
        else:
            # Normal selection for other dropdowns
            for item in items:
                item_text_actual = item.text.strip().lower()
                if target_text in item_text_actual or item_text_actual in target_text:
                    print(f"[INFO] Selecting '{item.text.strip()}' for target '{item_text}'")
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    WebDriverWait(driver, 2).until(EC.element_to_be_clickable(item))
                    item.click()
                    time.sleep(0.1)
                    return True
        
        print(f"[ERROR] '{item_text}' not found in dropdown '{dropdown_label}'. Available options: {[item.text.strip() for item in items]}")
        return False
        
    except Exception as e:
        print(f"[ERROR] Failed to select '{item_text}' from dropdown '{dropdown_label}': {e}")
        return False

def select_state_dynamic(driver, state_name):
    """
    Select state using stable selector based on the HTML provided.
    Handles both the full dropdown container and label-only cases.
    """
    try:
        print(f"[DEBUG] Attempting to select state: {state_name}")
        state_dropdown = None
        # Try to find the full dropdown container first
        try:
            state_dropdown = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[contains(@class, 'ui-selectonemenu') and .//select[.//option[contains(text(), 'All Vahan4 Running States')]]]"
                ))
            )
            print("[DEBUG] Found full state dropdown container.")
            if not robust_dropdown_click(driver, state_dropdown):
                print(f"[ERROR] Could not robustly click State dropdown")
                return False
        except Exception:
            print("[DEBUG] Full dropdown container not found, trying label fallback.")
            # Fallback: try to find the label directly
            try:
                label = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//label[contains(@class, 'ui-selectonemenu-label') and contains(text(), 'All Vahan4 Running States')]"
                    ))
                )
                label.click()
                print("[DEBUG] Clicked state label directly.")
                # Try to get the dropdown container from the label's parent if possible
                try:
                    state_dropdown = label.find_element(By.XPATH, "..")
                except Exception:
                    state_dropdown = None
            except Exception as e:
                print(f"[ERROR] Could not find or click state label: {e}")
                return False
        time.sleep(0.2)
        # Now proceed to find and click the state option as before...
        # Only proceed if we have a dropdown container with aria-owns
        if state_dropdown is not None and state_dropdown.get_attribute('aria-owns'):
            try:
                items_container = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((
                        By.CSS_SELECTOR,
                        f"#{state_dropdown.get_attribute('aria-owns')}"
                    ))
                )
                # Find and click the target state option
                state_options = items_container.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
                for state_opt in state_options:
                    if state_opt.text.strip() == state_name:
                        print(f"[INFO] Selecting state: {state_name}")
                        driver.execute_script("arguments[0].scrollIntoView(true);", state_opt)
                        WebDriverWait(driver, 2).until(EC.element_to_be_clickable(state_opt))
                        state_opt.click()
                        time.sleep(0.2)
                        return True
                print(f"[WARN] State '{state_name}' not found in dropdown. Available: {[opt.text.strip() for opt in state_options]}")
                return False
            except Exception as e:
                print(f"[ERROR] Could not find or click state option: {e}")
                return False
        else:
            print("[WARN] No dropdown container with aria-owns found after clicking label.")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to select state {state_name}: {e}")
        return False

def select_month_dynamic(driver, month_name):
    try:
        print(f"[DEBUG] Attempting to select month: {month_name}")
        month_dropdown = find_dropdown_by_label(driver, "Month", "select")
        if not month_dropdown:
            print(f"[ERROR] Could not find month dropdown")
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", month_dropdown)
        WebDriverWait(driver, 3).until(EC.element_to_be_clickable(month_dropdown))
        month_dropdown.click()
        time.sleep(0.1)
        items_container = find_dropdown_items_container(driver, month_dropdown)
        if not items_container:
            print(f"[ERROR] Could not find month items container")
            return False
        month_options = items_container.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none']), .ui-selectonemenu-item:not([style*='display: none'])")
        print(f"[DEBUG] Available months: {[m.text.strip() for m in month_options]}")
        for month_opt in month_options:
            if month_opt.text.strip().lower().startswith(month_name.lower()):
                print(f"[INFO] Selecting month: {month_opt.text.strip()}")
                driver.execute_script("arguments[0].scrollIntoView(true);", month_opt)
                WebDriverWait(driver, 2).until(EC.element_to_be_clickable(month_opt))
                month_opt.click()
                time.sleep(0.1)
                return True
        print(f"[WARN] Month '{month_name}' not found in dropdown")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to select month {month_name}: {e}")
        return False

def select_type_dynamic(driver, type_value):
    """
    Select type using stable selector based on the HTML provided.
    Uses the presence of specific options ("Actual Value", "In Thousand", etc.) to identify the dropdown.
    """
    try:
        print(f"[DEBUG] Attempting to select type: {type_value}")
        
        # Find the OUTERMOST Type dropdown container by looking for the specific options it contains
        type_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class, 'ui-selectonemenu') and .//select[.//option[text()='Actual Value'] and .//option[text()='In Thousand'] and .//option[text()='In Lakh'] and .//option[text()='In Crore']]]"
            ))
        )
        
        # Use robust click logic
        if not robust_dropdown_click(driver, type_dropdown):
            print(f"[ERROR] Could not robustly click Type dropdown")
            return False
        time.sleep(0.2)
        
        # Wait for dropdown items to appear
        items_container = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((
                By.CSS_SELECTOR,
                f"#{type_dropdown.get_attribute('aria-owns')}"
            ))
        )
        
        # Find and click the target option
        options = items_container.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
        for option in options:
            if type_value.lower() in option.text.lower():
                print(f"[INFO] Selected Type: {type_value}")
                driver.execute_script("arguments[0].scrollIntoView(true);", option)
                WebDriverWait(driver, 2).until(EC.element_to_be_clickable(option))
                option.click()
                time.sleep(0.2)
                return True
        
        print(f"[ERROR] Could not find Type option: {type_value}")
        return False
        
    except Exception as e:
        print(f"[ERROR] Could not select Type dropdown: {e}")
        return False

def get_available_states_dynamic(driver):
    """
    Get list of all available states from the dropdown using robust logic.
    Handles both the full dropdown container and label-only cases.
    """
    try:
        print("[DEBUG] Attempting to find state dropdown...")
        state_dropdown = None
        # Try to find the full dropdown container first
        try:
            state_dropdown = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[contains(@class, 'ui-selectonemenu') and .//select[.//option[contains(text(), 'All Vahan4 Running States')]]]"
                ))
            )
            print("[DEBUG] Found full state dropdown container.")
            if not robust_dropdown_click(driver, state_dropdown):
                print(f"[ERROR] Could not robustly click State dropdown for available states")
                return []
        except Exception:
            print("[DEBUG] Full dropdown container not found, trying label fallback for available states.")
            # Fallback: try to find the label directly
            try:
                label = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//label[contains(@class, 'ui-selectonemenu-label') and contains(text(), 'All Vahan4 Running States')]"
                    ))
                )
                label.click()
                print("[DEBUG] Clicked state label directly for available states.")
                # Try to get the dropdown container from the label's parent if possible
                try:
                    state_dropdown = label.find_element(By.XPATH, "..")
                except Exception:
                    state_dropdown = None
            except Exception as e:
                print(f"[ERROR] Could not find or click state label for available states: {e}")
                return []
        time.sleep(0.2)
        # Now proceed to get the state options if we have a dropdown container with aria-owns
        if state_dropdown is not None and state_dropdown.get_attribute('aria-owns'):
            try:
                items_container = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((
                        By.CSS_SELECTOR,
                        f"#{state_dropdown.get_attribute('aria-owns')}"
                    ))
                )
                # Get all state options
                state_options = items_container.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none'])")
                states = [opt.text.strip() for opt in state_options if opt.text.strip() and "All Vahan4 Running States" not in opt.text.strip()]
                print(f"[DEBUG] Found {len(states)} state options")
                # Close the dropdown
                try:
                    label = state_dropdown.find_element(By.CSS_SELECTOR, ".ui-selectonemenu-label")
                    label.click()
                except Exception:
                    pass
                time.sleep(0.2)
                return states
            except Exception as e:
                print(f"[ERROR] Could not get state options: {e}")
                return []
        else:
            print("[WARN] No dropdown container with aria-owns found after clicking label for available states.")
            return []
    except Exception as e:
        print(f"[ERROR] Failed to get available states: {e}")
        return []

def get_available_months_dynamic(driver):
    try:
        month_dropdown = find_dropdown_by_label(driver, "Month", "select")
        if not month_dropdown:
            print(f"[ERROR] Could not find month dropdown")
            return []
        driver.execute_script("arguments[0].scrollIntoView(true);", month_dropdown)
        WebDriverWait(driver, 3).until(EC.element_to_be_clickable(month_dropdown))
        month_dropdown.click()
        time.sleep(0.1)
        items_container = find_dropdown_items_container(driver, month_dropdown)
        if not items_container:
            print(f"[ERROR] Could not find month items container")
            return []
        month_options = items_container.find_elements(By.CSS_SELECTOR, "li:not([style*='display: none']), .ui-selectonemenu-item:not([style*='display: none'])")
        months = [opt.text.strip() for opt in month_options if opt.text.strip() and opt.text.strip() != "2025"]
        month_dropdown.click()
        time.sleep(0.1)
        return months
    except Exception as e:
        print(f"[ERROR] Failed to get available months: {e}")
        return []

def click_refresh_dynamic(driver):
    try:
        print("[INFO] Looking for refresh button...")
        refresh_button = find_refresh_button(driver)
        if not refresh_button:
            print(f"[ERROR] Could not find refresh button")
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", refresh_button)
        WebDriverWait(driver, 3).until(EC.element_to_be_clickable(refresh_button))
        refresh_button.click()
        print("[INFO] Clicked refresh button.")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to click refresh button: {e}")
        return False

def click_download_dynamic(driver):
    try:
        print("[INFO] Looking for Excel download button...")
        download_button = find_download_button(driver)
        if not download_button:
            print(f"[ERROR] Could not find download button")
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", download_button)
        WebDriverWait(driver, 3).until(EC.element_to_be_clickable(download_button))
        download_button.click()
        print("[INFO] Clicked Excel download button.")
        time.sleep(0.5)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to click download button: {e}")
        return False 