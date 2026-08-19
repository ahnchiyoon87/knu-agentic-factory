"""K-정밀 팩토리 시뮬레이터 — API 서버.

기동:  uv run python -m server.run          (프로젝트 루트에서)
문서:  http://localhost:8000/docs

주의: 시뮬레이션 상태가 프로세스 메모리에 있으므로 반드시 단일 워커로 띄운다.
      (uvicorn --workers 2 이상이면 학생마다 다른 공장을 보게 된다)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .api import agent, control, drill, read, diagnose
from .config import ROOT, get_settings
from .sim.runner import runner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sim")

WEB_DIR: Path = ROOT / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    log.info("설정: %s", s.masked())
    try:
        await db.init_pool()
    except db.DB못붙음 as exc:
        # 역추적을 뱉으면 강사가 무엇을 해야 할지 알 수 없다. 할 말만 남기고 세운다.
        print(str(exc), flush=True)
        raise SystemExit(1) from None
    await runner.start()
    try:
        yield
    finally:
        await runner.stop()
        await db.close_pool()
        log.info("종료 완료")


app = FastAPI(
    title="K-정밀 팩토리 시뮬레이터",
    version="2.0.0",
    description=(
        "경남대 RISE 피지컬AI 사관학교 8월 Agentic AI 특강 · 내 공장\n\n"
        "CNC 설비 6대(EQ-01~EQ-06)와 AMR 2대의 상태가 1초 주기로 변동하며 "
        "옆의 DB 컨테이너에 적재됩니다. 전부 이 컴퓨터 안에서 돕니다.\n\n"
        "제어 API 4종은 교안상 3일차에 개방됩니다."
    ),
    lifespan=lifespan,
)

# 학생이 자기 대시보드를 어디서 띄우든(로컬 파일·다른 포트) 읽을 수 있어야 한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(read.router)
app.include_router(control.router)
app.include_router(diagnose.router)
app.include_router(agent.router)
app.include_router(drill.router)

# 2D 공장 뷰
#   강사 콘솔·자리 배정 API 는 지웠다 — 공장이 학생 PC 에서 하나씩 도는 구조라
#   원격으로 조종할 대상도, 나눠 줄 자리도 없다. 이상 주입은 화면의 버튼이 한다.
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    return RedirectResponse("/view")


@app.get("/view", include_in_schema=False)
async def view() -> FileResponse:
    return FileResponse(WEB_DIR / "view" / "index.html")


