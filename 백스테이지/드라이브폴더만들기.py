"""구글드라이브에 올릴 폴더를 통째로 만든다 — 강사는 드래그해서 올리기만 한다.

    python 드라이브폴더만들기.py

왜 이 도구가 있나
    학생이 보는 곳은 드라이브 폴더 **하나**다. 손으로 모으면 반드시 하나를 빠뜨리고,
    자료를 고친 뒤 다시 올릴 때 옛 파일이 섞인다. 항상 여기서 다시 뽑는다.

무엇이 들어가나 — **학생이 읽을 것만**
    강사 문서(진행표·핸드오프·서버운영·일차별안내)와 백스테이지는 들어가지 않는다.
    슬라이드는 낱장 73개를 뿌리면 학생이 못 찾으므로 일차별 폴더로 묶는다.

이름 앞의 번호
    드라이브가 이름순으로 정렬한다. 번호가 없으면 「강의자료」가 맨 위로 가고
    사전안내문이 아래로 밀려 **학생이 제일 먼저 봐야 할 것을 못 본다.**
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

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # 백스테이지/
REPO = ROOT.parent                              # 경남대특강/
OUT = REPO / "드라이브업로드" / "경남대 AI 특강 (8월)"
ZIP = REPO / "k-precision-lab.zip"


def 배포본_최신인가() -> bool:
    """ZIP 이 배포본보다 오래됐으면 다시 뽑으라고 말한다."""
    배포본 = REPO / "배포본" / "k-precision-lab"
    if not 배포본.is_dir():
        return False
    if not ZIP.is_file():
        return False
    최신 = max((p.stat().st_mtime for p in 배포본.rglob("*") if p.is_file()), default=0)
    return ZIP.stat().st_mtime >= 최신


def main() -> int:
    문제 = []

    # ── 배포본 ZIP ────────────────────────────────────────────────────────
    if not (REPO / "배포본" / "k-precision-lab").is_dir():
        문제.append("배포본이 없습니다 — 먼저  python 배포본만들기.py --검증")
    elif not 배포본_최신인가():
        print("  ZIP 이 배포본보다 오래됐습니다 — 다시 압축합니다.")
        if ZIP.exists():
            ZIP.unlink()
        shutil.make_archive(str(ZIP.with_suffix("")), "zip",
                            root_dir=str(REPO / "배포본"), base_dir="k-precision-lab")

    if 문제:
        for x in 문제:
            print(f"  {x}", file=sys.stderr)
        return 1

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # ── 학생이 읽는 것만 ─────────────────────────────────────────────────
    옮길것 = [
        (REPO / "당일" / "인쇄물" / "사전안내문.md", "00_먼저읽으세요_사전안내문.md"),
        (ZIP,                                        "01_실습파일_k-precision-lab.zip"),
        (REPO / "학생배포" / "1일차" / "실습가이드.md", "02_실습가이드_1일차.md"),
        (REPO / "학생배포" / "2일차" / "실습가이드.md", "03_실습가이드_2일차.md"),
    ]
    for src, 새이름 in 옮길것:
        if not src.is_file():
            print(f"  [빠짐] {src}", file=sys.stderr)
            return 1
        shutil.copyfile(src, OUT / 새이름)
        print(f"  담음  {새이름}")

    # ── 슬라이드는 일차별로 묶는다 ───────────────────────────────────────
    강의자료 = OUT / "04_강의자료"
    강의자료.mkdir()
    for 일차 in ("1일차", "2일차"):
        src = REPO / "당일" / "슬라이드" / 일차
        if not src.is_dir():
            print(f"  [빠짐] {src}", file=sys.stderr)
            return 1
        dst = 강의자료 / f"{일차}_슬라이드"
        shutil.copytree(src, dst)
        print(f"  담음  04_강의자료/{일차}_슬라이드  ({len(list(dst.glob('*.png')))}장)")

    노션 = REPO / "당일" / "노션_자산화_강의자료.pptx"
    if 노션.is_file():
        shutil.copyfile(노션, 강의자료 / "1일차_1교시_노션자산화.pptx")
        print("  담음  04_강의자료/1일차_1교시_노션자산화.pptx")

    # ── 강사 것이 섞이지 않았는지 ────────────────────────────────────────
    금지 = ("진행표", "핸드오프", "서버운영", "일차별안내", "강사", "정답",
            "리허설", "배포본만들기", "verify_lab", ".env")
    샌것 = [p for p in OUT.rglob("*") if p.is_file()
            and any(k in p.name for k in 금지)]
    if 샌것:
        print("\n  ★ 강사 것이 섞였습니다 — 올리지 마세요", file=sys.stderr)
        for p in 샌것:
            print(f"      {p.relative_to(OUT)}", file=sys.stderr)
        return 1

    총 = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"\n  강사 것·정답은 섞이지 않았습니다 (검사 통과)")
    print("=" * 66)
    print(f"  {OUT}")
    print("=" * 66)
    print(f"  파일 {sum(1 for p in OUT.rglob('*') if p.is_file())}개 · {총 / 1024 / 1024:.1f}MB")
    print("\n  이 폴더를 **통째로** 구글드라이브에 끌어다 놓으세요.")
    print("  공유는 「링크가 있는 모든 사용자 — 뷰어」로 둡니다.")
    print("\n  ※ ZIP 안에는 정답(`정답/`)이 일부러 들어 있습니다 — `--열기` 가 읽습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
