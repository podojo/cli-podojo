"""List files in a Google Drive folder."""

from .upload import get_drive_service


def list_files(folder_id: str) -> list[dict]:
    """Return a list of files in the given folder (id, name, mimeType, webViewLink)."""
    drive = get_drive_service()

    results = (
        drive.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType, webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    return results.get("files", [])
