"""실사 UI 합성 도구(realkit) — 원본 흐림 배경 + 기기 화면 실제 재생 + HTML 앞 UI를 30fps로 찍어 영상으로 만든다.

층 구성(스킬 real-ui-design 1절)
  ① 배경: 원본 클립·그림을 cover로 키워 흐림·밝기 → JPEG 시퀀스(seq/still). 비네트는 theme-real.css, 느린 밀어 넣기는 data-anim="push".
  ② 기기 화면: 원본 클립을 잘라 휴대폰 화면·창 크기로 → JPEG 시퀀스. HTML의 <img data-seq>가 프레임 시각에 맞춰 넘어간다(실제 재생).
  ③ 앞 UI: 장면 HTML(base.css·theme-real.css·motion.css·realkit.js). CSS 애니메이션은 멈춘 채 currentTime = 프레임 시각.
  → 세 층을 브라우저 안에서 합쳐 찍는다(유리 카드 backdrop-filter가 실제 배경·영상 위에서 계산되게). 프레임은 ffmpeg로 바로 보낸다.

음성·효과음
  Voice(voices.json): 장면 길이 = 음성 + 0.22초(make_final·qa와 같은 계산, 30fps 프레임 단위). T(장면, '단어', n) = 그 단어가 시작하는 시각.
  sfx 이벤트 [{'t': 전체 초, 'kind': 'noti'|'pay'|'tap'|'pop'|'whoosh'|'click'|'tick'|'thud'|'rise'|'swish'|'stamp'|'done'}] → 합성(파일 없음).
  출력: 1920x1080(세로 모드 1080x1920) 30fps H.264(yuv420p) + AAC 48kHz, loudnorm -16 LUFS. 끝까지 디코딩 확인.

사용 예(영상 폴더의 빌드 스크립트에서)
  import sys; sys.path.insert(0, '<키트>/tools/realkit'); import realkit as rk
  V = rk.Voice('renders/voice-op/voices.json', base='.')
  rk.seq('clip.mp4', 'assets/op-real/src/c0_bg', t0=1.0, dur=V.dur('op-c0'), size=(960, 540), blur=8, bright=.76)
  shots = [rk.Shot('assets/op-real/c0.html', ['op-c0'], cues={'ai': V.T('op-c0', 'AI로')}, sfx=[{'t': 1.3, 'kind': 'noti'}])]
  rk.build(V, shots, 'renders/op-real-v1.mp4', workdir='renders/op-real-job')
CLI: python realkit.py shot <job.json>   (build()가 장면마다 병렬로 부른다)
     python realkit.py still <장면.html> <초> <out.png>
     python realkit.py sheet <영상.mp4> <out.jpg> [간격초]
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

KIT = Path(__file__).resolve().parent
FPS = 30
W, H = (1080, 1920) if os.environ.get('RK_FORMAT') == 'vertical' else (1920, 1080)   # 세로 쇼츠: 빌더가 import 전에 os.environ['RK_FORMAT'] = 'vertical'
GAP = 0.22          # 장면 사이 숨(make_final·qa와 같음)


def _ff(args, quiet=True):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *map(str, args)], capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr.decode('utf-8', 'replace')[-2000:])


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True).stdout
    return float(out)


def font(weight='Bold', size=30):
    return ImageFont.truetype(str(KIT / 'fonts' / f'HadaSans-{weight}.ttf'), size)


# ───────────────────────── 음성 ─────────────────────────
_PUNCT = re.compile(r"[\s'\"‘’“”.,!?…·]")


def _norm(s):
    return _PUNCT.sub('', s)


# ── 말 자막의 숫자·단위(Voice.captions) ──
# 대본은 소리 나는 대로 쓴 숫자(음성용), 자막은 숫자. 사고: 낱말 일부도 바꿔 피사→피4, 공사→공4, 만든→1만든, 오면→5면.
_KO_NUM = re.compile(r'(?:[영공일이삼사오육칠팔구십백천만억조]|하나|둘|셋|넷|다섯|여섯|일곱|여덟|아홉|열|스물|스무|서른|마흔|쉰|예순|일흔|여든|아흔|한|두|세|네)+')
UNITS = sorted(('센티미터 밀리미터 킬로미터 제곱미터 킬로그램 미터 센티 밀리 킬로 그램 톤 리터 퍼센트 헥타르 '
                '층 번 개월 개 명 시간 분 초 년 달 주 일 원 달러 배 곳 가지 살 대 도 장 권 채 척 마리 평 회 건 편 위').split(), key=len, reverse=True)
_UNIT = '(?:' + '|'.join(UNITS) + ')'
_PART = '(?:에서|에게|으로|까지|부터|만에|짜리|가량|정도|동안|이나|이에요|예요|입니다|이죠|은|는|이|가|을|를|의|에|도|와|과|로|만|나|쯤|째|씩|죠)'


def _split_punct(w):
    """'"팔백,' → ('"', '팔백', ',') — 앞뒤 문장부호를 떼어 낸 낱말."""
    return re.fullmatch(r'(\W*)(.*?)(\W*)', w, re.S).groups()


def is_unit(core):
    """단위 낱말(+조사): 층·층을·센티미터·미터짜리·대와 …"""
    return bool(core) and bool(re.fullmatch(f'{_UNIT}{_PART}*', core))


def _shows_number(d):
    return bool(re.search(r'\d(?:[.,]\d+)*(?:만|억|천|조)?%?$', d))


def sub_word(w, sub):
    """자막 숫자 바꾸기 — 낱말(앞뒤 문장부호 뗀 것) 전체가 key와 같을 때만 바꾼다.
    두 글자 이상인 숫자 낱말(이백팔십·사십)이나 단위 낱말(센티미터)은 뒤에 조사(은·는·이·가·을·를·의·에·도·와·과·로·으로·만에 …)가
    붙어도 바꾼다. 한 글자 key('사'·'만'·'오')는 낱말 전체가 같을 때만 — '사가'·'오는'·'만에'처럼 다른 뜻과 겹치기 때문.
    붙여 쓴 숫자+단위('사십센티미터')는 숫자를 바꾸고, 단위도 sub에 있으면 같이 바꾼다('40cm')."""
    pre, core, post = _split_punct(w)
    if core in sub: return pre + sub[core] + post
    if _KO_NUM.fullmatch(core): return w   # '삼십이'(32)를 '삼십'+'이'(조사)로 자르지 않는다
    keys = sorted(sub, key=len, reverse=True)
    for k in keys:
        if len(k) < 2 or not core.startswith(k): continue
        num, rest = bool(_KO_NUM.fullmatch(k)), core[len(k):]
        if not (num or is_unit(k)): continue
        if re.fullmatch(f'{_PART}+', rest): return pre + sub[k] + rest + post
        if num and is_unit(rest):
            u = next((u for u in keys if rest.startswith(u) and is_unit(u)), None)
            return pre + sub[k] + (sub[u] + rest[len(u):] if u else rest) + post
    return w


def is_number(w, sub=None):
    """자막에서 숫자로 보이는 낱말(바꾼 뒤 숫자로 끝나거나, 소리 나는 대로 쓴 숫자 낱말)."""
    d = sub_word(w, sub or {})
    return _shows_number(d) or bool(_KO_NUM.fullmatch(_split_punct(w)[1]))


def cap_text(raw_words, sub):
    """자막 한 묶음 글자: 낱말마다 sub_word, 숫자 바로 뒤 단위는 띄우지 않고 붙인다('19층', '1만대와')."""
    out, prev_num = '', False
    for r in raw_words:
        d = sub_word(r, sub)
        out += d if (out and prev_num and is_unit(_split_punct(r)[1])) else (' ' if out else '') + d
        prev_num = _shows_number(d)
    return out


class Voice:
    """voices.json(tools/voice.py 결과: id·wav·duration·words) → 장면별 시작·길이와 단어 시각."""

    def __init__(self, voices_json, base=None, gap=GAP, ids=None):
        vj = Path(voices_json)
        base = Path(base) if base else vj.parent
        data = json.loads(vj.read_text(encoding='utf-8'))
        if ids:
            data = [v for v in data if v['id'] in ids]
        self.scenes, pos = [], 0
        for v in data:
            n = round((v['duration'] + gap) * FPS)
            wav = Path(v['wav'].replace('\\', '/'))
            wav = wav if wav.is_absolute() else base / wav
            self.scenes.append(dict(id=v['id'], wav=wav, duration=v['duration'], words=v.get('words', []),
                                    frames=n, start_frame=pos, start=pos / FPS, dur=n / FPS))
            pos += n
        self.frames, self.total = pos, pos / FPS
        self.by = {s['id']: s for s in self.scenes}

    def __getitem__(self, sid):
        return self.by[sid]

    def start(self, sid):
        return self.by[sid]['start']

    def dur(self, *sids):
        return sum(self.by[s]['frames'] for s in sids) / FPS

    def T(self, sid, word, n=0, base=None, end=False):
        """sid 대사에서 n번째로 word로 시작하는 단어의 시작(end=True면 끝) 시각. base 장면 시작 기준으로 바꿀 수 있다."""
        q = _norm(word)
        hits = [w for w in self.by[sid]['words'] if _norm(w['text']).startswith(q)]
        if len(hits) <= n:
            raise KeyError(f'{sid}: "{word}" {n}번째 없음 — {[w["text"] for w in self.by[sid]["words"]]}')
        t = hits[n]['end' if end else 'start']
        if base:
            t += self.start(sid) - self.start(base)
        return round(t, 3)

    def captions(self, sids, base=None, words=3, chars=11, hl=(), lead=.05, sub=None):
        """말 자막 묶음(captions.js용): 단어 시각에서 2~3단어씩 → [{t0, t1, text, hl}] (base 장면 시작 기준 초).
        문장부호(, . ? !)에서 끊고, 한 묶음이 chars자를 넘으면 먼저 끊는다. 묶음은 다음 묶음 시작까지 보인다(깜빡임 없음).
        sub = {대본 글자: 화면 글자} — 대본엔 한글로 쓴 숫자를 자막에선 숫자로(예: {'팔백이십팔': '828', '센티미터': 'cm'}).
          낱말 전체가 key와 같을 때만 바뀐다(sub_word). 숫자 뒤 단위는 붙여 쓴다('19 층' → '19층', '40 센티미터' → '40cm')."""
        sub = sub or {}
        base = base or sids[0]; out = []
        for sid in sids:
            off = self.start(sid) - self.start(base); cur = []
            ws = self.by[sid]['words']
            for i, w in enumerate(ws):
                cur.append(w)
                text = cap_text([x['text'] for x in cur], sub)
                nxt = ws[i + 1]['text'] if i + 1 < len(ws) else ''
                unit = is_number(w['text'], sub) and is_unit(_split_punct(nxt)[1])   # 숫자와 단위는 한 묶음(사고: '280 / 층 쌓은', '1만 / 대와'로 끊김)
                if not unit and (len(cur) >= words or len(text.replace(' ', '')) >= chars or re.search(r'[,.?!…]$', w['text'])) or i == len(ws) - 1:
                    out.append({'t0': round(off + cur[0]['start'] - lead, 3), 't1': round(off + w['end'] + .25, 3),
                                'text': re.sub(r'[,.]$', '', text), 'hl': [h for h in hl if h in text]})
                    cur = []
        for a, b in zip(out, out[1:]): a['t1'] = max(a['t0'] + .2, min(a['t1'], b['t0']) if b['t0'] - a['t1'] > .6 else b['t0'])
        return out

    def write(self, out_wav, sids=None):
        """장면 음성을 장면 길이(프레임 단위)로 맞춰 이어 붙인 48kHz 모노 wav."""
        sc = [s for s in self.scenes if not sids or s['id'] in sids]
        ins, fl = [], []
        for i, s in enumerate(sc):
            ins += ['-i', s['wav']]
            fl.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=mono,apad=whole_dur={s["frames"] / FPS:.6f},'
                      f'atrim=0:{s["frames"] / FPS:.6f}[a{i}]')
        fl.append(''.join(f'[a{i}]' for i in range(len(sc))) + f'concat=n={len(sc)}:v=0:a=1[out]')
        _ff([*ins, '-filter_complex', ';'.join(fl), '-map', '[out]', '-c:a', 'pcm_s16le', out_wav])
        return out_wav


# ───────────────────────── 소스(배경·기기 화면) ─────────────────────────
def seq(src, out_dir, *, t0=0.0, dur, speed=1.0, crop=None, size, blur=0, bright=1.0, fx=.5, fy=.5, boxes=(), q=2, force=False):
    """원본 영상 구간 → 30fps JPEG 시퀀스(out_dir/0000.jpg…). 반환 {'n': 프레임 수}.
    t0: 원본 시작 초, dur: 출력 길이(초), speed: 재생 배속(원본이 끝나면 마지막 프레임 유지).
    crop=(x,y,w,h) 원본 좌표 자르기 → size=(w,h) cover 맞춤(fx·fy = 남는 부분을 자를 위치 0~1).
    blur: 가우시안 시그마(출력 해상도 기준), bright: 밝기 배율, boxes=[(x,y,w,h[,시그마])]: 원본 좌표에서 강하게 흐릴 곳(답·개인정보 가리기).
    같은 설정으로 이미 만든 폴더는 건너뛴다(seq.json)."""
    out = Path(out_dir)
    n = int(math.ceil(dur * FPS)) + 1
    meta = dict(src=Path(src).name, bytes=os.path.getsize(src), mtime=os.path.getmtime(src), t0=t0, dur=round(dur, 4), speed=speed, crop=crop,
                size=list(size), blur=blur, bright=bright, fx=fx, fy=fy, boxes=[list(b) for b in boxes], q=q, n=n, v=2)
    mf = out / 'seq.json'
    if not force and mf.exists() and json.loads(mf.read_text(encoding='utf-8')) == json.loads(json.dumps(meta)) \
            and (out / f'{n - 1:04d}.jpg').exists():
        return dict(n=n)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    w, h = size
    chain = [f'[0:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS},tpad=stop_mode=clone:stop_duration={dur + 2:.2f}[v0]']
    cur = 'v0'
    for i, b in enumerate(boxes):
        x, y, bw, bh = b[:4]
        sg = b[4] if len(b) > 4 else 26
        chain.append(f'[{cur}]split[a{i}][b{i}];[b{i}]crop={bw}:{bh}:{x}:{y},gblur=sigma={sg}:steps=4[c{i}];'
                     f'[a{i}][c{i}]overlay={x}:{y}[v{i + 1}]')
        cur = f'v{i + 1}'
    f = []
    if crop:
        f.append('crop={2}:{3}:{0}:{1}'.format(*crop))
    f.append(f'scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos')
    f.append(f'crop={w}:{h}:(iw-{w})*{fx}:(ih-{h})*{fy}')
    if blur:
        f.append(f'gblur=sigma={blur}:steps=3')
    if bright != 1:
        f.append(f'colorchannelmixer=rr={bright}:gg={bright}:bb={bright}')
    chain.append(f'[{cur}]' + ','.join(f) + ',format=yuvj420p[out]')
    _ff(['-ss', f'{t0:.3f}', '-i', src, '-filter_complex', ';'.join(chain), '-map', '[out]', '-frames:v', n,
         '-q:v', q, '-start_number', 0, out / '%04d.jpg'])
    got = len(list(out.glob('*.jpg')))
    if got < n:
        raise RuntimeError(f'{out}: 프레임 {got}/{n}')
    mf.write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    return dict(n=n)


def still(src, out, *, size, crop=None, blur=0, bright=1.0, fx=.5, fy=.5, sharpen=False, q=92):
    """그림 한 장 → 자르기·cover 맞춤·흐림(가우시안 반지름)·밝기 → JPEG."""
    im = Image.open(src).convert('RGB')
    if crop:
        x, y, w, h = crop
        im = im.crop((x, y, x + w, y + h))
    tw, th = size
    r = max(tw / im.width, th / im.height)
    im = im.resize((max(tw, round(im.width * r)), max(th, round(im.height * r))), Image.LANCZOS)
    x, y = round((im.width - tw) * fx), round((im.height - th) * fy)
    im = im.crop((x, y, x + tw, y + th))
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if bright != 1:
        im = ImageEnhance.Brightness(im).enhance(bright)
    if sharpen:
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=q)
    return out


def seq_info(html, names):
    """HTML 기준 상대 경로 이름(예 'src/c0_bg') → {'src/c0_bg': {'n': …}} (RK_INIT.seqs 용)."""
    base = Path(html).resolve().parent
    info = {}
    for nm in names:
        m = json.loads((base / nm / 'seq.json').read_text(encoding='utf-8'))
        info[nm] = {'n': m['n']}
    return info


# ───────────────────────── 앞 UI 찍기(playwright) ─────────────────────────
CHECK_JS = """
() => {
  const small = [], fams = new Set();
  const eff = (el) => { let s = 1, o = 1, p = el;
    while (p && p.nodeType === 1) { const cs = getComputedStyle(p);
      if (cs.transform && cs.transform !== 'none') { const m = new DOMMatrix(cs.transform); s *= Math.hypot(m.a, m.b); }
      if (cs.scale && cs.scale !== 'none') s *= parseFloat(cs.scale);
      o *= +cs.opacity; p = p.parentElement; }
    return [s, o]; };
  const walk = (n) => { for (const c of n.childNodes) {
      if (c.nodeType === 3 && c.nodeValue.trim()) {
        const el = c.parentElement, cs = getComputedStyle(el), r = el.getBoundingClientRect();
        if (el.closest('script,style,title') || cs.visibility === 'hidden' || cs.display === 'none' || r.width === 0) continue;
        const [s, o] = eff(el); if (o < 0.5) continue;
        if (r.right < 0 || r.left > innerWidth || r.bottom < 0 || r.top > innerHeight) continue;
        fams.add(cs.fontFamily);
        const px = parseFloat(cs.fontSize) * s;
        if (px < 27.5) small.push([c.nodeValue.trim().slice(0, 24), +px.toFixed(1)]);
      } else if (c.nodeType === 1) walk(c); } };
  walk(document.body);
  const hidden = [...document.querySelectorAll('.bgimg')].filter(e => getComputedStyle(e).display === 'none').length;   // 실제 사고: theme-real.css를 빠뜨려 배경 영상이 통째로 안 보임
  return {small, fams: [...fams], warns: ((window.RK && RK.warns) || []).concat(hidden ? ['배경 칸(.bgimg)이 숨겨져 있음 — theme-real.css 링크 확인'] : [])};
}
"""


def _platform_fonts(page):
    """CDP로 실제 그려진 글꼴(대체 글꼴 포함)을 모은다."""
    cdp = page.context.new_cdp_session(page)
    cdp.send('DOM.enable')
    cdp.send('CSS.enable')
    root = cdp.send('DOM.getDocument', {'depth': -1, 'pierce': True})['root']
    ids, fams = [], {}

    def walk(nd):
        kids = nd.get('children', [])
        if nd.get('nodeType') == 1 and nd.get('nodeName') not in ('SCRIPT', 'STYLE', 'TITLE') and \
                any(k.get('nodeType') == 3 and k.get('nodeValue', '').strip() for k in kids):
            ids.append(nd['nodeId'])
        for k in kids:
            walk(k)
    walk(root)
    for i in ids:
        try:
            for f in cdp.send('CSS.getPlatformFontsForNode', {'nodeId': i})['fonts']:
                fams[f['familyName']] = fams.get(f['familyName'], 0) + f['glyphCount']
        except Exception:
            pass
    return fams


def _open(p, html, dur, cues, seqs, extra=None):
    b = p.chromium.launch(args=['--disable-gpu-vsync', '--force-color-profile=srgb', '--hide-scrollbars', '--enable-unsafe-swiftshader'])   # GPU 없는 창 없는 브라우저에서도 WebGL(three.js 장면)이 그려지게
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    errs = []
    pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: (m.type in ('error', 'warning')) and 'GL Driver Message' not in m.text and errs.append(f'{m.type}: {m.text}'))   # GPU 성능 안내는 무시
    init = dict(dur=dur, cues=cues or {}, seqs=seqs or {}, extra=extra or {})
    pg.add_init_script(f'window.RK_INIT = {json.dumps(init, ensure_ascii=False)};')
    pg.goto(Path(html).resolve().as_uri())
    pg.evaluate('RK.ready')
    return b, pg, errs


def check_page(pg, t=None, fonts=False):
    if t is not None:
        pg.evaluate('t => RK.seek(t)', t)
    chk = pg.evaluate(CHECK_JS)
    msgs = []
    bad = [f for f in chk['fams'] if 'Hada' not in f]
    if bad:
        msgs.append(f'하다 산스 외 글꼴 지정 {bad}')
    if chk['small']:
        msgs.append(f'28px 미만 글자 {chk["small"][:8]}')
    if fonts:
        pf = _platform_fonts(pg)
        other = {k: v for k, v in pf.items() if not k.lower().startswith('hada')}
        if other:
            msgs.append(f'대체 글꼴로 그려진 글자 {other}')
    return msgs + [f'RK {w}' for w in chk['warns']]


def render_shot(html, out_mp4, frames, cues=None, seqs=None, check_at=(), crf=14, label='', extra=None):
    """장면 HTML을 frames장(30fps) 찍어 mp4로. 반환 경고 목록."""
    from playwright.sync_api import sync_playwright
    dur = frames / FPS
    ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg',
                           '-framerate', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf),
                           '-pix_fmt', 'yuv420p', '-r', str(FPS), str(out_mp4)], stdin=subprocess.PIPE)
    warns = []
    with sync_playwright() as p:
        b, pg, errs = _open(p, html, dur, cues, seqs, extra)
        for i in range(frames):
            pg.evaluate('t => RK.seek(t)', i / FPS)
            ff.stdin.write(pg.screenshot(type='jpeg', quality=94))
            if i and i % 60 == 0:
                print(f'  {label} {i}/{frames}', flush=True)
        for t in check_at:
            warns += [f'{t:.2f}s {m}' for m in check_page(pg, t, fonts=True)]
        warns += errs
        b.close()
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError(f'ffmpeg 실패 {out_mp4}')
    return sorted(set(warns))


def still_png(html, t, out_png, dur=10, cues=None, seqs=None):
    """한 시각의 정지 화면 PNG + 글꼴·글자 크기 점검."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b, pg, errs = _open(p, html, dur, cues, seqs)
        pg.evaluate('t => RK.seek(t)', t)
        pg.screenshot(path=str(out_png))
        msgs = check_page(pg, fonts=True) + errs
        b.close()
    return msgs


