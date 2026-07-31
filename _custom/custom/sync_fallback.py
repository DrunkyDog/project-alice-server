#!/usr/bin/env python3
"""
Phase 1 (WebUI-editable): สร้าง provider config แต่ละตัว (แก้ key ใน WebUI ได้)
+ sync คีย์จาก WebUI configs -> data/llm_fallback.yaml ที่ fallback provider อ่าน

- ORDER = ลำดับชั้น fallback (อ้าง id ของ ai_model_config)
- provider ที่ยังไม่มี key จริง จะถูก fallback ข้ามอัตโนมัติ (placeholder)
- รัน script นี้ซ้ำได้ (idempotent) + ตั้ง cron ให้ auto-sync คีย์ที่แก้ใน WebUI
"""
import subprocess, json, sys, os

DB = "xiaozhi_esp32_server"; DBC = "xiaozhi-esp32-server-db"
COMPOSE = os.path.expanduser("~/xiaozhi-server/docker-compose_all.yml")
YAML_PATH = os.path.expanduser("~/xiaozhi-server/data/llm_fallback.yaml")

# ลำดับชั้น fallback default — ใช้เมื่อ sys_param llm.fallback.order ยังไม่ถูกตั้ง
# (ตอนนี้ Groq ขึ้นก่อน Gemini เพราะ Gemini quota หมดรายวัน ยิงไปก็ 429 เปล่า)
# หมายเหตุ: ผู้ใช้แก้ลำดับเองได้ในหน้า WebUI > Parameter Management > llm.fallback.order
DEFAULT_ORDER = ["LLM_GroqLLM", "LLM_GeminiLiteOAI", "LLM_OpenRouterLLM", "LLM_GeminiOAI",
                 "LLM_GroqLLM8b", "LLM_OpenAILLM", "LLM_ClaudeSonnet", "LLM_OllamaLLM"]
DEFAULT_COOLDOWN = 60  # rate-limit ต่อนาทีฟื้นเร็ว — ไม่ sideline provider นาน

def dbpw():
    for line in open(COMPOSE, encoding="utf-8"):
        if "MYSQL_ROOT_PASSWORD" in line:
            return line.split("=",1)[-1].split(":",1)[-1].strip().strip('"')
    sys.exit("no pw")
PW = dbpw()

def mysql(sql, chk=True):
    p = subprocess.run(["docker","exec","-i",DBC,"mysql","--default-character-set=utf8mb4",
        "-uroot",f"-p{PW}","-N",DB], input=sql, capture_output=True, text=True)
    err = "\n".join(l for l in p.stderr.splitlines() if "Using a password" not in l).strip()
    if chk and err: sys.exit(f"MySQL error: {err}")
    return p.stdout.strip()

def upsert_config(cfg_id, model_code, model_name, config_obj, remark):
    hx = json.dumps(config_obj, ensure_ascii=False).encode("utf-8").hex()
    rhx = remark.encode("utf-8").hex()
    nhx = model_name.encode("utf-8").hex()
    mysql(f'''INSERT INTO ai_model_config
      (id, model_type, model_code, model_name, is_default, is_enabled, config_json, remark, sort, create_date, update_date)
      VALUES ("{cfg_id}","LLM","{model_code}",CONVERT(UNHEX("{nhx}") USING utf8mb4),0,1,
        CONVERT(UNHEX("{hx}") USING utf8mb4),CONVERT(UNHEX("{rhx}") USING utf8mb4),50,NOW(),NOW())
      ON DUPLICATE KEY UPDATE update_date=NOW();''')  # ถ้ามีแล้วไม่ทับ key ที่ user ตั้ง

