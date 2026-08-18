"""구글드라이브에 올릴 폴더를 통째로 만든다 — 강사는 드래그해서 올리기만 한다.

    python 드라이브폴더만들기.py

왜 이 도구가 있나
    학생이 보는 곳은 드라이브 폴더 **하나**다. 손으로 모으면 반드시 하나를 빠뜨리고,
    자료를 고친 뒤 다시 올릴 때 옛 파일이 섞인다. 항상 여기서 다시 뽑는다.

무엇이 들어가나 — **학생이 읽을 것만**
    강사 문서(진행.md·핸드오프·운영.md)와 제작·검증 도구는 들어가지 않는다.
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

ROOT = Path(__file__).resolve().parent          # 제작/빌드도구/
REPO = ROOT.parents[1]                          # 경남대특강/ (저장소 루트)
OUT = REPO / "제작" / "산출물" / "드라이브업로드" / "경남대 AI 특강 (8월)"


def main() -> int:
    if not (REPO / "제작" / "산출물" / "배포본" / "k-precision-lab").is_dir():
        print("  배포본이 없습니다 — 먼저  python 배포본만들기.py --검증", file=sys.stderr)
        return 1

    # ── 남의 번호·주소가 박힌 채 나가지 않는지 ─────────────────────────────
    #    `내번호.py` 가 채우는 자리다. 강사가 검증하며 돌리면 강사 값이 남는데,
    #    그대로 39명에게 나가면 **안 돌린 학생이 조용히 그 값으로 진행한다.**
    #    (S01 은 실재하는 남의 번호다. 실제로 이 상태로 zip 이 한 번 나갔다.)
    import json as _json
    랩 = REPO / "제작" / "산출물" / "배포본" / "k-precision-lab"
    더러움: list[str] = []
    도구 = 랩 / "3일차" / "실습" / "도구만들기" / "config.json"
    if 도구.is_file():
        fb = _json.loads(도구.read_text(encoding="utf-8")).get("fallback", {})
        더러움 += [f"도구만들기 {k}={fb[k]!r}" for k in ("shared_api", "tenant")
                  if fb.get(k)]
    폐루프 = 랩 / "3일차" / "실습" / "폐루프" / "config.json"
    if 폐루프.is_file():
        c = _json.loads(폐루프.read_text(encoding="utf-8"))
        더러움 += [f"폐루프 {k}={c[k]!r}" for k in ("tenant", "access_key", "base_url")
                  if c.get(k)]
    if 더러움:
        print("\n  ★ 배포본 config 에 강사 값이 남아 있습니다 — 올리지 마세요",
              file=sys.stderr)
        for d in 더러움:
            print(f"      {d}", file=sys.stderr)
        print("    고치기 —  python 제작/검증도구/배포본만들기.py", file=sys.stderr)
        return 1

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # ── 실습 ZIP — 드라이브 폴더 안에 **직접** 만든다 ─────────────────────
    #    전에는 산출물/ 루트에 만들어 복사했는데, 같은 ZIP 이 두 곳에 남아
    #    「어느 것이 최신인가」가 생겼다. ZIP 은 여기 하나뿐이다.
    zip_dst = OUT / "2. 실습 파일 (k-precision-lab)"
    shutil.make_archive(str(zip_dst), "zip",
                        root_dir=str(REPO / "제작" / "산출물" / "배포본"),
                        base_dir="k-precision-lab")
    print("  담음  2. 실습 파일 (k-precision-lab).zip  (배포본에서 새로 압축)")

    # ── 학생이 읽는 것 — 문서는 PDF 로 낸다 ──────────────────────────────
    #    `.md` 를 드라이브에 올리면 미리보기가 안 되고, 받아도 메모장에서
    #    `**굵게**` `|표|` 가 그대로 보인다. 학생이 이틀 내내 볼 문서다.
    #    실습 가이드는 **일차별로 두 권**이다. 한 권으로 묶어 두니 2일차 학생 화면에
    #    3일차 이야기가 같이 보였다. 그날 쓰는 것만 열게 한다 — 파일 이름에 일차가
    #    적혀 있어 「어느 걸 여나」는 판단할 것이 없다.
    문서 = [
        (REPO / "강의" / "준비안내.md",
         "1. 실습 환경 준비 안내.pdf", "실습 환경 준비 안내"),
        (REPO / "강의" / "실습가이드_2일차.md",
         "3. 실습 가이드 (2일차).pdf", "2일차 실습 가이드"),
        (REPO / "강의" / "실습가이드_3일차.md",
         "4. 실습 가이드 (3일차).pdf", "3일차 실습 가이드"),
    ]
    for src, 새이름, 제목 in 문서:
        if not src.is_file():
            print(f"  [빠짐] {src}", file=sys.stderr)
            return 1
        r = subprocess.run([sys.executable, str(ROOT / "md2pdf.py"), str(src),
                            str(OUT / 새이름), 제목],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode != 0 or not (OUT / 새이름).is_file():
            print(f"  [실패] PDF 변환 — {새이름}\n{r.stdout}{r.stderr}", file=sys.stderr)
            return 1
        print(f"  담음  {새이름}")

    # ── 슬라이드는 pptx 로 준다 (PNG 낱장 73개를 뿌리면 학생이 못 찾는다) ──
    강의자료 = OUT / "5. 강의 자료"
    강의자료.mkdir()
    # **편집본을 먼저 쓴다.** 강사가 강의 직전에 파워포인트에서 문구를 고칠 수 있어야 한다.
    # (그림 한 장짜리 `슬라이드.pptx` 는 글자를 한 자도 못 고친다)
    for 일차 in ("2일차", "3일차"):
        자료 = REPO / "강의" / 일차 / "강의자료"
        deck = 자료 / "슬라이드_편집본.pptx"
        if not deck.is_file():
            deck = 자료 / "슬라이드.pptx"
        if not deck.is_file():
            print(f"  [빠짐] {자료} 에 슬라이드가 없습니다 — "
                  f"먼저  python pptx편집본만들기.py", file=sys.stderr)
            return 1
        shutil.copyfile(deck, 강의자료 / f"{일차} 슬라이드.pptx")
        print(f"  담음  5. 강의 자료/{일차} 슬라이드.pptx")

    노션 = REPO / "강의" / "2일차" / "강의자료" / "노션_자산화.pptx"
    if 노션.is_file():
        shutil.copyfile(노션, 강의자료 / "노션 자산화 (2일차 1교시).pptx")
        print("  담음  5. 강의 자료/노션 자산화 (2일차 1교시).pptx")

    # ── 강사 것이 섞이지 않았는지 ────────────────────────────────────────
    금지 = ("진행", "핸드오프", "서버운영", "운영.md", "일차별안내", "강사", "정답",
            "리허설", "배포본만들기", "verify_lab", ".env")
    샌것 = [p for p in OUT.rglob("*") if p.is_file()
            and any(k in p.name for k in 금지)]
    if 샌것:
        print("\n  ★ 강사 것이 섞였습니다 — 올리지 마세요", file=sys.stderr)
        for p in 샌것:
            print(f"      {p.relative_to(OUT)}", file=sys.stderr)
        return 1

    총 = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    개수 = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"\n  강사 것·정답은 섞이지 않았습니다 (검사 통과)")

    # ── ZIP 하나만 남긴다 — 폴더는 지운다 (강사가 풀어서 통째로 업로드) ────
    zip_path = REPO / "제작" / "산출물" / "드라이브업로드"
    shutil.make_archive(str(zip_path), "zip",
                        root_dir=str(OUT.parent), base_dir=OUT.name)
    shutil.rmtree(OUT.parent)
    print("=" * 66)
    print(f"  {zip_path}.zip")
    print("=" * 66)
    print(f"  안에 파일 {개수}개 · {총 / 1024 / 1024:.1f}MB")
    print("\n  이 ZIP 을 풀어 나온 폴더를 **통째로** 구글드라이브에 끌어다 놓으세요.")
    print("  공유는 「링크가 있는 모든 사용자 — 뷰어」로 둡니다.")
    print("\n  ※ 실습 ZIP 안에는 정답(`정답/`)이 일부러 들어 있습니다 — `--정답` 가 읽습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
