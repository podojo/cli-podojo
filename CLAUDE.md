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
podojo auth login <api-key>
podojo auth logout
podojo projects list
podojo transcripts list <project>
podojo transcripts download <project> <batch_id> -o output.txt
podojo videos list <project>
podojo videos download <batch_id> -o output.mp4
podojo showreel create clips.json -o showreel.mp4
podojo gdrive setup ~/.podojo-gdrive.json
podojo gdrive upload report.md --title "My Report"
```

## User Tests (Unmoderated Tests)

```bash
podojo usertests list
podojo usertests get <usertest_id>
podojo usertests create --from-file usertest.yaml
podojo usertests update <usertest_id> --from-file updates.yaml
podojo usertests delete <usertest_id> [--yes]
podojo usertests example              # print template YAML to stdout
podojo usertests validate usertest.yaml # validate without creating
```

User test configs are YAML files. Run `podojo usertests example` for the full template.
Required fields: `usertest_id`, `client`, `title`, `logo`, `prototype_url`, `steps`.
Each step needs `type` ("screen" or "prototype") and `title`. Screen steps should have `variant` ("question" or "task").

## Configuration

Set via env vars or `~/.podojo.toml`:

```toml
base_url = "https://your-api.example.com"
api_key = "your-api-key"
```

## Git Commits

- Do NOT add "Co-Authored-By: Claude" trailers to commit messages
- Keep commit messages concise and focused on the "why"
