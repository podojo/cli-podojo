"""Synthetic usertest support: Playwright-backed browser primitives.

The driver runs as a background subprocess that reads commands from a JSON
file and writes state (URL, DOM text, buttons, screenshot path) to another
JSON file. The CLI commands in podojo_cli.commands.synth issue commands and
print the resulting state, so Claude Code can drive a usertest in a loop.
"""
