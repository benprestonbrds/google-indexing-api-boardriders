import json
import re
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import streamlit as st

# Streamlit UI
st.header("Boardriders SPAC Google Indexing API", divider='rainbow')

# Step 1: Select Auth Method
option = st.radio("Select an option:", ("Use a shared service account", "Upload JSON secrets"))

# Initialize shared variables
google_client = None
client_email = None

# === Option 1: Upload JSON Service Account File ===
if option == "Upload JSON secrets":
    st.markdown("### Step 2: Upload the JSON secrets file for your service account below:")
    uploaded_file = st.file_uploader("", type="json")

    if uploaded_file is not None:
        try:
            secrets = json.load(uploaded_file)
            credentials = service_account.Credentials.from_service_account_info(
                secrets, scopes=["https://www.googleapis.com/auth/indexing"]
            )
            google_client = build("indexing", "v3", credentials=credentials)
            client_email = secrets.get("client_email", "Unknown")
        except Exception:
            st.error("❌ Invalid JSON file. Please upload a valid Google service account key.")
            st.stop()

# === Option 2: Use Shared Secrets from .streamlit/secrets.toml ===
elif option == "Use a shared service account":
    st.markdown("### Step 1: Select a service account from the list below.")
    all_secrets = st.secrets

# 🐛 DEBUG: Show what secrets are available
st.write("✅ Secrets loaded from .streamlit/secrets.toml:", list(all_secrets.keys()))

selected_secret = st.selectbox(
    'Each account has a daily quota of 200 URLs. If one fails, please select another.',
    list(all_secrets.keys())
)

    try:
        secrets = all_secrets[selected_secret]

        # Extract credentials
        required_keys = [
            "type", "project_id", "private_key_id", "private_key", "client_email",
            "client_id", "auth_uri", "token_uri",
            "auth_provider_x509_cert_url", "client_x509_cert_url"
        ]
        service_account_info = {key: secrets[key] for key in required_keys}

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=["https://www.googleapis.com/auth/indexing"]
        )
        google_client = build("indexing", "v3", credentials=credentials)
        client_email = secrets["client_email"]

        st.markdown("### Step 2: Add the following account as a delegated owner in Google Search Console:")
        st.code(client_email, language="none")

    except KeyError as e:
        st.error(f"❌ Missing key in secrets: {e}")
        st.stop()
    except Exception as e:
        st.error("❌ Failed to initialize the shared service account.")
        st.exception(e)
        st.stop()

# === Step 3: Submit URLs ===
if google_client:
    st.markdown("### Step 3: Provide a list of URLs to request indexing for, then submit.")
    urls_input = st.text_area("Enter up to 100 URLs, one per line:")
    submit_button = st.button("Submit")

    if submit_button and urls_input:
        raw_urls = urls_input.strip().split("\n")
        urls = [url.strip() for url in raw_urls if url.strip()]
        url_pattern = re.compile(r'^https?://')
        invalid_urls = [url for url in urls if not url_pattern.match(url)]

        if invalid_urls:
            st.warning("⚠️ Some URLs are invalid and will be skipped:")
            st.write(invalid_urls)
            urls = [url for url in urls if url_pattern.match(url)]

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
                error_message = response.content.decode("utf-8")
                if "Permission denied. Failed to verify the URL ownership" in error_message:
                    st.error(f"❌ {url} — Failed: Please add '{client_email}' as an **Owner** in Google Search Console.")
                else:
                    st.error(f"❌ {url} — API Error: {error_message}")
                    st.info("Contact Ben Preston for help if this persists.")
            else:
                notify_time_str = response.get("urlNotificationMetadata", {}).get("latestUpdate", {}).get("notifyTime", "")
                if notify_time_str:
                    notify_time = datetime.strptime(
                        notify_time_str.split('.')[0].rstrip('Z'),
                        "%Y-%m-%dT%H:%M:%S"
                    ).replace(tzinfo=timezone.utc).replace(microsecond=0)
                    st.success(f"✅ {url} — Submitted successfully at {notify_time}.")
                else:
                    st.success(f"✅ {url} — Submitted successfully.")
