import requests
import json
from datetime import datetime
import re

# Your API keys and headers
sendgrid_api_key = 'HIDDEN'
airtable_api_key = "NICE"
airtable_base_id = 'TRY'
airtable_table_name = 'NERD'
sendgrid_headers = {"Authorization": f"Bearer {sendgrid_api_key}"}

def extract_links(html_content):
    """Extracts all href attributes from HTML content."""
    href_regex = r'href="(.*?)"'
    links = re.findall(href_regex, html_content)
    return links

def extract_utm_content(links):
    """Extracts the utm_campaign parameter from a list of links."""
    for link in links:
        utm_content_match = re.search(r'utm_content=([^&]+)', link)
        if utm_content_match:
            return utm_content_match.group(1)
    return ""  # Return an empty string if no utm_campaign is found

def fetch_single_sends():
    """Fetches the most recent Single Sends."""
    single_sends_url = 'https://api.sendgrid.com/v3/marketing/singlesends'
    response = requests.get(single_sends_url, headers=sendgrid_headers)
    if response.status_code == 200:
        single_sends = response.json()['result']
        sorted_sends = sorted(single_sends, key=lambda x: x['send_at'] if x['send_at'] else '0000-00-00T00:00:00Z', reverse=True)
        recent_sends = sorted_sends[:10]
        return recent_sends
    else:
        print(f"Failed to fetch Single Sends: {response.status_code} - {response.text}")
        return []

def process_and_upload_single_send(single_send_id):
    """Processes a single send and uploads its data to Airtable."""
    sendgrid_details_url = f"https://api.sendgrid.com/v3/marketing/singlesends/{single_send_id}"
    details_response = requests.get(sendgrid_details_url, headers=sendgrid_headers)
    details_data = details_response.json()

    subject = details_data['email_config']['subject']
    html_content = details_data['email_config']['html_content']
    extracted_links = extract_links(html_content)
    cleaned_html_content = " ".join(extracted_links)  # Join extracted links with a space
    utm_content = extract_utm_content(extracted_links)

    send_date = details_data.get('send_at', '')
    formatted_send_date = datetime.strptime(send_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d") if send_date else ""

    sendgrid_stats_url = f"https://api.sendgrid.com/v3/marketing/stats/singlesends/{single_send_id}"
    stats_response = requests.get(sendgrid_stats_url, headers=sendgrid_headers)
    stats_data = stats_response.json()

    single_send_stats = stats_data['results'][0]['stats'] if stats_data and 'results' in stats_data and len(stats_data['results']) > 0 else {}

    airtable_payload = {
        "fields": {
            "Date of Send": formatted_send_date,
            "Subject": subject,
            "Body": cleaned_html_content,
            "Deliverable ID": utm_content,  # Include the utm_campaign value
            "Emails Triggered": single_send_stats.get('requests', "N/A"),
            "Delivered": single_send_stats.get('delivered', "N/A"),
            "Unique Opens": single_send_stats.get('unique_opens', "N/A"),
            "Unique Clicks": single_send_stats.get('unique_clicks', "N/A"),
            "Bounces": single_send_stats.get('bounces', "N/A"),
            "Spam Reports": single_send_stats.get('spam_reports', "N/A"),
            "Unsubscribes": single_send_stats.get('unsubscribes', "N/A")
        }
    }

    airtable_url = f"https://api.airtable.com/v0/{airtable_base_id}/{airtable_table_name}"
    airtable_response = requests.post(airtable_url, headers={"Authorization": f"Bearer {airtable_api_key}", "Content-Type": "application/json"}, json=airtable_payload)

    if airtable_response.status_code in [200, 201]:
        print(f"Successfully uploaded data for Single Send ID {single_send_id} to Airtable.")
    else:
        print(f"Failed to upload data for Single Send ID {single_send_id} to Airtable: {airtable_response.status_code} - {airtable_response.text}")

def main():
    recent_single_sends = fetch_single_sends()
    for single_send in recent_single_sends:
        process_and_upload_single_send(single_send['id'])

if __name__ == "__main__":
    main()
