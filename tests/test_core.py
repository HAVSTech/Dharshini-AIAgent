from pathlib import Path
from dharshini.memory import MemoryStore
from dharshini.safety import SafetyManager
from dharshini.tools.registry import TOOLS, declarations

def test_memory_round_trip(tmp_path: Path):
    store=MemoryStore(str(tmp_path/"memory.db"))
    store.remember("name","Hari")
    assert store.recall("name")=="Hari"
    store.event("test","ok")
    assert ("name","Hari") in store.all_memories()
    store.close()

def test_safety_defaults_to_confirmation():
    manager=SafetyManager(True)
    assert manager.check("SAFE").allowed
    assert not manager.check("CONFIRM").allowed
    assert not manager.check("BLOCKED").allowed

def test_registry():
    assert {"open_app","open_url","open_folder","system_info","take_screenshot"}==set(TOOLS)
    assert {x["name"] for x in declarations()}==set(TOOLS)
