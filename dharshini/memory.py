from __future__ import annotations
import sqlite3
from datetime import datetime,timezone
from pathlib import Path

class MemoryStore:
    def __init__(self,db_path:str):
        p=Path(db_path);p.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(p,check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY,key TEXT UNIQUE,value TEXT,updated_at TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY,event TEXT,detail TEXT,created_at TEXT)")
        self.db.commit()
    def remember(self,key,value):
        self.db.execute("INSERT INTO memories(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(key,value,datetime.now(timezone.utc).isoformat()));self.db.commit()
    def recall(self,key):
        row=self.db.execute("SELECT value FROM memories WHERE key=?",(key,)).fetchone();return row[0] if row else None
    def all_memories(self): return self.db.execute("SELECT key,value FROM memories ORDER BY key").fetchall()
    def event(self,event,detail=""):
        self.db.execute("INSERT INTO events(event,detail,created_at) VALUES(?,?,?)",(event,detail,datetime.now(timezone.utc).isoformat()));self.db.commit()
    def close(self):self.db.close()
