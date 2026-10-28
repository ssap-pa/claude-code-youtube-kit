"""데모용 소스를 합성해 만든다(저작권 걱정 없는 시험용): assets/demo/bg.mp4(움직이는 배경), assets/bgm/demo-a.wav·demo-b.wav(배경음 두 곡).
실제 영상에선 원본 소스와 사용 허락된 음원으로 바꾼다(처음 세팅의 배경음 — kit-setup 스킬).
데모 곡은 같은 소절이 되풀이되지 않게 멜로디·박자를 매번 새로 뽑고, 60초 쇼츠 한 편을 한 곡으로 덮을 만큼 길다
(사고: 6음짜리 짧은 곡이 되풀이돼 qa.py가 '같은 곡 다른 지점이 섞임'으로 잘못 잡음). 예전의 짧은 데모 곡이 있으면 새로 만든다."""
import subprocess, wave
from pathlib import Path
import numpy as np

KIT = Path(__file__).resolve().parent.parent
PENTA = [0, 2, 4, 7, 9]   # 장조 5음 음계(반음)
SONGS = {'demo-a': dict(root=261.6, bpm=96, seconds=75, seed=1), 'demo-b': dict(root=220.0, bpm=112, seconds=95, seed=2)}


def note_hz(root, deg):
    o, i = divmod(deg, len(PENTA)); return root * 2 ** ((12 * o + PENTA[i]) / 12)


def cents(rng, c=18):   # 음마다 아주 조금 다른 음높이 — 같은 음 묶음이 다른 곳과 파형까지 똑같아지지 않게(검수가 '다른 지점'으로 착각하지 않게)
    return 2 ** (rng.uniform(-c, c) / 1200)


def pluck(f, n, sr, decay, vel):
    t = np.arange(n) / sr
    return vel * (.18 * np.sin(2 * np.pi * f * t) + .05 * np.sin(4 * np.pi * f * t)) * np.exp(-t * decay)


def song(path, root, bpm, seconds, seed, sr=44100):
    """되풀이 없는 데모 곡: 멜로디는 5음 음계 위를 무작위로 걷고(음 길이도 무작위), 베이스는 마디마다 무작위 화음 뿌리음."""
    rng = np.random.default_rng(seed); beat = 60 / bpm; out = np.zeros(int(seconds * sr)); deg, t = 5, 0.0
    while t < seconds:
        d = beat * rng.choice([.5, .5, .75, 1, 1, 1.5, 2]); deg = int(np.clip(deg + rng.choice([-2, -1, -1, 0, 1, 1, 2, 3, -3]), 0, 11))
        a = int((t + rng.uniform(0, .04)) * sr); n = min(int(beat * 2 * sr), len(out) - a)   # 박자에 살짝 사람 손맛
        if n > 0 and rng.random() > .12: out[a:a + n] += pluck(note_hz(root, deg) * cents(rng), n, sr, rng.uniform(3, 6), rng.uniform(.6, 1))   # 가끔 쉼표
        t += d
    for bar in range(int(seconds / (beat * 4)) + 1):   # 베이스: 마디마다 무작위 뿌리음, 박자 위치도 조금씩 다르게
        r = root / 2 * 2 ** (rng.choice([0, 5, 7, 9, -3]) / 12)
        for k in [[0], [0, 2], [0, 1.5, 3], [0, 3]][rng.integers(4)]:
            a = int((bar * 4 + k) * beat * sr); n = min(int(beat * 1.5 * sr), len(out) - a)
            if n > 0: out[a:a + n] += .7 * pluck(r * cents(rng, 30), n, sr, 2.5, rng.uniform(.5, .8))
    out /= np.abs(out).max() + 1e-9
    fade = int(1.5 * sr); out[-fade:] *= np.linspace(1, 0, fade)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out * .8 * 32767).astype('<i2').tobytes())


def seconds_of(path):
    try:
        with wave.open(str(path)) as w: return w.getnframes() / w.getframerate()
    except Exception:
        return 0


def main():
    bg = KIT / 'assets' / 'demo' / 'bg.mp4'; bg.parent.mkdir(parents=True, exist_ok=True)
    if not bg.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'gradients=s=1920x1080:c0=0x0b0d14:c1=0x1d2a44:c2=0x123a6a:x0=0:y0=0:x1=1920:y1=1080:nb_colors=3:speed=0.02:d=40:r=30',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', str(bg)], check=True)
    for name, o in SONGS.items():
        p = KIT / 'assets' / 'bgm' / f'{name}.wav'
        if seconds_of(p) < o['seconds'] - 1: song(p, **o)   # 없거나 예전 짧은 곡이면 새로
    print('데모 소스:', bg, *(KIT / 'assets' / 'bgm' / f'{n}.wav' for n in SONGS))


if __name__ == '__main__':
    import sys; sys.stdout.reconfigure(encoding='utf-8'); main()