# --- 1) provider configs ที่ต้องมี (สร้างถ้ายังไม่มี — ไม่ทับของเดิม) ---
groq_key = mysql('SELECT JSON_UNQUOTE(JSON_EXTRACT(config_json,"$.api_key")) FROM ai_model_config WHERE id="ASR_GroqASR";')
gemini_key = mysql('SELECT JSON_UNQUOTE(JSON_EXTRACT(config_json,"$.api_key")) FROM ai_model_config WHERE id="LLM_GeminiLLM";')
NEW = [
    ("LLM_GeminiOAI","GeminiOAI","Gemini 2.5 Flash (OpenAI-compat)",
     {"type":"openai","api_key":gemini_key,"base_url":"https://generativelanguage.googleapis.com/v1beta/openai/",
      "model_name":"gemini-2.5-flash","max_tokens":2048},"Gemini ผ่าน openai-compat (native พัง timeout)"),
    ("LLM_GeminiLiteOAI","GeminiLiteOAI","Gemini 2.5 Flash-Lite (เร็ว, bucket แยก)",
     {"type":"openai","api_key":gemini_key,"base_url":"https://generativelanguage.googleapis.com/v1beta/openai/",
      "model_name":"gemini-2.5-flash-lite","max_tokens":2048},"Gemini Lite — free quota แยกจาก 2.5-flash"),
    ("LLM_GroqLLM","GroqLLM","Groq Llama 3.3 70B",
     {"type":"openai","api_key":groq_key,"base_url":"https://api.groq.com/openai/v1",
      "model_name":"llama-3.3-70b-versatile","max_tokens":2048},"Groq 70B (ฟรี เร็ว) — reuse ASR key"),
    ("LLM_GroqLLM8b","GroqLLM8b","Groq Llama 3.1 8B (fast)",
     {"type":"openai","api_key":groq_key,"base_url":"https://api.groq.com/openai/v1",
      "model_name":"llama-3.1-8b-instant","max_tokens":2048},"Groq 8B — TPM สูง bucket แยกจาก 70B"),
    ("LLM_OpenRouterLLM","OpenRouterLLM","OpenRouter (free models)",
     {"type":"openai","api_key":"YOUR_OPENROUTER_KEY","base_url":"https://openrouter.ai/api/v1",
      "model_name":"meta-llama/llama-3.3-70b-instruct:free","max_tokens":2048},"OpenRouter — เติม key ใน WebUI"),
    ("LLM_OpenAILLM","OpenAILLM","OpenAI GPT-4o-mini",
     {"type":"openai","api_key":"YOUR_OPENAI_KEY","base_url":"https://api.openai.com/v1",
      "model_name":"gpt-4o-mini","max_tokens":2048},"OpenAI — เติม key ใน WebUI"),
]
existing = set(mysql('SELECT id FROM ai_model_config WHERE model_type="LLM";').split("\n"))
for cid, code, name, obj, rmk in NEW:
    if cid in existing:
        print(f"  [skip] {cid} มีอยู่แล้ว (ไม่ทับ key ที่ตั้งใน WebUI)")
    else:
        upsert_config(cid, code, name, obj, rmk)
        print(f"  [create] {cid} ({name})")

# --- 1.5) seed sys_params (เมนูใน WebUI: สลับลำดับ + ตั้ง cooldown เองได้) ---
def seed_param(code, value, remark):
    if mysql(f'SELECT 1 FROM sys_params WHERE param_code="{code}";'):
        return  # มีแล้ว ไม่ทับค่าที่ผู้ใช้แก้ใน WebUI
    nid = mysql('SELECT IFNULL(MAX(id),0)+1 FROM sys_params;')
    vhx = value.encode("utf-8").hex(); rhx = remark.encode("utf-8").hex()
    mysql(f'INSERT INTO sys_params (id, param_code, param_value, value_type, param_type, remark, create_date, update_date) '
          f'VALUES ({nid}, "{code}", CONVERT(UNHEX("{vhx}") USING utf8mb4), "string", 1, CONVERT(UNHEX("{rhx}") USING utf8mb4), NOW(), NOW());')
    print(f"  [seed] sys_param {code}")

seed_param("llm.fallback.order", ";".join(DEFAULT_ORDER),
           "ลำดับชั้น LLM fallback (id คั่นด้วย ;) แก้เพื่อสลับ provider หลัก/ปิดตัวที่ไม่ใช้")
seed_param("llm.fallback.cooldown", str(DEFAULT_COOLDOWN),
           "วินาทีพัก provider ที่ล่มก่อนลองใหม่ (rate-limit ต่อนาที ~60)")

# อ่านค่าจริงจาก sys_param (ผู้ใช้แก้ใน WebUI > Parameter Management)
_ord = mysql('SELECT param_value FROM sys_params WHERE param_code="llm.fallback.order";')
ORDER = [x.strip() for x in _ord.replace("\n", ";").replace(",", ";").split(";") if x.strip()] or DEFAULT_ORDER
_cd = mysql('SELECT param_value FROM sys_params WHERE param_code="llm.fallback.cooldown";')
COOLDOWN = int(_cd) if _cd and _cd.strip().isdigit() else DEFAULT_COOLDOWN

# --- 2) sync: อ่าน config ของแต่ละ id ตาม ORDER -> เขียน yaml ---
print(f"[order] {ORDER}  cooldown={COOLDOWN}s")
providers = []
for cid in ORDER:
    row = mysql(f'SELECT CONVERT(config_json USING utf8mb4) FROM ai_model_config WHERE id="{cid}" AND is_enabled=1;')
    if not row:
        print(f"  [warn] {cid} ไม่มี/ปิดอยู่ — ข้าม"); continue
    c = json.loads(row)
    providers.append({
        "label": cid, "type": c.get("type","openai"),
        "api_key": c.get("api_key",""), "base_url": c.get("base_url",""),
        "model_name": c.get("model_name",""), "max_tokens": c.get("max_tokens",2048),
    })

import yaml
with open(YAML_PATH,"w",encoding="utf-8") as f:
    yaml.safe_dump({"cooldown_seconds":COOLDOWN,"providers":providers}, f, allow_unicode=True, sort_keys=False)
os.chmod(YAML_PATH, 0o600)

active = [p["label"] for p in providers if not str(p["api_key"]).lower().startswith("your_") and p["api_key"]]
skip = [p["label"] for p in providers if str(p["api_key"]).lower().startswith("your_") or not p["api_key"]]
print(f"[sync] เขียน yaml {len(providers)} ชั้น | ใช้งาน(มี key)={active} | ต้องเติม key ใน WebUI={skip}")
