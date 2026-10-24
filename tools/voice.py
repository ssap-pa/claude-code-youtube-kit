"""대본(script.json) → 장면마다 음성 wav + 단어 시각(voices.json). 화면 신호는 이 단어 시각으로 만든다(음성·화면 싱크의 출발점).

사용: python tools/voice.py videos/<slug> [op v1 …] [--demo] [--force]
      python tools/voice.py --voices      내 계정 목소리와 voice_id(전문 복제한 내 목소리 찾기 — docs/06)
  - 클립 = 장면 id의 '-' 앞부분(op, v1, v2 …). 클립을 안 적으면 대본의 모든 클립.
  - 결과: videos/<slug>/renders/voice-<clip>/voices.json  [{id, wav, duration, words:[{text,start,end}], hash}]
  - 캐시: videos/<slug>/cache/voices/<hash>.wav|json — 대사·목소리·설정이 같으면 다시 합성하지 않는다(크레딧 절약).
  - --demo: API 키 없이 무음 wav + 글자 수 비례 가짜 단어 시각으로 만든다(설치·파이프라인 시험용, 업로드용 아님).

대본 설정(script.json "settings")
  voice: {"voice_id": "...", "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": .5, "similarity_boost": .8, "style": 0, "use_speaker_boost": true, "speed": 1}}
  tones: {"hype": {"stability": .25, "style": .7, "speed": 1.15}, "urgent": {...}}   ← 장면에 "tone": "hype"을 적으면 voice_settings에 덮어쓴다
  pron:  {"2월 2일부터": "이월 이일부터"}   ← 합성에만 쓰는 소리 나는 대로 표기. 화면·대본·단어 시각 글자는 원문 그대로 남는다.
키: 환경변수 ELEVENLABS_API_KEY (파일에 적지 않는다).
"""
import base64, hashlib, json, os, re, subprocess, sys, urllib.request, wave
from pathlib import Path

API = 'https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_192'


def clip_of(sid): return sid.split('-')[0]


def say_of(text, pron):
    for k, v in pron.items(): text = text.replace(k, v)
    return text


def spec(scene, settings):
    v = dict(settings.get('voice') or {}); vs = dict(v.get('voice_settings') or {})
    vs.update((settings.get('tones') or {}).get(scene.get('tone'), {}))
    v['voice_settings'] = vs
    return v


def key_of(scene, v, say):
    return hashlib.sha256(json.dumps([say, v.get('voice_id'), v.get('model_id'), v['voice_settings']], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def probe(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)], capture_output=True, text=True).stdout)


def words_from_alignment(a):
    """글자 단위 정렬 → 띄어쓰기 기준 단어 [{text,start,end}]."""
    words, cur = [], None
    for c, s, e in zip(a['characters'], a['character_start_times_seconds'], a['character_end_times_seconds']):
        if c.isspace():
            if cur: words.append(cur); cur = None
            continue
        if cur is None: cur = {'text': '', 'start': s, 'end': e}
        cur['text'] += c; cur['end'] = e
    if cur: words.append(cur)
    return words


def back_to_original(text, say, words, pron):
    """발음 표기로 합성한 단어 시각을 대본 원문 단어로 되돌린다. 원문 한 단어가 표기에서 여러 단어가 되면 시각을 합친다."""
    if say == text: return words
    orig = text.split()
    if len(orig) == len(words): return [dict(w, text=o) for w, o in zip(words, orig)]
    out, j = [], 0
    for o in orig:
        n = len(say_of(o, pron).split()); g = words[j:j + n]
        if not n or len(g) < n: return words
        out.append({'text': o, 'start': g[0]['start'], 'end': g[-1]['end']}); j += n
    return out if j == len(words) else words


