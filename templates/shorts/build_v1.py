"""세로 설명 쇼츠 빌더(예제) — 3D 장면(three.js) + 말 자막 + 핵심 숫자 카드. 사용: python videos/<slug>/build_v1.py → renders/v1-vN.mp4
장면 HTML(clips/v1/*.html)은 화면 신호를 RK.cues로, 자막은 RK.extra.caps로 받는다. 신호·자막 모두 대사 단어 시각에서 만든다(싱크).
컷: 장면 HTML 하나 안에서도 카메라를 바꿔 2~4초마다 그림이 바뀌게 한다(세로 설명 쇼츠는 멈춘 그림이 길면 넘긴다)."""
import os, re, sys
from pathlib import Path

os.environ['RK_FORMAT'] = 'vertical'   # realkit import 전에 — 1080x1920
HERE = Path(__file__).resolve().parent; KIT = HERE.parents[1]
sys.path.insert(0, str(KIT / 'tools' / 'realkit')); import realkit as rk  # noqa: E402

CLIP = 'v1'
V = rk.Voice(HERE / 'renders' / f'voice-{CLIP}' / 'voices.json', base=HERE)
S = HERE / 'clips' / CLIP
SUB = {'이백팔십': '280', '백팔십': '180', '팔백이십팔': '828', '오백십팔': '518', '삼백십': '310'}   # 대본은 한글 숫자(음성용), 자막은 숫자. 긴 말을 앞에(이백팔십 ⊃ 백팔십)
HL = ['280', '180', '828', '310', '바람', '소용돌이', '계단처럼', '박자', '에펠탑']


def shot(html, sids, cues, sfx=(), check=()):
    T0 = sids[0]
    caps = V.captions(sids, base=T0, sub=SUB, hl=HL)
    return rk.Shot(str(S / html), sids, cues, [], list(sfx), list(check), extra={'caps': caps})


def shots():
    T = lambda sid, w, base, n=0: V.T(sid, w, n, base=base)
    st = lambda sid, base: round(V.start(sid) - V.start(base), 3)
    a = {'apt': T('v1-s1', '이백팔십', 'v1-s1'), 'num': T('v1-s1', '팔백이십팔', 'v1-s1'), 's2': st('v1-s2', 'v1-s1'), 'name': T('v1-s2', '부르즈', 'v1-s1')}
    b = {'m518': T('v1-s3', '백팔십', 'v1-s3'), 's4': st('v1-s4', 'v1-s3'), 'wind': T('v1-s4', '바람이었거든요', 'v1-s3')}
    c = {'vortex': T('v1-s5', '소용돌이가', 'v1-s5'), 'shake': T('v1-s5', '흔듭니다', 'v1-s5')}
    d = {'trick': T('v1-s6', '속이기로', 'v1-s6'), 's7': st('v1-s7', 'v1-s6'), 'step': T('v1-s7', '계단처럼', 'v1-s6')}
    e = {'beat': T('v1-s8', '박자가', 'v1-s8'), 'calm': T('v1-s8', '흔들림이', 'v1-s8')}
    f = {'grow': T('v1-s9', '다듬자', 'v1-s9'), 'up': T('v1-s9', '올라갔습니다', 'v1-s9'), 'eiffel': T('v1-s9', '에펠탑', 'v1-s9')}
    ev = lambda t, k, g=1: {'t': t, 'kind': k, 'gain': g}
    return [
        shot('a.html', ['v1-s1', 'v1-s2'], a, [ev(a['apt'] - .1, 'thud', 1.2), ev(a['num'], 'pop'), ev(a['s2'], 'whoosh'), ev(a['name'], 'pop')], [a['num'] + .6, a['name'] + .6]),
        shot('b.html', ['v1-s3', 'v1-s4'], b, [ev(0, 'whoosh'), ev(b['m518'], 'stamp', .8), ev(b['s4'], 'swish', 1.4)], [b['m518'] + .6]),
        shot('c.html', ['v1-s5'], c, [ev(0, 'whoosh'), ev(c['vortex'], 'pop'), ev(c['shake'], 'thud')], [c['vortex'] + .6]),
        shot('d.html', ['v1-s6', 'v1-s7'], d, [ev(0, 'whoosh'), ev(d['trick'], 'pop'), ev(d['s7'], 'whoosh'), ev(d['step'], 'rise')], [d['trick'] + .6]),
        shot('e.html', ['v1-s8'], e, [ev(0, 'whoosh'), ev(e['beat'], 'tick'), ev(e['calm'], 'done')]),
        shot('f.html', ['v1-s9'], f, [ev(0, 'whoosh'), ev(f['grow'], 'rise'), ev(f['up'] + .2, 'stamp'), ev(f['eiffel'], 'pop')], [f['eiffel'] + .8]),
    ]


def next_version():
    vs = [int(m.group(1)) for p in (HERE / 'renders').glob(f'{CLIP}-v*.mp4') if (m := re.fullmatch(rf'{CLIP}-v(\d+)\.mp4', p.name))]
    return max(vs, default=0) + 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if 'demo-' in (HERE / 'bgm.json').read_text(encoding='utf-8'):   # 데모 곡(합성음)이 없거나 예전 짧은 곡이면 만든다 — 실제 영상에선 처음 세팅에서 고른 곡으로
        import subprocess; subprocess.run([sys.executable, str(KIT / 'tools' / 'make_demo_assets.py')], check=True, stdout=subprocess.DEVNULL)
    n = next_version(); out = HERE / 'renders' / f'{CLIP}-v{n}.mp4'
    info = rk.build(V, shots(), str(out), str(HERE / 'renders' / f'{CLIP}-v{n}-job'))
    rk.sheet(str(out), str(HERE / 'renders' / f'{CLIP}-v{n}-sheet.jpg'), 1.0)
    print(out.name, info)
    if info['warns']: print('⚠ 경고(글꼴·작은 글자·없는 신호):', info['warns'])
