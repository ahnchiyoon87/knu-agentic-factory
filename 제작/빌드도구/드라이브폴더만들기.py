"""최종본을 만든다 — 드라이브에 올릴 폴더 하나.

    python 드라이브폴더만들기.py

산출물은 이렇게 놓인다. **압축을 풀 일이 없다.**

    제작/산출물/
        경남대 AI 특강 (8월)/       ← 이게 최종본. 통째로 드라이브에 끌어다 놓는다
        경남대 AI 특강 (8월).zip    ← 위 폴더를 압축한 것. 옮길 일이 있을 때만
        k-precision-lab/            ← 학생 실습파일이 **풀린 채로**. 여기서 고치고 본다

왜 이렇게 두나
    전에는 zip 만 남기고 폴더를 지웠다. 그래서 한 줄 고칠 때마다 **확인하려고 zip 을
    풀어야 했고**, 그 안에 실습 zip 이 또 들어 있어 두 번 풀어야 했다.
    이제 풀린 것이 정본이고 zip 은 그 그림자다 — 이 스크립트를 돌리면 같이 바뀐다.

    학생 실습파일을 최종본 **안**이 아니라 옆에 두는 이유 — 최종본은 통째로 올라간다.
    풀린 폴더가 그 안에 있으면 학생이 zip 과 폴더 둘을 보고 어느 것을 받을지 헷갈린다.

    강사가 볼 가이드 PDF 도 최종본 안의 것 하나뿐이다. 전에는 저장소 루트에도 따로 뽑아서
    같은 문서가 두 곳에서 각각 만들어졌고, 어느 것이 최신인지가 매번 생겼다.

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
산출물 = REPO / "제작" / "산출물"
OUT = 산출물 / "경남대 AI 특강 (8월)"     # ← 이 폴더가 곧 최종본이다. 통째로 올린다
실습원본 = 산출물 / "k-precision-lab"      # ← 풀린 채로 사는 학생 실습파일. 여기서 고친다


def main() -> int:
    if not 실습원본.is_dir():
        print(f"  실습파일이 없습니다 — {실습원본}", file=sys.stderr)
        print("  먼저  python 제작/검증도구/배포본만들기.py --검증", file=sys.stderr)
        return 1

    # ── config 가 정확히 고정값인지 ────────────────────────────────────────
    #    공장이 학생 PC 에서 돌게 되면서 설정은 전원 공통 고정값으로 **미리 채워서**
    #    나간다 (S01 · local-lab-key · localhost:8000 — 비밀 아님). 여기서 막을 것은
    #    빈 칸도, 채워진 칸도 아니고 **고정값과 다른 값**이다 — 옛 클라우드 주소나
    #    진짜 키가 박혀 나가는 사고를 잡는다.
    import json as _json
    랩 = 실습원본
    기대 = {"tenant": "S01", "access_key": "local-lab-key",
            "주소": "http://localhost:8000"}
    더러움: list[str] = []
    도구 = 랩 / "3일차" / "실습" / "도구만들기" / "config.json"
    if 도구.is_file():
        fb = _json.loads(도구.read_text(encoding="utf-8")).get("fallback", {})
        if fb.get("shared_api") != 기대["주소"]:
            더러움.append(f"도구만들기 shared_api={fb.get('shared_api')!r} (기대: {기대['주소']})")
        if fb.get("tenant") != 기대["tenant"]:
            더러움.append(f"도구만들기 tenant={fb.get('tenant')!r} (기대: S01)")
        if fb.get("access_key") != 기대["access_key"]:
            더러움.append(f"도구만들기 access_key={fb.get('access_key')!r} (기대: local-lab-key)")
    폐루프 = 랩 / "3일차" / "실습" / "폐루프" / "config.json"
    if 폐루프.is_file():
        c = _json.loads(폐루프.read_text(encoding="utf-8"))
        if c.get("tenant") != 기대["tenant"]:
            더러움.append(f"폐루프 tenant={c.get('tenant')!r} (기대: S01)")
        if c.get("access_key") != 기대["access_key"]:
            더러움.append(f"폐루프 access_key={c.get('access_key')!r} (기대: local-lab-key)")
        if c.get("base_url") != 기대["주소"]:
            더러움.append(f"폐루프 base_url={c.get('base_url')!r} (기대: {기대['주소']})")
    # 공장 .env — 열쇠는 **캡슐(KNU1:)로 실려 있어야** 하고, 평문(sk-)은 금지다
    공장env = 랩 / "공장" / ".env"
    if 공장env.is_file():
        내용전체 = 공장env.read_text(encoding="utf-8-sig")
        if "sk-" in 내용전체:
            더러움.append("공장/.env 에 평문 열쇠(sk-)가 있음 — 캡슐로만 나가야 함")
        for line in 내용전체.splitlines():
            k = line.strip()
            if k.startswith("OPENAI_API_KEY=") and not k.startswith("OPENAI_API_KEY=KNU1:"):
                더러움.append("공장/.env 의 열쇠가 캡슐(KNU1:)이 아님")
            if k.startswith("CONTROL_API_ENABLED=") and k != "CONTROL_API_ENABLED=false":
                더러움.append("공장/.env 의 제어가 잠금(false)이 아님")
    if 더러움:
        print("\n  ★ 배포본 config 가 고정값과 다릅니다 — 올리지 마세요",
              file=sys.stderr)
        for d in 더러움:
            print(f"      {d}", file=sys.stderr)
        print("    고치기 —  python 제작/검증도구/배포본만들기.py", file=sys.stderr)
        return 1

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # ── 실습 ZIP — 옆에 풀려 있는 그 폴더를 그대로 압축한다 ────────────────
    #    학생은 zip 을 받아 풀어서 VS Code 로 연다(준비안내 ③). 그래서 zip 은 없앨 수 없다.
    #    대신 **풀린 것이 정본**이고 이 zip 은 그 그림자라, 고친 것이 반드시 따라온다.
    zip_dst = OUT / "2. 실습 파일 (k-precision-lab)"
    shutil.make_archive(str(zip_dst), "zip",
                        root_dir=str(산출물), base_dir=실습원본.name)
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
            # 옛 이름(`pptx편집본만들기.py`)을 안내하던 자리다. 그 파일은 없어졌고
            # 지금 pptx 를 만드는 것은 `편집pptx.py` 하나뿐이다.
            print(f"  [빠짐] {자료} 에 슬라이드가 없습니다 — "
                  f"먼저  python 편집pptx.py {일차}", file=sys.stderr)
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

    # ── 폴더는 남긴다. 옮길 일이 있을 때만 쓰라고 zip 도 하나 만들어 둔다 ──
    #    전에는 zip 만 남기고 폴더를 지워서, 한 줄 고칠 때마다 zip 을 풀어야 했다.
    zip_path = OUT.with_suffix(".zip")
    shutil.make_archive(str(OUT), "zip", root_dir=str(산출물), base_dir=OUT.name)
    print("=" * 70)
    print("  최종본")
    print("=" * 70)
    print(f"  올릴 폴더   {OUT}")
    print(f"              파일 {개수}개 · {총 / 1024 / 1024:.1f}MB")
    print(f"  통째로 옮길 때만   {zip_path.name}")
    print()
    print(f"  실습파일 고칠 곳   {실습원본}")
    print("              풀린 채로 있습니다. 여기서 고치고 이 스크립트를 다시 돌리면")
    print("              위 폴더의 실습 ZIP 이 그대로 다시 만들어집니다.")
    print()
    print("  드라이브에는 **올릴 폴더**를 통째로 끌어다 놓으세요.")
    print("  공유는 「링크가 있는 모든 사용자 — 뷰어」로 둡니다.")
    print("\n  ※ 실습 ZIP 안에는 정답(`정답/`)이 일부러 들어 있습니다 — `--정답` 가 읽습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
