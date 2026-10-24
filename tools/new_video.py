"""새 영상 폴더 만들기: templates/video → videos/<slug>, 그리고 현재 영상으로 지정(.current-video — 훅이 피드백을 이 영상에 붙인다).
사용: python tools/new_video.py <slug>      (slug = 영문 소문자·숫자·하이픈, 예: ai-shopping-automation)
      python tools/new_video.py --shorts <slug>   세로 설명 쇼츠(templates/shorts — 3D 장면·말 자막 예제)
      python tools/new_video.py --switch <slug>   이미 있는 영상으로 현재 영상만 바꾸기"""
import json, re, shutil, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent


def main(a):
    if not a: sys.exit(__doc__)
    switch = a[0] == '--switch'; kind = 'shorts' if '--shorts' in a else 'video'; slug = a[-1]
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,60}', slug): sys.exit('slug는 영문 소문자·숫자·하이픈만(예: ai-shopping-automation)')
    dst = KIT / 'videos' / slug
    if switch:
        if not dst.exists(): sys.exit(f'{dst} 없음')
    else:
        if dst.exists(): sys.exit(f'{dst}가 이미 있습니다 — 이어서 하려면 --switch {slug}')
        if not (KIT / 'templates' / kind).exists(): sys.exit(f'templates/{kind}가 없습니다 — 세로 쇼츠는 전체 키트에 있어요(https://ssapable.com/courses/youtube-automation-kit)')
        shutil.copytree(KIT / 'templates' / kind, dst)
    (KIT / '.current-video').write_text(slug, encoding='utf-8')
    print(f'현재 영상: videos/{slug}')
    if not switch:
        print('다음: script.json의 settings.voice.voice_id를 넣고 대본을 쓴 뒤 → python tools/voice.py videos/' + slug)
        if not json.loads((dst / 'script.json').read_text(encoding='utf-8'))['settings']['voice'].get('voice_id'):
            print('목소리가 아직 없다면: 내 목소리를 한 번 전문 복제해 두면 앞으로 녹음 없이 대본만 쓰면 된다 → docs/06-내-목소리-전문-복제.md')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main(sys.argv[1:])
