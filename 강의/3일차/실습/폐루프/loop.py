"""오케스트레이터 — 폐루프를 돌리는 자리. 여기는 이미 되어 있습니다.

    감지 → 진단 → 조치

총괄이 나누고 담당이 처리하는 구조입니다.
이 파일은 **누가 무슨 일을 하는지 모릅니다.** agents/__init__.py 의 등록표만 봅니다.
그래서 에이전트 하나를 갈아 끼우거나 새로 붙여도 여기는 그대로입니다.

    uv run loop.py --check      공장에 닿는지, 통로가 열렸는지만 본다
    uv run loop.py --once       한 바퀴만 돈다
    uv run loop.py              계속 돈다 (Ctrl+C 로 멈춤)
"""

from __future__ import annotations

# ── 한글 윈도우(cp949)에서 출력이 깨져 죽는 것을 막는다 ──────────────────
#    학생 PC 기본 콘솔은 cp949 라 `—` `→` 같은 글자에서 UnicodeEncodeError 가 난다.
#    리허설은 PYTHONUTF8=1 로 돌아가 이 문제가 안 보인다. 학생은 그냥 실행한다.
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
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import agents
except SyntaxError as _e:
    # 학생이 agents/*.py 를 채우다 만 문법 오류 — 역추적 대신 자리를 짚어 준다.
    _f = Path(getattr(_e, "filename", "") or "agents/").name
    raise SystemExit(f"{_f} {_e.lineno}행에 문법 오류가 있습니다 — {_e.msg}\n"
                     f"  괄호·따옴표·들여쓰기를 그 줄에서 확인하세요.") from None
from agents import DiagnoseFailed          # 등록표를 거친다 — 누가 진단을 맡는지 몰라야 한다
from control_client import DirectControl, open_control
from factory_api import CFG, ControlLocked, FactoryAPI

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "실행기록.jsonl"


@dataclass
class Context:
    """에이전트들이 공유하는 것.

    api      공장을 **읽는** 창구 (감지·진단이 쓴다)
    control  공장을 **움직이는** 통로 — 교안 8~9장의 MCP 도구 4개 (조치가 쓴다)
    """
    api: FactoryAPI
    cfg: dict
    control: object = None
    round_no: int = 0
    slow_clock: bool = False          # 배속이 1이면 드리프트가 안 잡힌다
    quiet_rounds: int = 0
    lines: list[str] = field(default_factory=list)
    # 같은 설비를 회차마다 다시 진단하면 39명분 호출이 몰려 한도를 넘는다.
    # 한 번 낸 진단을 재사용하고, 조치는 매 회차 새로 판단한다.
    진단캐시: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.control is None:
            self.control = DirectControl(self.api)

    def log(self, message: str) -> None:
        print(message, flush=True)
        self.lines.append(message)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# 한 바퀴
# =============================================================================
def one_round(ctx: Context) -> dict:
    ctx.round_no += 1
    ctx.lines.clear()
    ctx.log(f"\n── {ctx.round_no}회차 · {_now()} " + "─" * 28)

    # 1. 감지
    findings = agents.SENSE.run(ctx)
    if findings:
        ctx.log(f"감지  이상 {len(findings)}건")
        for f in findings:
            ctx.log(f"  · {f['equipment_id']} — {f.get('detail', f.get('kind'))}")
    else:
        ctx.log("감지  이상 없음")
        ctx.quiet_rounds += 1
        # 계속 조용하면 원인을 짚어 준다. 학생이 자기 코드를 의심하며 시간을 쓰지 않게.
        if ctx.quiet_rounds % 5 == 0:
            if ctx.slow_clock:
                ctx.log("  ⚠ 배속이 1배입니다 — 이 상태로는 드리프트가 안 잡힙니다."
                        " 강사에게 배속 120을 요청하세요.")
            else:
                ctx.log(f"  {ctx.quiet_rounds}회차째 조용합니다."
                        " 강사가 아직 주입을 안 했거나, 임계(detect.drift_delta_c)가 높습니다.")
    if findings:
        ctx.quiet_rounds = 0

    # 2~3. 이상마다 진단하고 조치한다
    cases = []
    for finding in findings:
        eq = finding["equipment_id"]
        기존 = ctx.진단캐시.get(eq)
        if 기존 is not None:
            ctx.log(f"\n진단  {eq}  (앞서 낸 진단을 그대로 씁니다)")
            diagnosis = 기존
        else:
            ctx.log(f"\n진단  {eq}")
            diagnosis = agents.DIAGNOSE.run(ctx, finding)
            ctx.진단캐시[eq] = diagnosis
        ctx.log(f"  원인({diagnosis.get('backend')})  {diagnosis.get('cause')}")
        for e in diagnosis.get("evidence", []):
            ctx.log(f"  근거  {e}")
        ctx.log(f"  심각도  {diagnosis.get('severity')}")

        ctx.log(f"\n조치  {finding['equipment_id']}")
        actions = agents.ACT.run(ctx, finding, diagnosis)

        cases.append({"finding": finding, "diagnosis": diagnosis, "actions": actions})

    record = {"round": ctx.round_no, "at": _now(),
              "findings": findings, "cases": cases}

    # 4. 추가 에이전트 — agents/__init__.py 의 EXTRA 에 등록돼 있으면 여기서 붙는다
    #    (README 「끝낸 뒤 — 더 해 볼 것」 4번이 쓰는 자리)
    extras = {}
    for agent in agents.EXTRA:
        name = getattr(agent, "ROLE", agent.__name__)
        ctx.log(f"\n{name}")
        try:
            extras[name] = agent.run(ctx, record)
        except Exception as exc:                                   # noqa: BLE001
            ctx.log(f"  실패 — {type(exc).__name__}: {exc}")
            extras[name] = {"error": f"{type(exc).__name__}: {exc}"}
    if extras:
        record["extra"] = extras

    record["log"] = list(ctx.lines)
    _append(record)
    return record


