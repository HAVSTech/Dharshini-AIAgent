from pathlib import Path

from dharshini.memory import MemoryStore
from dharshini.safety import SafetyManager
from dharshini.tools.printer import STANDARD_PAPERS_MM, SUPPORTED_EXTENSIONS
from dharshini.tools.registry import TOOLS, declarations


def test_memory_round_trip(tmp_path: Path):
    store = MemoryStore(str(tmp_path / "memory.db"))
    store.remember("name", "Hari")
    assert store.recall("name") == "Hari"
    store.event("test", "ok")
    assert ("name", "Hari") in store.all_memories()
    store.close()


def test_safety_defaults_to_confirmation():
    manager = SafetyManager(True)
    assert manager.check("SAFE").allowed
    assert not manager.check("CONFIRM").allowed
    assert not manager.check("BLOCKED").allowed


def test_registry():
    expected = {
        "open_app",
        "open_url",
        "open_folder",
        "system_info",
        "take_screenshot",
        "printer_status",
        "printer_capabilities",
        "list_printers",
        "default_printer",
        "print_file",
        "print_folder",
    }
    assert expected == set(TOOLS)
    assert {x["name"] for x in declarations()} == expected


def test_printer_file_types():
    assert {".pdf", ".doc", ".docx", ".xls", ".xlsx"} == SUPPORTED_EXTENSIONS


def test_standard_paper_sizes():
    assert STANDARD_PAPERS_MM["a4"] == (210, 297)
    assert STANDARD_PAPERS_MM["letter"] == (216, 279)