def eleven(v, say, mp3):
    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key: sys.exit('ELEVENLABS_API_KEY가 없습니다. docs/03-음성-ElevenLabs.md를 보세요(시험만 하려면 --demo).')
    if not v.get('voice_id'): sys.exit('script.json settings.voice.voice_id가 비었습니다. 목록: python tools/voice.py --voices / 내 목소리 만들기: docs/06-내-목소리-전문-복제.md')
    body = json.dumps({'text': say, 'model_id': v.get('model_id', 'eleven_multilingual_v2'), 'voice_settings': v['voice_settings']}).encode()
    req = urllib.request.Request(API.format(voice=v['voice_id']), body, {'xi-api-key': key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as r: j = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f'ElevenLabs HTTP {e.code}: {e.read()[:300].decode("utf-8", "replace")}')
    mp3.write_bytes(base64.b64decode(j['audio_base64']))
    return words_from_alignment(j.get('alignment') or j['normalized_alignment'])


def demo(say, wav):
    """무음 + 가짜 단어 시각(글자당 0.13초, 단어 사이 0.08초)."""
    words, t = [], 0.15
    for w in say.split():
        d = 0.13 * len(re.sub(r'\W', '', w) or w); words.append({'text': w, 'start': round(t, 3), 'end': round(t + d, 3)}); t += d + .08
    n = int((t + .2) * 44100)
    with wave.open(str(wav), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100); f.writeframes(b'\0\0' * n)
    return words


def list_voices():
    """내 계정 목소리와 voice_id. 전문 복제(docs/06)가 끝나면 [professional]로 나온다."""
    key = os.environ.get('ELEVENLABS_API_KEY')
    if not key: sys.exit('ELEVENLABS_API_KEY가 없습니다. docs/03-음성-ElevenLabs.md를 보세요.')
    req = urllib.request.Request('https://api.elevenlabs.io/v2/voices?page_size=100&voice_type=personal', headers={'xi-api-key': key})
    with urllib.request.urlopen(req, timeout=60) as r: vs = json.loads(r.read())['voices']
    if not vs: print('내 목소리가 없습니다 — 전문 복제 안내: docs/06-내-목소리-전문-복제.md'); return
    for v in vs: print(f"{v['voice_id']}  [{v.get('category')}]  {v['name']}")
    print('→ script.json settings.voice.voice_id에 넣는다(모든 새 영상에 쓰려면 templates/video/script.json에도).')


def main(argv):
    flags = {a for a in argv if a.startswith('--')}; args = [a for a in argv if not a.startswith('--')]
    if '--voices' in flags: return list_voices()
    if not args: sys.exit(__doc__)
    F = Path(args[0]).resolve(); P = json.loads((F / 'script.json').read_text(encoding='utf-8'))
    settings, pron = P.get('settings') or {}, (P.get('settings') or {}).get('pron') or {}
    clips = args[1:] or list(dict.fromkeys(clip_of(s['id']) for s in P['scenes']))
    cache = F / 'cache' / ('voices-demo' if '--demo' in flags else 'voices'); cache.mkdir(parents=True, exist_ok=True)
    made = used = 0
    for c in clips:
        out, res = F / 'renders' / f'voice-{c}', []
        out.mkdir(parents=True, exist_ok=True)
        for s in [s for s in P['scenes'] if clip_of(s['id']) == c]:
            v = spec(s, settings); say = say_of(s['text'], pron); h = key_of(s, v, say)
            wav, meta = cache / f'{h}.wav', cache / f'{h}.json'
            if '--force' in flags or not (wav.exists() and meta.exists()):
                if '--demo' in flags: words = demo(say, wav)
                else:
                    mp3 = cache / f'{h}.mp3'; words = eleven(v, say, mp3)
                    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp3), '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', str(wav)], check=True)
                    mp3.unlink()
                meta.write_text(json.dumps({'hash': h, 'say': say, 'words': back_to_original(s['text'], say, words, pron)}, ensure_ascii=False), encoding='utf-8')
                made += 1; used += len(say)
            m = json.loads(meta.read_text(encoding='utf-8'))
            res.append({'id': s['id'], 'wav': os.path.relpath(wav, F).replace('\\', '/'), 'duration': round(probe(wav), 3), 'words': m['words'], 'hash': h,
                        'demo': '--demo' in flags})
        (out / 'voices.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'{c}: {len(res)}장면 {sum(r["duration"] for r in res):.1f}초 → {out / "voices.json"}')
    print(f'새로 합성 {made}장면({used}자), 나머지는 캐시')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main(sys.argv[1:])
