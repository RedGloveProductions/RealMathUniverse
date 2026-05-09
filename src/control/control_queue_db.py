from __future__ import annotations
import json, os, tempfile, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

def atomic_write_json(path: Path, payload: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    tmp_path=Path(tmp)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(payload,f,indent=2,sort_keys=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            try: tmp_path.unlink()
            except OSError: pass

def read_json(path: Path, default=None):
    if default is None: default={}
    try:
        if not path.exists(): return default
        data=json.loads(path.read_text())
        return data if isinstance(data, dict) else default
    except Exception:
        return default

def clamp(v, lo, hi): return max(lo, min(hi, v))
def safe_float(x, d=0.0):
    try: return float(x)
    except Exception: return d
def safe_int(x, d=0):
    try: return int(float(x))
    except Exception: return d

import sqlite3, time
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp_utc TEXT NOT NULL,source TEXT NOT NULL,channel TEXT NOT NULL,domain TEXT NOT NULL,raw_voltage REAL NOT NULL,stepped_value INTEGER NOT NULL,label TEXT NOT NULL,consumed INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_events_domain_consumed_id ON events(domain, consumed, id);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
"""
def connect(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True); conn=sqlite3.connect(str(db_path), timeout=5.0); conn.executescript(SCHEMA_SQL); conn.commit(); return conn
def get_meta(conn,key,default=''):
    row=conn.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone(); return row[0] if row else default
def set_meta(conn,key,value): conn.execute('INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)',(key,value)); conn.commit()
def label_for(domain,value):
    if domain=='behavior': return {0:'none',1:'stable_orbit',2:'radial_flow',3:'orbital_flow',4:'turbulence_flow',5:'black_hole_capture',6:'shell_boundary',7:'species_controlled'}.get(value,f'behavior_{value}')
    if domain=='field': return {0:'manual_default',1:'radial_focus',2:'orbital_focus',3:'vertical_focus',4:'turbulence_focus',5:'shell_focus',6:'full_hybrid',7:'species_driven'}.get(value,f'field_{value}')
    return f'{domain}_{value}'
def insert_event(conn, source, channel, domain, raw_voltage, stepped_value, dedupe=True, min_interval_ms=250):
    if dedupe:
        last=conn.execute('SELECT stepped_value FROM events WHERE domain=? ORDER BY id DESC LIMIT 1',(domain,)).fetchone()
        if last and int(last[0])==int(stepped_value): return None
    key=f'last_insert_ms_{domain}'; cur=int(time.time()*1000); last=int(get_meta(conn,key,'0') or '0')
    if cur-last < min_interval_ms: return None
    conn.execute('INSERT INTO events(timestamp_utc,source,channel,domain,raw_voltage,stepped_value,label,consumed) VALUES(?,?,?,?,?,?,?,0)',(utc_now_iso(),source,channel,domain,float(raw_voltage),int(stepped_value),label_for(domain,int(stepped_value))))
    set_meta(conn,key,str(cur)); conn.commit(); return conn.execute('SELECT last_insert_rowid()').fetchone()[0]
def next_unconsumed(conn,domain): return conn.execute('SELECT id,stepped_value,label,timestamp_utc FROM events WHERE domain=? AND consumed=0 ORDER BY id ASC LIMIT 1',(domain,)).fetchone()
def consume_next(conn,domain):
    row=next_unconsumed(conn,domain)
    if not row: return None
    conn.execute('UPDATE events SET consumed=1 WHERE id=?',(row[0],)); conn.commit(); return row
def step_relative(conn,domain,current_id,delta):
    if delta>=0: return conn.execute('SELECT id,stepped_value,label,timestamp_utc FROM events WHERE domain=? AND id>? ORDER BY id ASC LIMIT 1',(domain,current_id)).fetchone()
    return conn.execute('SELECT id,stepped_value,label,timestamp_utc FROM events WHERE domain=? AND id<? ORDER BY id DESC LIMIT 1',(domain,current_id)).fetchone()
def stats(conn):
    out={}
    for domain in ['behavior','field','behavior_gate_deprecated']:
        total=conn.execute('SELECT COUNT(*) FROM events WHERE domain=?',(domain,)).fetchone()[0]; pending=conn.execute('SELECT COUNT(*) FROM events WHERE domain=? AND consumed=0',(domain,)).fetchone()[0]; last=conn.execute('SELECT id,stepped_value,label FROM events WHERE domain=? ORDER BY id DESC LIMIT 1',(domain,)).fetchone(); out[domain]={'total':total,'pending':pending,'last':list(last) if last else None}
    return out
