"""학습 메모리(피드백 → 규칙) 관리. Claude Code가 파일을 직접 고쳐도 되고, 사람이 이 명령으로 해도 된다.

구조
  memory/INDEX.md          한 줄 목록 — 세션 시작 훅이 매번 이 파일을 Claude에게 넣는다(짧게 유지)
  memory/rules/<이름>.md    규칙 하나 = 파일 하나(무엇·왜·어떻게, 언제 생겼는지)
  memory/inbox.jsonl       사용자 프롬프트 훅이 남긴 원문(피드백 후보). 분류가 끝나면 status를 바꾼다

사용
  python tools/memory.py add <이름> --area 대본 --rule "숫자+고유어 단위는 한글로" --why "음성이 22번을 이십이 번으로 읽음" [--how "..."]
  python tools/memory.py list [--area 대본]
  python tools/memory.py search <낱말>
  python tools/memory.py inbox [--all]                 분류 안 된 피드백 후보 보기
  python tools/memory.py done <inbox id> <결과>        분류 결과 기록(rule:<이름> · item:<영상> · skill · regression:<id> · ignore)
  python tools/memory.py check                         INDEX ↔ rules 폴더가 맞는지
"""
import argparse, datetime as dt, json, re, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
MEM = KIT / 'memory'; RULES = MEM / 'rules'; INDEX = MEM / 'INDEX.md'; INBOX = MEM / 'inbox.jsonl'
AREAS = ['대본', '음성', '화면', '소스', '배경음', '제목·썸네일', '업로드', '작업 방식']
HEAD = '# 학습 메모리 목록\n\n규칙 하나 = `rules/<이름>.md` 한 개. 새 영상을 시작하기 전에 이 목록을 읽고, 관련 규칙 파일을 열어 적용한다.\n'


def slug(s): return re.sub(r'[^\w가-힣-]+', '-', s.strip()).strip('-').lower()


def parse(p):
    t = p.read_text(encoding='utf-8'); m = re.match(r'---\n(.*?)\n---\n(.*)', t, re.S); meta = {}
    if m:
        for ln in m.group(1).splitlines():
            if ':' in ln: k, v = ln.split(':', 1); meta[k.strip()] = v.strip()
    return meta, (m.group(2) if m else t)


def rebuild_index():
    rows = {}
    for p in sorted(RULES.glob('*.md')):
        meta, _ = parse(p); rows.setdefault(meta.get('area', '작업 방식'), []).append(f"- [{meta.get('title', p.stem)}](rules/{p.name}) — {meta.get('summary', '')}")
    body = HEAD + ''.join(f'\n## {a}\n' + '\n'.join(rows[a]) + '\n' for a in AREAS + sorted(set(rows) - set(AREAS)) if a in rows)
    INDEX.write_text(body, encoding='utf-8')


def add(a):
    RULES.mkdir(parents=True, exist_ok=True); name = slug(a.name); p = RULES / f'{name}.md'; today = dt.date.today().isoformat()
    if p.exists() and not a.force: sys.exit(f'{p.name}가 이미 있습니다 — 같은 규칙이면 그 파일을 고치고, 덮어쓰려면 --force')
    p.write_text(f"---\ntitle: {a.title or a.rule[:40]}\narea: {a.area}\nsummary: {a.rule}\nsince: {today}\n---\n\n"
                 f"**규칙.** {a.rule}\n\n**왜.** {a.why}\n\n**어떻게 적용.** {a.how or a.rule}\n", encoding='utf-8')
    rebuild_index(); print(f'저장: {p.relative_to(KIT)} (INDEX 갱신)')


def inbox(a):
    if not INBOX.exists(): print('비어 있음'); return
    for ln in INBOX.read_text(encoding='utf-8').splitlines():
        r = json.loads(ln)
        if a.all or r.get('status', 'new') == 'new': print(f"{r['id']} [{r.get('status', 'new')}] {r.get('video') or '-'} {r['at'][:16]} {r['prompt'][:120]}")


def done(a):
    rows = [json.loads(x) for x in INBOX.read_text(encoding='utf-8').splitlines()]
    hit = [r for r in rows if r['id'] == a.id]
    if not hit: sys.exit(f'{a.id} 없음')
    hit[0]['status'] = a.result; hit[0]['done_at'] = dt.datetime.now().isoformat(timespec='seconds')
    INBOX.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8'); print(f'{a.id} → {a.result}')


def main(argv):
    ap = argparse.ArgumentParser(description='학습 메모리'); sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('add'); p.add_argument('name'); p.add_argument('--area', choices=AREAS, required=True); p.add_argument('--rule', required=True)
    p.add_argument('--why', required=True); p.add_argument('--how'); p.add_argument('--title'); p.add_argument('--force', action='store_true')
    p = sp.add_parser('list'); p.add_argument('--area')
    p = sp.add_parser('search'); p.add_argument('word')
    p = sp.add_parser('inbox'); p.add_argument('--all', action='store_true')
    p = sp.add_parser('done'); p.add_argument('id'); p.add_argument('result')
    sp.add_parser('check'); sp.add_parser('reindex')
    a = ap.parse_args(argv)
    if a.cmd == 'add': add(a)
    elif a.cmd in ('list', 'search'):
        for f in sorted(RULES.glob('*.md')):
            meta, body = parse(f)
            if (a.cmd == 'list' and (not a.area or meta.get('area') == a.area)) or (a.cmd == 'search' and a.word.lower() in (str(meta) + body).lower()):
                print(f"{f.stem} [{meta.get('area')}] {meta.get('summary')}")
    elif a.cmd == 'inbox': inbox(a)
    elif a.cmd == 'done': done(a)
    elif a.cmd == 'reindex': rebuild_index(); print('INDEX 갱신')
    else:
        idx = INDEX.read_text(encoding='utf-8') if INDEX.exists() else ''
        linked = set(re.findall(r'\(rules/([^)]+)\)', idx)); files = {p.name for p in RULES.glob('*.md')}
        miss, dead = files - linked, linked - files
        print('INDEX 정상' if not (miss or dead) else f'INDEX에 없는 규칙 {sorted(miss)} / 파일 없는 링크 {sorted(dead)} → python tools/memory.py reindex')
        sys.exit(1 if miss or dead else 0)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main(sys.argv[1:])
