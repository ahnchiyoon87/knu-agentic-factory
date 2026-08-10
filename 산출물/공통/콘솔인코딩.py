# -*- coding: utf-8 -*-
"""한글 윈도우(cp949)에서 출력이 깨지거나 죽는 것을 막는다.

왜 필요한가 — 학생 PC의 기본 콘솔 코드페이지는 cp949 다.
우리 출력 문장에는 `—` `→` `★` 처럼 cp949 에 없는 글자가 들어 있어서,
출력이 파이프로 넘어가는 순간 `UnicodeEncodeError` 로 **실행이 중간에 죽는다.**

리허설(`공통/리허설.py`)은 자식 프로세스에 PYTHONUTF8=1 을 넣어 돌리기 때문에
이 문제가 드러나지 않는다. 학생은 그 환경변수 없이 그냥 실행한다.

쓰는 법 — 학생이 직접 실행하는 파일 맨 위에서 한 번 부른다.

    from 콘솔인코딩 import 적용; 적용()

경로가 안 잡히는 자리에서는 아래 세 줄을 그대로 복사해 넣어도 된다.
"""
from __future__ import annotations

import sys


def 적용() -> None:
    """stdout·stderr 를 UTF-8 로 돌린다. 이미 UTF-8 이면 아무것도 하지 않는다."""
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if enc == "utf8":
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:      # noqa: BLE001  — 콘솔이 아닌 경우 등. 죽이지 않는다
            pass


apply = 적용   # 영문 이름으로도 부를 수 있게
