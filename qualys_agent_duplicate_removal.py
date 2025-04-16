import os
import json
import logging
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
import time
from pathlib import Path
import argparse

# Load environment variables
dotenv_path = Path(__file__).parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found. Environment variables might be missing.")

# API configuration
API_LOGIN = os.getenv("API_LOGIN")
API_PASSWORD = os.getenv("API_PASSWORD")
API_PLATFORM_URL = os.getenv("API_PLATFORM_URL")
API_HEADERS = json.loads(os.getenv("API_HEADERS", '{}'))
API_CREDENTIALS = (API_LOGIN, API_PASSWORD)
API_REQUEST_DELAY = float(os.getenv("API_REQUEST_DELAY", 1))

# Logging configuration
def setup_logging():
    """Sets up logging to a file in the /logs/ directory."""
    log_directory = Path(__file__).parent / "logs"
    os.makedirs(log_directory, exist_ok=True)
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = os.path.join(log_directory, f"CA_REMOVE_{current_time}.log")
    logging.basicConfig(
        filename=log_file_path,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    return log_file_path

LOG_FILE_PATH = setup_logging()

def log_debug(message):
    """Logs a debug-level message with a timestamp and prints to console."""
    timestamped = f"[{datetime.now():%d.%m.%Y %H:%M:%S}] {message}"
    logging.debug(timestamped)
    print(timestamped)

# API interaction functions
def fetch_cloud_agents():
    """Fetches cloud agents from the API."""
    log_debug("Fetching cloud agents from the API...")
    api_url = f"{API_PLATFORM_URL}/qps/rest/2.0/search/am/hostasset?fields=name,id,address,modified,created"
    agents_data = pd.DataFrame(columns=["id", "hostname", "address", "created", "modified"])
    tracking_method = "QAGENT"
    offset = 1

    while True:
        try:
            request_payload = f"""
            <ServiceRequest>
                <filters>
                    <Criteria field=\"trackingMethod\" operator=\"EQUALS\">{tracking_method}</Criteria>
                </filters>
                <preferences>
                    <limitResults>1000</limitResults>
                    <startFromOffset>{offset}</startFromOffset>
                </preferences>
            </ServiceRequest>
            """
            response = requests.post(api_url, auth=API_CREDENTIALS, headers=API_HEADERS, data=request_payload)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            entries = root.findall("data/HostAsset")

            for entry in entries:
                hostname = entry.findtext("name", default="").lower()
                agent_id = entry.findtext("id", default="")
                address = entry.findtext("address", default="")
                modified = entry.findtext("modified", default="")
                created = entry.findtext("created", default="")

                new_row = pd.DataFrame([{
                    "id": agent_id,
                    "hostname": hostname,
                    "address": address,
                    "created": created,
                    "modified": modified,
                }])
                agents_data = pd.concat([agents_data, new_row], ignore_index=True)

            if root.findtext("hasMoreRecords") == "true":
                offset += 1000
            else:
                break

        except requests.exceptions.RequestException as e:
            log_debug(f"Error while fetching data from API: {e}")
            break

    agents_data["created"] = pd.to_datetime(agents_data["created"], errors="coerce", utc=True).dt.tz_localize(None)
    agents_data["modified"] = pd.to_datetime(agents_data["modified"], errors="coerce", utc=True).dt.tz_localize(None)
    return agents_data

def find_duplicate_agents(agents_data):
    """Finds duplicate cloud agents based on hostname and address."""
    log_debug("Identifying duplicate cloud agents...")
    duplicates = agents_data[agents_data.duplicated(["hostname", "address"], keep=False)]
    sorted_duplicates = duplicates.sort_values(
        ["hostname", "address", "modified", "created"],
        ascending=[True, True, False, True],
    )
    latest_entries = sorted_duplicates.drop_duplicates(subset=["hostname", "address"], keep="first")
    to_remove = sorted_duplicates[~sorted_duplicates.index.isin(latest_entries.index)]

    log_debug(f"Found {len(duplicates)} duplicate agents.")
    log_debug(f"Marked {len(to_remove)} agents for removal.")
    return to_remove

def remove_cloud_agents(agents_to_remove, dry_run=False):
    """Removes duplicate cloud agents using the API."""
    log_debug("Starting removal of duplicate cloud agents...")
    for _, agent in agents_to_remove.iterrows():
        agent_id = agent["id"]
        hostname = agent["hostname"]
        address = agent["address"]
        created_date = agent["created"]
        modified_date = agent["modified"]

        log_debug(f"[{'DRY-RUN' if dry_run else 'ACTION'}] Agent ID: {agent_id}, Name: {hostname}, IP: {address}")

        if dry_run:
            continue

        try:
            time.sleep(API_REQUEST_DELAY)
            api_url = f"{API_PLATFORM_URL}/qps/rest/2.0/uninstall/am/asset/{agent_id}"
            request_payload = """<?xml version=\"1.0\" encoding=\"UTF-8\" ?>
            <ServiceRequest></ServiceRequest>"""

            response = requests.post(api_url, auth=API_CREDENTIALS, headers=API_HEADERS, data=request_payload)
            response.raise_for_status()

            root = ET.fromstring(response.text)
            response_code = root.findtext("responseCode")
            count = root.findtext("count")

            if response_code == "SUCCESS" and count != "0":
                log_debug(f"Successfully uninstalled agent ID: {agent_id}, Name: {hostname}, IP: {address}, Created: {created_date}, Modified: {modified_date}")
            else:
                log_debug(f"Failed to uninstall agent ID: {agent_id}, Name: {hostname}, IP: {address}, ResponseCode: {response_code}, Count: {count}")

        except Exception as e:
            log_debug(f"Error while uninstalling agent ID {agent_id}: {e}")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Qualys Agent Duplicate Removal Tool")
    parser.add_argument("--dry-run", action="store_true", help="Simulate the removal process without calling the API")
    args = parser.parse_args()

    try:
        agents_data = fetch_cloud_agents()
        if agents_data.empty:
            log_debug("No agents found to process.")
            return

        duplicates_to_remove = find_duplicate_agents(agents_data)
        if not duplicates_to_remove.empty:
            remove_cloud_agents(duplicates_to_remove, dry_run=args.dry_run)
            if args.dry_run:
                log_debug("Dry-run mode enabled. No agents were actually uninstalled.")
        else:
            log_debug("No duplicates found to process.")

    except Exception as e:
        log_debug(f"Unexpected error in main function: {e}")

if __name__ == "__main__":
    main()
