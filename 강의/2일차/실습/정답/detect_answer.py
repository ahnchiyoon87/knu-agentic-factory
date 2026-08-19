"""2일차 참고 정답 — 학생 파일과 같은 뼈대에 빈칸만 채운 모습입니다.

**먼저 열어 보지 마세요.** 막혔을 때 `확인.py --정답 <번호>` 가
그 함수 **하나만** 여기서 가져다 채웁니다. 여러분이 쓰던 것은
`detect_내가짠것.py` 로 먼저 백업됩니다.

빈칸 5(방침)는 가장 단순한 `1`(그냥 둔다)로 채웠습니다.
유일한 정답이 아닙니다 — `2` 를 고르고 이유를 말할 수 있으면 그쪽이 더 낫습니다.
"""

from __future__ import annotations


def window_stats(values: list[float], i: int, window: int) -> tuple[float, float] | None:
    """i 번째 값 '바로 앞' window 개로 (평균, 표준편차) 를 구한다. 못 구하면 None."""

    # 앞이 모자라면 아직 판단할 수 없다
    if i < window:
        return None

    # 지금 값 '바로 앞' window 개만 남긴다.
    # 뒤끝이 i 라서 지금 값(values[i])은 안 들어간다 —
    # 넣으면 튀는 값이 자기 평균을 끌어올려 자기를 숨긴다.
    seg = [v for v in values[i - window:i] if v is not None]
    if len(seg) < 2:
        return None

    # ── 빈칸 1 ───────────────────────────────────────────────────────────
    #   seg 의 평균. 다 더해서 개수로 나눈다.
    #   쓸 것 :  sum(seg)   len(seg)
    mean = sum(seg) / len(seg)

    # ── 빈칸 2 ───────────────────────────────────────────────────────────
    #   표본분산. (각 값 − mean) 을 제곱해서 전부 더한 뒤 (개수 − 1) 로 나눈다.
    #   개수가 아니라 (개수 − 1) 이다. 개수로 나누면 값이 작아져 더 자주 울린다.
    #   쓸 것 :  sum((x - mean) ** 2 for x in seg)   len(seg)
    var = sum((x - mean) ** 2 for x in seg) / (len(seg) - 1)

    return mean, var ** 0.5


def is_anomaly(value: float, mean: float, std: float, k: float) -> bool:
    """z-score 의 절댓값이 k 를 넘으면 이상으로 본다."""

    # 표준편차가 0 이면 나눌 수 없다.
    # 최근 값이 한동안 완전히 똑같았다는 뜻이고, 실제 데이터에서 생긴다.
    if std == 0:
        # ── 빈칸 3 ───────────────────────────────────────────────────────
        #   그 자리를 이상으로 볼 것인가 — True 도 False 도 정답이다.
        #   하나를 골라 적고, 왜 골랐는지 말할 수 있으면 된다.
        #   예 :  value != mean     (평평했는데 지금 값이 다르면 이상으로 본다)
        return value != mean

    # ── 빈칸 4 ───────────────────────────────────────────────────────────
    #   z 의 절댓값이 k 를 넘으면 True.
    #   위로 벗어난 것도 아래로 벗어난 것도 이상이다 — 그래서 절댓값을 쓴다.
    #   쓸 것 :  (value - mean) / std     abs(...)     > k
    return abs((value - mean) / std) > k


def handle_missing(values: list[float | None]) -> list[float | None]:
    """값이 안 들어온 자리(None)를 어떻게 다룰지 정한다."""

    # 이 데이터에는 EQ-01 에 2시간(120개) 짜리 빈 구간이 있다.
    #
    # ── 빈칸 5 ───────────────────────────────────────────────────────────
    #   `방침 = ...` 자리에 1 이나 2 를 적는다.
    #
    #     1  그냥 둔다 — 그 구간은 판정하지 않는다.
    #        없는 값을 지어내지 않는다. 대신 그 구간은 못 본다.
    #
    #     2  직전 값으로 메운다.
    #        판정할 구간이 늘어난다. 대신 2시간 내내 같은 값이 들어가 표준편차가
    #        0 이 되고, 값이 돌아오는 순간 없던 이상이 하나 생긴다.
    #
    #   1 도 2 도 정답이다. 하나를 골라 적고, 왜 골랐는지 말할 수 있으면 된다.
    #   앞뒤 평균으로 메우는 등 다른 길을 가고 싶으면 아래를 통째로 바꿔도 된다.
    #
    #   ※ 돌려주는 목록의 길이는 원래와 같아야 한다. 빼 버리면 시각이 밀려
    #     엉뚱한 시각을 가리킨다.
    방침 = 1

    if 방침 == 1:
        return list(values)

    if 방침 == 2:
        채운것: list[float | None] = []
        직전: float | None = None
        for v in values:
            if v is None:
                채운것.append(직전)
            else:
                채운것.append(v)
                직전 = v
        return 채운것

    raise ValueError(f"방침은 1 이나 2 로 정합니다. 지금 적힌 값 — {방침!r}")



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
