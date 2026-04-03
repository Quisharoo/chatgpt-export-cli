"""Core conversion logic."""

from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set


def extract_messages(mapping: Optional[Dict]) -> List[Dict[str, str]]:
    """Flatten the primary message chain from a ChatGPT export mapping."""
    if not isinstance(mapping, dict) or not mapping:
        return []

    root_id = _find_root_message(mapping)
    if not root_id:
        return []

    messages: List[Dict[str, str]] = []
    visited = set()
    current_id = root_id

    while current_id and current_id not in visited:
        visited.add(current_id)
        node = mapping.get(current_id, {})
        message = node.get("message", {})

        if message and message.get("content"):
            text = _extract_text_content(message.get("content"))
            if text.strip():
                messages.append(
                    {
                        "author": message.get("author", {}).get("role", "unknown"),
                        "content": text.strip(),
                    }
                )

        children = node.get("children", [])
        current_id = children[0] if children else None

    return messages


def clean_citation_artifacts(content: str) -> str:
    """Remove broken inline citation artifacts emitted in some ChatGPT exports."""
    cleaned = content
    cleaned = re.sub(
        r"[\ue000-\uf8ff]*(?:cite|navlist)[\ue000-\uf8ff]*.*?turn\d+(?:search|news)\d+[\ue000-\uf8ff]*\.?",
        "",
        cleaned,
    )
    cleaned = re.sub(r"turn\d+(?:search|news)\d+[\ue000-\uf8ff]*\.?", "", cleaned)
    cleaned = re.sub(r"turn\d+(?:search|news)\d+\.?", "", cleaned)
    cleaned = re.sub(r"[\ue000-\uf8ff]+", "", cleaned)
    return cleaned


def convert_conversation_to_markdown(conversation: Dict) -> str:
    """Convert a single ChatGPT conversation to Markdown."""
    created = datetime.fromtimestamp(conversation.get("create_time", 0))
    messages = extract_messages(conversation.get("mapping", {}))

    lines = [
        f"**Created:** {created.strftime('%Y-%m-%d, %H:%M:%S')}",
        "",
        "---",
        "",
    ]

    for message in messages:
        author = "**🧑‍💬 User**" if message["author"] == "user" else "**🤖 Assistant**"
        lines.append(author)
        lines.append("")
        lines.extend(_format_blockquote(message["content"]))
        lines.append("")

    return clean_citation_artifacts("\n".join(lines))


def generate_filename(conversation: Dict, existing_filenames: Optional[Sequence[str]] = None) -> str:
    """Generate a stable, readable filename."""
    existing_filenames = existing_filenames or []
    title = _clean_filename(conversation.get("title", "Untitled Conversation")) or "Conversation"
    conversation_id = conversation.get("id", "unknown")
    filename = f"[{conversation_id}] {title}.md"

    counter = 2
    while filename in existing_filenames:
        filename = f"[{conversation_id}] {title} ({counter}).md"
        counter += 1

    return filename


def get_existing_conversation_ids(output_dir: Path) -> Set[str]:
    """Read IDs already present in the output directory."""
    existing_ids = set()
    if not output_dir.exists():
        return existing_ids

    for file_path in output_dir.glob("*.md"):
        stem = file_path.stem
        if stem.startswith("[") and "] " in stem:
            existing_ids.add(stem[1:].split("]", 1)[0])

    return existing_ids


def load_conversations(input_path: Path) -> List[Dict]:
    """Load ChatGPT conversations from JSON or ZIP."""
    if not input_path.exists():
        raise FileNotFoundError(f"{input_path} not found")

    if input_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(input_path, "r") as archive:
            member = next((name for name in archive.namelist() if Path(name).name == "conversations.json"), None)
            if not member:
                raise FileNotFoundError(f"No conversations.json found inside {input_path.name}")
            with archive.open(member, "r") as handle:
                data = json.loads(handle.read().decode("utf-8"))
    else:
        data = json.loads(input_path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise ValueError("Expected a list of conversations")
    return [item for item in data if isinstance(item, dict)]


def process_conversations(conversations: Iterable[Dict], processed_ids: Optional[Set[str]] = None) -> Dict:
    """Convert conversations into in-memory file records."""
    processed_ids = set(processed_ids or set())
    results = {"processed": 0, "skipped": 0, "errors": 0, "files": []}
    used_filenames: List[str] = []

    valid = [conversation for conversation in conversations if isinstance(conversation, dict)]
    for conversation in sorted(valid, key=lambda item: item.get("create_time", 0)):
        conversation_id = conversation.get("id")
        if not conversation_id:
            results["errors"] += 1
            continue

        if conversation_id in processed_ids:
            results["skipped"] += 1
            continue

        results["files"].append(
            {
                "filename": generate_filename(conversation, used_filenames),
                "content": convert_conversation_to_markdown(conversation),
                "title": conversation.get("title", "Untitled"),
                "conversation_id": conversation_id,
            }
        )
        used_filenames.append(results["files"][-1]["filename"])
        processed_ids.add(conversation_id)
        results["processed"] += 1

    return results


def write_markdown_files(results: Dict, output_dir: Path) -> List[Path]:
    """Write converted markdown files to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for file_data in results["files"]:
        path = output_dir / file_data["filename"]
        path.write_text(file_data["content"], encoding="utf-8")
        written.append(path)
    return written


def _find_root_message(mapping: Dict) -> Optional[str]:
    for message_id, node in mapping.items():
        if node.get("parent") is None and node.get("message"):
            return message_id
    for message_id, node in mapping.items():
        if node.get("message", {}).get("content"):
            return message_id
    return None


def _extract_text_content(content: object) -> str:
    if isinstance(content, dict):
        parts = content.get("parts", [])
        if isinstance(parts, list):
            return "".join(part for part in parts if isinstance(part, str))
        return ""
    if isinstance(content, str):
        return content
    return ""


def _format_blockquote(content: str) -> List[str]:
    return [">" if line.strip() == "" else f"> {line}" for line in content.splitlines()]


def _clean_filename(text: str) -> str:
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    text = re.sub(r"[^\w\s.-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:100]