# ───────────────────────── 효과음 ─────────────────────────
RATE = 48000


def _sfx(kind, rng):
    dur = {'click': .075, 'whoosh': .22, 'pop': .16, 'done': .48, 'thud': .18, 'stamp': .55, 'swish': .35, 'tick': .03,
           'rise': .4, 'noti': .62, 'pay': .75, 'tap': .07}.get(kind, .5)
    t = np.arange(round(dur * RATE)) / RATE
    sm = lambda x, k: np.convolve(x, np.ones(k) / k, mode='same')
    if kind == 'click':
        v = (.065 * np.sin(2 * np.pi * 1850 * t) + .027 * rng.normal(size=len(t))) * np.exp(-t * 65)
    elif kind == 'whoosh':
        v = .058 * sm(rng.normal(size=len(t)), 9) * np.sin(np.pi * t / dur) ** 2
    elif kind == 'pop':
        v = .075 * np.sin(2 * np.pi * (440 * t - 600 * t * t)) * np.exp(-t * 22)
    elif kind == 'thud':
        v = (.16 * np.sin(2 * np.pi * (150 * t - 180 * t * t)) + .05 * sm(rng.normal(size=len(t)), 25)) * np.exp(-t * 30)
    elif kind == 'stamp':
        v = (.30 * np.sin(2 * np.pi * (95 * t - 60 * t * t)) + .14 * sm(rng.normal(size=len(t)), 5) * np.exp(-t * 18)) * np.exp(-t * 7)
    elif kind == 'swish':
        v = .07 * sm(rng.normal(size=len(t)), 4) * np.sin(np.pi * t / dur) ** 3 * (1 + np.sin(2 * np.pi * 12 * t)) / 2
    elif kind == 'tick':
        v = .05 * np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 220)
    elif kind == 'rise':
        v = .05 * np.sin(2 * np.pi * (500 * t + 900 * t * t)) * np.sin(np.pi * t / dur)
    elif kind == 'noti':      # 알림 배너: 맑은 두 음(유리 종) — 상표 알림음 아님
        def bell(f0, at, amp):
            u = np.clip(t - at, 0, None)
            on = (t >= at).astype(float)
            return on * amp * (np.sin(2 * np.pi * f0 * u) + .32 * np.sin(2 * np.pi * 2 * f0 * u) + .12 * np.sin(2 * np.pi * 3.01 * f0 * u)) \
                * np.exp(-u * 9) * np.minimum(1, u * 400)
        v = bell(1318.5, 0, .045) + bell(1975.5, .085, .05)
    elif kind == 'pay':       # 결제: 짧은 금속 딸깍 + 밝은 종 두 번(카칭)
        def bell(fs, at, amp, dec):
            u = np.clip(t - at, 0, None)
            on = (t >= at).astype(float)
            return on * amp * sum(np.sin(2 * np.pi * f * u) / (k + 1) for k, f in enumerate(fs)) * np.exp(-u * dec) * np.minimum(1, u * 600)
        click = .05 * np.diff(rng.normal(size=len(t) + 1)) * np.exp(-t * 160)
        v = click + bell((2093, 2637, 3136), .03, .032, 7) + bell((2637, 3520, 4186), .11, .036, 6)
    elif kind == 'tap':       # 화면 탭: 부드러운 톡
        v = (.07 * np.sin(2 * np.pi * (900 * t - 2500 * t * t)) + .02 * sm(rng.normal(size=len(t)), 3)) * np.exp(-t * 85)
    else:                     # done(완료음)
        v = .045 * (np.sin(2 * np.pi * 784 * t) + .5 * np.sin(2 * np.pi * 1175 * t)) * np.exp(-t * 8) * np.minimum(1, t * 100)
    return v.astype(np.float32)


