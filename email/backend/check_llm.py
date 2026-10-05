"""Quick check that your LLM key works:   cd backend && python check_llm.py"""
from app.config import settings
from app.services import llm

prov = llm.resolve_provider()
print(f"Provider : {prov or 'NONE (heuristic only - no API key found in backend/.env)'}")
if prov:
    print(f"Model    : {llm._model_for(prov)}")
    try:
        data, info = llm.complete_json('Reply ONLY with JSON like {"ok": true}.', "ping")
        print(f"OK       : {data}  (used model {info.model}, {info.latency_ms} ms)")
    except Exception as exc:
        print(f"FAILED   : {exc}")
