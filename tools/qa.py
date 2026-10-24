"""업로드 전 전체 검수 — 사람이 끝까지 보기 전에 기계가 먼저 잡는다. 결과: videos/<slug>/qa/QA-<합본>.md

사용: python tools/qa.py videos/<slug> final-v1            → 보고서(⚠ 개수 요약 + 직접 확인 목록)
      python tools/qa.py videos/<slug> final-v1 --gate     → 업로드 가능 여부(⚠ 0 · 직접 확인 모두 [x] · 검수 뒤 합본 안 바뀜), 아니면 종료 코드 2

검사 여섯 가지
 ① 판 사슬   대본(script.json) = 음성(voices.json)인가, 음성 파일보다 클립 렌더가 새것인가, 클립보다 합본이 새것인가
             → '대본을 고쳤는데 음성을 안 다시 만듦', '음성은 새로 만들었는데 클립을 안 다시 찍음'이 가장 흔한 사고다.
 ② 싱크      클립 길이 = 그 클립 음성 길이(장면마다 +0.22초)인가, 합본 안에서 장면마다 음성이 계획한 시각에 나오는가(상호상관으로 ms 단위),
             합본의 영상/소리 길이가 같은가 → 화면 신호는 단어 시각으로 만들므로 음성 위치가 맞으면 화면도 맞다.
 ③ 발음      장면 음성을 받아써(ElevenLabs Speech to Text, 없으면 faster-whisper) 대본과 자모 단위로 대조, 영어 낱말이 들리는지, 소문자 영어 표기
 ④ 배경음    배경음만 다시 뽑아(bgm.py bgm-only) 구간마다 계획한 곡·지점이 나오는지, 다른 곡·같은 곡 다른 지점이 섞였는지(두 곡 겹침 사고)
 ⑤ 화면·소리 검은 화면·5초 넘게 멈춘 화면, 음량(LUFS·true peak), 3초 간격 프레임 시트(qa/sheet-N.jpg — 직접 열어 본다)
 ⑥ 재발      tools/regressions.json(전에 고친 문제 목록)의 대본·코드·배경음 계획 검사 + 직접 확인 목록
예외: 확인이 끝난 장면·검사는 qa/ok.json {"장면 id 또는 검사 id": "사유"}. 받아쓰기는 qa/transcripts.json에 캐시(음성 해시별).
"""
import difflib, json, os, re, subprocess, sys, urllib.request, uuid
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest
from pathlib import Path
import numpy as np

SR, GAP, FPS = 8000, 0.22, 30
TOOLS = Path(__file__).resolve().parent; KIT = TOOLS.parent
REG = json.loads((TOOLS / 'regressions.json').read_text(encoding='utf-8'))['items']
READ = {'ai': ['에이아이'], 'ceo': ['씨이오', '시이오'], 'k': ['케이'], 'd': ['디'], 'mcp': ['엠씨피'], 'api': ['에이피아이']}   # 영어 낱말을 한글로 받아 적었을 때 맞게 읽은 것으로 볼 표기
NUMW = r'[0-9]|열|스물|스무|서른|마흔|쉰|하나|한|둘|두|셋|세|넷|네|다섯|여섯|일곱|여덟|아홉|일|이|삼|사|오|육|칠|팔|구|십|백|천|만|억'   # 받아쓰기가 숫자로 적는 말


def sh(cmd): return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')


def probe(p, *a): return sh(['ffprobe', '-v', 'error', *a, '-of', 'csv=p=0', str(p)]).stdout.strip()


def dur(p): return float(probe(p, '-show_entries', 'format=duration'))