def sfx_wav(events, total, out_wav, volume=.7, seed=31):
    """[{'t': 초, 'kind': 종류, 'gain': 배율(선택)}] → 48kHz 모노 wav."""
    fx = np.zeros(round(total * RATE), dtype=np.float32)
    rng = np.random.default_rng(seed)
    for e in sorted(events, key=lambda e: e['t']):
        v = _sfx(e['kind'], rng) * volume * e.get('gain', 1)
        i = max(0, round(e['t'] * RATE))
        k = min(len(v), len(fx) - i)
        if k > 0:
            fx[i:i + k] += v[:k]
    with wave.open(str(out_wav), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes((np.clip(fx, -1, 1) * 32767).astype('<i2').tobytes())
    return out_wav


def mix(voice_wav, fx_wav, out_wav, total):
    _ff(['-i', voice_wav, '-i', fx_wav, '-filter_complex',
         '[0:a][1:a]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]', '-map', '[a]', '-t', f'{total:.4f}',
         '-ar', RATE, '-c:a', 'pcm_s16le', out_wav])
    return out_wav


# ───────────────────────── 장면 묶음 → 최종 영상 ─────────────────────────
@dataclass
class Shot:
    """HTML 한 장이 맡는 장면 묶음. cues·sfx 시각은 첫 장면 시작 기준(초)."""
    html: str
    scenes: list
    cues: dict = field(default_factory=dict)
    seqs: list = field(default_factory=list)      # HTML 기준 상대 경로('src/c0_bg')
    sfx: list = field(default_factory=list)
    check_at: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)     # HTML에서 RK.extra로 읽는 자료(자막 묶음 등)


