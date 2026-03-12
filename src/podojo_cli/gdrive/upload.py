"""Upload a markdown file to Google Drive as a Google Doc."""

import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


DEFAULT_FOLDER_ID = "REDACTED"  # "UX Reports" shared folder


def get_drive_service(credentials_path: str):
    creds = Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def upload_md_as_doc(
    md_file: str,
    credentials_path: str,
    title: str | None = None,
    folder_id: str | None = None,
) -> tuple[str, str]:
    drive = get_drive_service(credentials_path)

    if not title:
        title = os.path.splitext(os.path.basename(md_file))[0]

    parent = folder_id or DEFAULT_FOLDER_ID

    media = MediaFileUpload(md_file, mimetype="text/markdown")
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
        "parents": [parent],
    }
    result = (
        drive.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True,
        )
        .execute()
    )

    doc_id = result["id"]
    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return doc_id, url
