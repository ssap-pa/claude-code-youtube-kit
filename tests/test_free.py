"""무료 키트 시험 — 네트워크·API 키 없이 돈다. 실행: python tests/test_free.py"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / 'tools'))
import voice, memory, qa, make_final  # noqa: E402
import numpy as np

PY = sys.executable
ENV = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}


def run(*a, inp=None, cwd=KIT):
    return subprocess.run([PY, *map(str, a)], capture_output=True, text=True, encoding='utf-8', input=inp, env=ENV, cwd=cwd)


def test_check_script_catches_demo_mistakes():
    out = run(KIT / 'tools' / 'check_script.py', KIT / 'videos' / 'demo')
    assert out.returncode == 1, out.stdout
    for rule in ('lower-latin', 'digit-native-counter', 'jamo-only'):
        assert rule in out.stdout, rule   # 데모 대본엔 일부러 세 가지 실수를 넣어 두었다


def test_feedback_hook_logs_and_nudges(tmp_path):
    kit = tmp_path / 'kit'; shutil.copytree(KIT / 'hooks', kit / 'hooks'); (kit / 'memory').mkdir()
    hook = lambda p: subprocess.run([PY, str(kit / 'hooks' / 'capture_feedback.py')], input=json.dumps({'prompt': p}), capture_output=True, text=True, encoding='utf-8', env=ENV).stdout
    assert '피드백 후보' in hook('앞으로 첫 장면은 결과부터, 방법은 숨겨')
    assert hook('좋아 진행해') == ''
    rows = [json.loads(x) for x in (kit / 'memory' / 'inbox.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [r['status'] for r in rows] == ['new', 'note']


def test_session_start_injects_index():
    out = run(KIT / 'hooks' / 'session_start.py').stdout
    assert '학습 메모리 목록' in out and 'feedback-loop' in out and 'youtube-script' in out and 'real-ui-design' in out and 'youtube-video' not in out


def test_memory_add_then_listed(tmp_path):
    kit = tmp_path / 'kit'; shutil.copytree(KIT / 'tools', kit / 'tools'); shutil.copytree(KIT / 'memory', kit / 'memory')
    r = run(kit / 'tools' / 'memory.py', 'add', 'hide-answer-opening', '--area', '대본', '--rule', '첫 장면은 결과부터, 방법은 숨겨 본론에서 공개한다', '--why', '답을 먼저 말하면 시청자가 나간다', cwd=kit)
    assert r.returncode == 0, r.stderr
    assert '첫 장면은 결과부터' in (kit / 'memory' / 'INDEX.md').read_text(encoding='utf-8')
    assert run(kit / 'tools' / 'memory.py', 'check', cwd=kit).returncode == 0


def test_demo_voice_and_listen(tmp_path):
    demo = tmp_path / 'demo'; shutil.copytree(KIT / 'videos' / 'demo', demo)
    assert run(KIT / 'tools' / 'voice.py', demo, '--demo').returncode == 0
    v = json.loads((demo / 'renders' / 'voice-v1' / 'voices.json').read_text(encoding='utf-8'))
    assert len(v) == 3 and v[0]['words'][0]['text'] == '요즘'
    out = run(KIT / 'tools' / 'listen.py', demo)
    assert out.returncode == 0 and (demo / 'renders' / 'listen.wav').exists()


def test_pron_maps_back_to_script_words():
    pron = {'챗GPT': '챗 지피티'}; say = voice.say_of('챗GPT한테 물어봐', pron)
    words = [{'text': '챗', 'start': 0, 'end': .2}, {'text': '지피티한테', 'start': .3, 'end': .8}, {'text': '물어봐', 'start': .9, 'end': 1.2}]
    assert [w['text'] for w in voice.back_to_original('챗GPT한테 물어봐', say, words, pron)] == ['챗GPT한테', '물어봐']


def test_discount_link_present():
    for f in ('README.md', 'docs/06-내-목소리-전문-복제.md'):
        t = (KIT / f).read_text(encoding='utf-8'); assert 'try.elevenlabs.io/surgaf77dx55' in t and '50% 할인' in t, f


def test_sync_offset_detection():
    rng = np.random.default_rng(1); sr = qa.SR
    needle = rng.normal(size=int(1.5 * sr)) * np.hanning(int(1.5 * sr))
    hay = np.zeros(10 * sr); start = int(4 * sr) + int(.12 * sr); hay[start:start + len(needle)] += needle; hay += .05 * rng.normal(size=len(hay))
    off, r = qa.xcorr_offset(hay, needle, int(4 * sr), int(.5 * sr))
    assert abs(off - .12) < .002 and r > .9   # 음성이 120ms 밀린 것을 찾아낸다


def test_big_number_needs_comparison():
    out = subprocess.run([PY, str(KIT / 'tools' / 'check_script.py'), str(KIT / 'videos' / 'demo')], capture_output=True, text=True, encoding='utf-8', env=ENV).stdout
    assert '규칙 ' in out
    it = next(i for i in json.loads((KIT / 'tools' / 'regressions.json').read_text(encoding='utf-8'))['items'] if i['id'] == 'relatable-numbers-script')
    import re
    assert re.search(it['pattern'], '팔백이십팔 미터짜리 건물') and not re.search(it['unless'], '팔백이십팔 미터짜리 건물')


def test_shorts_mode_included(tmp_path):
    for f in ['tools/realkit/vertical.css', 'tools/realkit/captions.js', 'tools/realkit/scene3d.js', 'tools/realkit/vendor/three.min.js',
              'templates/shorts/build_v1.py', 'templates/shorts/clips/v1/burj.js', '.claude/skills/shorts-explainer/SKILL.md']:
        assert (KIT / f).exists(), f
    out = subprocess.run([PY, str(KIT / 'tools' / 'check_script.py'), str(KIT / 'templates' / 'shorts')], capture_output=True, text=True, encoding='utf-8', env=ENV).stdout
    assert '통과' in out, out   # 예제 쇼츠 대본은 표기·체감 수치 규칙을 지킨다
    node = shutil.which('node')
    if node:
        for f in ['realkit.js', 'captions.js', 'scene3d.js']:
            r = subprocess.run([node, '-e', "new Function(require('fs').readFileSync(process.argv[1],'utf8'))", str(KIT / 'tools' / 'realkit' / f)], capture_output=True, text=True)
            assert r.returncode == 0, (f, r.stderr[-300:])


if __name__ == '__main__':
    import inspect
    sys.stdout.reconfigure(encoding='utf-8'); fails = 0
    for n, f in list(globals().items()):
        if n.startswith('test_'):
            try:
                f(*([Path(tempfile.mkdtemp())] if inspect.signature(f).parameters else [])); print('ok  ', n)
            except Exception as e:
                fails += 1; print('FAIL', n, repr(e))
    print('실패', fails); sys.exit(1 if fails else 0)
