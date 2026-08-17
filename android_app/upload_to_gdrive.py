#!/usr/bin/env python3
import os
import sys
import json
import requests
from dotenv import load_dotenv

def upload_apk():
    env_path = "/home/ubuntu/Rasa/.env"
    apk_path = "/home/ubuntu/Rasa/android_app/app/build/outputs/apk/release/app-release.apk"
    if not os.path.exists(apk_path):
        apk_path = "/home/ubuntu/Rasa/android_app/app/build/outputs/apk/debug/app-debug.apk"
    
    if not os.path.exists(apk_path):
        print(f"Error: APK not found at {apk_path}. Please run './gradlew assembleRelease' first.")
        sys.exit(1)
        
    load_dotenv(env_path)
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh_token):
        print("Error: Google OAuth credentials missing in .env")
        sys.exit(1)

    print("Refreshing Google Drive access token...")
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    resp = requests.post(token_url, data=payload)
    if resp.status_code != 200:
        print(f"Error refreshing token: {resp.text}")
        sys.exit(1)

    access_token = resp.json().get("access_token")

    filename = "Alya-AI-Voice-Assistant-v2.0.apk"
    metadata = {
        "name": filename,
        "mimeType": "application/vnd.android.package-archive"
    }

    files = {
        "data": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
        "file": (filename, open(apk_path, "rb"), "application/vnd.android.package-archive")
    }

    headers = {"Authorization": f"Bearer {access_token}"}
    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink,webContentLink"

    print("Uploading APK to Google Drive...")
    upload_resp = requests.post(upload_url, headers=headers, files=files)
    if upload_resp.status_code not in (200, 201):
        print(f"Upload failed: {upload_resp.text}")
        sys.exit(1)

    file_data = upload_resp.json()
    file_id = file_data.get("id")

    # Set public sharing permission
    perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
    perm_payload = {"role": "reader", "type": "anyone"}
    requests.post(perm_url, headers=headers, json=perm_payload)

    view_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    download_link = f"https://drive.google.com/uc?id={file_id}&export=download"

    print("\n==========================================")
    print(" Upload Successful! ")
    print(f"File Name: {filename}")
    print(f"View Link: {view_link}")
    print(f"Direct Download: {download_link}")
    print("==========================================")

if __name__ == "__main__":
    upload_apk()
