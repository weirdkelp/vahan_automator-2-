import os
import threading
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, send_file
import subprocess
import zipfile
import io
from calendar import month_abbr
import re
import pandas as pd
from merge_companies import merge_companies

print("[DEBUG] Flask app started and loaded")

app = Flask(__name__)

# Service status tracking
task_status = {
    'vahan': 'Idle',
    'check_missing': 'Idle',
    'combine': 'Idle',
    'filter': 'Idle'
}
task_output = {
    'vahan': '',
    'check_missing': '',
    'combine': '',
    'filter': ''
}

# Background task runner
def run_script(name, cmd):
    def task():
        task_status[name] = 'Running'
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            print(f"[DEBUG] {name} returncode: {result.returncode}")
            print(f"[DEBUG] {name} stdout: {result.stdout}")
            print(f"[DEBUG] {name} stderr: {result.stderr}")
            task_output[name] = result.stdout + '\n' + result.stderr
            if result.returncode == 0:
                task_status[name] = 'Completed'
            else:
                task_status[name] = 'Error'
        except Exception as e:
            task_status[name] = 'Error'
            task_output[name] = str(e)
    threading.Thread(target=task).start()

def parse_folder_range(folder_name):
    m = re.search(r'_(\d{4})([A-Z]{3})_to_(\d{4})([A-Z]{3})', folder_name)
    if m:
        start_year, start_month, end_year, end_month = m.groups()
        return start_year, start_month, end_year, end_month
    return None, None, None, None

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

def normalize_name(name):
    import re
    return re.sub(r'[^a-z0-9]', '', name.lower())

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

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    print("[DEBUG] missing_check_dashboard route called")
    base_dir = os.getcwd()
    outputs_folders = [d for d in os.listdir(base_dir) if d.startswith('outputs') and os.path.isdir(os.path.join(base_dir, d))]
    selected_missing_folder = None
    missing = []
    folder_range = None
    filter_candidates = [f for f in os.listdir('.') if f.startswith('combined') and f.endswith('.xlsx')]
    if request.method == 'POST' and 'folder_to_check_missing' in request.form:
        selected_missing_folder = request.form.get('folder_to_check_missing')
        start_year, start_month, end_year, end_month = parse_folder_range(selected_missing_folder)
        folder_range = (start_year, start_month, end_year, end_month)
        year_month_seq = []
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
            outputs_dir = os.path.join(os.getcwd(), selected_missing_folder)
            raw_state_folders = [d for d in os.listdir(outputs_dir) if os.path.isdir(os.path.join(outputs_dir, d))]
            normalized_folder_states = [normalize_name(d) for d in raw_state_folders]
            normalized_master_states = [normalize_name(s) for s in MASTER_STATES]
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
    return render_template('dashboard.html', status=task_status, outputs_folders=outputs_folders,
                           missing=missing, selected_missing_folder=selected_missing_folder, 
                           folder_range=folder_range, filter_candidates=filter_candidates)

@app.route('/run/<service>', methods=['POST'])
def run_service(service):
    if service == 'vahan':
        run_script('vahan', 'python main.py --run-now')
    elif service == 'check_missing':
        run_script('check_missing', 'python check_missing_fixed.py')
    elif service == 'combine':
        folder_to_combine = request.form.get('folder_to_combine', 'outputs')
        run_script('combine', f'python combine_all_vahan_data.py "{folder_to_combine}"')
    elif service == 'filter':
        run_script('filter', 'python filter_vehicles.py')
    return redirect(url_for('dashboard'))

@app.route('/status/<service>')
def status(service):
    return jsonify({
        'status': task_status.get(service, 'Unknown'),
        'output': task_output.get(service, '')
    })

@app.route('/download/<path:filename>')
def download_file(filename):
    directory = os.path.dirname(filename)
    fname = os.path.basename(filename)
    return send_from_directory(directory or '.', fname, as_attachment=True)

# Add a route to download a folder as a zip file
@app.route('/download_folder/<path:foldername>')
def download_folder(foldername):
    folder_path = os.path.join('outputs', foldername)
    if not os.path.isdir(folder_path):
        return f"Folder not found: {foldername}", 404
    # Create a zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)
    zip_buffer.seek(0)
    zip_filename = foldername.replace(os.sep, '_') + '.zip'
    return send_file(zip_buffer, as_attachment=True, download_name=zip_filename, mimetype='application/zip')

