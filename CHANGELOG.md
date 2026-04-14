# Changelog

All notable changes to the Podojo CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org).

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
