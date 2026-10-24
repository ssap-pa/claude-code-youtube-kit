"""데모용 소스를 합성해 만든다(저작권 걱정 없는 시험용): assets/demo/bg.mp4(움직이는 배경), assets/bgm/demo-a.wav·demo-b.wav(배경음 두 곡).
실제 영상에선 원본 소스와 사용 허락된 음원으로 바꾼다."""
import subprocess, wave
from pathlib import Path
import numpy as np

KIT = Path(__file__).resolve().parent.parent


def song(path, notes, bpm, seconds, seed):
    sr = 44100; beat = 60 / bpm; t_all = np.zeros(int(seconds * sr)); rng = np.random.default_rng(seed)
    for i in range(int(seconds / beat * 2)):
        f = notes[i % len(notes)] * (2 if rng.random() < .15 else 1); a = int(i * beat / 2 * sr); n = int(beat * sr)
        t = np.arange(min(n, len(t_all) - a)) / sr
        t_all[a:a + len(t)] += .18 * np.sin(2 * np.pi * f * t) * np.exp(-t * 5) + .06 * np.sin(2 * np.pi * f / 2 * t) * np.exp(-t * 2)
    t_all /= np.abs(t_all).max() + 1e-9
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((t_all * .8 * 32767).astype('<i2').tobytes())


def main():
    bg = KIT / 'assets' / 'demo' / 'bg.mp4'; bg.parent.mkdir(parents=True, exist_ok=True)
    if not bg.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'gradients=s=1920x1080:c0=0x0b0d14:c1=0x1d2a44:c2=0x123a6a:x0=0:y0=0:x1=1920:y1=1080:nb_colors=3:speed=0.02:d=40:r=30',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', str(bg)], check=True)
    a, b = KIT / 'assets' / 'bgm' / 'demo-a.wav', KIT / 'assets' / 'bgm' / 'demo-b.wav'
    if not a.exists(): song(a, [261.6, 329.6, 392.0, 523.3, 392.0, 329.6], 96, 9, 1)
    if not b.exists(): song(b, [220.0, 277.2, 329.6, 440.0, 329.6, 277.2], 120, 30, 2)
    print('데모 소스:', bg, a, b)


if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8'); main()