def _append(record: dict) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


# =============================================================================
# 실행
# =============================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description="폐루프 오케스트레이터")
    ap.add_argument("--check", action="store_true", help="공장에 닿는지만 확인한다")
    ap.add_argument("--once", action="store_true", help="한 바퀴만 돈다")
    ap.add_argument("--rounds", type=int, default=None, help="몇 바퀴 돌지")
    ap.add_argument("--tenant", default=None, help="네임스페이스 (기본: config.json)")
    ap.add_argument("--base-url", default=None, help="시뮬레이터 주소")
    ap.add_argument("--규칙으로", dest="rules", action="store_true",
                    help="AI 없이 규칙으로 돌린다. **강사 안내가 있을 때만 쓰세요.** "
                         "오늘의 핵심 장면(AI 가 정비 이력을 근거로 원인을 대는 것)을 못 봅니다")
    ap.add_argument("--열기", nargs="+", metavar="번호",
                    help="★ 시간이 다 됐을 때만 — 막힌 자리를 완성본으로 채워서 돌린다. "
                         "1 감지 · 2 진단 · 3 조치. 여러 개를 한 번에: --열기 1 2 · "
                         "세 자리 다 막혔으면: --열기 전부. 나머지는 내가 쓴 것 그대로 돕니다")
    # 강사 시연용. --help 에 안 띄운다 — 학생이 보면 실습을 통째로 건너뛰게 된다.
    # 막힌 학생에게 주는 것은 `--열기` 다 (막힌 자리 하나만).
    ap.add_argument("--use-answers", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.use_answers:
        sys.path.insert(0, str(ROOT / "정답"))
        try:
            import agent_bodies
        except ModuleNotFoundError:
            print("정답/agent_bodies.py 를 못 찾았습니다.", file=sys.stderr)
            return 1
        agent_bodies.install()
        print("참고 답안으로 실행합니다 (강사 시연 모드)")
    elif args.열기:
        번호들 = []
        for a in args.열기:
            if str(a).strip() in ("전부", "다", "all"):
                번호들 = [1, 2, 3]
                break
            if not str(a).isdigit() or int(a) not in (1, 2, 3):
                print(f"--열기 에는 1 2 3 또는 '전부' 를 주세요 (받은 값: {a})", file=sys.stderr)
                return 2
            번호들.append(int(a))
        번호들 = sorted(set(번호들))

        sys.path.insert(0, str(ROOT / "정답"))
        try:
            import agent_bodies
        except ModuleNotFoundError:
            print("완성본(정답/agent_bodies.py)을 못 찾았습니다.", file=sys.stderr)
            print("  실습 저장소를 통째로 내려받았는지 확인하세요. 안 되면 손 드세요.",
                  file=sys.stderr)
            return 1
        열린것 = []
        for n in 번호들:
            try:
                이름, 파일, 역할 = agent_bodies.install_one(n)
            except Exception as exc:                               # noqa: BLE001
                print(f"완성본을 열지 못했습니다 — {type(exc).__name__}: {exc}", file=sys.stderr)
                return 1
            열린것.append(f"{역할}({이름}) — {파일}")

        남은것 = [agent_bodies.ONE[n][2] for n in (1, 2, 3) if n not in 번호들]
        print("=" * 58)
        for 줄 in 열린것:
            print(f"  {줄} 를 완성본으로 채웠습니다")
        if 남은것:
            print(f"  {' · '.join(남은것)} 는 여러분이 쓴 것 그대로 돕니다.")
        else:
            print("  세 자리를 다 열었습니다. 오늘 볼 장면까지는 이걸로 갑니다.")
        print("  파일은 안 고쳤습니다. 이 옵션을 빼면 다시 내 코드로 돕니다.")
        print("  ※ 오늘 목표는 세 자리를 혼자 채우는 게 아니라, 공장이 움직이는 것을 보는 것입니다.")
        print("=" * 58)

    if args.rules:
        CFG["diagnose"]["backend"] = "rules"
        print("=" * 58)
        print("  규칙 모드로 돕니다 — AI 진단이 아닙니다.")
        print("  오늘 봐야 할 장면(AI 가 정비 이력을 읽고 원인을 대는 것)은")
        print("  이 모드에서 나오지 않습니다. 강사 안내에 따라 쓰세요.")
        print("=" * 58)

    # 설정을 안 채웠으면 여기서 잡힌다 — 역추적 대신 사람이 읽을 말로 세운다
    try:
        api = FactoryAPI(base_url=args.base_url, tenant=args.tenant)
    except ValueError as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        return 1

    try:
        info = api.preflight()
    except Exception as exc:                                       # noqa: BLE001
        print(f"공장에 닿지 못했습니다 — {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"  주소 {api.base} · 네임스페이스 {api.tenant}", file=sys.stderr)
        if "34.64.94.16" in api.base:
            print("  ★ 주소가 예시(34.64.94.16) 그대로입니다 — 아직 안 채워졌습니다.",
                  file=sys.stderr)
        print("  2일차/실습 에서 uv run 내번호.py 를 돌리면 이 설정이 자동으로 채워집니다.",
              file=sys.stderr)
        print("      cd ../../../2일차/실습  →  uv run 내번호.py", file=sys.stderr)
        print("  그래도 안 되면 손 드세요.", file=sys.stderr)
        return 1

    print(f"연결  {info['base_url']} · {info['tenant']} · "
          f"설비 {info['설비']}대 · 로봇 {info['로봇']}대 · 배속 x{info['배속']}")

    # 어디까지 채웠는지 먼저 말해 준다. 빈 함수는 조용히 None 을 돌려주므로
    # 안 알려 주면 「이상 없음」만 보고 자기 코드를 의심하며 시간을 쓴다.
    빈자리 = agents.안채운자리()
    if 빈자리:
        print("  아직 안 채운 자리 — " +
              " · ".join(f"{역할}({이름})" for 이름, _파일, 역할 in 빈자리))
        print("  채운 데까지만 돌립니다. 그 자리 차례가 오면 멈추고 어디인지 알려 줍니다.")
    if not info["제어_개방"]:
        print("  제어 통로가 아직 잠겨 있습니다. 강사가 이 네임스페이스를 개방해야 합니다.",
              file=sys.stderr)
    if info["배속_경고"]:
        print("\n  ⚠ 배속이 1배입니다 — 이 상태로는 드리프트가 잡히지 않습니다.", file=sys.stderr)
        print("     온도가 시간당 0.5℃ 씩 오르는 이상이라, 1배로 두면 실제로 4시간이 걸립니다.", file=sys.stderr)
        print("     코드가 맞아도 화면에는 「감지  이상 없음」만 나옵니다.", file=sys.stderr)
        print("     강사에게 **배속을 120으로 올려 달라고** 요청하세요.\n", file=sys.stderr)
    if args.check:
        if not info["제어_개방"]:
            return 2
        return 4 if info["배속_경고"] else 0

    control = open_control(CFG, api)
    ctx = Context(api=api, cfg=CFG, control=control, slow_clock=info["배속_경고"])
    interval = float(CFG["watch"]["interval_seconds"])
    limit = 1 if args.once else (args.rounds if args.rounds is not None
                                 else int(CFG["watch"]["max_rounds"]))

    try:
        while True:
            try:
                one_round(ctx)
            except ControlLocked as exc:
                print(f"\n제어가 잠겨 있습니다 — {exc}", file=sys.stderr)
                return 2
            except DiagnoseFailed:
                # 실패 안내는 진단 담당이 이미 사람 말로 냈다 (「N회 실패 · 다음 회차에
                # 다시 겁니다」). 여기서 죽으면 그 안내가 거짓말이 된다 — 감지 상태를
                # 유지한 채 다음 회차로 넘어간다.
                pass
            except agents.안채움 as exc:
                # 아직 안 채운 자리다. 학생에게 traceback 을 보여 줄 이유가 없다.
                # 어느 파일인지는 등록표가 안다 — 여기는 모른다.
                path, role = agents.where(exc.이름)
                print(f"\n아직 안 채운 자리가 있습니다 — {role} 에이전트", file=sys.stderr)
                print(f"  {path} 의 {exc.이름}() 을 채우세요.", file=sys.stderr)
                print("  그 함수의 `...` 줄을 고칩니다.", file=sys.stderr)
                print(f"  순서는 {agents.FILL_ORDER} 입니다.", file=sys.stderr)
                print("  시간이 다 됐으면 —  uv run loop.py --열기 1"
                      "   (1 감지 · 2 진단 · 3 조치)", file=sys.stderr)
                return 3
            if limit and ctx.round_no >= limit:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n멈춥니다.")
    finally:
        control.close()
        api.close()

    print(f"\n{ctx.round_no}회차까지 돌았습니다. 기록: {LOG_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