def render_shots(V, shots, workdir, parallel=True):
    """장면 묶음마다 별도 프로세스로 렌더(병렬). 반환 [(mp4, 경고)]."""
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    procs = []
    for i, s in enumerate(shots):
        frames = sum(V[sid]['frames'] for sid in s.scenes)
        job = dict(html=str(Path(s.html).resolve()), out=str((work / f'shot{i}.mp4').resolve()), frames=frames, cues=s.cues,
                   seqs=seq_info(s.html, s.seqs), check_at=s.check_at, label=Path(s.html).stem, extra=s.extra)
        jf = work / f'shot{i}.json'
        jf.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
        cmd = [sys.executable, str(Path(__file__).resolve()), 'shot', str(jf)]
        if parallel:
            procs.append((job, subprocess.Popen(cmd, env={**os.environ, 'PYTHONUTF8': '1'})))
        else:
            subprocess.run(cmd, check=True, env={**os.environ, 'PYTHONUTF8': '1'})
            procs.append((job, None))
    res = []
    for job, pr in procs:
        if pr and pr.wait():
            raise RuntimeError(f'장면 렌더 실패 {job["html"]}')
        wf = Path(job['out'] + '.warn.json')
        res.append((Path(job['out']), json.loads(wf.read_text(encoding='utf-8')) if wf.exists() else []))
    return res


