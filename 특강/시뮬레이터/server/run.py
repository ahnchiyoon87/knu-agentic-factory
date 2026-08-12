"""기동 진입점 — python -m server.run

시뮬레이션 상태가 메모리에 있으므로 워커는 반드시 1개다.

기동에 실패하면 **역추적 대신 사람이 읽을 말**만 남긴다.
강의장에서 파이썬 스택트레이스를 보고 대응할 수 있는 사람은 없다.
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 안내문이 깨져 죽는 것을 막는다 ────────────────
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import asyncio
import sys

import uvicorn

from server.app import db
from server.app.config import get_settings


def _먼저_확인() -> None:
    """서버를 띄우기 전에 DB 부터 두들겨 본다.

    uvicorn 안에서 실패하면 안내문이 역추적에 파묻혀 안 보인다.
    그래서 여기서 먼저 붙어 보고, 안 되면 할 말만 남기고 세운다.
    """
    try:
        asyncio.run(_붙어보기())
    except db.DB못붙음 as exc:
        print(str(exc), flush=True)
        sys.exit(1)


async def _붙어보기() -> None:
    await db.init_pool()
    await db.close_pool()


def _포트가_이미_쓰이나(port: int) -> bool:
    """이미 서버가 떠 있는데 또 켜면 uvicorn 이 winerror 10048 만 뱉는다.

    당일 흔한 상황이다 — 시작.bat 를 두 번 눌렀거나, 어제 창을 안 닫았다.
    """
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def main() -> None:
    s = get_settings()

    if _포트가_이미_쓰이나(s.port):
        print("\n" + "=" * 66)
        print(f"  포트 {s.port} 을 이미 쓰고 있습니다 — 서버가 벌써 떠 있는 것 같습니다.")
        print("=" * 66)
        print("  · 이미 떠 있다면 **이대로 수업하면 됩니다.** 새로 켤 필요가 없습니다.")
        print(f"    확인 — 브라우저에서  http://127.0.0.1:{s.port}/console")
        print("  · 정말 다시 켜야 한다면 먼저 그 창을 닫으세요.")
        print("=" * 66 + "\n", flush=True)
        sys.exit(1)

    _먼저_확인()

    if s.host in ("127.0.0.1", "localhost", "::1"):
        print("\n" + "!" * 66)
        print(f"  서버가 {s.host} 에만 열립니다 — 강사 PC 에서만 보입니다.")
        print("  학생 39명은 전부 「연결 실패」가 납니다.")
        print("  .env 의 HOST 를 0.0.0.0 으로 바꾸고 다시 켜세요.")
        print("!" * 66 + "\n", flush=True)

    uvicorn.run(
        "server.app.main:app",
        host=s.host,
        port=s.port,
        workers=1,          # 절대 늘리지 말 것
        log_level="info",
        access_log=False,   # 39명 x 1초 폴링이면 액세스 로그가 병목이 된다
    )


if __name__ == "__main__":
    main()
