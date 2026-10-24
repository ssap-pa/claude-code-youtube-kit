"""UserPromptSubmit 훅: 사용자가 보낸 말을 memory/inbox.jsonl에 남기고, 고칠 점·앞으로의 규칙으로 보이면 저장 절차를 Claude에게 상기시킨다.
판단은 Claude가 한다 — 이 훅은 원문을 잃지 않게 기록하고 놓치지 않게 알려 주는 안전장치다(단어 목록은 넓게, 차단은 하지 않는다)."""
import datetime as dt, hashlib, json, re, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
HINT = re.compile(r'말고|대신|바꿔|고쳐|수정|빼|넣어|하지 ?마|쓰지 ?마|다시|앞으로|항상|매번|절대|별로|이상해|어색|틀렸|아니야|아니라|너무|작아|커|느려|빨라|늦|안 ?들려|안 ?보여|겹|잘려|규칙|기억해|저장해')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8') or '{}')
    except ValueError:
        return
    prompt = (data.get('prompt') or '').strip()
    if not prompt or prompt.startswith('/'): return
    cur = KIT / '.current-video'; video = cur.read_text(encoding='utf-8').strip() if cur.exists() else ''
    fb = bool(HINT.search(prompt)); now = dt.datetime.now().isoformat(timespec='seconds')
    rid = 'fb-' + hashlib.sha1((now + prompt).encode()).hexdigest()[:8]
    (KIT / 'memory').mkdir(exist_ok=True)
    with open(KIT / 'memory' / 'inbox.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'id': rid, 'at': now, 'video': video, 'session': data.get('session_id'), 'feedback': fb, 'prompt': prompt[:4000], 'status': 'new' if fb else 'note'}, ensure_ascii=False) + '\n')
    if fb:
        print(f'[피드백 후보 {rid}] 이 말이 고칠 점이나 앞으로의 규칙이면, 작업을 끝낸 뒤 feedback-loop 스킬대로 분류해 저장하세요: '
              f'이번 영상만 → videos/{video or "<slug>"}/FEEDBACK-ITEMS.md, 앞으로 계속 → memory/rules + INDEX, 일하는 순서 → 스킬, '
              f'다시 생길 수 있는 사고 → tools/regressions.json. 끝나면 python tools/memory.py done {rid} <결과>.')


if __name__ == '__main__':
    main()
