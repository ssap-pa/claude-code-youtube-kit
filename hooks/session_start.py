"""SessionStart 훅: 새 세션·/clear·대화 요약 뒤마다 학습 메모리 목록과 현재 영상의 미반영 피드백을 Claude에게 넣는다.
출력(stdout)이 그대로 세션 맥락이 된다. 규칙 본문은 넣지 않는다 — 목록만 넣고, 관련 규칙은 Claude가 파일을 열어 읽는다(맥락 절약)."""
import json, re, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = ['[유튜브 자동화 키트] 작업 전에 아래 학습 메모리를 확인하고, 지금 작업과 관련된 규칙 파일(memory/rules/…)을 열어 적용하세요.']
    cfg = KIT / 'config' / 'channel.json'
    if (KIT / '.claude' / 'skills' / 'kit-setup').exists():
        c = json.loads(cfg.read_text(encoding='utf-8')) if cfg.exists() else {}
        if not c.get('setup_done'):
            out.append('[처음 세팅 전] 채널·목소리·배경음·썸네일·아이콘 스타일이 아직 정해지지 않았어요. 영상 작업을 시작하기 전에 kit-setup 스킬로 처음 세팅을 먼저 제안하세요(사용자가 원하면 건너뛰기 가능, 그때는 예시 기본값).'
                       + ('' if (c.get('voice') or {}).get('voice_id') else
                          ' 단, 목소리(voice_id)만은 건너뛰지 않는다 — 비어 있으면 음성을 만들 수 없다. python tools/voice.py --voices로 목록을 보여 주고 하나 고르게 한다(내 목소리가 없으면 기본 제공 목소리 중 설명형 하나를 추천).'))
        else:
            sec = lambda k: c.get(k) or {}
            bgm = '설정됨' if sec('bgm').get('intro') or sec('bgm').get('main') else '미설정(데모 합성음 — 업로드 전 내 곡으로)'
            out.append(f"내 설정(config/channel.json): 채널 {sec('channel').get('name')} · 썸네일 {sec('thumbnail').get('style')}안 · "
                       f"아이콘 {sec('design').get('icons')} · 배경음 {bgm} · 출력 {sec('output').get('resolution')} — 관련 스킬은 이 값을 따른다.")
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
