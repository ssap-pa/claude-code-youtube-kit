# AI가 나를 학습하는 구조 — 유튜브 자동화 무료 키트 (Claude Code)

by **ssapable** · [ssapable.com](https://ssapable.com)

> **English:** A free Claude Code kit that makes your AI learn from your feedback. Hooks record every correction, a skill files it as a rule, one rule per file, and the next session loads the rules before it starts, so you stop repeating yourself. Includes a script-writing skill, a pre-TTS script checker, and ElevenLabs text-to-speech with word timestamps. Docs are in Korean.

AI한테 같은 피드백을 반복하고 있다면, AI가 멍청해서가 아니라 **내 피드백이 어디에도 남지 않아서**예요.

이 키트는 내가 한 말을 규칙 파일로 쌓고, 다음 작업을 시작할 때 AI가 그 규칙부터 읽게 만드는 구조예요. 영상을 만들며 실제로 쓰는 구조를 그대로 떼어 왔어요. 첫 영상 땐 고칠 점만 백 번 가까이 말했지만, 이 구조로 규칙이 쌓인 뒤로는 한 영상에 진행 지시 열 번, 고칠 점 스무 번이면 끝나요.

> **처음이면 [START-HERE.md](START-HERE.md)부터.** 압축을 풀고 Claude에게 말 거는 법까지 10분이면 따라 할 수 있어요.

## 들어 있는 것

| 무엇 | 파일 | 하는 일 |
|---|---|---|
| 피드백 기록 훅 | `hooks/capture_feedback.py` | 내가 한 말을 원문 그대로 `memory/inbox.jsonl`에 남겨요. 고칠 점으로 보이면 저장하라고 Claude에게 알려 줘요 |
| 세션 시작 훅 | `hooks/session_start.py` | 새 세션·`/clear`·대화 요약 뒤마다 규칙 목록을 Claude에게 넣어요 |
| 저장 절차 스킬 | `.claude/skills/feedback-loop/` | 피드백을 네 곳으로 나눠 저장해요: 이번 작업만, 앞으로 계속, 작업 순서, 재발 사고 |
| 대본 스킬 | `.claude/skills/youtube-script/` | 학습한 규칙대로 대본을 장면 단위로 쓰고 → 표기 검사 → 내 목소리 음성까지 |
| 규칙 관리 | `tools/memory.py`, `memory/` | 규칙 하나 = 파일 하나(무엇·왜·어떻게). 시작 규칙 4개 포함 |
| 대본 검사 | `tools/check_script.py`, `tools/regressions.json` | 전에 고친 표기 사고가 대본에 다시 들어오면 음성을 만들기 전에 막아요 |
| ElevenLabs 연결 | `tools/voice.py`, `.mcp.json`, `docs/03` | 공식 API로 단어 시각까지 받는 음성 합성(캐시로 크레딧 절약), 공식 원격 MCP 연결 |
| 내 목소리 전문 복제 | `docs/06`, `tools/check_recording.py` | 녹음이 공식 기준에 맞는지 검사하고, 만든 목소리를 연결해요 |
| 데모 | `videos/demo/` | 일부러 틀린 대본 → 검사 → 고치고 규칙으로 저장 → 새 세션에서 적용되는지 확인 |

## 내 목소리로 만들면 채널이 달라져요

기본 목소리는 누구나 써서 다른 채널과 똑같이 들려요. 시청자가 기억하는 건 **내 목소리**예요. ElevenLabs 전문 복제로 한 번 녹음해 두면 감정과 억양까지 살아 있는 내 목소리가 나오고, 그다음부터는 대본만 쓰면 돼요. 한 번 해 놓으면 앞으로가 계속 편해요.

**👉 [ElevenLabs 첫 달 50% 할인 링크로 내 목소리 전문 복제하기](https://try.elevenlabs.io/surgaf77dx55)** · 녹음부터 연결까지: [docs/06](docs/06-내-목소리-전문-복제.md)

<sub>Creator 요금제(전문 복제가 되는 요금제) 첫 달 50% 할인 — 2026-10-25 ElevenLabs 요금 화면 기준. 할인 조건은 ElevenLabs 사정에 따라 바뀔 수 있어요.</sub>

## 전체 키트 (신규 기수 수강생 특전)

이 무료 키트는 "학습하는 구조"까지예요. 영상을 끝까지 만드는 부분은 **AI 쌉파써블 강의 신규 기수 수강생에게 전체 키트로** 드려요.
- 주제 하나로 리서치 → 대본 → 음성 → 편집 → 합본 → 업로드 준비까지 가는 제작 스킬
- 실사 UI 편집 도구(대사 단어에 맞춰 화면이 움직임)
- 음성·화면 싱크 검수(ms 단위 음성 위치, 받아쓰기 대조, 배경음 겹침, 재발 검사)
- 3D 장면 세로 설명 쇼츠 모드
- 실제 사고에서 나온 시작 규칙 14개

모집 소식: [ssapable.com](https://ssapable.com)

## 준비물

- [Claude](https://claude.com/download) 데스크톱 앱(Pro 이상 요금제), Python 3.10+, ffmpeg
- ElevenLabs 계정: 없어도 데모는 돌아가요(`--demo`)

라이선스: [LICENSE.txt](LICENSE.txt). 무료로 쓰고 고쳐도 돼요. 공유할 때는 원래 받은 곳 링크로 안내해 주세요.
