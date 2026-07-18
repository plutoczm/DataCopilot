import os
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from backend.app.core.constants import APP_VERSION
from backend.app.core.settings import Settings
from backend.app.domain.ports.llm_provider import LLMProvider
from backend.app.domain.ports.vector_store import VectorStore
from backend.app.infrastructure.vectorstore.exceptions import CollectionNotFoundError
from backend.app.presentation.api.dependencies.providers import (
    DEFAULT_KNOWLEDGE_COLLECTION,
    get_app_settings,
    get_llm_provider,
    get_vector_store,
)
from backend.app.presentation.api.schemas.health import (
    HealthResponse,
    ProviderHealthResponse,
    RootResponse,
    VectorStoreHealthResponse,
)


router = APIRouter(tags=["Health"])


_VERCEL_CONSOLE_FALLBACK = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>DataPilot-AI</title><style>body{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;max-width:900px;margin:40px auto;padding:0 20px;background:#07111f;color:#ecf5ff}a{color:#5ba7ff}section{background:#102540;border:1px solid #27415f;border-radius:14px;padding:20px;margin:16px 0}textarea{width:100%;min-height:130px;background:#0a1a2e;color:#ecf5ff;border:1px solid #27415f;border-radius:8px;padding:10px;box-sizing:border-box}button{margin-top:10px;padding:10px 16px;border:0;border-radius:8px;background:#45d6b0;color:#04121d;font-weight:700;cursor:pointer}pre{white-space:pre-wrap;background:#06101e;border-radius:8px;padding:12px;overflow:auto}</style></head>
<body><h1>DataPilot-AI 数据工程智能工作台</h1><p>公网 API 已启动。你可以直接使用下面的 Agent 问答，或打开 <a href="/docs">Swagger 文档</a>。</p>
<section><h2>Agent 问答</h2><textarea id="q">什么是 Spark AQE？</textarea><br><button onclick="ask()">发送</button><pre id="r">等待输入…</pre></section>
<p><a href="/docs">API 文档</a> · <a href="/openapi.json">OpenAPI</a> · <a href="/health">健康检查</a></p>
<script>async function ask(){const r=document.getElementById('r');r.textContent='处理中…';try{const x=await fetch('/api/v1/agent/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:document.getElementById('q').value,engine:'hive',collection_name:'knowledge_base',top_k:5,use_rag:true})});const t=await x.text();r.textContent=x.ok?JSON.stringify(JSON.parse(t),null,2):t}catch(e){r.textContent='请求失败：'+e.message}}</script></body></html>"""


@router.get(
    "/",
    response_model=None,
    summary="Service metadata",
    description="Return service metadata and API documentation links.",
)
def root(settings: Settings = Depends(get_app_settings)) -> RootResponse | FileResponse | RedirectResponse:
    if os.getenv("DATACOPILOT_WEB_CONSOLE", "").lower() in {"1", "true", "yes"}:
        project_root = Path(__file__).resolve().parents[5]
        public_path = project_root / "public" / "index.html"
        if public_path.exists():
            return FileResponse(public_path)
        # Vercel serves public/ through its CDN, while the Python function
        # bundle may not contain that file. Redirect to the CDN copy so the
        # full console is used instead of the small emergency fallback.
        return RedirectResponse(url="/index.html")
    return RootResponse(
        service=settings.app.name,
        version=APP_VERSION,
        status="running",
        docs="/docs",
        openapi="/openapi.json",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health",
    description="Validate application, LLM provider, and vector store status.",
)
async def health(
    settings: Settings = Depends(get_app_settings),
    llm_provider: LLMProvider = Depends(get_llm_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> HealthResponse:
    llm_status = await llm_provider.health_check()
    try:
        stats = vector_store.collection_stats(DEFAULT_KNOWLEDGE_COLLECTION)
        vector_status = "ok"
        document_count = stats.document_count
    except CollectionNotFoundError:
        vector_status = "missing"
        document_count = 0
    return HealthResponse(
        service=settings.app.name,
        status="ok" if llm_status.ok and vector_status == "ok" else "degraded",
        environment=settings.environment.value,
        llm_provider=ProviderHealthResponse(**llm_status.model_dump(exclude={"latency_ms"})),
        vector_store=VectorStoreHealthResponse(
            status=vector_status,
            collection_name=DEFAULT_KNOWLEDGE_COLLECTION,
            document_count=document_count,
        ),
    )
