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
