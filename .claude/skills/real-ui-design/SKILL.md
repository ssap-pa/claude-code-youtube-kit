---
name: real-ui-design
description: 유튜브 영상 화면을 '원본 장면 흐림 배경 + 디테일한 실사 기기(휴대폰·앱 창·브라우저) + 앞 UI 카드·알림'의 세 층으로 만드는 디자인 방식과 realkit 사용법. 영상 클립·오프닝·썸네일 시안을 만들 때, 사용자가 "실사 UI", "원본 흐림 배경", "휴대폰 화면처럼", "앱 알림 뜨는 화면", "장면 HTML 만들어" 같은 말을 하거나 영상 클립·오프닝 화면을 만들 때 사용한다. 이 스킬은 화면 모양만 정한다 — 대본은 youtube-script 스킬, 검수는 tools/qa.py를 따른다.
---

# 실사 UI 디자인

장면 하나 = 세 층. 실제 소스가 화면의 주인공이고, UI는 그것을 "실제 휴대폰·앱에서 일어나는 일"처럼 보이게 감싼다. 원 제작자가 여러 안(보라·코랄 그라데이션, 게임 HUD, 클립아트)을 비교한 끝에 고른 방식이다.

키트: `tools/realkit/` — `base.css`(휴대폰·알림·카드·창·플레이어·스포트라이트·로고 배지 뼈대), `theme-real.css`(색·재질 변수), `motion.css`(움직임 키프레임), `realkit.js`(시간 제어 `RK.seek`), `ui-icons.js`(자체 그린 UI 기호), `realkit.py`(합성·렌더 도구). 글꼴은 `python tools/get_fonts.py`로 받는다(없으면 대체 글꼴로 그려진다).

## 1. 세 층

1. **뒤: 원본 장면 흐림 배경** — 그 장면의 실제 소스(원본 영상 구간·녹화)를 화면 가득(cover) 깔고 흐림(1080p 기준 반지름 16~18px, realkit 960×540 시퀀스에선 `blur=8`쯤), 밝기 0.70~0.78, 가장자리 어두운 비네트. 흐림은 CSS blur가 아니라 **미리 구워**(realkit `seq`·`still`) 가장자리 번짐을 막는다. 영상이면 아주 느린 밀어 넣기(`data-anim="push"`). 장면이 바뀌면 배경 원본도 그 장면의 것으로 바꾼다.
2. **가운데: 실사 기기** — 얇은 베젤·다이내믹 아일랜드·상태 표시줄(9:41·신호·와이파이·배터리)을 갖춘 휴대폰, 또는 앱 창·브라우저 창. **화면 안은 실제 소스**(원본을 세로로 잘라 실제 재생, 실제 녹화)이지 그린 그림이 아니다. 정지된 검은 화면 금지.
3. **앞: 정보 카드·알림** — iOS식 밝은 반투명 알림 배너(앱 아이콘 + 제목 + 한 줄 내용 + 시간)가 기기 밖으로 떠오르고, 프로필·매출·통계는 어두운 유리 카드.

## 2. 색·재질 (`theme-real.css` 변수로만 바꾼다)

- 바탕 `#0d0d0f`, 글자 흰색 / 72% / 50%.
- 강조(누르는 것·링크·잠금) 파랑 `#0a84ff`, **돈은 초록 `#30d158`**, 좋아요 빨강 `#ff3040`은 작게만.
- 어두운 유리 카드: `rgba(22,22,26,.56)` + `backdrop-filter: blur(28px) saturate(150%)` + 테두리 `rgba(255,255,255,.16)` + 그림자.
- 알림 배너: `rgba(242,242,247,.80)` + `blur(30px) saturate(180%)`, 글자 `#111113`/`#3c3c43`, 아이콘 모서리 20px.
- 매출 같은 핵심 숫자는 크게(120px 안팎) 초록, 아래 작은 설명 한 줄.

## 3. 하지 않는 것

