# Changelog

All notable changes to the Podojo CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org).

## [1.4.0] - 2026-05-31

### Added
- Support `image_file:` in usertest step config — a local image path that is uploaded to Podojo-hosted storage on `create`/`update` and replaced with the hosted URL. Relative paths resolve against the YAML file's location. Externally-hosted `image:` URLs continue to work.

## [1.3.0] - 2026-05-25

### Removed
- Drop `privacy_text` field from usertest config. It was never used in practice, and the participant frontend no longer renders it.

## [1.2.0] - 2026-05-25

### Removed
- Drop `intro` and `feedback` step variants. They had no rendering effect on the participant frontend. Use `instruction` (briefing before a prototype step) or `question` (open-ended response) instead. Existing stored values are not migrated and continue to render as default.

## [1.1.2] - 2026-05-24

### Changed
- Re-publish to refresh PyPI verified-URLs status under the trusted publisher.

## [1.1.1] - 2026-05-24

### Changed
- Mark package as Production/Stable in PyPI classifiers. Add `LICENSE` file to the source tree.

## [1.1.0] - 2026-05-24

### Added
- `projects upload-doc --type agent` to upload an agent report markdown file to a project. Previously only the `brief` and `final` document types were uploadable via the CLI.

## [1.0.2] - 2026-05-23

### Added
- `synth swipe-xy` and `synth frame-swipe-xy` for drag/swipe gestures (slide-to-confirm, dismissable cards, carousels). Backed by Playwright `mouse.move` → `mouse.down` → stepped `mouse.move` → `mouse.up`. `--steps` controls swipe speed. The frame variant translates iframe-local coords to page coords automatically.

## [1.0.1] - 2026-05-23

### Fixed
- `synth frame_click_xy` now works on SVG elements (e.g. map icons, inline-SVG buttons). Uses real mouse events at the iframe offset instead of `elementFromPoint(...).click()`, which threw `e.click is not a function` on non-HTMLElement targets and didn't dispatch `mousedown`/`mouseup` for pointer-event listeners.

## [1.0.0] - 2026-05-21

### Changed
- First stable release. The CLI's commands and config format are now considered stable; no functional changes from 0.11.0.

## [0.11.0] - 2026-05-21

### Added
- `collect_contact` field for usertests. Set `collect_contact: true` in a usertest YAML (`create` or `update`) to make the recording app show a name/email form on the final screen. Defaults to false.

## [0.10.0] - 2026-05-14

### Added
- `interviews label <batch_id> --quality <good|review|exclude>` to set a quality indicator on an interview.
- Quality column in `transcripts list` showing each interview's quality label.

## [0.9.0] - 2026-05-14

### Removed
- `gdrive` command group (upload/list). The Google Drive integration was unused; this also drops the `google-auth` and `google-api-python-client` dependencies.

## [0.8.3] - 2026-05-14

### Changed
- Expanded the README with a full command reference, authentication/config docs, and setup notes for the `showreel` and `synth` extras.

## [0.8.2] - 2026-05-14

### Changed
- Enriched PyPI package metadata: added `keywords`, `classifiers`, author email, and a `Changelog` project URL.

## [0.8.1] - 2026-05-13

### Changed
- `projects upload-doc` strips embedded images (base64 reference definitions, inline `![](...)`, reference-style `![][ref]`, and `<img>` tags) before upload. Google-Docs-exported markdown often inlines images as multi-MB base64 blobs; the CLI now prints the count and size reduction.

## [0.8.0] - 2026-05-13

### Added
- `projects upload-doc` attaches a markdown research brief or final report to a project (`--type brief|final`). Enforces a `.md` extension and UTF-8 content.
- `projects get-doc` downloads a project document (`--type brief|agent|final`) to stdout or a file.

## [0.7.0] - 2026-05-12

### Added
- Experimental `synth` command group drives a Playwright-controlled browser through a usertest preview, so an agent (e.g. Claude Code) can play a synthetic participant. Install with `pip install 'podojo-cli[synth]'` and run `playwright install chromium`.

## [0.6.0] - 2026-05-05

### Added
- Background check against PyPI prints an upgrade notice when a newer version is available, with a 24h cache and zero added latency

## [0.5.0] - 2026-05-01

### Added
- `interviews upload` command uploads audio/video interview files to an existing project
- `projects create` command creates a new empty project (uploads now require a pre-existing project, no auto-creation)

## [0.4.5] - 2026-04-25

### Added
- Show interview date/time in `transcripts list` and `videos list` tables

## [0.4.4] - 2026-04-19

### Added
- `usertests snippet` command prints the recorder script to embed in self-hosted prototypes
- `usertests create` now hints at the snippet command so users know how to enable screen recording

## [0.4.3] - 2026-04-14

### Added
- Support `instruction` step variant for usertests (briefing screen with a "Continue" button, useful before prototype steps)

## [0.4.2] - 2026-04-05

### Changed
- Enable attestations in publish workflow for verified PyPI details

## [0.4.1] - 2026-04-05

### Changed
- Add project URLs and author metadata for verified PyPI details

## [0.4.0] - 2026-04-05

### Changed
- Store API key in OS credential store (Keychain/Credential Locker) via keyring instead of plaintext ~/.podojo.toml
- `auth login` now prompts for key with hidden input instead of accepting it as a positional argument

## [0.3.2] - 2026-04-04

### Added
- Support `intro` and `feedback` step variants for usertests

## [0.3.1] - 2026-04-04

### Added
- Auto-publish to PyPI on push to main
- CHANGELOG.md for tracking version history

## [0.3.0] - 2026-04-01

### Changed
- Renamed `sessions` command to `usertests` (breaking change)
- Removed `client` field from usertest commands

### Added
- Show preview and live URLs after `usertest create` and `usertest get`

## [0.2.1] - 2026-03-28

### Changed
- Default `project_name` to session ID on session creation

### Fixed
- Test mocks to match actual API response shape

## [0.2.0] - 2026-03-25

### Added
- `sessions` command for unmoderated test management
- Live status column in sessions list

### Fixed
- Publish workflow permissions for checkout
- Projects list iterating over paginated response dict

## [0.1.0] - 2026-03-20

### Added
- Initial CLI with Typer, httpx, and Rich
- `auth login/logout` commands with API key validation
- `showreel` command with video download
- `gdrive` upload and list commands
- `projects` list command
- PyPI publishing workflow
