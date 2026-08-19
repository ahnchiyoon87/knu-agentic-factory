# -*- coding: utf-8 -*-
"""최종본을 연다 — 학생에게 나갈 것이 실제로 어떻게 생겼는지 눈으로 볼 때.

    uv run 가이드보기.py          최종본 폴더를 연다
    uv run 가이드보기.py --가이드   가이드 두 권을 바로 띄운다

어디를 여는가
    `제작/산출물/경남대 AI 특강 (8월)/` 하나뿐이다.
    준비안내 PDF · 가이드 두 권 PDF · 실습파일 zip · 슬라이드 pptx 가 **펼쳐진 채로** 있다.
    zip 을 풀 것도, 다른 폴더를 뒤질 것도 없다.

    학생 실습 코드를 고칠 일이면 그 옆 `제작/산출물/k-precision-lab/` 이다.
    거기도 풀린 채로 있다.

왜 여기 하나인가
    전에는 이 스크립트가 저장소 루트에 가이드 PDF 를 따로 뽑았다. 그래서 같은 문서가
    **두 곳에서 각각 만들어졌고**, 하나만 다시 뽑으면 어느 것이 최신인지가 생겼다.
    지금은 만드는 곳이 한 곳이라 그 어긋남이 아예 없다.

없으면 어떻게 하나
    아래 한 줄이면 폴더와 zip 이 같이 새로 만들어진다.

        uv run --with playwright 제작/빌드도구/드라이브폴더만들기.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
최종본 = ROOT / "제작" / "산출물" / "경남대 AI 특강 (8월)"
실습원본 = ROOT / "제작" / "산출물" / "k-precision-lab"

만드는법 = ("  다시 만들려면 —\n"
         "      uv run --with playwright 제작/빌드도구/드라이브폴더만들기.py\n"
         "  (그 앞에 배포본이 있어야 합니다 — 제작/검증도구/배포본만들기.py)")


def 열기(경로: Path) -> None:
    subprocess.Popen(["cmd", "/c", "start", "", str(경로)], shell=False)


def main() -> int:
    if not 최종본.is_dir():
        print(f"  최종본이 아직 없습니다 — {최종본}", file=sys.stderr)
        print(만드는법, file=sys.stderr)
        return 1

    가이드만 = "--가이드" in sys.argv
    파일들 = sorted(p for p in 최종본.iterdir() if p.is_file())

    print(f"  최종본 — {최종본}")
    for p in 파일들:
        print(f"    {p.name}  ({p.stat().st_size // 1024}KB)")
    자료 = 최종본 / "5. 강의 자료"
    if 자료.is_dir():
        for p in sorted(자료.iterdir()):
            print(f"    5. 강의 자료/{p.name}  ({p.stat().st_size // 1024}KB)")

    if 가이드만:
        연것 = [p for p in 파일들 if "실습 가이드" in p.name]
        if not 연것:
            print("\n  가이드 PDF 를 못 찾았습니다.", file=sys.stderr)
            print(만드는법, file=sys.stderr)
            return 1
        for p in 연것:
            열기(p)
        print("\n  가이드 두 권을 띄웠습니다.")
    else:
        열기(최종본)
        print("\n  폴더를 열었습니다. 확인할 것을 그냥 더블클릭하세요.")

    if 실습원본.is_dir():
        print(f"\n  학생 실습파일 (풀린 채)  {실습원본}")
    print("\n  자료를 고쳤으면 —\n"
          "      uv run --with playwright 제작/빌드도구/드라이브폴더만들기.py\n"
          "  최종본 폴더와 그 안의 실습 ZIP 이 **같이** 새로 만들어집니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
