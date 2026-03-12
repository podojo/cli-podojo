# Podojo CLI

CLI tool for the Podojo user research platform. Part of the Podojo multi-repo architecture.

## Tech Stack

- Python 3.12, uv for dependency management
- Typer for CLI framework
- httpx for HTTP client
- Rich for terminal output
- ffmpeg for video editing (system dependency, install via `brew install ffmpeg`)

## Usage

```bash
podojo projects list
podojo transcripts list <project>
podojo transcripts download <project> <batch_id> -o output.txt
podojo videos list <project>
podojo videos download <batch_id> -o output.mp4
podojo showreel create clips.json -o showreel.mp4
```

## Configuration

Set via env vars or `~/.podojo.toml`:

```toml
base_url = "https://your-api.example.com"
api_key = "your-api-key"
```

## Git Commits

- Do NOT add "Co-Authored-By: Claude" trailers to commit messages
- Keep commit messages concise and focused on the "why"