def load(path, ss=None, t=None):
    cut = (['-ss', f'{ss:.3f}'] if ss is not None else []) + (['-t', f'{t:.3f}'] if t is not None else [])
    out = subprocess.run(['ffmpeg', '-v', 'error', *cut, '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(out, np.float32).astype(np.float64)


def clip_of(sid): return sid.split('-')[0]


class Video:
    def __init__(self, folder, final):
        self.F = Path(folder).resolve(); self.R = self.F / 'renders'; self.name = final
        self.final, self.nobgm = self.R / f'{final}.mp4', self.R / f'{final}-nobgm.mp4'
        self.P = json.loads((self.F / 'script.json').read_text(encoding='utf-8'))
        self.spans = {x['clip']: x for x in json.loads((self.R / f'{final}.json').read_text(encoding='utf-8'))} if (self.R / f'{final}.json').exists() else {}
        self.voices = {}
        for vf in sorted(self.R.glob('voice-*/voices.json')):
            for v in json.loads(vf.read_text(encoding='utf-8')): self.voices[v['id']] = v
        okf = self.F / 'qa' / 'ok.json'; self.ok = json.loads(okf.read_text(encoding='utf-8')) if okf.exists() else {}

    def clip_file(self, c):
        return self.R / self.spans[c]['file'] if c in self.spans else None


# ───────── ① 판 사슬 ─────────
def check_chain(V, lines):
    bad = 0; pron = list(((V.P.get('settings') or {}).get('pron') or {}).items())
    say = lambda t: __import__('functools').reduce(lambda a, kv: a.replace(*kv), pron, t)
    nw = lambda s: re.sub(r'\W', '', s)
    for s in V.P['scenes']:
        v = V.voices.get(s['id'])
        if not v: bad += 1; lines.append(f'- ⚠ `{s["id"]}` 음성 없음 → python tools/voice.py videos/{V.F.name} {clip_of(s["id"])}'); continue
        said = ' '.join(w['text'] for w in v['words'])
        if nw(said) not in (nw(s['text']), nw(say(s['text']))):
            bad += 1; lines.append(f'- ⚠ `{s["id"]}` 대본 ≠ 음성(대본을 고친 뒤 음성을 다시 만들지 않음)\n  - 대본: {s["text"]}\n  - 음성: {said}')
    for c in dict.fromkeys(clip_of(s['id']) for s in V.P['scenes']):
        f = V.clip_file(c)
        if f is None: bad += 1; lines.append(f'- ⚠ {c}: 합본에 클립 없음'); continue
        ws = [V.F / V.voices[s['id']]['wav'] for s in V.P['scenes'] if clip_of(s['id']) == c and s['id'] in V.voices]
        if ws and max(w.stat().st_mtime for w in ws) > f.stat().st_mtime: bad += 1; lines.append(f'- ⚠ {c}: 음성이 {f.name}보다 새것 → 클립을 판 올려 다시 렌더')
        if f.stat().st_mtime > V.final.stat().st_mtime: bad += 1; lines.append(f'- ⚠ {f.name}이 {V.name}보다 새것 → 합본을 다시')
        lines.append(f'- {c}: {f.name}')
    return bad


# ───────── ② 싱크 ─────────
def xcorr_offset(hay, needle, center, win):
    """hay에서 needle이 center(샘플) ±win 안 어디서 가장 닮았나 → (어긋남 초, 닮음)."""
    a, b = max(0, center - win), min(len(hay), center + win + len(needle))
    seg = hay[a:b]
    if len(seg) < len(needle) or (needle ** 2).sum() < 1e-9: return None, 0.0
    N = 1 << int(np.ceil(np.log2(len(seg) + len(needle))))
    c = np.fft.irfft(np.fft.rfft(seg, N) * np.conj(np.fft.rfft(needle, N)), N)[:len(seg) - len(needle) + 1]
    cs = np.concatenate([[0.0], np.cumsum(seg ** 2)]); en = np.sqrt((cs[len(needle):] - cs[:-len(needle)])[:len(c)] * (needle ** 2).sum()) + 1e-12
    r = c / en; i = int(np.argmax(r))
    return (a + i - center) / SR, float(r[i])


def check_sync(V, lines, tol=.06):
    bad = 0; hay = load(V.nobgm) if V.nobgm.exists() else None
    if hay is None: lines.append(f'- ⚠ {V.nobgm.name} 없음 → make_final.py로 합본 다시'); return 1
    offs = []
    for c, sp in V.spans.items():
        if c == 'outro': continue
        sc = [s for s in V.P['scenes'] if clip_of(s['id']) == c and s['id'] in V.voices]
        want = sum(round((V.voices[s['id']]['duration'] + GAP) * FPS) for s in sc) / FPS; got = sp['end'] - sp['start']
        ok = abs(want - got) <= 1.5 / FPS; bad += not ok
        lines.append(f"- {'✅' if ok else '⚠'} {c}: 클립 {got:.2f}초 / 음성 기준 {want:.2f}초" + ('' if ok else ' → 음성을 바꾼 뒤 클립을 다시 안 찍음(장면 신호가 어긋남)'))
        t = sp['start']
        for s in sc:
            v = V.voices[s['id']]
            if not v.get('demo'):
                needle = load(V.F / v['wav'], 0, min(3.0, v['duration']))
                off, r = xcorr_offset(hay, needle, int(t * SR), int(.5 * SR))
                if off is None: pass
                elif r < .3: bad += s['id'] not in V.ok; lines.append(f'- ⚠ `{s["id"]}` {t:.2f}초 근처에서 이 장면 음성을 못 찾음(닮음 {r:.2f}) — 다른 판 음성이 들어갔을 수 있음')
                else:
                    offs.append(off)
                    if abs(off) > tol and s['id'] not in V.ok: bad += 1; lines.append(f'- ⚠ `{s["id"]}` 음성이 계획보다 {off * 1000:+.0f}ms(화면 신호와 어긋남, 기준 ±{tol * 1000:.0f}ms)')
            t += round((v['duration'] + GAP) * FPS) / FPS
    if offs: lines.append(f'- 장면 음성 위치: {len(offs)}장면, 어긋남 중앙 {np.median(offs) * 1000:+.0f}ms · 최대 {max(map(abs, offs)) * 1000:.0f}ms(AAC 지연 수십 ms는 정상)')
    elif all(v.get('demo') for v in V.voices.values()): lines.append('- (데모 음성은 무음이라 위치 대조를 건너뜀)')
    vd, ad = float(probe(V.final, '-select_streams', 'v:0', '-show_entries', 'stream=duration')), float(probe(V.final, '-select_streams', 'a:0', '-show_entries', 'stream=duration'))
    ok = abs(vd - ad) <= .15; bad += not ok
    lines.append(f"- {'✅' if ok else '⚠'} 합본 영상 {vd:.2f}초 / 소리 {ad:.2f}초")
    return bad


# ───────── ③ 발음 ─────────
def jamo(s):
    out = []
    for ch in s:
        c = ord(ch) - 0xAC00
        out += [chr(0x1100 + c // 588), chr(0x1161 + c % 588 // 28)] + ([chr(0x11A7 + c % 28)] if c % 28 else []) if 0 <= c < 11172 else [ch]
    return ''.join(out)


def sim(a, b):
    """자모 단위 유사도(메일/매일처럼 소리가 같은 표기는 거의 같게). 숫자 표기 차이(열 번/10번)를 뺀 값과 큰 쪽."""
    n = lambda s: re.sub(r'\W', '', s.lower())
    r = lambda x, y: difflib.SequenceMatcher(None, jamo(x), jamo(y), autojunk=False).ratio()
    return max(r(n(a), n(b)), r(re.sub(NUMW, '', n(a)), re.sub(NUMW, '', n(b))))


def stt_eleven(wav):
    key = os.environ['ELEVENLABS_API_KEY']; bd = uuid.uuid4().hex
    body = (f'--{bd}\r\nContent-Disposition: form-data; name="model_id"\r\n\r\nscribe_v1\r\n'
            f'--{bd}\r\nContent-Disposition: form-data; name="language_code"\r\n\r\nkor\r\n'
            f'--{bd}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode() + Path(wav).read_bytes() + f'\r\n--{bd}--\r\n'.encode()
    req = urllib.request.Request('https://api.elevenlabs.io/v1/speech-to-text', body, {'xi-api-key': key, 'Content-Type': f'multipart/form-data; boundary={bd}'})
    with urllib.request.urlopen(req, timeout=120) as r: return json.loads(r.read())['text']


def transcriber():
    if os.environ.get('ELEVENLABS_API_KEY'): return 'elevenlabs', stt_eleven
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None, None
    m = WhisperModel('small', device='cpu', compute_type='int8')
    return 'faster-whisper', lambda wav: ' '.join(s.text.strip() for s in m.transcribe(str(wav), language='ko')[0])


def check_voice(V, lines):
    real = [v for v in V.voices.values() if not v.get('demo')]
    if not real: lines.append('- (데모 음성뿐이라 받아쓰기를 건너뜀)'); return 0
    cf = V.F / 'qa' / 'transcripts.json'; cache = json.loads(cf.read_text(encoding='utf-8')) if cf.exists() else {}; bad = 0; fn = None
    for v in real:
        text = ' '.join(w['text'] for w in v['words']); key = v.get('hash') or v['wav']
        if key not in cache:
            if fn is None:
                who, fn = transcriber()
                if fn is None: lines.append('- ⚠ 받아쓰기 도구 없음 → ELEVENLABS_API_KEY를 넣거나 pip install faster-whisper'); return 1
                lines.append(f'- 받아쓰기: {who}')
            cache[key] = fn(V.F / v['wav'])
        got = cache[key]; r = sim(text, got); heard = re.sub(r'\s', '', got.lower())
        lower = re.findall(r'(?<![A-Za-z])[a-z]{2,}(?![A-Za-z])', text)
        unheard = [w for w in dict.fromkeys(re.findall(r'[A-Za-z][A-Za-z0-9]*', text)) if w.lower() not in heard and not any(x in heard for x in READ.get(w.lower(), []))]
        issues = ([f'소문자 영어 {",".join(lower)}'] if lower else []) + ([f'안 들린 영어 {",".join(unheard)}'] if unheard else []) + ([f'글자 차이 큼 r={r:.2f}'] if r < .8 else [])
        if not issues: continue
        if v['id'] in V.ok: lines.append(f'- ✔ `{v["id"]}` 확인됨: {V.ok[v["id"]]} ({"; ".join(issues)})'); continue
        bad += 1; lines.append(f'- ⚠ `{v["id"]}` {"; ".join(issues)}\n  - 대본: {text}\n  - 들림: {got}')
    cf.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding='utf-8')
    if not bad: lines.append(f'- ✅ {len(real)}장면 받아쓰기 = 대본')
    return bad


# ───────── ④ 배경음 ─────────
def matcher(song, L):
    N = 1 << int(np.ceil(np.log2(len(song) + L))); S = np.fft.rfft(song, N); cs = np.concatenate([[0.0], np.cumsum(song ** 2)])
    def f(win):
        c = np.fft.irfft(S * np.conj(np.fft.rfft(win, N)), N)[:len(song) - L + 1]
        return c / (np.sqrt((cs[L:L + len(c)] - cs[:len(c)]) * (win ** 2).sum()) + 1e-9)
    return f


def best(r, d, skip=None):
    if skip is not None: r = np.where(np.abs((np.arange(len(r)) / SR - skip + d / 2) % d - d / 2) < 2, -1, r)
    i = int(np.argmax(r)); return float(r[i]), i / SR


def check_bgm(V, lines):
    pf = V.R / f'{V.name}-bgm.json'
    if not pf.exists(): lines.append('- (bgm.json 없이 만든 합본 — 배경음 검사 없음)'); return 0
    plan = json.loads(pf.read_text(encoding='utf-8')); segs = plan['segments']
    stem_f = V.F / 'qa' / f'{V.name}-bgm-only.wav'
    if not stem_f.exists() or stem_f.stat().st_mtime < max(pf.stat().st_mtime, V.nobgm.stat().st_mtime):
        r = sh([sys.executable, str(TOOLS / 'bgm.py'), str(V.nobgm), str(pf), str(stem_f), 'bgm-only'])
        if r.returncode: lines.append('- ⚠ bgm-only 실패: ' + r.stderr[-300:]); return 1
    songs = {k: load(p) for k, p in plan['files'].items()}; sd = {k: len(s) / SR for k, s in songs.items()}
    W = 4; L = W * SR; PLAN_MIN, EXTRA_MIN, RESID_MIN, MIX_MIN = .6, .35, .05, .03
    ext = {k: np.concatenate([s, s[:L + SR]]) for k, s in songs.items()}; M = {k: matcher(s, L) for k, s in ext.items()}
    st = load(stem_f); bad = 0
    nc = lambda a, b: float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12))
    piece = lambda k, p: ext[k][int((p % sd[k]) * SR):int((p % sd[k]) * SR) + L]

    def remove(x, y, blk=int(.25 * SR)):   # 덕킹으로 크기가 바뀌니 0.25초마다 크기를 맞춰 계획 곡을 뺀다
        out = x.copy()
        for i in range(0, len(x), blk):
            yy = y[i:i + blk]; out[i:i + blk] -= yy * ((x[i:i + blk] * yy).sum() / ((yy * yy).sum() + 1e-12))
        return out

    def aligned(x, k, p):
        bc, by = -1.0, None
        for d in range(-int(.05 * SR), int(.05 * SR) + 1, max(1, int(.0025 * SR))):
            y = piece(k, p + d / SR)
            if len(y) == L and (c := nc(x, y)) > bc: bc, by = c, y
        return bc, by
    for a, b, key, off, *_ in segs:
        span = b - a
        for T in ([a + max(.6, (span - W) / 2)] if span < W + 8 else [a + max(.6, span * f - W / 2) for f in (.3, .75)]):
            if T + W > min(b - .6, len(st) / SR): continue
            x = st[int(T * SR):int(T * SR) + L]; m, s = divmod(int(T), 60)
            if (x ** 2).mean() < 1e-8: bad += 1; lines.append(f'- ⚠ {m}:{s:02d} 계획 {key} — 배경음이 나오지 않음'); continue
            exp = (off + T - a) % sd[key]; r, y = aligned(x, key, exp)
            if r < PLAN_MIN:
                rr, pos = best(M[key](x), sd[key]); bad += 1
                lines.append(f'- ⚠ {m}:{s:02d} 계획 {key} {exp:.1f}초 지점 → 못 찾음(닮음 {r:.2f}, 가장 닮은 곳 {pos:.1f}초 {rr:.2f})'); continue
            resid = remove(x, y); left = float((resid ** 2).sum() / ((x ** 2).sum() + 1e-12)); others = []
            if left >= RESID_MIN:
                for k in songs:
                    rk, pk = best(M[k](resid), sd[k], skip=exp if k == key else None)
                    if k == key and nc(piece(key, exp), piece(key, pk)) >= .3: continue   # 곡 자체의 반복 소절
                    if rk >= EXTRA_MIN and left * rk * rk >= MIX_MIN: others.append(f'{k} {pk:.1f}초 지점(섞인 크기 {left * rk * rk * 100:.0f}%)')
            bad += bool(others)
            lines.append(f'- {"⚠" if others else "✅"} {m}:{s:02d} 계획 {key} {exp:.1f}초 지점 → 맞음(닮음 {r:.2f})' + (f' / 같이 나옴: {", ".join(others)}' if others else ''))
    return bad


# ───────── ⑤ 화면·소리 ─────────
def check_av(V, lines):
    f, Q = V.final, V.F / 'qa'; bad = 0
    for old in Q.glob('sheet-*.jpg'): old.unlink()
    fonts = TOOLS / 'realkit' / 'fonts'   # drawtext 글꼴: 키트 글꼴을 그 폴더에서 이름만으로 넘긴다(윈도 경로의 ':' 이스케이프 문제 회피)
    font = next(iter(sorted(fonts.glob('*.ttf'))), None) if fonts.exists() else None
    tile = "fps=1/3,scale=384:-2," + (f"drawtext=fontfile='{font.name}':" if font else "drawtext=") + "text='%{pts\\:hms}':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=10x5"
    jobs = [['ffmpeg', '-v', 'info', '-i', str(f), '-an', '-vf', 'scale=480:-2,blackdetect=d=0.3:pix_th=0.10,freezedetect=n=0.003:d=5', '-f', 'null', '-'],
            ['ffmpeg', '-v', 'info', '-i', str(f), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-']]
    with ThreadPoolExecutor(2) as ex: scan, loud = ex.map(sh, jobs)
    sheet = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(f), '-an', '-vf', tile, str((Q / 'sheet-%d.jpg').resolve())], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', cwd=str(fonts) if font else None)
    if sheet.returncode:
        sh(['ffmpeg', '-v', 'error', '-y', '-i', str(f), '-an', '-vf', 'fps=1/3,scale=384:-2,tile=10x5', str(Q / 'sheet-%d.jpg')]); lines.append('- (시트 시각 표시 실패 → 칸 번호×3초로 읽기)')
    vd = dur(f); wh = probe(f, '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate')
    lines.append(f'- {wh}, {vd:.2f}초')
    for s, e in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', scan.stderr):
        edge = float(s) < .5 or float(e) > vd - 3; bad += not edge
        lines.append(f'- {"(처음·끝)" if edge else "⚠"} 검은 화면 {float(s):.1f}~{float(e):.1f}초')
    for s, e in zip_longest(re.findall(r'freeze_start: ([\d.]+)', scan.stderr), re.findall(r'freeze_end: ([\d.]+)', scan.stderr), fillvalue=f'{vd:.1f}'):
        lines.append(f'- 확인: 5초 넘게 멈춘 화면 {float(s):.1f}~{float(e):.1f}초(정지 캡처면 정상, 멈춤 사고면 고침)')
    I = re.findall(r'I:\s+(-?[\d.]+) LUFS', loud.stderr); Pk = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', loud.stderr)
    if I and Pk:
        i, p = float(I[-1]), float(Pk[-1]); warn = not -20 <= i <= -12 or p > -1.0
        if warn and V.voices and all(v.get('demo') for v in V.voices.values()): lines.append(f'- (데모 무음 음성이라 음량 기준 제외: {i:.1f} LUFS)')
        else: bad += warn; lines.append(f'- {"⚠" if warn else "✅"} 음량 {i:.1f} LUFS, true peak {p:.1f} dBFS(기준: -20~-12 LUFS, peak -1 이하)')
    lines.append(f'- 프레임 시트: {", ".join(p.name for p in sorted(Q.glob("sheet-*.jpg"), key=lambda p: int(p.stem.split("-")[1])))} → 직접 열어 겹침·빈 화면·잘림·가림 누락을 본다')
    return bad


# ───────── ⑥ 재발 ─────────
def check_regress(V, lines):
    bad = 0; pf = V.R / f'{V.name}-bgm.json'
    plan = json.loads(pf.read_text(encoding='utf-8')) if pf.exists() else None
    segs = sorted(plan['segments'], key=lambda x: x[0]) if plan else []; total = dur(V.final)
    for it in REG:
        hits, k = [], it['kind']
        if k == 'script':
            hits = [(s['id'], ', '.join(dict.fromkeys(m.group(0) for m in re.finditer(it['pattern'], s['text'])))) for s in V.P['scenes']
                    if re.search(it['pattern'], s['text']) and not (it.get('unless') and re.search(it['unless'], s['text']))]
        elif k == 'code':
            for f in it['files']:
                path = Path(f.replace('{video}', str(V.F))) if f.startswith('{video}') else KIT / f
                for p in ([path] if path.is_file() else sorted(path.parent.glob(path.name))):
                    if p.exists() and any(it['forbid'] in ln.split('#')[0] for ln in p.read_text(encoding='utf-8').splitlines()): hits.append((p.name, f"'{it['forbid']}' 사용"))
        elif k == 'plan':
            if not segs: continue
            if it['id'] == 'bgm-plan-gaps':
                if segs[0][0] > .05: hits.append(('계획', f'0~{segs[0][0]:.2f}초 배경음 없음'))
                for x, y in zip(segs, segs[1:]):
                    if y[0] < x[1] - .05: hits.append(('계획', f'{y[0]:.2f}초 구간이 앞 구간 끝({x[1]:.2f}) 전에 시작 — 겹침'))
                    elif y[0] > x[1] + .05: hits.append(('계획', f'{x[1]:.2f}~{y[0]:.2f}초 빈 구간'))
                if segs[-1][1] < total - .5: hits.append(('계획', f'{segs[-1][1]:.2f}초 뒤 배경음 없음(영상 {total:.2f}초)'))
            elif it['id'] == 'bgm-whole-song':
                sd = {key: dur(p) for key, p in plan['files'].items()}
                for i, (a0, b0, k0, off0, *_) in enumerate(segs):
                    prev = segs[i - 1] if i else None
                    cont = prev and prev[2] == k0 and abs(prev[3] + prev[1] - prev[0] - off0) < 1
                    if off0 > 1 and not cont: hits.append((f'{int(a0 // 60)}:{int(a0 % 60):02d}', f'{k0}를 {off0:.0f}초 지점부터 다시 꺼냄'))
                    if i + 1 < len(segs) and segs[i + 1][2] != k0 and b0 < total - 1 and off0 + b0 - a0 < sd[k0] - 15:
                        hits.append((f'{int(b0 // 60)}:{int(b0 % 60):02d}', f'{k0}가 끝나기 {sd[k0] - off0 - (b0 - a0):.0f}초 전에 다음 곡으로 바꿈'))
        else:
            if k != 'look': lines.append(f"- ↪ {it['id']} — {it['symptom']}: {it['fix']}")
            continue
        hits = [(w, h) for w, h in hits if w not in V.ok and it['id'] not in V.ok and f"{it['id']}:{w}" not in V.ok]
        bad += bool(hits)
        lines.append(f"- {'⚠' if hits else '✅'} {it['id']} — {it['symptom']}" + ''.join(f"\n  - `{w}`: {h} → {it['fix']}" for w, h in hits))
    return bad


def look_items(keep):
    items = [(it['id'], f"{it['symptom']} → {it['fix']}") for it in REG if it['kind'] == 'look']
    items.append(('feedback-items', '영상 폴더 FEEDBACK-ITEMS.md의 미반영 항목이 이 판에 모두 들어갔는지'))
    return [keep.get(i) or f'- [ ] {i} — {d}' for i, d in items]


def sig(f): st = f.stat(); return f'{st.st_size}:{int(st.st_mtime)}'


def gate(F, final):
    rep, f = F / 'qa' / f'QA-{final}.md', F / 'renders' / f'{final}.mp4'
    if not rep.exists(): return [f'검수 보고서 없음 → python tools/qa.py {F} {final}']
    t = rep.read_text(encoding='utf-8'); why = []
    if f'sig {sig(f)}' not in t: why.append('검수 뒤에 합본이 바뀜 → 검수 다시')
    m = re.search(r'요약\(⚠ 개수\): ([^.]*)\.', t)
    if not m or any(int(x) for x in re.findall(r' (\d+)', m.group(1))): why.append(f'⚠ 남음({m.group(1) if m else "요약 없음"})')
    left = re.findall(r'^- \[ \] (\S+)', t, re.M)
    if left: why.append('직접 확인 안 한 항목: ' + ', '.join(left))
    return why


PARTS = [('판 사슬', '대본 → 음성 → 클립 → 합본', check_chain), ('싱크', '음성 위치·클립 길이·영상/소리 길이', check_sync),
         ('발음', '받아쓰기 ↔ 대본', check_voice), ('배경음', '구간마다 계획한 곡만', check_bgm),
         ('화면·소리', '검은·멈춘 화면, 음량, 시트', check_av), ('재발', '전에 고친 문제 — tools/regressions.json', check_regress)]


def main(folder, final):
    V = Video(folder, final); (V.F / 'qa').mkdir(exist_ok=True)
    if not V.final.exists(): sys.exit(f'{V.final} 없음 → python tools/make_final.py {folder} {final}')
    outs = [[] for _ in PARTS]
    with ThreadPoolExecutor(len(PARTS)) as ex: counts = list(ex.map(lambda i: PARTS[i][2](V, outs[i]), range(len(PARTS))))
    out = V.F / 'qa' / f'QA-{final}.md'; keep = {}
    if out.exists() and f'sig {sig(V.final)}' in (old := out.read_text(encoding='utf-8')):   # 같은 합본이면 직접 확인 결과를 지우지 않는다
        keep = {m.group(1): m.group(0) for m in re.finditer(r'^- \[x\] (\S+).*$', old, re.M)}
    lines = [f'# 업로드 전 전체 검수 — {final}', '', '요약(⚠ 개수): ' + ', '.join(f'{p[0]} {n}' for p, n in zip(PARTS, counts))
             + '. 0이 아니면 고친 뒤 다시 돌린다. 아래 직접 확인을 모두 [x]로 채워야 업로드(--gate).', f'합본 renders/{final}.mp4 (sig {sig(V.final)})']
    for (name, desc, _), n, body in zip(PARTS, counts, outs): lines += ['', f'## {name}({desc}) — ⚠ {n}', *body]
    lines += ['', '## 직접 확인(프레임 시트 → 의심 구간은 원본 크기로) — 확인 뒤 [x]와 결과 메모', *look_items(keep)]
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(out); print(lines[2])
    return sum(counts)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    a = sys.argv[1:]
    if len(a) < 2: sys.exit(__doc__)
    if '--gate' in a:
        why = gate(Path(a[0]).resolve(), a[1]); print('업로드 가능' if not why else '멈춤: ' + ' / '.join(why)); sys.exit(2 if why else 0)
    sys.exit(1 if main(a[0], a[1]) else 0)
