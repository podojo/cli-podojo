import urllib.parse
from pathlib import Path

import httpx

from .config import load_config


class PodojoClient:
    def __init__(self):
        config = load_config()
        self.base_url = config["base_url"].rstrip("/") + "/api/v1"
        self.api_key = config["api_key"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def list_projects(self, skip: int = 0, limit: int = 50) -> list:
        r = httpx.get(
            f"{self.base_url}/projects",
            params={"skip": skip, "limit": limit},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()["projects"]

    def create_project(self, name: str, brief: str = "") -> dict:
        r = httpx.post(
            f"{self.base_url}/projects",
            json={"name": name, "brief": brief},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def upload_interview(
        self,
        project: str,
        file_path: Path,
        audio_only: bool = False,
        batch_name: str | None = None,
    ) -> dict:
        encoded = urllib.parse.quote(project, safe="")
        data = {"audio_only": str(audio_only).lower()}
        if batch_name:
            data["batch_name"] = batch_name
        with file_path.open("rb") as f:
            r = httpx.post(
                f"{self.base_url}/projects/{encoded}/interviews",
                files={"file": (file_path.name, f)},
                data=data,
                headers=self._headers(),
                timeout=httpx.Timeout(None),
            )
        r.raise_for_status()
        return r.json()

    def upload_project_document(self, project: str, doc_type: str, content: str) -> dict:
        encoded = urllib.parse.quote(project, safe="")
        r = httpx.put(
            f"{self.base_url}/projects/{encoded}/documents/{doc_type}",
            json={"content": content},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def get_project_document(self, project: str, doc_type: str) -> dict:
        encoded = urllib.parse.quote(project, safe="")
        r = httpx.get(
            f"{self.base_url}/projects/{encoded}/documents/{doc_type}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def set_interview_quality(self, batch_id: str, label: str) -> dict:
        r = httpx.put(
            f"{self.base_url}/interviews/{batch_id}/quality",
            json={"label": label},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def list_transcripts(self, project: str) -> dict:
        r = httpx.get(
            f"{self.base_url}/projects/{project}/transcripts",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def download_transcript(self, project: str, batch_id: str) -> str:
        r = httpx.get(
            f"{self.base_url}/projects/{project}/transcripts/{batch_id}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.text

    def list_videos(self, project: str) -> dict:
        r = httpx.get(
            f"{self.base_url}/projects/{project}/videos",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def get_video_url(self, batch_id: str) -> dict:
        r = httpx.get(
            f"{self.base_url}/videos/{batch_id}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def list_usertests(self, skip: int = 0, limit: int = 50) -> dict:
        r = httpx.get(
            f"{self.base_url}/usertests",
            params={"skip": skip, "limit": limit},
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def get_usertest(self, usertest_id: str) -> dict:
        r = httpx.get(
            f"{self.base_url}/usertests/{usertest_id}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    IMAGE_CONTENT_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    def upload_usertest_image(self, file_path: Path) -> dict:
        content_type = self.IMAGE_CONTENT_TYPES.get(file_path.suffix.lower())
        if content_type is None:
            raise ValueError(
                f"Unsupported image type '{file_path.suffix}'. Allowed: PNG, JPEG, WebP, GIF."
            )
        with file_path.open("rb") as f:
            r = httpx.post(
                f"{self.base_url}/usertests/images",
                files={"file": (file_path.name, f, content_type)},
                headers=self._headers(),
                timeout=httpx.Timeout(None),
            )
        r.raise_for_status()
        return r.json()

    def create_usertest(self, data: dict) -> dict:
        r = httpx.post(
            f"{self.base_url}/usertests",
            json=data,
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def update_usertest(self, usertest_id: str, data: dict) -> dict:
        r = httpx.put(
            f"{self.base_url}/usertests/{usertest_id}",
            json=data,
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()

    def delete_usertest(self, usertest_id: str) -> dict:
        r = httpx.delete(
            f"{self.base_url}/usertests/{usertest_id}",
            headers=self._headers(),
        )
        r.raise_for_status()
        return r.json()
