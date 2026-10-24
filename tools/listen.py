"""만든 음성을 한 파일로 이어 들어 보기 + 단어 시각 표. 사용: python tools/listen.py videos/<slug>  → videos/<slug>/renders/listen.wav
단어 시각은 ElevenLabs가 글자마다 준 시작·끝 시각을 단어로 묶은 것이다. 전체 키트는 이 시각으로 화면 움직임·자막을 대사에 맞춘다."""
import json, subprocess, sys
from pathlib import Path


def main(argv):
    sys.stdout.reconfigure(encoding='utf-8')
    if not argv: sys.exit(__doc__)
    F = Path(argv[0]).resolve(); vs = []
    for vf in sorted((F / 'renders').glob('voice-*/voices.json')): vs += json.loads(vf.read_text(encoding='utf-8'))
    if not vs: sys.exit(f'음성이 없습니다 → python tools/voice.py {argv[0]}')
    out = F / 'renders' / 'listen.wav'; args, fl = [], []
    for i, v in enumerate(vs):
        args += ['-i', str(F / v['wav'])]; fl.append(f'[{i}:a]aresample=44100,apad=pad_dur=0.22[a{i}]')
    fl.append(''.join(f'[a{i}]' for i in range(len(vs))) + f'concat=n={len(vs)}:v=0:a=1[o]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args, '-filter_complex', ';'.join(fl), '-map', '[o]', str(out)], check=True)
    for v in vs:
        print(f"{v['id']} ({v['duration']:.2f}초{', 데모 무음' if v.get('demo') else ''})")
        print('   ' + '  '.join(f"{w['text']}@{w['start']:.2f}" for w in v['words']))
    print('→', out)


if __name__ == '__main__':
    main(sys.argv[1:])