- 보라·코랄·네온 그라데이션 배경, 클립아트 동전·하트 더미, 장난감 스티커, 게임 HUD(원 제작자가 비교 후 거절).
- 회색 줄로 대충 그린 가짜 알림·내용 없는 자리 표시 카드.
- **지어낸 숫자·댓글·후기.** 알림·카드 속 숫자와 문구는 원본·녹화에서 확인한 값만(예: "주문 23건 · 건당 $12"). 확인 못 한 값은 넣지 않는다. 시안용 임시 문구는 최종 영상 전에 실제 값으로 바꾼다.
- 상표 그대로 베끼기(실제 앱 로고·고유 아이콘으로 앱 UI를 흉내). 'OO풍' 자체 UI로 만들고 앱 이름은 쓰지 않거나 일반 단어로. 브랜드를 **말하는** 장면의 심볼 로고 배지(출처 표시)는 logo-symbol 규칙대로 쓴다.
- '예시'·'재연' 칩. 실사형 AI 생성 장면은 업로드 설정의 AI 합성 공개로 표시한다.
- 답 먼저 보여 주기: 제목·오프닝이 숨긴 답은 잠금 화면 + 큰 물음표로 가린다.

## 4. 글자

- 기본값 하다 산스 하나만(Black 900 / ExtraBold 800 / Bold 700 / SemiBold 600 / Medium 500). 바꾸려면 memory 규칙으로 남기고 `base.css`의 `@font-face`와 realkit 글꼴 검사를 함께 바꾼다.
- **1080p 기준 가장 작은 글자도 28px 이상**(휴대폰 시청 가독성). realkit이 28px 미만·다른 글꼴·대체 글꼴을 경고한다.
- 글자는 실제 앱 문구(짧게)·숫자·고유명사만. 긴 문장은 의미 단위로 줄바꿈.
- 출처 칩: 원본이 들어간 곳 근처에 작게 "채널 · YouTube"(빨간 재생 아이콘 + 흰 글자, 어두운 반투명 바탕). 방송 자막·로고를 가리지 않게.

## 5. 움직임

- 알림: 위에서 미끄러져 내려오며 살짝 튕김(0.3~0.4초), 여러 개면 부채꼴로 쌓임, 등장마다 `noti` 효과음.
- 결제 알림 → 매출 카드: 숫자 세기(0.8~1.2초, `data-count`) + 작은 상승 그래프, 등장 때 `pay` 효과음.
- 탭: 손가락 커서가 눌림 + 퍼지는 파란 원, 누른 뒤 화면 전환은 흐림 사이로 녹아들기. `tap` 효과음.
- 기기 화면 안 원본은 실제로 재생한다. 원본 영상 소리는 쓰지 않는다(우리 대사만).
- 실제 녹화(데스크톱 앱 등)는 기기 대신 실사 창 프레임 안에 넣어도 된다. 클릭 대상은 대사 시점에 스포트라이트.
- 움직임은 개별 속성(`translate`·`scale`·`opacity`)만. 잠깐 커지는 등장(pop·zin) 중엔 글자가 28px보다 작아질 수 있으니 점검은 움직임이 끝난 시각으로.

## 6. 만드는 순서

1. 장면마다 쓸 실제 소스를 고른다 — 배경용, 기기 화면용, 카드에 들어갈 확인값.
2. 소스 준비(클립 빌더 `videos/<slug>/build_<clip>.py` 안에서):
   ```python
   import sys; sys.path.insert(0, 'tools/realkit'); import realkit as rk   # 키트 루트에서 실행 기준
   V = rk.Voice('videos/<slug>/renders/voice-v1/voices.json')            # 장면 길이 = 음성 + 0.22초
   S = 'videos/<slug>/clips/v1/src'
   rk.seq(f'{S}/news.mp4', f'{S}/s1_bg', t0=0.6, dur=V.dur('v1-s1'), size=(960, 540), blur=8, bright=.76)      # 흐림 배경
   rk.seq(f'{S}/news.mp4', f'{S}/s1_screen', t0=0.6, dur=V.dur('v1-s1'), crop=(1298, 0, 622, 1080), size=(476, 984))  # 휴대폰 화면
   rk.seq(f'{S}/rec.mp4', f'{S}/s2_rec', dur=V.dur('v1-s2'), size=(1280, 720), boxes=[(578, 455, 772, 78, 26)])  # 원본 좌표 상자를 흐림(개인 정보·숨길 답)
   rk.still(f'{S}/page.png', f'{S}/bg.jpg', size=(960, 540), blur=9, bright=.6)                            # 그림 한 장
   ```
