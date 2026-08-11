"""1일차 참고 정답.

학생에게 배포하지 않습니다. Step 3(자기 구현 vs AI 구현 비교)에서
강사가 세 번째 축으로 꺼내 쓰는 용도입니다.

`python run.py --impl 정답` 으로 이 구현을 돌려볼 수 있습니다.

결측 처리를 일부러 '가장 단순한 방침'으로 뒀습니다.
이것이 유일한 정답이 아니며, 학생이 다른 선택을 하고 근거를 말하면 그쪽이 더 낫습니다.
"""

from __future__ import annotations

import math


def window_stats(values, i, window):
    if i < window:
        return None
    seg = [v for v in values[i - window:i] if v is not None]
    if len(seg) < 2:
        return None                       # 표본 표준편차를 못 구한다
    mean = sum(seg) / len(seg)
    var = sum((x - mean) ** 2 for x in seg) / (len(seg) - 1)
    return mean, math.sqrt(var)


def is_anomaly(value, mean, std, k):
    if std == 0:
        # 최근 값이 전부 똑같았다. 지금 값이 다르면 이상, 같으면 정상.
        return value != mean
    return abs((value - mean) / std) > k


def handle_missing(values):
    # 방침: 메우지 않고 그대로 둔다. 결측 구간은 판정하지 않는다.
    #
    # 이유 — 없는 값을 지어내면 그 구간의 z-score 가 거짓말이 된다.
    # 직전 값으로 메우면(ffill) 2시간 내내 같은 값이 들어가 표준편차가 0 이 되고,
    # 결측이 끝나 값이 돌아오는 순간 거대한 z 가 튀어 없던 이상이 하나 생긴다.
    return list(values)


def detect(values, window=60, k=3.0):
    cleaned = handle_missing(values)
    flags = []
    for i in range(len(cleaned)):
        stats = window_stats(cleaned, i, window)
        cur = cleaned[i]
        if stats is None or cur is None:
            flags.append(False)
            continue
        mean, std = stats
        flags.append(bool(is_anomaly(cur, mean, std, k)))
    return flags
