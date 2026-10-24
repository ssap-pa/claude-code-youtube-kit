"""V1 클립 빌더(예제) — 이 파일을 복사해 build_v2.py …를 만든다. 사용: python videos/<slug>/build_v1.py  → renders/v1-vN.mp4(판 자동 증가)

음성·화면 싱크의 핵심: 화면 신호(cues)를 숫자로 적지 않고 V.T(장면, '단어')로 대사 단어 시각에서 만든다.
대본을 고쳐 음성을 다시 만들면 신호도 자동으로 따라온다. 단어가 대사에서 빠지면 KeyError로 바로 멈춘다(조용히 어긋나지 않음).
"""
import re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; KIT = HERE.parents[1]
sys.path.insert(0, str(KIT / 'tools' / 'realkit')); import realkit as rk  # noqa: E402

CLIP = 'v1'
V = rk.Voice(HERE / 'renders' / f'voice-{CLIP}' / 'voices.json', base=HERE)
S = HERE / 'clips' / CLIP


def sources():
    """소스 준비 — 원본을 잘라 흐린 배경 JPEG 시퀀스로. 데모는 원본 대신 합성 영상(assets/demo/bg.mp4)."""
    src = KIT / 'assets' / 'demo' / 'bg.mp4'
    if not src.exists(): subprocess.run([sys.executable, str(KIT / 'tools' / 'make_demo_assets.py')], check=True)
    rk.seq(src, S / 'src' / 'bg', t0=0, dur=V.dur('v1-s1', 'v1-s2', 'v1-s3'), size=(960, 540), blur=8, bright=.76)


def shots():
    T = lambda sid, w, n=0: V.T(sid, w, n, base='v1-s1')   # 세 장면을 한 HTML로 찍으니 첫 장면 시작 기준
    cues = {'fb': T('v1-s1', '피드백을'), 'mem': T('v1-s1', '기억해요'), 's2': V.start('v1-s2') - V.start('v1-s1'),
            'rule': T('v1-s3', '규칙이'), 'qa': T('v1-s3', '검수가')}
    sfx = [{'t': cues['fb'], 'kind': 'noti'}, {'t': cues['mem'], 'kind': 'noti'}, {'t': cues['s2'] + .2, 'kind': 'whoosh'},
           {'t': cues['rule'], 'kind': 'pop'}, {'t': cues['qa'], 'kind': 'done'}]
    return [rk.Shot(str(S / 'v1.html'), ['v1-s1', 'v1-s2', 'v1-s3'], cues, ['src/bg'], sfx, check_at=[cues['mem'] + .6, cues['qa'] + .6])]


def next_version():
    vs = [int(m.group(1)) for p in (HERE / 'renders').glob(f'{CLIP}-v*.mp4') if (m := re.fullmatch(rf'{CLIP}-v(\d+)\.mp4', p.name))]
    return max(vs, default=0) + 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sources()
    n = next_version(); out = HERE / 'renders' / f'{CLIP}-v{n}.mp4'
    info = rk.build(V, shots(), str(out), str(HERE / 'renders' / f'{CLIP}-v{n}-job'))
    rk.sheet(str(out), str(HERE / 'renders' / f'{CLIP}-v{n}-sheet.jpg'), 1.0)
    print(out.name, info)
    if info['warns']: print('⚠ 경고(글꼴·작은 글자·없는 신호):', info['warns'])
