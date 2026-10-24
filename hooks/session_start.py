"""SessionStart 훅: 새 세션·/clear·대화 요약 뒤마다 학습 메모리 목록과 현재 영상의 미반영 피드백을 Claude에게 넣는다.
출력(stdout)이 그대로 세션 맥락이 된다. 규칙 본문은 넣지 않는다 — 목록만 넣고, 관련 규칙은 Claude가 파일을 열어 읽는다(맥락 절약)."""
import json, re, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = ['[유튜브 자동화 키트] 작업 전에 아래 학습 메모리를 확인하고, 지금 작업과 관련된 규칙 파일(memory/rules/…)을 열어 적용하세요.']
    idx = KIT / 'memory' / 'INDEX.md'
    out.append(idx.read_text(encoding='utf-8') if idx.exists() else '(memory/INDEX.md 없음)')
    skills = sorted(p.parent.name for p in (KIT / '.claude' / 'skills').glob('*/SKILL.md'))
    out.append('스킬: ' + ', '.join(skills) + ' — 피드백 저장은 feedback-loop' + (', 영상 제작은 youtube-video' if 'youtube-video' in skills else '') + '.')
    cur = KIT / '.current-video'
    if cur.exists() and (slug := cur.read_text(encoding='utf-8').strip()):
        fi = KIT / 'videos' / slug / 'FEEDBACK-ITEMS.md'
        out.append(f'현재 영상: videos/{slug}')
        if fi.exists():
            todo = [ln for ln in fi.read_text(encoding='utf-8').splitlines() if re.match(r'\s*- \[ \]', ln)]
            out.append(f'이 영상의 미반영 피드백 {len(todo)}개' + (':\n' + '\n'.join(todo[:20]) if todo else ''))
    inbox = KIT / 'memory' / 'inbox.jsonl'
    if inbox.exists():
        new = [json.loads(x) for x in inbox.read_text(encoding='utf-8').splitlines() if x.strip()]
        new = [r for r in new if r.get('status', 'new') == 'new' and r.get('feedback')]
        if new: out.append(f'분류 안 된 피드백 후보 {len(new)}개 → feedback-loop 스킬로 정리(python tools/memory.py inbox)')
    print('\n\n'.join(out))


if __name__ == '__main__':
    main()
