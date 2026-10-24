"""기본 글꼴(하다 산스)을 공식 배포처에서 받아 tools/realkit/fonts/에 푼다. 글꼴 파일은 키트에 넣지 않는다(배포처 라이선스를 직접 확인).
다른 글꼴을 쓰려면 tools/realkit/base.css의 @font-face와 realkit.py check_page()의 'Hada' 검사를 함께 바꾼다."""
import io, sys, urllib.request, zipfile
from pathlib import Path

URL = 'https://hada-type.com/static/fonts/packages/HadaSans-TTF.zip'   # 예전 주소 type.hada0127.net은 여기로 넘어간다
OUT = Path(__file__).resolve().parent / 'realkit' / 'fonts'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(list(OUT.glob('HadaSans-*.ttf'))) >= 5: print('이미 있음:', OUT); return
    OUT.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (youtube-automation-starter-kit)'})   # 파이썬 기본 User-Agent는 403으로 막힌다
    with urllib.request.urlopen(req, timeout=120) as r: z = zipfile.ZipFile(io.BytesIO(r.read()))
    n = 0
    for name in z.namelist():
        if name.lower().endswith('.ttf') and 'HadaSans-' in name:
            (OUT / Path(name).name).write_bytes(z.read(name)); n += 1
    print(f'{n}개 글꼴 → {OUT}')


if __name__ == '__main__':
    main()
