"""완성 영상에 배경음악을 깐다. 곡마다 음량을 노멀라이즈하고, 대사가 나오면 자동으로 줄인다(덕킹). 영상은 다시 인코딩하지 않는다.
사용: python bgm.py 영상.mp4 계획.json 출력.mp4
계획 = {"files": {"이름": "음원 경로"}, "gain_db": -13, "fade": 0.5, "end_fade": 3,   # end_fade: 영상 끝에서 배경음악을 서서히 줄이는 초(없으면 0)
        "segments": [[시작초, 끝초, "이름", 곡시작초(, 추가dB)], ...]}   # 구간끼리 fade만큼 겹쳐 자연스럽게 넘어간다. 추가dB: 대사 없는 엔딩처럼 음악만 나오는 구간을 키울 때
"""
import json, subprocess, sys, tempfile
from pathlib import Path

def main(video, plan_file, out, mode=''):   # mode='bgm-only': 덕킹된 배경음악만 wav로(음량 점검용)
    plan = json.loads(Path(plan_file).read_text(encoding='utf-8')); base = Path(plan_file).parent
    fade = float(plan.get('fade', .5)); gain = float(plan.get('gain_db', -13)); segs = plan['segments']; end_fade = float(plan.get('end_fade', 0))
    probe = lambda p: float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)], capture_output=True, text=True).stdout)
    total = probe(video)
    args, chains, tmp = ['-i', video], [], Path(tempfile.mkdtemp(prefix='bgm_'))
    for i, sg in enumerate(segs):
        a, b, key, off = sg[:4]; extra = float(sg[4]) if len(sg) > 4 else 0.0
        b = min(b, total); dur = b - a + (fade if b < total - .01 else 0)
        src = (base / plan['files'][key]).resolve()
        if off + dur > probe(src) - .05:
            # 곡 끝을 넘는 구간: 예전 '-stream_loop -1'은 곡이 한 바퀴 돈 뒤 -t·afade가 먹지 않아 구간이 끝나도 곡이 계속 나와
            # 다음 구간 곡과 겹쳤다(실제 사고: 업로드한 영상 7분부터 두 곡이 같이 나옴). 같은 곡을 이어 붙인 목록(concat)에서 잘라 쓴다.
            lst = tmp / f'loop{i}.txt'
            lst.write_text(''.join(f"file '{src.as_posix()}'\n" for _ in range(int((off + dur) // probe(src)) + 2)), encoding='utf-8')
            args += ['-f', 'concat', '-safe', '0', '-ss', str(off), '-t', f'{dur:.3f}', '-i', str(lst)]
        else:
            args += ['-ss', str(off), '-t', f'{dur:.3f}', '-i', str(src)]
        ms = round(a * 1000)
        chains.append(f'[{i + 1}:a]loudnorm=I=-16:LRA=7:TP=-2,aresample=48000,aformat=channel_layouts=stereo,'
                      f'afade=t=in:d={fade if a > 0 else .05},afade=t=out:st={max(0, dur - fade):.3f}:d={fade},volume={extra}dB,adelay={ms}|{ms}[m{i}]')
    n = len(segs)
    g = ';'.join(chains) + ';' + ''.join(f'[m{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0:duration=longest,volume={gain}dB,atrim=0:{total:.3f}' + (f',afade=t=out:st={total - end_fade:.3f}:d={end_fade}' if end_fade else '') + '[bgm];' \
        '[0:a]pan=stereo|c0=c0|c1=c0,asplit=2[v][key];' \
        '[bgm][key]sidechaincompress=threshold=0.08:ratio=2:attack=60:release=600:makeup=1[duck];' \
        '[v][duck]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[out]'
    if mode == 'bgm-only':
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *args, '-filter_complex', g.replace('[duck];[v][duck]amix', '[duck];[v]anullsink;[duck]anull[out];[v0]amix', 1).split(';[v0]amix')[0], '-map', '[out]', out], check=True); return
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args, '-filter_complex', g, '-map', '0:v', '-map', '[out]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    print('bgm ok', out)

if __name__ == '__main__':
    main(*sys.argv[1:5])
