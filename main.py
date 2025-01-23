import csv
import os
import time
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import threading
import pyttsx3  # For text-to-speech

# Path to your ChromeDriver executable
chromedriver_path = r"C:/Users/innov_e9dohn9/projects/Help_Call/Help-Call-Automation-main/chromedriver-win64/chromedriver.exe"  # Update the path to your ChromeDriver

# Set Chrome options
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')  # Run in headless mode
chrome_options.add_argument('--ignore-certificate-errors')  # Ignore SSL certificate errors

# Set up the ChromeDriver with options
service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# CSV file paths
data_csv = 'data.csv'
form_data_csv = 'form_data.csv'

# Maintain a set of unique rows to prevent duplicates
unique_rows = set()

# Flask application
app = Flask(__name__)

# Function to fetch help call stations
def get_helpcall_stations():
    stations = []
    with open(data_csv, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            stations.append((row[3].strip(), row[4].strip()))
    return stations

# Function to save form data to CSV
def save_form_data_to_csv(data):
    write_headers = not os.path.exists(form_data_csv) or os.path.getsize(form_data_csv) == 0
    with open(form_data_csv, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if write_headers:
            writer.writerow(['Date', 'Shift', 'Station Name', 'Operator Name', 'Problem Categories', 'Raised Time', 'Closed Time', 'Concern Category', 'Problem Description', 'Action Taken'])
        writer.writerow(data)
        
# Function to save rows to CSV
def save_to_csv(headers, rows):
    try:
        # Check if the file exists and read existing rows
        existing_rows = set()
        if os.path.exists(data_csv):
            with open(data_csv, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                existing_rows = set(tuple(row) for row in reader)  # Store rows as tuples for comparison

        # Filter rows to save only unique entries
        new_rows = [row for row in rows if tuple(row) not in existing_rows]

        # Write to CSV
        with open(data_csv, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Write headers only if the file is empty
            if csvfile.tell() == 0:
                writer.writerow(headers)
            # Write only new rows
            writer.writerows(new_rows)
            print(f"Saved {len(new_rows)} new rows.")
    except Exception as e:
        print(f"Error writing to CSV: {e}")

# Function to fetch and process data from the website
def fetch_data():
    try:
        url = "http://10.244.103.183/ASB2/N_Stop_List/"  # Replace with your URL
        driver.get(url)

        while True:
            try:
                # Locate and interact with dropdown and button
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'DropDownLine')))
                dropdown = Select(driver.find_element(By.ID, 'DropDownLine'))
                dropdown.select_by_value('121')

                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'View_Btn')))
                generate_button = driver.find_element(By.ID, 'View_Btn')
                generate_button.click()

                # Wait for table to load and scrape data
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'DataGrid1')))
                time.sleep(1)
                html_content = driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                table = soup.find('table', {'id': 'DataGrid1'})

                # Extract table headers and rows
                headers = [header.text.strip() for header in table.find_all('th')]
                new_rows = []
                for row in table.find_all('tr')[1:]:
                    cells = row.find_all('td')
                    row_data = tuple(cell.text.strip() for cell in cells)
                    
                    # Avoid duplicate rows by checking against unique_rows set
                    if row_data and row_data not in unique_rows:
                        unique_rows.add(row_data)
                        new_rows.append(row_data)

                # Save new rows to the CSV
                if new_rows:
                    save_to_csv(headers, new_rows)
                    print(f"Saved {len(new_rows)} new rows.")
                    print(f"New rows added: {new_rows}")
                else:
                    print("No new rows found.")
                time.sleep(1)

            except Exception as e:
                print(f"Error during processing: {e}")
                time.sleep(1)

    except Exception as e:
        print(f"An error occurred in setup: {e}")

    finally:
        driver.quit()

# Flask routes
@app.route('/', methods=['GET', 'POST'])
def home():
    stations = get_helpcall_stations()
    message = None
    if request.method == 'POST':
        selected_station = eval(request.form['helpcall_alert_station'])
        station_name = request.form['station_name']
        operator_name = request.form['operator_name']
        problem_categories = request.form['problem_categories']
        problem_description = request.form['problem_description']
        action_taken = request.form['action_taken']
    
        current_datetime = datetime.now()
        current_date = current_datetime.strftime('%Y/%m/%d')
        closed_time = current_datetime.strftime('%Y/%m/%d %I:%M:%S %p')

        rows, shift, raised_time, row_deleted = [], None, None, False
        with open(data_csv, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            for row in reader:
                if row[3] == selected_station[0] and row[4] == selected_station[1]:
                    shift = row[1]
                    raised_time = row[2]
                    row_deleted = True
                else:
                    rows.append(row)
        
        if not row_deleted:
            message = "No matching row found to delete."
        else:
            form_data = [current_date, shift, station_name, operator_name, problem_categories, raised_time, closed_time, selected_station[0], problem_description, action_taken]
            save_form_data_to_csv(form_data)
            with open(data_csv, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)
                writer.writerows(rows)
            message = "Form submitted successfully and corresponding row deleted from data.csv!"
            
            # Redirect to prevent resubmission on page refresh
            return redirect(url_for('home', _external=True, _scheme='http', message=message))
    return render_template('index.html', stations=stations, message=message)

# Function to get the latest help call's specific column (Column 4)
def get_latest_help_call():
    try:
        with open(data_csv, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip headers if any
            latest_row = None
            for row in reader:
                latest_row = row  # Retain the last row
        if latest_row:
            return latest_row[3]  # Extract only the 4th column (zero-based index)
    except FileNotFoundError:
        print("CSV file not found!")
        return None
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

@app.route('/latest-help-call', methods=['GET'])
def latest_help_call():
    latest_call = get_latest_help_call()
    return {"latest_call": latest_call or "No new help call available."}

def periodic_text_to_speech():
    while True:
        try:
            latest_call = get_latest_help_call()
            if latest_call:
                # Use text-to-speech library to speak the latest call
                print(f"Speaking: {latest_call}")
                # Add your text-to-speech code here
            else:
                print("No help call data found.")
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
        time.sleep(3)  # Wait for 3 seconds before rechecking

# Periodic data fetch in a thread
def periodic_fetch_data():
    while True:
        try:
            fetch_data()
        except Exception as e:
            print(f"Error fetching data: {e}")
        time.sleep(7)

if __name__ == "__main__":
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        if not hasattr(app, 'fetch_thread_started'):
            app.fetch_thread_started = True
            fetch_thread = threading.Thread(target=periodic_fetch_data, daemon=True)
            fetch_thread.start()

            tts_thread = threading.Thread(target=periodic_text_to_speech, daemon=True)
            tts_thread.start()
    app.run(host="0.0.0.0", port=5000, debug=True)
