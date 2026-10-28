# AI가 나를 학습하는 구조 — 유튜브 자동화 무료 키트 (Claude Code)

by **ssapable** · [ssapable.com](https://ssapable.com)

> **English:** A free Claude Code kit for YouTube automation that learns from your feedback. Hooks record every correction, a skill files it as a rule (one rule per file), and the next session loads the rules first, so you stop repeating yourself. It also includes a real-UI video editor (HTML scenes rendered at 30fps, with on-screen motion keyed to word timestamps), ElevenLabs text-to-speech, and a pre-upload QA that checks voice/screen sync to the millisecond, transcripts, background-music overlap and loudness. Docs are in Korean.

AI한테 같은 피드백을 반복하고 있다면, AI가 멍청해서가 아니라 **내 피드백이 어디에도 남지 않아서**예요.

이 키트는 내가 한 말을 규칙 파일로 쌓고, 다음 작업을 시작할 때 AI가 그 규칙부터 읽게 만드는 구조예요. 그 위에 영상을 실제로 만드는 **편집 도구·음성·음성↔화면 싱크 검수**까지 넣었어요. 첫 영상 땐 고칠 점만 백 번 가까이 말했지만, 이 구조로 규칙이 쌓인 뒤로는 한 영상에 진행 지시 열 번, 고칠 점 스무 번이면 끝나요.

> **처음이면 [START-HERE.md](START-HERE.md)부터.** 압축을 풀고 Claude에게 말 거는 법부터 첫 데모 영상까지 30분이면 따라 할 수 있어요.

## 들어 있는 것

| 무엇 | 파일 | 하는 일 |
|---|---|---|
| 피드백 기록·세션 시작 훅 | `hooks/` | 내가 한 말을 원문 그대로 남기고, 새 세션·`/clear` 뒤마다 규칙 목록을 Claude에게 넣어요 |
| 피드백 저장 스킬 | `.claude/skills/feedback-loop/` | 피드백을 네 곳으로 나눠 저장해요: 이번 영상만, 앞으로 계속, 작업 순서, 재발 사고 |
| 대본 스킬 | `.claude/skills/youtube-script/` | 학습한 규칙대로 대본을 장면 단위로 쓰고 → 표기 검사 → 내 목소리 음성까지 |
| 화면 디자인 스킬 | `.claude/skills/real-ui-design/` | 원본 흐림 배경 + 실사 휴대폰·앱 화면 + 알림·카드의 세 층으로 장면을 만드는 법 |
| 편집 도구 | `tools/realkit/`, `templates/video/` | 장면을 HTML로 짜서 30fps로 찍어요. **화면 움직임이 대사 단어 시각에 맞춰 자동으로 붙어요** |
| 세로 설명 쇼츠 | `.claude/skills/shorts-explainer/`, `templates/shorts/`, `docs/07` | 3D 모형 장면 + 2~3단어 말 자막 + 큰 숫자 카드로 "왜?"를 설명하는 9:16 쇼츠. 새 쇼츠는 빈 틀(`new_video.py --shorts`)에서 시작하고, 「부르즈 할리파는 왜 계단처럼 깎였을까」 완성 예제(`--shorts --example`)도 그대로 들어 있어요. 스타일은 로우폴리 3D(무료). AI 실사 컷을 섞는 실사 스타일은 전체 키트 |
| 합본·배경음 | `tools/make_final.py`, `tools/bgm.py` | 클립 이음새 입 밀림 방지, 대사 때 배경음 자동으로 줄이기, 곡을 끝까지 틀고 바꾸기 |
| 업로드 전 검수 | `tools/qa.py`, `tools/regressions.json` | 대본=음성=클립=합본 판 확인, 장면 음성 위치(ms 단위), 받아쓰기↔대본, 배경음 겹침, 검은 화면, 음량, 전에 고친 사고 재발 |
| 대본 검사 | `tools/check_script.py` | 소문자 'ai'를 '아이'로 읽는 것처럼 전에 고친 실수, 체감 비교 없는 큰 숫자를 음성 만들기 전에 막아요 |
| ElevenLabs 연결 | `tools/voice.py`, `.mcp.json`, `docs/03`, `docs/06` | 단어 시각까지 받는 음성 합성(캐시로 크레딧 절약), 내 목소리 전문 복제 가이드 |
| 시작 규칙 7개 | `memory/rules/` | 실제 사고에서 나온 규칙(숫자는 한글로, 영어는 대문자로, 큰 숫자는 체감되게 …) |
| 데모 | `videos/demo/`, `templates/video/` | 일부러 틀린 대본으로 학습 구조 시험 + 12초 데모 영상 렌더·검수 |

## 내 목소리로 만들면 채널이 달라져요

기본 목소리는 누구나 써서 다른 채널과 똑같이 들려요. 시청자가 기억하는 건 **내 목소리**예요. ElevenLabs 전문 복제로 한 번 녹음해 두면 감정과 억양까지 살아 있는 내 목소리가 나오고, 그다음부터는 대본만 쓰면 돼요. 한 번 해 놓으면 앞으로가 계속 편해요.

**👉 [ElevenLabs 첫 달 50% 할인 링크로 내 목소리 전문 복제하기](https://try.elevenlabs.io/surgaf77dx55)** · 녹음부터 연결까지: [docs/06](docs/06-내-목소리-전문-복제.md)

<sub>Creator 요금제(전문 복제가 되는 요금제) 첫 달 50% 할인 — 2026-10-25 ElevenLabs 요금 화면 기준. 할인 조건은 ElevenLabs 사정에 따라 바뀔 수 있어요.</sub>

## 나에게 맞는 단계

| 단계 | 무엇을 받나 | 이런 분께 |
|---|---|---|
| **무료 키트** (이 저장소) | 학습 구조 + 편집·음성·싱크 검수 도구 + 3D 세로 설명 쇼츠 + 스킬 4개 + 시작 규칙 7개 | 구조를 직접 써 보고, 3D 쇼츠 한 편을 손으로 이끌며 만들어 보고 싶은 분 |
| **[전체 키트 — 99,000원](https://ssapable.com/courses/youtube-automation-kit)** | 쌉파의 스킬 100% — 주제 하나로 리서치 → 소스 수집 → 클립 병렬 제작 → 오프닝 → 업로드 준비까지 가는 제작 스킬, AI 실사 장면 생성 연결(After 영상 수준), 시작 규칙 14개 | 검증된 방식을 한 번에 적용해서 주제만 말하면 영상이 나오게 하고 싶은 분 |

**Before / After 예시:** 같은 주제를 무료 키트(3D 장면)와 전체 키트(AI 실사 장면 + 3D + 체감 수치)로 만든 영상 — [무료 키트 상품 페이지](https://ssapable.com/courses/youtube-kit-free)에서 볼 수 있어요.
| **[강의](https://ssapable.com/courses/ai-agent)** | 내 분야에 맞는 영상 구조·학습 구조·스킬을 직접 설계하고 쌓는 법, 그걸 내 키트로 만들어 파는 법 | 나에게 맞게 바꾸고 싶은 분, 어떤 분야든 영상을 만들고 싶은 분, 나도 키트를 만들어 팔고 싶은 분 |

무료판 사용 안내: [ssapable.com/courses/youtube-kit-free](https://ssapable.com/courses/youtube-kit-free)

## 준비물

- [Claude](https://claude.com/download) 데스크톱 앱(Pro 이상 요금제), Python 3.10+, ffmpeg
- ElevenLabs 계정: 없어도 데모는 돌아가요(`--demo`)

라이선스: [LICENSE.txt](LICENSE.txt). 무료로 쓰고 고쳐도 돼요. 공유할 때는 원래 받은 곳 링크로 안내해 주세요.
