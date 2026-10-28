# 03. 음성 — ElevenLabs 연결

키트는 ElevenLabs를 두 가지로 쓴다.

| 방법 | 무엇에 | 인증 |
|---|---|---|
| **공식 API** (`tools/voice.py`, `tools/qa.py` 받아쓰기) | 영상 음성 합성. **글자마다 시작·끝 시각**을 함께 받아 화면 신호를 만든다(싱크의 출발점) | API 키(환경변수 `ELEVENLABS_API_KEY`) |
| **공식 원격 MCP** (`.mcp.json`) | Claude와 대화하며 목소리 고르기·짧은 시험 음성·계정 확인 | 로그인(OAuth), 키를 설정 파일에 넣지 않음 |

MCP로 만든 음성은 짧은 다운로드 링크로 오고 단어 시각이 없어서, 영상 제작 음성은 API(`voice.py`)로 만든다.

## 1. API 키

1. [elevenlabs.io](https://elevenlabs.io) 로그인 → 왼쪽 아래 프로필 → **API Keys** → Create. 권한은 Text to Speech, Speech to Text, Voices(읽기)면 된다.
2. 환경변수로 넣는다(파일에 적지 않는다).
   - Windows(PowerShell, 한 번만): `setx ELEVENLABS_API_KEY "sk_..."` → 터미널·Claude Code를 새로 연다
   - macOS: `~/.zshrc`에 `export ELEVENLABS_API_KEY="sk_..."` → 새 터미널
3. 확인: `python -c "import os; print(bool(os.environ.get('ELEVENLABS_API_KEY')))"` → `True`

## 2. 목소리 고르기

`script.json`의 `settings.voice.voice_id`에 넣는다.
- 기본 목소리: ElevenLabs **Voices** 화면에서 목소리 → 메뉴 → Copy voice ID. 한국어는 모델 `eleven_multilingual_v2`.
- **내 목소리(추천)**: 채널을 계속할 거라면 처음부터 내 목소리로 가는 게 낫다. 전문 복제(PVC)는 감정·억양까지 살리고, 한 번 만들어 두면 그다음부터는 녹음 없이 대본만 쓰면 된다. 녹음·본인 확인·키트 연결까지 전 과정은 **[docs/06-내-목소리-전문-복제.md](06-내-목소리-전문-복제.md)**에 있다. 가입은 [첫 달 50% 할인 링크](https://try.elevenlabs.io/surgaf77dx55)에서.
- 목소리 ID 찾기: `python tools/voice.py --voices` — 내 목소리(복제)와 기본 제공 목소리(premade)가 함께 나온다. 목록 조회는 크레딧이 들지 않는다. `voice_id`가 비어 있으면 `voice.py`는 합성하지 않고 멈춘다(`--demo` 제외).

```json
"voice": {"voice_id": "여기에", "model_id": "eleven_multilingual_v2",
          "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0, "use_speaker_boost": true, "speed": 1}}
```

## 3. 합성

```bash
python tools/voice.py videos/<slug>          # 전체
python tools/voice.py videos/<slug> v2       # 클립 하나
```
- 대사·목소리·설정이 같으면 캐시를 쓴다(`cache/voices/`) — 고친 장면만 크레딧이 든다.
- 장면에 `"tone": "hype"`(오프닝 첫 대사처럼 빠르고 감정 큰 톤)이나 `"urgent"`를 적으면 `settings.tones` 값으로 덮어쓴다.
- 발음이 틀리면 대본은 그대로 두고 `settings.pron`에 소리 나는 대로 등록한다: `{"2월 2일부터": "이월 이일부터"}`. 화면·단어 시각은 원문 글자로 남는다.
- 대본 표기 규칙(숫자 한글, 영어 대문자, 자모 금지)은 `memory/rules`와 `qa.py` 재발 검사가 지킨다.

## 4. 공식 원격 MCP

ElevenLabs의 예전 로컬 MCP 서버(`elevenlabs-mcp`, uvx)는 더 이상 관리되지 않는 저장소가 됐고, 공식 안내는 원격(호스팅) 서버 `https://api.elevenlabs.io/v1/mcp`다. 로그인 방식이라 키를 설정 파일에 넣지 않는다.

**Claude Code** — 키트에 `.mcp.json`이 들어 있다:
```json
{"mcpServers": {"elevenlabs": {"type": "http", "url": "https://api.elevenlabs.io/v1/mcp"}}}
```
키트 폴더에서 Claude Code를 열고 `/mcp` → elevenlabs → Authenticate → 브라우저에서 ElevenLabs 로그인·승인. 직접 추가하려면:
```bash
claude mcp add --transport http elevenlabs https://api.elevenlabs.io/v1/mcp
```

**Claude 데스크톱 앱·claude.ai** — 설정 → 커넥터 → ElevenLabs 검색 → 연결 → 로그인.

**데이터 거주 지역 계정(EU 등)** — 별도 주소를 쓴다(예: EU `https://api.eu.residency.elevenlabs.io/v1/mcp`). 공식 문서: [Hosted MCP](https://elevenlabs.io/docs/eleven-agents/operate/hosted-mcp).

주의: MCP 도구에는 에이전트 삭제처럼 되돌릴 수 없는 작업도 있다. Claude가 그런 도구를 부르면 승인 전에 내용을 확인한다.

## 5. 받아쓰기(발음 검수)

`qa.py`가 장면 음성을 ElevenLabs Speech to Text(`scribe_v1`)로 받아써 대본과 대조한다. 결과는 `qa/transcripts.json`에 캐시. 키 없이 하려면 `pip install faster-whisper`(CPU, 처음 한 번 모델을 받는다).
