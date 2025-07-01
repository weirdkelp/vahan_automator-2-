# VAHAN Data Automation Tool

This tool automates data collection from the VAHAN dashboard.

## Deployment Options

### Option 1: Using the Executable (Recommended)
1. Download the `vahan_automator.exe` file
2. Create a folder named `vahan_automator` on your desktop
3. Place the executable in this folder
4. Create a `prompt.txt` file in the same folder with your filter settings
5. Double-click the executable to run

### Option 2: Using Python
1. Install Python 3.8 or higher
2. Install Chrome browser
3. Open command prompt in the project folder
4. Run: `pip install -r requirements.txt`
5. Run: `python main.py`

## Configuration
Create a `prompt.txt` file with your filter settings in this format:
```
y-axis: value1, value2
x-axis: value1, value2
type: value1, value2
state: value1, value2
rto: value1, value2
year type: value1, value2
year: value1, value2
month: value1, value2
```

## Output
- Downloaded files will be saved in the `downloads` folder
- Processed files will be saved in the `outputs` folder, organized by month

## Troubleshooting
1. If the executable doesn't run, ensure Chrome is installed
2. If you get any errors, check the console output
3. Make sure you have write permissions in the folder

## Support
For any issues or questions, please contact the development team. 