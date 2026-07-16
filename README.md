# podojo-cli

Command-line tool for the [Podojo](https://podojo.com) user research platform.

`podojo` lets UX researchers manage projects, upload and transcribe interviews,
build unmoderated user tests, run AI voice interviews, download research
videos, cut showreels, and run synthetic test participants — all without
leaving the terminal.

## Installation

```bash
uv tool install podojo-cli
```

Or with pip:

```bash
pip install podojo-cli
```

Requires Python 3.11+. Some commands need extra tooling:

- `showreel` requires [`ffmpeg`](https://ffmpeg.org/) on your `PATH` (`brew install ffmpeg`).
- `synth` requires the optional `synth` extra: `pip install 'podojo-cli[synth]'` then `playwright install chromium`.

## Authentication

Log in once with your Podojo API key — it's stored in your system keychain:

```bash
podojo auth login            # prompts for the key
podojo auth login --key XXX  # or pass it directly
podojo auth logout           # remove the stored key
```

Configuration is read from, in order of precedence:

1. Environment variables — `PODOJO_API_KEY`, `PODOJO_BASE_URL`
2. `~/.podojo.toml`
3. The system keyring (set by `podojo auth login`)

## Usage

```bash
podojo --help            # top-level help
podojo <group> --help    # help for a command group
```

### Projects

```bash
podojo projects list
podojo projects create "Checkout Redesign" --brief "Q1 usability study"
podojo projects upload-doc "Checkout Redesign" brief.md --type brief
podojo projects get-doc "Checkout Redesign" --type final -o final-report.md
```

`upload-doc` and `get-doc` accept `brief`, `agent`, and `final` document types.
Embedded images are stripped from markdown before upload.

### Interviews & transcripts

```bash
podojo interviews upload session-03.mp4 --project "Checkout Redesign"
podojo transcripts list "Checkout Redesign"
podojo transcripts download "Checkout Redesign" <batch-id> -o transcript.txt
```

### Videos & showreels

```bash
podojo videos list "Checkout Redesign"
podojo videos download <batch-id> -o clip.mp4
podojo showreel create clips.json -o showreel.mp4
```

The showreel `clips.json` is a list of clips, each with `batch_id`,
`participant`, `country`, `topic`, `start`, and `end` (`MM:SS` or `HH:MM:SS`).
Each clip gets an auto-generated title card.

### Unmoderated user tests

```bash
podojo usertests example > my-test.yaml   # print a template to start from
podojo usertests validate my-test.yaml    # check it without creating
podojo usertests create -f my-test.yaml
podojo usertests list
podojo usertests get checkout-usability-v1
podojo usertests update checkout-usability-v1 -f changes.yaml
podojo usertests delete checkout-usability-v1
podojo usertests snippet                  # recorder script for self-hosted prototypes
```

A user test can open with an optional participant screener: on-screen
single-select `screening_questions` whose options carry `qualifies: true`
flags. Participants must pick a qualifying option on every question; everyone
else sees the test's `rejection_message` and never reaches the recorded test.
See `podojo usertests example` for the exact shape.

### AI interviews

An AI interview is a self-serve voice conversation: an AI interviewer asks
your questions in order and adaptively follows up. One YAML file defines one
study:

```bash
podojo aiinterviews example > my-interview.yaml   # print a template to start from
podojo aiinterviews validate my-interview.yaml    # check it without creating
podojo aiinterviews create -f my-interview.yaml
podojo aiinterviews list
podojo aiinterviews get checkout-experience-v1
podojo aiinterviews update checkout-experience-v1 -f changes.yaml
podojo aiinterviews delete checkout-experience-v1
```

`create` and `get` print the participant Preview and Live URLs. The frontend
base URL can be overridden via `ai_interviews_url` in `~/.podojo.toml` or
`PODOJO_AI_INTERVIEWS_URL`.

A study can open with an optional participant screener: on-screen single-select
`screening_questions` whose options carry `qualifies: true` flags. Participants
must pick a qualifying option on every question; everyone else sees the study's
`rejection_message` and never reaches the voice interview. See
`podojo aiinterviews example` for the exact shape.

### Synthetic participants

The `synth` group drives a Playwright browser through a user test preview so an
agent (e.g. Claude Code) can act as a synthetic participant:

```bash
podojo synth start checkout-usability-v1   # or a preview URL
podojo synth state
podojo synth click "Get Started"
podojo synth fill "#answer" "It felt slow"
podojo synth advance
podojo synth stop
```

## Links

- [Source & issues](https://github.com/podojo/cli-podojo)
- [Changelog](https://github.com/podojo/cli-podojo/blob/main/CHANGELOG.md)

## License

MIT
