# Dynamic Dropdown Finder for VAHAN Automation

## Problem
The VAHAN website dynamically changes dropdown IDs every day, making hardcoded ID-based automation unreliable and requiring manual updates.

## Solution
A dynamic dropdown finder that locates elements by their stable attributes (labels, text content, CSS classes) instead of relying on hardcoded IDs.

## How It Works

### 1. Dynamic Dropdown Finding
The `find_dropdown_by_label()` function uses multiple strategies to locate dropdowns:

- **Strategy 1**: Find by label text in various elements (label, span, div)
- **Strategy 2**: Find by aria-label or title attributes
- **Strategy 3**: Find by class names that typically contain labels
- **Strategy 4**: Find by data attributes
- **Strategy 5**: Find by common dropdown patterns and parent text

### 2. Dynamic Items Container Finding
The `find_dropdown_items_container()` function locates the dropdown menu items:

- **Strategy 1**: Try common ID patterns for items containers
- **Strategy 2**: Look for items container by class and proximity
- **Strategy 3**: Look for any visible list with items

### 3. Dynamic Button Finding
- `find_refresh_button()`: Finds refresh buttons by text, patterns, and attributes
- `find_download_button()`: Finds Excel download buttons by various selectors

## Files

### `dynamic_dropdown_finder.py`
Contains all the dynamic finding functions:
- `find_dropdown_by_label()`
- `find_dropdown_items_container()`
- `find_refresh_button()`
- `find_download_button()`
- `select_dropdown_dynamic()`
- `select_state_dynamic()`
- `select_month_dynamic()`
- `get_available_states_dynamic()`
- `get_available_months_dynamic()`
- `click_refresh_dynamic()`
- `click_download_dynamic()`

### Updated Files
- `main.py`: Now uses dynamic functions instead of hardcoded IDs
- `check_missing_fixed.py`: Now uses dynamic functions instead of hardcoded IDs

### Test File
- `test_dynamic_finder.py`: Test script to verify the dynamic finder works

## Usage

### Running the Test
```bash
python test_dynamic_finder.py
```

### Running the Updated Automation
```bash
python main.py --run-now
python check_missing_fixed.py
```

## Benefits

1. **No Manual Updates**: No need to manually check and update IDs daily
2. **Robust**: Multiple fallback strategies ensure elements are found
3. **Maintainable**: Centralized logic in one module
4. **Debug-Friendly**: Detailed logging shows which strategy worked
5. **Future-Proof**: Works even if the website changes its ID generation

## How to Add New Dropdowns

To add support for a new dropdown:

1. Add the label to the dropdown order in `main.py`:
```python
dropdown_order = [
    ("yaxis", "Y-Axis", False),
    ("xaxis", "X-Axis", False),
    # Add new dropdown here
    ("new_field", "New Field Label", False),
]
```

2. The dynamic finder will automatically try to locate it using the label text.

## Troubleshooting

If a dropdown is not found:

1. Check the debug output to see which strategies were tried
2. Verify the label text matches exactly what's on the website
3. Run the test script to see what elements are found
4. Add new strategies to `find_dropdown_by_label()` if needed

## Example Debug Output
```
[DEBUG] Found dropdown with label 'State' using strategy: //label[contains(text(), 'State')]
[DEBUG] Found items container with ID: j_idt39_items
[INFO] Found 36 state options
[INFO] Selecting state: Andhra Pradesh
```

This approach makes the automation resilient to ID changes and eliminates the need for daily manual updates. 