def build(V, shots, out_mp4, workdir, sfx_volume=.7, crf=18, parallel=True):
    """음성(V) + 장면 묶음 렌더 + 효과음 → out_mp4(1920x1080 30fps H.264 + AAC). 반환 dict(경고·길이)."""
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    order = [sid for s in shots for sid in s.scenes]
    if order != [s['id'] for s in V.scenes]:
        raise ValueError(f'장면 순서가 음성과 다름: {order}')
    rendered = render_shots(V, shots, work, parallel)
    events = []
    for s in shots:
        base = V.start(s.scenes[0])
        events += [dict(e, t=round(base + e['t'], 4)) for e in s.sfx]
    (work / 'sfx-events.json').write_text(json.dumps(events, ensure_ascii=False, indent=0), encoding='utf-8')
    total = V.total
    V.write(work / 'voice.wav')
    sfx_wav(events, total, work / 'sfx.wav', sfx_volume)
    mix(work / 'voice.wav', work / 'sfx.wav', work / 'mix.wav', total)
    lst = work / 'shots.txt'
    lst.write_text(''.join(f"file '{p.as_posix()}'\n" for p, _ in rendered), encoding='utf-8')
    _ff(['-f', 'concat', '-safe', 0, '-i', lst, '-i', work / 'mix.wav', '-map', '0:v', '-map', '1:a',
         '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-pix_fmt', 'yuv420p', '-r', FPS,
         '-c:a', 'aac', '-b:a', '192k', '-ar', RATE, '-ac', 2, '-t', f'{total:.4f}', '-movflags', '+faststart', out_mp4])
    info = verify(out_mp4)
    warns = {Path(s.html).name: w for s, (_, w) in zip(shots, rendered) if w}
    return dict(info, warns=warns, events=len(events))


