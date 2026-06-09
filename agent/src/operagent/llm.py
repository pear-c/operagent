"""Anthropic 호출로 4블록 진단 리포트를 만든다. read-only — 액션을 제안하지 않는다."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from operagent.config import settings

SYSTEM_PROMPT = """당신은 운영 장애 진단 보조다. 이미 발생한 alert과 수집된 메트릭·로그를 받아,
담당자가 빠르게 판단하도록 진단 리포트를 만든다.

반드시 지키는 원칙:
- 탐지하지 않는다. 입력으로 받은 alert은 이미 발생한 사실이다.
- 원인은 단정하지 말고 가설로 제시한다.
- 자동 복구·실행 액션을 제안하지 않는다(읽기 전용 진단 단계). "다음 확인할 것"은
  사람이 직접 볼 항목이지 자동 조치 명령이 아니다.
- 근거는 제공된 메트릭·로그에서만 인용한다. 없는 사실을 지어내지 않는다.

출력은 한국어, 정확히 아래 4블록. 굵게는 Slack mrkdwn 한 별표(*굵게*)를 쓴다:
*상황* — 어떤 alert이 언제, 어떤 서비스에서
*원인 가설* — A: ... / B: ... (가설로)
*근거* — 각 가설을 뒷받침하는 메트릭·로그 인용
*다음 확인할 것* — 사람이 이어서 볼 항목 (액션 아님)
"""


async def synthesize(context: str) -> str:
    """수집된 컨텍스트를 받아 4블록 리포트 텍스트를 반환한다.

    high max_tokens + adaptive thinking이므로 스트리밍으로 타임아웃을 피한다.
    """
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    async with client.messages.stream(
        model=settings.operagent_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    ) as stream:
        message = await stream.get_final_message()
    return "".join(block.text for block in message.content if block.type == "text").strip()
