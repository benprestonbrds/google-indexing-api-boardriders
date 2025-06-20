import os
import json
import base64
import datetime
from datetime import datetime, timedelta, timezone
import requests
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import streamlit as st
import pytz

# Streamlit application interface
st.header("Google Index submission tool", divider='rainbow')

# read all secrets
all_secrets = st.secrets

# Create a menu to let the user choose which secrets
selected_secret = st.selectbox('Please select the API you want to use. For bulk use, please select AMP and authorize the relevant mailbox！', list(all_secrets.keys()))

# Use selected secrets
secrets = all_secrets[selected_secret]

# Create a service account key
service_account_info = {
    "type": secrets["type"],
    "project_id": secrets["project_id"],
    "private_key_id": secrets["private_key_id"],
    "private_key": secrets["private_key"],
    "client_email": secrets["client_email"],
    "client_id": secrets["client_id"],
    "auth_uri": secrets["auth_uri"],
    "token_uri": secrets["token_uri"],
    "auth_provider_x509_cert_url": secrets["auth_provider_x509_cert_url"],
    "client_x509_cert_url": secrets["client_x509_cert_url"],
}

credentials = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=["https://www.googleapis.com/auth/indexing"]
)

# Building a Google API client
google_client = build("indexing", "v3", credentials=credentials)

# working with files
st.markdown("Index api Tool usage files：[https://bit.ly/45mHyGJ](https://bit.ly/45mHyGJ)")
st.markdown('''
    :rainbow[Please ask the SEO Team to assit you]。''')

urls_input = st.text_area("Please enter the URL to submit（one per line）")
submit_button = st.button("Submit")

if submit_button and urls_input:
    urls = urls_input.strip().split("\n")

    def submit_urls(urls):
        responses = []
        for url in urls:
            try:
                response = google_client.urlNotifications().publish(
                    body={"url": url, "type": "URL_UPDATED"}
                ).execute()
                responses.append((url, response))
            except HttpError as e:
                responses.append((url, e))
        return responses

    responses = submit_urls(urls)

    for url, response in responses:
        if isinstance(response, HttpError):
            st.error(f"{url} | Submission failed, is it because the customer authorisation failed!")
        else:
            notify_time_str = response.get("urlNotificationMetadata", {}).get("latestUpdate", {}).get("notifyTime", "")
            notify_time = datetime.strptime(notify_time_str.split('.')[0].rstrip('Z'), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            notify_time = notify_time.replace(microsecond=0)

            # Convert time to UTC+10
            tz = pytz.timezone('Australia/Brisbane')
            notify_time = notify_time.astimezone(brisbane_tz)

            st.success(f"{url} | Submission successful, submission time is {notify_time.strftime('%Y年%m月%d日 %H:%M')}")
