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
Required fields: `usertest_id`, `title`, `prototype_url`, `steps`. `logo` is optional —
the test app falls back to the account's logo (group mapping in unmoderated-usertests).
Each step needs `type` ("screen" or "prototype") and `title`. Screen steps should have `variant` ("question", "task", or "instruction" — instruction screens render a "Continue" button instead of "Done with Step", useful as a briefing before a prototype step).

## Synthetic User Tests (experimental)

The `synth` command group drives a Playwright-controlled browser through a usertest
preview so an agent (typically Claude Code) can act as a synthetic participant.
It's an experimental, optional extra:

```bash
pip install 'podojo-cli[synth]'
playwright install chromium
```

```bash
podojo synth start <usertest_id|preview-url> [--headed]
podojo synth state
podojo synth click "Get Started"
podojo synth click-role button "Submit"
podojo synth fill "textarea" "..."
podojo synth press Enter
podojo synth advance 1        # auto-click "Done with Step" / "Continue"
podojo synth stop
```

Each action prints the new page state (URL, title, buttons, links, inputs, body text)
plus the path to a fresh full-page screenshot. The agent reads the screenshot and
decides the next action. State lives in `~/.podojo/synth/`; v1 supports one session
at a time. No LLM is bundled with the CLI — the calling agent provides the reasoning.

## Configuration

Set via env vars or `~/.podojo.toml`:

```toml
base_url = "https://your-api.example.com"
api_key = "your-api-key"
```

## Git Commits

- Commit directly to `main` — this is a solo project, no branching needed
