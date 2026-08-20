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
import zipfile
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

    # 폴더를 통째로 지웠다 다시 만든다. 다만 **강사가 pptx 를 열어 둔 채로**
    # 이걸 돌리면 그 파일 하나에 걸려 전부 멈춘다(WinError 32) — 실제로 그랬다.
    # 열린 파일은 건너뛰고 나머지를 갱신한 뒤, 무엇이 안 바뀌었는지 끝에 알린다.
    못지운것: list[Path] = []
    if OUT.exists():
        for p in sorted(OUT.rglob("*"), key=lambda q: -len(q.parts)):
            try:
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    p.rmdir()
            except OSError:
                if p.is_file():
                    못지운것.append(p)
    OUT.mkdir(parents=True, exist_ok=True)

    # ── 실습 ZIP — 옆에 풀려 있는 그 폴더를 압축한다 ──────────────────────
    #    학생은 zip 을 받아 풀어서 VS Code 로 연다(준비안내 ③). 그래서 zip 은 없앨 수 없다.
    #    대신 **풀린 것이 정본**이고 이 zip 은 그 그림자라, 고친 것이 반드시 따라온다.
    #
    #    ★ 통째로 담으면 안 된다. 이 폴더에서 `uv run` 을 한 번이라도 돌리면
    #      `.venv` 가 생기고, make_archive 는 그것까지 담는다. 실제로 1MB 짜리
    #      실습 zip 이 파일 6천 개로 불어난 적이 있다. 학생 PC 에서는 경로가
    #      달라 쓰지도 못하는 짐이다.
    찌꺼기폴더 = {".venv", "__pycache__", ".git", ".pytest_cache", ".ruff_cache"}
    zip_dst = OUT / "2. 실습 파일 (k-precision-lab).zip"
    담은수 = 0
    with zipfile.ZipFile(zip_dst, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(실습원본.rglob("*")):
            rel = p.relative_to(실습원본.parent)
            if 찌꺼기폴더 & set(rel.parts) or p.suffix in {".pyc", ".pyo"}:
                continue
            if p.is_file():
                z.write(p, str(rel))
                담은수 += 1
    print(f"  담음  {zip_dst.name}  (배포본에서 새로 압축 · 파일 {담은수}개)")

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
    강의자료.mkdir(exist_ok=True)      # 잠긴 pptx 가 남으면 이 폴더도 남는다
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
        나갈곳 = 강의자료 / f"{일차} 슬라이드.pptx"
        try:
            shutil.copyfile(deck, 나갈곳)
            print(f"  담음  5. 강의 자료/{일차} 슬라이드.pptx")
        except OSError:                       # 강사가 그 파일을 열어 두었다
            못지운것.append(나갈곳)

    노션 = REPO / "강의" / "2일차" / "강의자료" / "노션_자산화.pptx"
    if 노션.is_file():
        나갈곳 = 강의자료 / "노션 자산화 (2일차 1교시).pptx"
        try:
            shutil.copyfile(노션, 나갈곳)
            print("  담음  5. 강의 자료/노션 자산화 (2일차 1교시).pptx")
        except OSError:
            못지운것.append(나갈곳)

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

    # 실습 zip 에 작업 찌꺼기가 들어갔는지 — 눈으로는 안 보이고 크기로만 드러난다
    with zipfile.ZipFile(zip_dst) as z:
        샌것 = [n for n in z.namelist()
               if 찌꺼기폴더 & set(Path(n).parts) or n.endswith((".pyc", ".pyo"))]
    if 샌것:
        print(f"\n  ★ 실습 zip 에 작업 찌꺼기가 {len(샌것)}개 들어갔습니다 — 올리지 마세요",
              file=sys.stderr)
        for n in 샌것[:5]:
            print(f"      {n}", file=sys.stderr)
        return 1

    총 = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    개수 = sum(1 for p in OUT.rglob("*") if p.is_file())
    print(f"\n  강사 것·정답은 섞이지 않았습니다 (검사 통과)")

    # ── 폴더는 남긴다. 옮길 일이 있을 때만 쓰라고 zip 도 하나 만들어 둔다 ──
    #    전에는 zip 만 남기고 폴더를 지워서, 한 줄 고칠 때마다 zip 을 풀어야 했다.
    # 파워포인트를 열어 두면 `~$이름.pptx` 잠금 파일이 옆에 생긴다 — 담기지도 않고
    # 담을 것도 아니다. 통째 압축(make_archive)은 그걸 만나면 그대로 죽는다.
    zip_path = OUT.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file() and not p.name.startswith("~$"):
                z.write(p, str(p.relative_to(산출물)))
    print("=" * 70)
    print("  최종본")
    print("=" * 70)
    print(f"  올릴 폴더   {OUT}")
    print(f"              파일 {개수}개 · {총 / 1024 / 1024:.1f}MB")
    print(f"  통째로 옮길 때만   {zip_path.name}")
    남은 = sorted({str(p.relative_to(OUT)) for p in 못지운것
                  if not p.name.startswith("~$")})
    if 남은:
        print()
        print("  ※ 열려 있어 갱신하지 못한 파일 — 닫고 다시 돌리면 따라옵니다")
        for 이름 in 남은:
            print(f"      {이름}")
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