def verify(mp4):
    """끝까지 디코딩 + 규격 확인."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(mp4), '-f', 'null', '-'], capture_output=True, text=True)
    if r.returncode or r.stderr.strip():
        raise RuntimeError(f'디코딩 오류 {mp4}: {r.stderr[-800:]}')
    pr = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(mp4)]))
    v = next(s for s in pr['streams'] if s['codec_type'] == 'video')
    a = [s for s in pr['streams'] if s['codec_type'] == 'audio']
    return dict(duration=float(pr['format']['duration']), size_mb=round(int(pr['format']['size']) / 1e6, 2),
                video=f"{v['codec_name']} {v['width']}x{v['height']} {v['r_frame_rate']} {v.get('pix_fmt')}",
                audio=f"{a[0]['codec_name']} {a[0]['sample_rate']}Hz {a[0]['channels']}ch" if a else None, full_decode='passed')


def preview(src, out, height=480, max_mb=30):
    """휴대폰 확인용 작은 사본(기본 480p, max_mb 이하가 될 때까지 crf를 올린다)."""
    for crf in (20, 23, 26, 29, 32):
        _ff(['-i', src, '-vf', f'scale=-2:{height}:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', crf,
             '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out])
        if os.path.getsize(out) / 1e6 <= max_mb:
            break
    return verify(out)


def sheet(mp4, out_jpg, every=1.0, cols=5, tw=480, title=''):
    """every초 간격 프레임 시트(시각 표시) — 겹침·잘림·빈 화면 점검용."""
    total = duration(mp4)
    ts = [round(i * every, 3) for i in range(int(total / every) + 1) if i * every < total - 0.02]
    if H > W: tw, cols = min(tw, 270), max(cols, 8)   # 세로 영상 시트
    th = round(tw * H / W)
    rows = math.ceil(len(ts) / cols)
    top = 60 if title else 0
    sh = Image.new('RGB', (cols * tw + (cols + 1) * 8, top + rows * (th + 8) + 8), '#121316')
    d = ImageDraw.Draw(sh)
    if title:
        d.text((12, 12), title, font=font('Bold', 32), fill='#d8dae0')
    tmp = Path(out_jpg).with_suffix('.frames')
    tmp.mkdir(exist_ok=True)
    for i, t in enumerate(ts):
        f = tmp / f'{i:04d}.jpg'
        _ff(['-ss', f'{t:.3f}', '-i', mp4, '-frames:v', 1, '-vf', f'scale={tw}:{th}', '-q:v', 3, f])
        im = Image.open(f).convert('RGB')
        x, y = 8 + (i % cols) * (tw + 8), top + 8 + (i // cols) * (th + 8)
        sh.paste(im, (x, y))
        lab = f'{t:.1f}s'
        d.rectangle((x, y, x + 12 + 16 * len(lab), y + 36), fill=(0, 0, 0))
        d.text((x + 6, y + 2), lab, font=font('Bold', 28), fill='#ffffff')
    shutil.rmtree(tmp, ignore_errors=True)
    sh.save(out_jpg, quality=88)
    return out_jpg


def grid(pngs, labels, out_jpg, cols=2, tw=960, title=''):
    """정지 시안 여러 장 → 한 장 시트(라벨 포함)."""
    th = round(tw * 9 / 16)
    rows = math.ceil(len(pngs) / cols)
    top = 70 if title else 10
    lh = 50
    sh = Image.new('RGB', (cols * tw + (cols + 1) * 16, top + rows * (th + lh + 16) + 10), '#121316')
    d = ImageDraw.Draw(sh)
    if title:
        d.text((16, 16), title, font=font('Bold', 36), fill='#ffffff')
    for i, (p, lab) in enumerate(zip(pngs, labels)):
        x, y = 16 + (i % cols) * (tw + 16), top + (i // cols) * (th + lh + 16)
        d.text((x, y + 6), lab, font=font('SemiBold', 30), fill='#c8cad2')
        sh.paste(Image.open(p).convert('RGB').resize((tw, th), Image.LANCZOS), (x, y + lh))
    sh.save(out_jpg, quality=90)
    return out_jpg


# ───────────────────────── CLI ─────────────────────────
def _cli():
    a = sys.argv[1:]
    if a and a[0] == 'shot':
        job = json.loads(Path(a[1]).read_text(encoding='utf-8'))
        w = render_shot(job['html'], job['out'], job['frames'], job['cues'], job['seqs'], job.get('check_at', ()), label=job.get('label', ''), extra=job.get('extra'))
        Path(job['out'] + '.warn.json').write_text(json.dumps(w, ensure_ascii=False), encoding='utf-8')
        print(job['label'], '완료', job['frames'], '프레임', ('경고 ' + str(len(w))) if w else '')
    elif a and a[0] == 'still':
        print(still_png(a[1], float(a[2]), a[3]) or '점검 통과')
    elif a and a[0] == 'sheet':
        print(sheet(a[1], a[2], float(a[3]) if len(a) > 3 else 1.0))
    else:
        print(__doc__)


if __name__ == '__main__':
    _cli()
