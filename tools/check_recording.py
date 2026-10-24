"""전문 복제(PVC)용 녹음 검사 — ElevenLabs 공식 권장 기준에 맞는지 파일마다 확인한다(docs/06).
사용: python tools/check_recording.py <파일 또는 폴더> [...]
기준: 평균 -23 ~ -18 dB RMS, true peak -3 dB 이하, MP3면 192kbps 이상, 한 사람·잡음 없이. 합계 최소 30분, 권장 60분 이상.
잡음은 소리가 없는 구간(숨·멈춤)의 크기로 어림한다 — -60 dB보다 크면 방 소음·에어컨·컴퓨터 팬을 의심한다."""
import json, re, subprocess, sys
from pathlib import Path

EXT = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg'}


def info(p):
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,bit_rate:stream=codec_name,sample_rate,channels', '-of', 'json', str(p)],
                                   capture_output=True, text=True).stdout or '{}')
    st = (pr.get('streams') or [{}])[0]; fm = pr.get('format') or {}
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(p), '-af', 'astats=measure_overall=RMS_level+Peak_level+RMS_trough:measure_perchannel=none,ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace').stderr
    num = lambda pat: (float(m[-1]) if (m := re.findall(pat, r)) and m[-1] not in ('-inf', 'inf') else None)
    return dict(dur=float(fm.get('duration') or 0), kbps=int(fm.get('bit_rate') or 0) // 1000, codec=st.get('codec_name'), ch=st.get('channels'),
                rms=num(r'RMS level dB: (-?[\d.]+|-inf)'), trough=num(r'RMS trough dB: (-?[\d.]+|-inf)'), tp=num(r'Peak:\s+(-?[\d.]+) dBFS'))


def main(args):
    sys.stdout.reconfigure(encoding='utf-8')
    if not args: sys.exit(__doc__)
    files = sorted(f for a in args for f in ([Path(a)] if Path(a).is_file() else Path(a).rglob('*')) if f.suffix.lower() in EXT)
    if not files: sys.exit('녹음 파일이 없습니다(mp3·wav·m4a·flac)')
    total, bad = 0.0, 0
    for f in files:
        x = info(f); total += x['dur']; why = []
        if x['rms'] is not None and not -23 <= x['rms'] <= -18: why.append(f"평균 {x['rms']:.1f} dB → {'마이크 입력을 올리거나 조금 더 가까이' if x['rms'] < -23 else '입력을 낮추거나 조금 멀리'}")
        if x['tp'] is not None and x['tp'] > -3: why.append(f"최고점 {x['tp']:.1f} dB → -3 dB 이하가 되게 입력을 낮춘다(소리 깨짐 위험)")
        if x['codec'] == 'mp3' and x['kbps'] and x['kbps'] < 192: why.append(f"MP3 {x['kbps']}kbps → 192kbps 이상으로 저장")
        if x['trough'] is not None and x['trough'] > -60: why.append(f"조용한 구간 {x['trough']:.0f} dB → 방 소음 의심(팬·에어컨 끄기, 담요로 울림 줄이기)")
        bad += bool(why)
        print(f"{'⚠' if why else '✅'} {f.name}  {x['dur'] / 60:.1f}분  평균 {x['rms'] if x['rms'] is None else round(x['rms'], 1)} dB  최고점 {x['tp']} dB" + ''.join(f'\n    - {w}' for w in why))
    m = total / 60
    print(f"\n합계 {m:.0f}분 — " + ('부족(최소 30분)' if m < 30 else '최소 기준 통과, 60분 이상이면 더 좋아진다' if m < 60 else '권장 분량 통과') + f" / 기준 밖 파일 {bad}개")
    sys.exit(1 if bad or m < 30 else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
