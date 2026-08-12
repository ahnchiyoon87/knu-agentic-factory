"""내 공장 받기 — 이 파일을 한 번 실행하면 끝입니다.

    python 내번호.py                 처음 (자동으로 하나 받습니다)
    python 내번호.py S07             자리를 옮겼을 때 (원래 번호를 되찾습니다)

무엇을 하나
  1. 강사 서버에서 **내 공장 번호와 접속 키**를 받습니다.
  2. 받은 것을 `.내번호` 파일에 적어 둡니다 — 다음부터는 그걸 씁니다.
  3. 3일차 실습 폴더의 `config.json` 두 개를 **자동으로 채웁니다.**
     여러분이 번호나 키를 손으로 옮겨 적을 일이 없습니다.

기억할 것은 화면에 뜨는 **번호 하나**뿐입니다 (예: S07).
자리를 옮기거나 컴퓨터를 바꿨으면 그 번호를 뒤에 붙여 다시 실행하세요.
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
# ─────────────────────────────────────────────────────────────────────────

import argparse
import json
import secrets
import sys
from pathlib import Path

try:
    import httpx
except ModuleNotFoundError:
    print("httpx 가 없습니다. 먼저 이것부터 —  pip install -r requirements.txt",
          file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent          # 2일차/실습
BASE = ROOT.parents[1]                          # 저장소 루트
번호표파일 = BASE / ".내번호"                     # 저장소 루트에 둔다 (두 일차가 같이 씀)


def 번호표() -> str:
    """이 컴퓨터의 번호표. 없으면 무작위로 하나 만들어 적어 둔다.

    MAC 주소나 컴퓨터 이름을 쓰지 않는 이유 —
    MAC 은 못 읽는 PC 에서 매번 다른 값이 나오고, 실습실 복제 PC 는 이름이 같습니다.
    내가 만든 무작위 번호표는 그런 실패가 없습니다.
    """
    if 번호표파일.is_file():
        try:
            d = json.loads(번호표파일.read_text(encoding="utf-8"))
            if d.get("번호표"):
                return d["번호표"]
        except Exception:                                          # noqa: BLE001
            # 조용히 새 번호로 갈아타면 학생은 공장이 바뀐 것을 모른다 — 알리고 진행한다.
            print("※ 번호표 파일이 깨져 있어 새로 만듭니다.")
            print("   어제 받은 번호를 기억하면  python 내번호.py S07  처럼 붙여 되찾으세요.")
    새표 = secrets.token_urlsafe(24)
    _저장(번호표={"번호표": 새표})
    return 새표


def _저장(번호표: dict) -> None:
    기존 = {}
    if 번호표파일.is_file():
        try:
            기존 = json.loads(번호표파일.read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            기존 = {}
    기존.update(번호표)
    번호표파일.write_text(json.dumps(기존, ensure_ascii=False, indent=2),
                        encoding="utf-8")


def _내컴퓨터인가(주소: str) -> bool:
    """`127.0.0.1`·`localhost` 는 **자기 컴퓨터**를 가리킨다.

    학생이 이걸 넣으면 서버에 못 붙는다 — 그런데 조용히 실패하지 않는다.
    번호는 받아지고(강사 서버가 아니라 자기 PC 라 실은 못 받지만) 3일차
    `config.json` 의 `shared_api` 에 그대로 박혀서, **오전 진단 리포트가
    밋밋하게 나오고 학생은 자기 코드 탓이라고 생각한다.**
    가이드에 경고가 적혀 있지만 그걸 읽을 때는 이미 늦다. 여기서 막는다.
    """
    낮 = 주소.lower()
    return any(x in 낮 for x in ("127.0.0.1", "localhost", "0.0.0.0", "::1"))


def 서버주소(직접: str | None) -> str:
    if 직접:
        return 직접.rstrip("/")
    if 번호표파일.is_file():
        try:
            d = json.loads(번호표파일.read_text(encoding="utf-8"))
            if d.get("서버"):
                return str(d["서버"]).rstrip("/")
        except Exception:                                          # noqa: BLE001
            pass
    print("강사가 알려 준 **서버 주소**를 넣으세요. (화면에 떠 있습니다)")
    print("  예)  http://192.168.0.10:8000")
    try:
        답 = input("  서버 주소: ").strip().rstrip("/")
    except EOFError:
        답 = ""
    if not 답:
        print("\n주소를 안 넣었습니다. 이렇게 다시 실행하세요 —", file=sys.stderr)
        print("  python 내번호.py --서버 http://<강사가 알려 준 주소>:8000", file=sys.stderr)
        sys.exit(1)
    if not 답.startswith("http"):
        답 = "http://" + 답
    return 답


def 주소확인(주소: str, 물어봐도되나: bool) -> str:
    """자기 컴퓨터를 가리키는 주소면 되묻는다. 여기서 막아야 오후가 안 무너진다."""
    if not _내컴퓨터인가(주소):
        return 주소
    print()
    print("  ※ 잠깐 — 넣은 주소가 **내 컴퓨터**를 가리킵니다.")
    print(f"       {주소}")
    print("     강사 서버는 다른 컴퓨터에 있습니다. 화면에 떠 있는 주소를 그대로 넣으세요.")
    print("     예)  http://192.168.0.10:8000")
    print("     이대로 두면 내일 오전 진단 리포트에 원인 추정이 안 나옵니다.")
    if not 물어봐도되나:
        print()
        print("  강사 PC 에서 확인용으로 돌린 것이면 그대로 진행합니다.")
        return 주소
    print()
    try:
        다시 = input("  강사가 알려 준 주소 (그냥 Enter 면 이대로 진행): ").strip().rstrip("/")
    except EOFError:
        다시 = ""
    if not 다시:
        return 주소
    if not 다시.startswith("http"):
        다시 = "http://" + 다시
    return 다시


def config채우기(번호: str, 키: str, 서버: str) -> list[str]:
    """3일차 실습 두 곳의 config.json 을 채운다. 손으로 옮겨 적지 않게."""
    바꾼곳 = []
    도구 = BASE / "3일차" / "실습" / "도구만들기" / "config.json"
    폐루프 = BASE / "3일차" / "실습" / "폐루프" / "config.json"

    if 도구.is_file():
        c = json.loads(도구.read_text(encoding="utf-8"))
        c.setdefault("fallback", {})
        c["fallback"]["tenant"] = 번호
        c["fallback"]["shared_api"] = 서버
        도구.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        바꾼곳.append("3일차/실습/도구만들기/config.json")

    if 폐루프.is_file():
        c = json.loads(폐루프.read_text(encoding="utf-8"))
        c["tenant"] = 번호
        c["access_key"] = 키
        c["base_url"] = 서버
        폐루프.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        바꾼곳.append("3일차/실습/폐루프/config.json")

    return 바꾼곳


def main() -> int:
    ap = argparse.ArgumentParser(description="내 공장 받기")
    ap.add_argument("번호", nargs="?", default=None,
                    help="자리를 옮겼을 때 원래 번호 (예: S07)")
    ap.add_argument("--서버", default=None, help="강사 서버 주소")
    args = ap.parse_args()

    서버 = 주소확인(서버주소(args.서버), 물어봐도되나=sys.stdin.isatty())
    표 = 번호표()

    몸 = {"번호표": 표}
    if args.번호:
        몸["되찾을_번호"] = args.번호.strip().upper()

    try:
        r = httpx.post(f"{서버}/api/v1/claim", json=몸, timeout=20)
    except Exception as exc:                                       # noqa: BLE001
        print(f"\n서버에 닿지 못했습니다 — {type(exc).__name__}", file=sys.stderr)
        print(f"  주소 {서버}", file=sys.stderr)
        print("  주소를 잘못 적었거나 강사 서버가 아직 안 켜졌습니다. 손 드세요.",
              file=sys.stderr)
        return 1

    if r.status_code != 200:
        try:
            까닭 = r.json().get("detail", r.text)
        except Exception:                                          # noqa: BLE001
            까닭 = r.text
        print(f"\n받지 못했습니다 — {까닭}", file=sys.stderr)
        return 1

    d = r.json()
    번호, 키 = d["tenant_id"], d["access_key"]
    _저장({"서버": 서버, "번호": 번호, "키": 키})
    바꾼곳 = config채우기(번호, 키, 서버)

    print()
    print("=" * 58)
    print(f"  당신의 공장은  ★ {번호} ★  입니다")
    print("=" * 58)
    if d.get("되찾음"):
        print("  (원래 쓰던 공장을 되찾았습니다)")
    elif not d.get("새로_받음"):
        print("  (전에 받아 둔 공장입니다)")
    print()
    print(f"  이 번호를 적어 두세요. 자리를 옮기거나 컴퓨터를 바꾸면")
    print(f"     python 내번호.py {번호}")
    print("  한 줄로 이 공장을 다시 가져옵니다.")
    print()
    print("  ■ 2일차 — 크롬 주소창에 그대로 붙여넣으세요")
    print(f"     {서버}/view?tenant={번호}")
    if 바꾼곳:
        print()
        print("  ■ 3일차 설정은 이미 채워 뒀습니다 (손으로 적을 것 없음)")
        for f in 바꾼곳:
            print(f"     {f}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
