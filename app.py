import json
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import streamlit as st


# Streamlit Header
st.header("Boardriders SPAC Google Indexing API", divider='rainbow')


option = st.radio("Select an option:", ("Use a shared service account", "Upload JSON secrets"))



if option == "Upload JSON secrets":
    # Let users upload their secrets, which is a JSON file
    # STEP 2
    st.markdown("### Step 2: Upload the JSON secrets file for your service account below:")
    uploaded_file = st.file_uploader("", type="json")
    if uploaded_file is not None:
        secrets = json.load(uploaded_file)
        service_account_info = secrets
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=["https://www.googleapis.com/auth/indexing"]
        )
        google_client = build("indexing", "v3", credentials=credentials)
        client_email = secrets["client_email"]


elif option == "Use a shared service account":
    # Display the list of service accounts and let users select one
    
    # STEP 1
    st.markdown("### Step 1: Select a service account from the list below.")
    all_secrets = st.secrets
    selected_secret = st.selectbox('Each account has a daily quota of 200 URLs. If one fails, please select another.', list(all_secrets.keys()))
    secrets = all_secrets[selected_secret]

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

    google_client = build("indexing", "v3", credentials=credentials)

    # STEP 2
    st.markdown("### Step 2: Add the following account as a delegated owner in Google Search Console for the website for which you wish to submit URLs:")
    client_email = secrets["client_email"]
    st.markdown(client_email)


# STEP 3 
st.markdown("### Step 3: Provide a list of URLs that you would like to request indexing for, then submit.")
urls_input = st.text_area("Enter up to 100 URLs you wish to submit, one URL per line.")
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
                # st.write(f"API Response: {response}")
                
                responses.append((url, response))
            except HttpError as e:
                responses.append((url, e))
        return responses

    responses = submit_urls(urls)

    for url, response in responses:
        if isinstance(response, HttpError):
            error_message = response.content.decode("utf-8")
            if "Permission denied. Failed to verify the URL ownership" in error_message:
                st.error(f"Permission denied. Failed to verify the URL ownership. Please add '{client_email}' as an 'Owner' in Google Search Console.")
            else:
                st.error(f"Error Message: {error_message}")
                st.error("Please contact Ben Preston for assistance.")
        else:
            notify_time_str = response.get("urlNotificationMetadata", {}).get("latestUpdate", {}).get("notifyTime", "")
            if notify_time_str:
                notify_time = datetime.strptime(notify_time_str.split('.')[0].rstrip('Z'), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                notify_time = notify_time.replace(microsecond=0)
                st.success(f"{url} | URL submitted successfully at {notify_time}.")
            else:
                st.success(f"{url} | URL submitted successfully. Response: {response}")
