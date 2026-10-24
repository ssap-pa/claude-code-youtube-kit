"""클립 이어 붙이기 + 배경음 → 합본.

사용: python tools/make_final.py videos/<slug> final-v1 [--force] [--no-preview] [--allow-missing]
  순서: 오프닝(op)이 있으면 맨 앞, 나머지는 script.json에 나온 클립 순서, settings.outro(mp4 경로)가 있으면 맨 뒤.
  클립 판: CLIPS.md 대신 script.json settings.approved {"v1": 3, …}(사용자가 승인한 판). 적지 않은 클립은 가장 높은 판.
  결과: renders/<이름>-nobgm.mp4(배경음 없는 판, 검수용) → renders/<이름>.mp4(배경음) + <이름>.json(클립 위치) + <이름>-bgm.json(실제 쓴 배경음 계획)

이음새: 영상은 다시 인코딩하지 않고(concat copy), 소리는 클립마다 그 클립 영상 길이에 정확히 맞춘 뒤(apad+atrim) 가장자리 8ms 페이드.
  → 클립마다 소리/영상 길이 차이가 쌓여 뒤로 갈수록 입이 밀리는 사고를 막는다. AAC 이음새 '틱' 소리도 막는다.

배경음(bgm.json, 영상 폴더):
  {"files": {"a": "../../assets/bgm/song-a.mp3", "b": "..."}, "gain_db": -13, "fade": 0.5, "end_fade": 3,
   "auto": ["a", "b"]}                       ← 곡을 처음부터 끝까지 틀고, 끝나면 다음 곡(마지막 곡 뒤엔 처음으로). 곡 중간에서 바꾸지 않는다.
   또는 "segments": [[시작초, 끝초, "a", 곡안시작초(, 추가dB)], …]   ← 직접 배치(검수가 겹침·빈 구간·곡 중간 교체를 본다)
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
EDGE = 0.008


def dur(p, stream=None):
    sel = ['-select_streams', f'{stream}:0', '-show_entries', 'stream=duration'] if stream else ['-show_entries', 'format=duration']
    return float(subprocess.run(['ffprobe', '-v', 'error', *sel, '-of', 'csv=p=0', str(p)], capture_output=True, text=True).stdout.strip())


def versions(R, clip):
    return sorted((int(m.group(1)), p) for p in R.glob(f'{clip}-v*.mp4') if (m := re.fullmatch(rf'{re.escape(clip)}-v(\d+)\.mp4', p.name)))


def pick(R, clip, approved):
    vs = versions(R, clip)
    if clip in approved:
        hit = [p for n, p in vs if n == approved[clip]]
        if not hit: raise SystemExit(f'{clip}-v{approved[clip]}.mp4 없음(script.json settings.approved)')
        if vs[-1][0] > approved[clip]: print(f'  ! {clip}: 승인본 v{approved[clip]}보다 높은 v{vs[-1][0]}가 있음 — 승인본을 쓴다')
        return hit[0]
    return vs[-1][1] if vs else None


def join(parts, out):
    vd = [dur(p, 'v') for p in parts]
    lst = out.with_suffix('.txt'); lst.write_text(''.join(f"file '{p.resolve().as_posix()}'\n" for p in parts), encoding='utf-8')
    vtmp, atmp = out.with_name(out.stem + '-v.mp4'), out.with_name(out.stem + '-a.m4a')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-map', '0:v', '-c', 'copy', str(vtmp)], check=True)
    args, ch = [], []
    for i, (p, d) in enumerate(zip(parts, vd)):
        args += ['-i', str(p)]
        ch.append(f'[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=0:{d:.6f},asetpts=PTS-STARTPTS,'
                  f'afade=t=in:d={EDGE},afade=t=out:st={d - EDGE:.6f}:d={EDGE}[a{i}]')
    g = ';'.join(ch) + ';' + ''.join(f'[a{i}]' for i in range(len(parts))) + f'concat=n={len(parts)}:v=0:a=1[a]'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args, '-filter_complex', g, '-map', '[a]', '-c:a', 'aac', '-b:a', '192k', str(atmp)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(vtmp), '-i', str(atmp), '-map', '0:v', '-map', '1:a', '-c', 'copy', '-movflags', '+faststart', str(out)], check=True)
    for f in (vtmp, atmp, lst): f.unlink()
    t, spans = 0.0, []
    for d in vd: spans.append((round(t, 3), round(t + d, 3))); t += d
    return spans


def auto_segments(plan, base, total):
    """곡 하나를 끝까지 → 다음 곡. 곡 길이에서 페이드만큼 빼고 넘긴다."""
    order, fade, segs, t, i = plan['auto'], float(plan.get('fade', .5)), [], 0.0, 0
    while t < total - .05:
        k = order[i % len(order)]; L = dur((base / plan['files'][k]).resolve()) - fade - .1
        segs.append([round(t, 3), round(min(total, t + L), 3), k, 0]); t += L; i += 1
    return segs


def main(argv):
    flags = {a for a in argv if a.startswith('--')}; args = [a for a in argv if not a.startswith('--')]
    if len(args) < 2: sys.exit(__doc__)
    F, name = Path(args[0]).resolve(), args[1]; R = F / 'renders'
    P = json.loads((F / 'script.json').read_text(encoding='utf-8')); S = P.get('settings') or {}
    clips = list(dict.fromkeys(s['id'].split('-')[0] for s in P['scenes']))
    if 'op' in clips: clips = ['op'] + [c for c in clips if c != 'op']
    out = R / f'{name}.mp4'
    if out.exists() and '--force' not in flags: sys.exit(f'{out.name}가 이미 있음 — 이름(버전)을 올리거나 --force')
    parts, order = [], []
    for c in clips:
        p = pick(R, c, S.get('approved') or {})
        if p is None:
            if '--allow-missing' in flags: print(f'  ! {c}: 렌더 없음 — 빼고 이어 붙임(시험용)'); continue
            sys.exit(f'{c}: 클립 렌더가 없습니다(renders/{c}-vN.mp4). 시험으로 빼려면 --allow-missing')
        parts.append(p); order.append(c)
    if S.get('outro'):
        parts.append((F / S['outro']).resolve()); order.append('outro')
    nob = R / f'{name}-nobgm.mp4'
    spans = join(parts, nob)
    (R / f'{name}.json').write_text(json.dumps([{'clip': c, 'file': p.name, 'start': a, 'end': b} for c, p, (a, b) in zip(order, parts, spans)],
                                              ensure_ascii=False, indent=1), encoding='utf-8')
    total = dur(nob); bf = F / 'bgm.json'
    if bf.exists():
        plan = json.loads(bf.read_text(encoding='utf-8'))
        miss = [v for v in plan['files'].values() if not (F / v).exists()]
        if miss: sys.exit(f'배경음 파일이 없습니다: {miss} — 데모 곡은 python tools/make_demo_assets.py로 만들고, 실제 곡은 bgm.json의 files 경로를 고친다')
        if 'auto' in plan: plan['segments'] = auto_segments(plan, F, total)
        plan['files'] = {k: str((F / v).resolve()) for k, v in plan['files'].items()}
        pf = R / f'{name}-bgm.json'; pf.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
        subprocess.run([sys.executable, str(TOOLS / 'bgm.py'), str(nob), str(pf), str(out)], check=True)
    else:
        print('  ! bgm.json 없음 — 배경음 없이 합본'); shutil.copy(nob, out)
    dec = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(out), '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if dec.returncode or dec.stderr.strip(): sys.exit(f'{out.name} 끝까지 디코딩 실패: {dec.stderr.strip()[:300]}')
    if '--no-preview' not in flags:
        sys.path.insert(0, str(TOOLS / 'realkit')); import realkit as rk
        rk.preview(str(out), str(R / f'{name}-preview.mp4'), 480, 30)
    print(f'{out.name} {total:.2f}초, 영상 {dur(out, "v"):.3f} / 소리 {dur(out, "a"):.3f}, 끝까지 디코딩 통과')
    print('클립:', ' / '.join(f'{c} {a:.1f}–{b:.1f}' for c, (a, b) in zip(order, spans)))
    print(f'다음: python tools/qa.py {args[0]} {name}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main(sys.argv[1:])
