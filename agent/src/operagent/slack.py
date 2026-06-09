"""Slack chat.postMessage로 진단 리포트를 게시한다."""

from __future__ import annotations

import httpx

from operagent.config import settings

_SECTION_LIMIT = 2900  # Slack section text 3000자 제한 안전 마진


def _chunks(text: str, size: int = _SECTION_LIMIT) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


async def post_report(header: str, body_markdown: str) -> None:
    """헤더 + 본문(mrkdwn)을 채널에 게시. 실패 시 예외(graceful 처리는 호출부)."""
    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": header[:150]}},
    ]
    for chunk in _chunks(body_markdown):
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})

    payload = {"channel": settings.slack_channel_id, "text": header, "blocks": blocks}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        # not_in_channel / invalid_auth 등 — 호출부가 로그 후 stdout로 폴백
        raise RuntimeError(f"slack chat.postMessage 실패: {data.get('error')}")
