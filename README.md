# ChatGPT Export CLI Converter

Local-first CLI for converting ChatGPT exports into Markdown files.

## Scope

- Input: ChatGPT export ZIP or `conversations.json`
- Output: one Markdown file per conversation
- Goal: clean, predictable Markdown for Obsidian or other file-based workflows

## Usage

Install locally first:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

Then run:

```bash
chatgpt-export ~/Downloads/chatgpt-export.zip --output ChatGPT
```

```bash
chatgpt-export conversations.json --output ChatGPT
```

If no input is provided, the CLI prompts for the export path.

You can also run it without installing:

```bash
PYTHONPATH=src python3 -m chatgpt_export_cli_converter conversations.json --output ChatGPT
```

## Behavior

- sorts conversations oldest first
- skips conversations already written to the output directory
- uses filenames prefixed with the conversation ID for stable dedupe
- filters broken inline citation artifacts from exported text
- keeps output local on disk

Example filename:

```text
[abc123] My Conversation Title.md
```

## Development

```bash
PYTHONPATH=src python3 -m pytest -q
```
