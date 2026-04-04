# Changelog

All notable changes to the Podojo CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and this project adheres to [Semantic Versioning](https://semver.org).

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