3. 장면 HTML `videos/<slug>/clips/v1/<장면>.html` — `tools/realkit/`의 `base.css`·`theme-real.css`·`motion.css`·`ui-icons.js`·`realkit.js`를 상대 경로(`../../../../tools/realkit/…`)로 링크.
   - `<img data-seq="src/s1_bg" data-t0="ai">` : 신호 시각에 0번 프레임부터 30fps 재생.
   - `data-anim="drop@like, out@and+0.05"` : `이름[:길이[:fill]]@시각`. 시각은 초 또는 신호 이름±초.
   - `<span data-count="276" data-ct="week+0.2" data-ct-end="rev+0.75" data-dec="2" data-pre="$">` : 숫자 세기.
   - 브라우저에서 바로 보기: `<장면>.html?t=3.5`(정지), `?play=1`(실시간).
4. 정지 시안 ✋: `python tools/realkit/realkit.py still videos/<slug>/clips/v1/<장면>.html 3.5 videos/<slug>/renders/v1-still-1.png`. 새 영상의 첫 시안은 사용자 확인을 받는다.
5. 신호·효과음·렌더(같은 빌더 안):
   ```python
   cues = {'ai': V.T('v1-s1', 'AI로'), 'like': V.T('v1-s1', '인플루언서로')}   # 대사 단어가 시작하는 시각
   shots = [rk.Shot('videos/<slug>/clips/v1/s1.html', ['v1-s1'], cues, seqs=['src/s1_bg', 'src/s1_screen'],
                    sfx=[{'t': 1.3, 'kind': 'noti'}], check_at=[3.9])]           # 장면 순서 = voices.json 순서
   rk.build(V, shots, 'videos/<slug>/renders/v1-v1.mp4', 'videos/<slug>/renders/v1-v1-job')   # 병렬 렌더 → 음성+효과음 → 끝까지 디코딩
   rk.preview('videos/<slug>/renders/v1-v1.mp4', 'videos/<slug>/renders/v1-v1-preview.mp4')    # 휴대폰 확인용 480p
   ```
   효과음은 파일 없이 합성된다: `noti`·`pay`·`tap`·`click`·`pop`·`whoosh`·`tick`·`thud`·`rise`·`swish`·`stamp`·`done`. 출력은 1920×1080 30fps H.264 + AAC, -16 LUFS.
6. 점검: `python tools/realkit/realkit.py sheet videos/<slug>/renders/v1-v1.mp4 videos/<slug>/renders/v1-v1-sheet.jpg 1` — 1초 간격 시트로 겹침·잘림(사방 40px 여백)·대비·답 노출·지어낸 값을 확인하고, `check_at` 경고(28px·글꼴·없는 신호)를 0으로 만든다.

## 7. 다른 규칙과의 관계

소스 우선순위(원본 영상 1순위), 0~3초 실제 소스 중 가장 센 장면, 심볼 로고, 답 숨기기, 화면 글자 최소화, 같은 소스 반복 금지, 검수는 `tools/qa.py`(docs/04)를 따른다. 이 스킬은 **화면 모양만** 정한다. 사용자가 다른 디자인을 원하면 같은 두 장면(0~3초·반전)으로 정지 시안 3안을 만들어 비교 시트(`rk.grid`)로 보여 주고 고르게 한 뒤, 고른 방향을 memory 규칙으로 남긴다.
