import json
import tempfile
import zipfile
from pathlib import Path

from chatgpt_export_cli_converter.cli import main
from chatgpt_export_cli_converter.core import (
    convert_conversation_to_markdown,
    extract_messages,
    generate_filename,
    load_conversations,
    process_conversations,
)


def sample_conversation():
    return {
        "id": "test_conv_001",
        "title": "Python Best Practices",
        "create_time": 1703522622,
        "mapping": {
            "msg_001": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["What are Python best practices?"]},
                },
                "children": ["msg_002"],
                "parent": None,
            },
            "msg_002": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"parts": ["Follow PEP 8 and write tests."]},
                },
                "children": [],
                "parent": "msg_001",
            },
        },
    }


def test_extract_messages():
    messages = extract_messages(sample_conversation()["mapping"])
    assert len(messages) == 2
    assert messages[0]["author"] == "user"
    assert messages[1]["author"] == "assistant"


def test_convert_conversation_to_markdown():
    markdown = convert_conversation_to_markdown(sample_conversation())
    assert "**Created:**" in markdown
    assert "**🧑‍💬 User**" in markdown
    assert "**🤖 Assistant**" in markdown


def test_generate_filename_includes_id():
    filename = generate_filename(sample_conversation())
    assert filename == "[test_conv_001] Python Best Practices.md"


def test_process_conversations_skips_duplicates():
    conversation = sample_conversation()
    results = process_conversations([conversation], {"test_conv_001"})
    assert results["processed"] == 0
    assert results["skipped"] == 1


def test_load_conversations_from_zip():
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "chatgpt-export.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("export/conversations.json", json.dumps([sample_conversation()]))

        loaded = load_conversations(zip_path)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "test_conv_001"


def test_cli_end_to_end():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_path = temp_path / "conversations.json"
        output_dir = temp_path / "ChatGPT"
        input_path.write_text(json.dumps([sample_conversation()]), encoding="utf-8")

        exit_code = main([str(input_path), "--output", str(output_dir)])

        assert exit_code == 0
        files = list(output_dir.glob("*.md"))
        assert len(files) == 1
        assert "test_conv_001" in files[0].name


def test_cli_skips_existing_output_ids():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_path = temp_path / "conversations.json"
        output_dir = temp_path / "ChatGPT"
        output_dir.mkdir()
        (output_dir / "[test_conv_001] Existing.md").write_text("old", encoding="utf-8")
        input_path.write_text(json.dumps([sample_conversation()]), encoding="utf-8")

        exit_code = main([str(input_path), "--output", str(output_dir)])

        assert exit_code == 0
        files = list(output_dir.glob("*.md"))
        assert len(files) == 1


def test_cli_reports_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "0.1.0" in captured.out