@app.route('/download_all_outputs')
def download_all_outputs():
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all outputs* folders
        base_dir = os.getcwd()
        outputs_folders = [d for d in os.listdir(base_dir) if d.startswith('outputs') and os.path.isdir(os.path.join(base_dir, d))]
        for outputs_folder in outputs_folders:
            for root, dirs, files in os.walk(outputs_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, '.')
                    zipf.write(file_path, arcname)
        # Add all combined data files and filtered/non_filtered files in root
        for fname in os.listdir(base_dir):
            if (
                fname.startswith('combined_data_') or 
                fname.startswith('combined_vahan_data') or 
                fname in ['filtered_vehicles.xlsx', 'non_filtered_vehicles.xlsx'] or
                (fname.startswith('filtered_') and fname.endswith('.xlsx')) or
                (fname.startswith('non_filtered_') and fname.endswith('.xlsx')) or
                (fname.startswith('merged_') and (fname.endswith('.xlsx') or fname.endswith('.csv')))
            ):
                if os.path.isfile(fname):
                    zipf.write(fname, fname)
    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name='all_outputs_and_selected_files.zip', mimetype='application/zip')

@app.route('/dashboard_filters', methods=['POST'])
def dashboard_filters():
    # Get selected values from the form
    yaxis = request.form.getlist('yaxis')
    xaxis = request.form.getlist('xaxis')
    year = request.form.getlist('year')
    start_year = request.form.get('start_year')
    start_month = request.form.get('start_month')
    end_year = request.form.get('end_year')
    end_month = request.form.get('end_month')
    # Read existing prompt.txt
    prompt_lines = {}
    if os.path.exists('prompt.txt'):
        with open('prompt.txt', 'r') as f:
            for line in f:
                if ':' in line:
                    key, val = line.split(':', 1)
                    prompt_lines[key.strip().lower()] = val.strip()
    # Update only the relevant keys
    if yaxis:
        prompt_lines['y-axis'] = ', '.join(yaxis)
    if xaxis:
        prompt_lines['x-axis'] = ', '.join(xaxis)
    if year:
        prompt_lines['year'] = ', '.join(year)
    if start_year:
        prompt_lines['start_year'] = start_year
    if start_month:
        prompt_lines['start_month'] = start_month
    if end_year:
        prompt_lines['end_year'] = end_year
    if end_month:
        prompt_lines['end_month'] = end_month
    # Write back all keys, preserving others
    with open('prompt.txt', 'w') as f:
        for key, val in prompt_lines.items():
            f.write(f"{key.title()}: {val}\n")
    return redirect(url_for('dashboard'))

@app.route('/run/download_missing', methods=['POST'])
def run_download_missing():
    folder = request.form.get('folder_to_check_missing')
    if folder:
        run_script('download_missing', f'python check_missing_fixed.py --download-missing --folder "{folder}"')
    return redirect(url_for('dashboard'))

@app.route('/run/filter', methods=['POST'])
def run_filter():
    filter_file = request.form.get('filter_file', 'combined_vahan_data(1).xlsx')
    run_script('filter', f'python filter_vehicles.py "{filter_file}"')
    return redirect(url_for('dashboard'))

@app.route('/merge_companies', methods=['GET', 'POST'])
def merge_companies_route():
    import json
    base_dir = os.getcwd()
    # Only show files that are likely to be combined/filterable
    filter_candidates = [f for f in os.listdir('.') if f.endswith('.xlsx') and not f.startswith('~$')]
    selected_file = request.form.get('file') if request.method == 'POST' else None
    unique_companies = []
    merge_result_file = None
    download_link = None
    if selected_file:
        df = pd.read_excel(selected_file)
        maker_col = next((col for col in df.columns if isinstance(col, str) and "MAKER" in col.upper()), None)
        if maker_col:
            unique_companies = sorted(df[maker_col].dropna().unique().tolist())
    if request.method == 'POST' and 'merge_map_json' in request.form:
        merge_map = json.loads(request.form['merge_map_json'])
        output_file = f"merged_{selected_file}"
        merge_companies(selected_file, merge_map, output_file)
        merge_result_file = output_file
        download_link = url_for('download_file', filename=output_file)
    return render_template('merge_companies.html', 
        filter_candidates=filter_candidates, 
        unique_companies=unique_companies, 
        selected_file=selected_file,
        merge_result_file=merge_result_file,
        download_link=download_link)

# --- TEMPLATES ---
# Create templates/dashboard.html with Bootstrap 5 UI

# ensure_templates()  # Disabled to prevent overwriting custom dashboard.html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 