"""기동 진입점 — python -m server.run

시뮬레이션 상태가 메모리에 있으므로 워커는 반드시 1개다.
"""

from __future__ import annotations

import uvicorn

from server.app.config import get_settings


def main() -> None:
    s = get_settings()
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
