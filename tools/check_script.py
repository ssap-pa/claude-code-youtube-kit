"""대본 검사 — 음성을 만들기 전에 script.json을 tools/regressions.json의 대본 항목(kind: script)으로 검사한다.
사용: python tools/check_script.py videos/<slug>      → 걸린 장면과 고치는 법, 걸리면 종료 코드 1
전에 고친 표기 사고(소문자 영어를 '아이'로 읽음, 'ㅇㅇ'을 못 읽음, 숫자를 한자어로 읽음 …)가 대본에 다시 들어오면 합성 전에 막는다(크레딧 절약).
규칙을 인용하는 장면처럼 일부러 쓴 것은 영상 폴더 qa/ok.json {"장면 id" 또는 "검사 id:장면 id": "사유"}."""
import json, re, sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent


def check(folder):
    F = Path(folder).resolve(); scenes = json.loads((F / 'script.json').read_text(encoding='utf-8'))['scenes']
    okf = F / 'qa' / 'ok.json'; ok = json.loads(okf.read_text(encoding='utf-8')) if okf.exists() else {}
    items = [it for it in json.loads((TOOLS / 'regressions.json').read_text(encoding='utf-8'))['items'] if it['kind'] == 'script']
    hits = []
    for it in items:
        for s in scenes:
            found = list(dict.fromkeys(m.group(0) for m in re.finditer(it['pattern'], s['text'])))
            if found and it.get('unless') and re.search(it['unless'], s['text']): found = []   # 같은 장면에 체감 비교 등이 있으면 통과
            if found and s['id'] not in ok and it['id'] not in ok and f"{it['id']}:{s['id']}" not in ok:
                hits.append((s['id'], it, found))
    return scenes, items, hits


def main(argv):
    sys.stdout.reconfigure(encoding='utf-8')
    if not argv: sys.exit(__doc__)
    scenes, items, hits = check(argv[0])
    for sid, it, found in hits:
        print(f"⚠ {sid} [{it['id']}] {', '.join(found)}\n    왜: {it['symptom']}\n    고치기: {it['fix']}")
    print(f"{len(scenes)}장면 × 규칙 {len(items)}개 → " + (f'걸림 {len(hits)}건' if hits else '통과'))
    sys.exit(1 if hits else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
