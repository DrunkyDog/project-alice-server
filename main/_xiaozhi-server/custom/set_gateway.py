#!/usr/bin/env python3
"""
ชี้ base_url ของ LLM providers ทั้งหมดไปที่ Cloudflare AI Gateway (project-alice)
- แก้ที่ MySQL (ต้นทาง) เพราะ cron sync_fallback.py จะ regenerate yaml ทุก 10 นาที
- แตะเฉพาะ model_type='LLM' (ไม่ยุ่ง ASR/TTS)
- idempotent: รันซ้ำได้
- --revert เพื่อย้อนกลับเป็น direct
"""
import subprocess, json, sys, os

DB = "xiaozhi_esp32_server"; DBC = "xiaozhi-esp32-server-db"
COMPOSE = os.path.expanduser("~/xiaozhi-server/docker-compose_all.yml")
ACCT = "3eb6d55cb9325ff1311202b66fca4ff3"
GW = f"https://gateway.ai.cloudflare.com/v1/{ACCT}/project-alice"

MAP = {
    "https://api.groq.com/openai/v1": f"{GW}/groq",
    "https://generativelanguage.googleapis.com/v1beta/openai/": f"{GW}/google-ai-studio/v1beta/openai/",
    "https://openrouter.ai/api/v1": f"{GW}/openrouter/v1",
    "https://api.openai.com/v1": f"{GW}/openai",
    "https://api.anthropic.com/v1": f"{GW}/anthropic/v1",
}
REVERT = {v: k for k, v in MAP.items()}


def dbpw():
    for line in open(COMPOSE, encoding="utf-8"):
        if "MYSQL_ROOT_PASSWORD" in line:
            return line.split("=", 1)[-1].split(":", 1)[-1].strip().strip('"')
    sys.exit("no pw")


PW = dbpw()


def mysql(sql, chk=True):
    p = subprocess.run(["docker", "exec", "-i", DBC, "mysql", "--default-character-set=utf8mb4",
                        "-uroot", f"-p{PW}", "-N", DB], input=sql, capture_output=True, text=True)
    err = "\n".join(l for l in p.stderr.splitlines() if "Using a password" not in l).strip()
    if chk and err:
        sys.exit(f"MySQL error: {err}")
    return p.stdout.strip()


table = REVERT if "--revert" in sys.argv else MAP
mode = "REVERT -> direct" if "--revert" in sys.argv else "APPLY -> AI Gateway"
print(f"[mode] {mode}")

rows = mysql('SELECT id, JSON_UNQUOTE(JSON_EXTRACT(config_json,"$.base_url")) '
             'FROM ai_model_config WHERE model_type="LLM";')
changed = 0
for line in rows.split("\n"):
    if not line.strip():
        continue
    cid, cur = (line.split("\t") + [""])[:2]
    new = table.get(cur)
    if not new:
        print(f"  [skip] {cid:22s} {cur}")
        continue
    hx = json.dumps(new).encode("utf-8").hex()
    mysql(f'UPDATE ai_model_config SET config_json=JSON_SET(config_json,"$.base_url",'
          f'JSON_UNQUOTE(CONVERT(UNHEX("{hx}") USING utf8mb4))), update_date=NOW() WHERE id="{cid}";')
    print(f"  [ok]   {cid:22s} {cur}\n         -> {new}")
    changed += 1

print(f"[done] แก้ {changed} รายการ")
if changed:
    print("[next] รัน: cd ~/xiaozhi-server && python3 custom/sync_fallback.py && docker restart xiaozhi-esp32-server")
