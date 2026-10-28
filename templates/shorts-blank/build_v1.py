"""세로 설명 쇼츠 빌더(빈 틀) — 사용: python videos/<slug>/build_v1.py → renders/v1-vN.mp4 + 프레임 시트
장면 HTML(clips/v1/*.html)은 화면 신호를 RK.cues로, 말 자막은 RK.extra.caps로 받는다. 신호·자막 모두 대사 단어 시각에서 만든다(싱크).

장면 늘리는 법(한 장면 HTML = 대사 1~2문장):
  1. clips/v1/a.html을 b.html로 복사해 모형·카메라를 바꾼다(모형을 여러 장면에서 쓰면 clips/v1/<모형>.js로 따로 — 예제: templates/shorts의 burj.js).
  2. 아래 shots()에 한 줄: shot('b.html', ['v1-s3'], {'신호': T('v1-s3', '단어', 'v1-s3')}, [효과음…])
  3. 신호 이름은 HTML의 data-anim="pop@신호", JS의 RK.cues.신호와 같게.
완성 예제: python tools/new_video.py --shorts --example <slug> (부르즈 할리파 40초)."""
import os, re, sys
from pathlib import Path

os.environ['RK_FORMAT'] = 'vertical'   # realkit import 전에 — 1080x1920
HERE = Path(__file__).resolve().parent; KIT = HERE.parents[1]
sys.path.insert(0, str(KIT / 'tools' / 'realkit')); import realkit as rk  # noqa: E402

CLIP = 'v1'
V = rk.Voice(HERE / 'renders' / f'voice-{CLIP}' / 'voices.json', base=HERE)
S = HERE / 'clips' / CLIP
# 대본은 한글 숫자(음성용), 자막은 숫자. 낱말 전체가 같을 때만 바뀐다(피사·공사·만든은 안 바뀜). 두 글자 이상 숫자·단위 낱말은 조사가 붙어도 바뀜.
SUB = {}    # 예: {'팔백이십팔': '828', '열아홉': '19', '사십': '40', '센티미터': 'cm'} → 자막 '828미터', '19층', '40cm'
HL = []     # 자막에서 노랗게 칠할 낱말(바꾼 뒤 글자로): 예 ['828', '바람']


def shot(html, sids, cues, sfx=(), check=(), seqs=()):
    """seqs: 장면 HTML이 쓰는 영상 시퀀스(실사 스타일의 AI 컷 — rk.seq로 만든 'src/g1' 등)."""
    caps = V.captions(sids, base=sids[0], sub=SUB, hl=HL)
    return rk.Shot(str(S / html), sids, cues, list(seqs), list(sfx), list(check), extra={'caps': caps})


def shots():
    T = lambda sid, w, base, n=0: V.T(sid, w, n, base=base)   # 그 단어가 시작하는 시각(base 장면 시작 기준)
    st = lambda sid, base: round(V.start(sid) - V.start(base), 3)   # 그 장면이 시작하는 시각
    ev = lambda t, k, g=1: {'t': t, 'kind': k, 'gain': g}   # 효과음: pop·whoosh·thud·rise·stamp·tick·done …
    a = {'s2': st('v1-s2', 'v1-s1')}   # 대본을 쓰면 단어 신호로 바꾼다: {'num': T('v1-s1', '팔백이십팔', 'v1-s1'), …}
    return [
        shot('a.html', ['v1-s1', 'v1-s2'], a, [ev(0, 'whoosh'), ev(a['s2'], 'pop')]),
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
