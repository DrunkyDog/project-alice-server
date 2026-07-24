#!/usr/bin/env python3
"""
ผูก alice-edge Worker เข้ากับ Project-ALICE
  1) ลงทะเบียน plugin SYSTEM_PLUGIN_KNOWLEDGE (search_knowledge) + map เข้า agent
  2) ตั้ง Context Provider ชี้ไป /context
idempotent — รันซ้ำได้
"""
import subprocess, sys, os, json, uuid

DB = "xiaozhi_esp32_server"; DBC = "xiaozhi-esp32-server-db"
COMPOSE = os.path.expanduser("~/xiaozhi-server/docker-compose_all.yml")
WORKER = "https://alice-edge.atty-dhamanoon.workers.dev"
ALICE_KEY = os.environ["ALICE_KEY"]

PW = [l.split("=", 1)[-1].split(":", 1)[-1].strip().strip('"')
      for l in open(COMPOSE, encoding="utf-8") if "MYSQL_ROOT_PASSWORD" in l][0]


def q(sql, quiet=False):
    p = subprocess.run(["docker", "exec", "-i", DBC, "mysql", "--default-character-set=utf8mb4",
                        "-uroot", f"-p{PW}", "-N", DB], input=sql, capture_output=True, text=True)
    err = "\n".join(l for l in p.stderr.splitlines() if "Using a password" not in l).strip()
    if err and not quiet:
        sys.exit("MySQL error: " + err)
    return p.stdout.strip()


def hx(s):
    return s.encode("utf-8").hex()


agent_id = q("SELECT id FROM ai_agent LIMIT 1;")
print(f"[agent] {agent_id}")

# ── 1) provider row ────────────────────────────────────────────────────────────
PID = "SYSTEM_PLUGIN_KNOWLEDGE"
fields = [
    {"key": "endpoint", "type": "string", "label": "Worker endpoint (/knowledge/query)",
     "default": f"{WORKER}/knowledge/query", "editing": False, "selected": False},
    {"key": "api_key", "type": "string", "label": "x-alice-key",
     "default": "", "editing": False, "selected": False},
    {"key": "top_k", "type": "string", "label": "จำนวน chunk ที่ดึง",
     "default": "5", "editing": False, "selected": False},
    {"key": "min_score", "type": "string", "label": "คะแนนขั้นต่ำ (0-1)",
     "default": "0.35", "editing": False, "selected": False},
]
if q(f"SELECT 1 FROM ai_model_provider WHERE id='{PID}';"):
    print(f"[skip] provider {PID} มีอยู่แล้ว")
else:
    q(f'''INSERT INTO ai_model_provider (id, model_type, provider_code, name, fields, sort, create_date, update_date)
          VALUES ("{PID}","Plugin","search_knowledge",
                  CONVERT(UNHEX("{hx('คลังความรู้ ALICE (Vectorize)')}") USING utf8mb4),
                  CONVERT(UNHEX("{hx(json.dumps(fields, ensure_ascii=False))}") USING utf8mb4),
                  90, NOW(), NOW());''')
    print(f"[ok] สร้าง provider {PID}")

# ── 2) map plugin เข้า agent ───────────────────────────────────────────────────
param = {"endpoint": f"{WORKER}/knowledge/query", "api_key": ALICE_KEY,
         "top_k": "5", "min_score": "0.35"}
if q(f"SELECT 1 FROM ai_agent_plugin_mapping WHERE agent_id='{agent_id}' AND plugin_id='{PID}';"):
    q(f'''UPDATE ai_agent_plugin_mapping
          SET param_info=CONVERT(UNHEX("{hx(json.dumps(param, ensure_ascii=False))}") USING utf8mb4)
          WHERE agent_id="{agent_id}" AND plugin_id="{PID}";''')
    print("[ok] อัปเดต param ของ plugin mapping เดิม")
else:
    mid = str(int(uuid.uuid4().int % 9_000_000_000_000_000_000) + 1_000_000_000_000_000_000)
    q(f'''INSERT INTO ai_agent_plugin_mapping (id, agent_id, plugin_id, param_info)
          VALUES ({mid}, "{agent_id}", "{PID}",
                  CONVERT(UNHEX("{hx(json.dumps(param, ensure_ascii=False))}") USING utf8mb4));''')
    print("[ok] เปิดใช้ plugin search_knowledge ให้ agent แล้ว")

# ── 3) context provider ────────────────────────────────────────────────────────
providers = [{"url": f"{WORKER}/context", "headers": {"x-alice-key": ALICE_KEY}}]
pj = hx(json.dumps(providers, ensure_ascii=False))
row = q(f"SELECT id FROM ai_agent_context_provider WHERE agent_id='{agent_id}';")
if row:
    q(f'''UPDATE ai_agent_context_provider
          SET context_providers=CONVERT(UNHEX("{pj}") USING utf8mb4), updated_at=NOW()
          WHERE id="{row}";''')
    print(f"[ok] ตั้ง context provider (row {row})")
else:
    cid = uuid.uuid4().hex
    q(f'''INSERT INTO ai_agent_context_provider (id, agent_id, context_providers, created_at, updated_at)
          VALUES ("{cid}", "{agent_id}", CONVERT(UNHEX("{pj}") USING utf8mb4), NOW(), NOW());''')
    print(f"[ok] สร้าง context provider (row {cid})")

print("\n[verify]")
print("  plugins:", q(f"SELECT plugin_id FROM ai_agent_plugin_mapping WHERE agent_id='{agent_id}';").replace("\n", ", "))
print("  context:", q(f"SELECT CONVERT(context_providers USING utf8mb4) FROM ai_agent_context_provider WHERE agent_id='{agent_id}';")[:120])
