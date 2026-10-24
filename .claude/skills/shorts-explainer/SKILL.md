---
name: shorts-explainer
description: 세로(9:16) 설명 쇼츠를 만드는 흐름 — 건축·과학·사건의 "왜?"를 3D 모형 장면 + 내레이션 + 2~3단어 말 자막 + 큰 숫자 카드로 30초~3분에 설명한다. 사용자가 "쇼츠 만들어", "세로 영상", "설명 쇼츠", "이 채널 쇼츠 스타일로", "3D로 설명하는 영상"이라고 하거나 참고 채널의 세로 영상 스타일을 따라 하고 싶다고 할 때 쓴다. 가로 영상은 real-ui-design 스킬과 templates/video.
---

# 세로 설명 쇼츠

작동 예제: `templates/shorts`(「부르즈 할리파는 왜 계단처럼 깎였을까」 40초 — 장면 6개, three.js 3D, 말 자막, 숫자 카드). 새 쇼츠는 `python tools/new_video.py --shorts <slug>`로 이 예제를 복사해 시작하고 내용을 바꾼다.

## 0. 참고 채널이 있으면 — 스타일을 규칙으로 먼저 저장

사용자가 참고 채널·영상을 주면 만들기 전에 분석해 `memory/rules`에 남긴다(feedback-loop 스킬). 다음 쇼츠부터 묻지 않고 적용된다.
- 조회수가 높은 영상 2~3편의 프레임 시트(2~3초 간격)와 자막을 본다. 받기: `python -m yt_dlp -f "b[height<=720]" --write-auto-subs --sub-langs ko <URL>`(분석용, 영상·장면을 그대로 쓰지 않는다).
- 뽑을 것: 길이, 컷 간격, 화면 재료(실사·3D·그림), 자막 위치·크기·단어 수, 숫자 카드 쓰는 법, **대본 뼈대**(첫 문장 형식, 갈등 문장, 반전 문장, 마무리), 숫자 비유 방식, 말투.
- 남기지 않을 것: 그 채널의 고유 문구를 그대로 베끼기, 영상·장면 재사용, 같은 주제 그대로 따라 하기.

## 1. 주제·대본 ✋

- 한 편 = 질문 하나("왜 ~일까?"). 답은 끝에서 공개한다(hide-answer 규칙).
- 예제 뼈대: ① "여기 ~이 있습니다" + 가장 센 숫자 → ② 배경 → ③ "진짜 문제는 ~" → ④ "그래서 ~하기로 합니다" → ⑤ 원리 → ⑥ 결과 숫자 + 체감 비교.
- 사실은 원문 출처로 확인하고 `RESEARCH.md`에 적는다(no-invented-facts). 숫자는 대본에 한글로, 자막엔 `SUB`로 숫자로(빌더 상단).
- **큰 수치는 반드시 체감 비교와 같이**(big-numbers-relatable): 828m → "아파트 이백팔십 층", 435m → "축구장 네 개". 화면 카드도 비교를 크게, 원래 수치를 작게("아파트 280층 / 828m"). 환산 근거는 RESEARCH에. `check_script.py`가 비교 없는 큰 수치를 막는다(사고: 예제 첫 문장 '팔백이십팔 미터짜리 건물').
- 한 장면 = 한 문장. 장면 6~12개(30~60초) 또는 20~30개(2~3분).

## 2. 음성

`python tools/voice.py videos/<slug>` — 첫 장면은 `"tone": "hype"`. 쇼츠는 `speed` 1.05~1.1이 잘 맞는다.

## 3. 장면 — 비용 없는 3D가 기본

- 장면 HTML 하나 = 문장 1~2개, 그 안에서도 카메라를 바꿔 **2~4초마다 그림이 바뀌게** 한다(`if (t < c.다음) S.orbit(...) else S.orbit(...)`).
- 도구: `tools/realkit/scene3d.js`.
  - 바닥과 도시: `S.ground`
  - 상자와 Y자 평면 블록: `S.box`·`S.yBlock`
  - 바람과 흐름: `S.trails`(굵은 점 꼬리, 휴대폰에서 잘 보임)·`S.streaks`(선)
  - 카메라: `S.orbit`
  - 3D 위치 꼬리표: `S.tag`
  - 잘라 보이기: `S.renderer.clippingPlanes`
  - 계속 쓸 모형은 `clips/<clip>/<모형>.js`로 따로 둔다(예: `burj.js`).
- 화면 신호는 대사 단어에서: `V.T('v1-s3', '오백십팔', base='v1-s3')` → HTML `data-anim="pop@m518"`, JS `RK.cues.m518`.
- 큰 숫자·낱말 카드 `.kw`(위쪽 1/3), 3D 꼬리표 `.tag3d`, 말 자막은 빌더가 `V.captions(...)`로 자동.
- 세로 안전 영역: 위 220px·아래 380px엔 글자를 두지 않는다(쇼츠 화면 버튼·제목이 덮음). 자막은 1120px 높이.
- 실사 인물·현장감이 꼭 필요한 컷의 AI 영상 생성(Gemini) 연결은 전체 키트에 있다(https://ssapable.com/courses/youtube-automation-kit). 무료 키트는 3D 장면과 직접 촬영·저작권 문제없는 실제 사진·영상으로 만든다. 사용자가 원하면 한 줄로 알리고, 없는 도구를 지어내지 않는다.
- 정지 시안 먼저: `RK_FORMAT=vertical python tools/realkit/realkit.py still videos/<slug>/clips/v1/a.html 2.0 a.png` → 사용자 확인 ✋ (Windows PowerShell은 `$env:RK_FORMAT="vertical"`).

## 4. 렌더·합본·검수

```bash
python videos/<slug>/build_v1.py                    # renders/v1-vN.mp4 + 프레임 시트(1초 간격)
python tools/make_final.py videos/<slug> final-v1
python tools/qa.py videos/<slug> final-v1           # 싱크·발음·배경음·재발
```
프레임 시트를 직접 본다. 실제로 났던 사고는 이렇다.
- 카메라가 건물 속을 지나가 화면이 회색으로 가려짐 → `cityMin`으로 막는다.
- 바람 입자가 밝은 배경에 묻힘 → 진한 색 `S.trails`로 그린다.
- 자막과 숫자 카드가 겹침.

## 5. 업로드 준비 ✋

제목은 질문형, 답을 넣지 않는다. 쇼츠는 60초를 넘으면(최대 3분) 길이에 맞게 끝까지 볼 이유를 중간에 한 번 더 건다. 업로드는 사용자 확인 뒤.
