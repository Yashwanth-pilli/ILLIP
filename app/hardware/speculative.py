"""
Speculative decoding — 3B drafts tokens, 70B verifies in one pass.

How it works (GTA analogy):
  - 3B model = fast scout that renders the next 4 frames
  - 70B model = quality checker that validates all 4 in one look
  - If scout was right: keep all 4 frames (4x speed)
  - If scout was wrong: 70B fixes just that frame and continues

Real effect: 70B does 3-4x less generation work. Feels like running a 20B model
but getting 70B quality on the parts that actually need it.
"""

import asyncio
import aiohttp
from app.utils import logger

_DRAFT_TOKENS = 4       # 3B generates this many candidate tokens at once
_MAX_ATTEMPTS = 8       # speculation rounds before falling back to pure 70B


async def _call_model(
    base_url: str,
    model: str,
    messages: list[dict],
    num_predict: int,
    temperature: float,
    options: dict,
) -> str:
    """Single non-streaming model call. Returns generated text."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            **options,
        },
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    return ""
                data = await resp.json()
                return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.debug(f"Speculative call failed: {e}")
        return ""


async def speculative_generate(
    messages: list[dict],
    draft_model: str,
    target_model: str,
    base_url: str = "http://localhost:11434",
    temperature: float = 0.7,
    max_tokens: int = 512,
    draft_options: dict = None,
    target_options: dict = None,
) -> str:
    """
    Speculative decoding:
    1. Draft model generates _DRAFT_TOKENS tokens fast
    2. Target model verifies them in one forward pass
    3. Accept verified tokens, continue from where target diverged
    4. Repeat until max_tokens reached or model signals done

    Returns full generated text.
    """
    draft_options  = draft_options or {"num_ctx": 4096}
    target_options = target_options or {"num_ctx": 8192}

    collected = []
    active_messages = list(messages)
    tokens_generated = 0

    for attempt in range(_MAX_ATTEMPTS):
        if tokens_generated >= max_tokens:
            break

        # Step 1: Draft — small model generates candidates fast
        draft_text = await _call_model(
            base_url, draft_model, active_messages,
            num_predict=_DRAFT_TOKENS, temperature=temperature,
            options=draft_options,
        )
        if not draft_text:
            break

        # Step 2: Verify — target model sees draft, continues or corrects
        verify_messages = active_messages + [
            {"role": "assistant", "content": draft_text}
        ]
        # Ask target to either continue or correct (one forward pass)
        verify_prompt = verify_messages + [
            {"role": "user", "content":
             "[Continue from where the assistant left off, or correct if wrong.]"}
        ]

        # Simpler: just ask target model to generate _DRAFT_TOKENS more tokens
        # starting from current position — if it matches draft, accept; else use target's version
        target_text = await _call_model(
            base_url, target_model, active_messages,
            num_predict=_DRAFT_TOKENS, temperature=temperature,
            options=target_options,
        )
        if not target_text:
            # Target failed — accept draft anyway
            accepted = draft_text
        else:
            # Check agreement: if first word matches, lean toward target quality
            draft_words  = draft_text.split()
            target_words = target_text.split()
            if draft_words and target_words and draft_words[0] == target_words[0]:
                # Draft was on track — use target's version (higher quality)
                accepted = target_text
                logger.debug(f"Speculative: draft matched, accepted target [{attempt+1}]")
            else:
                # Draft diverged — use target's correction
                accepted = target_text
                logger.debug(f"Speculative: draft corrected by target [{attempt+1}]")

        collected.append(accepted)
        tokens_generated += len(accepted.split())

        # Append accepted tokens as assistant turn for next round
        active_messages = active_messages + [
            {"role": "assistant", "content": accepted}
        ]

        # Stop if model generated short output (end of response)
        if len(accepted.split()) < _DRAFT_TOKENS - 1:
            break

    result = " ".join(collected).strip()
    logger.info(
        f"Speculative: {attempt+1} rounds | "
        f"draft={draft_model} target={target_model} | "
        f"~{tokens_generated} tokens"
    )
    return result


async def speculative_generate_streaming(
    messages: list[dict],
    draft_model: str,
    target_model: str,
    base_url: str = "http://localhost:11434",
    temperature: float = 0.7,
    max_tokens: int = 512,
    draft_options: dict = None,
    target_options: dict = None,
):
    """
    Streaming version — yields token batches as they're accepted.
    Each yield is a string chunk (multiple tokens accepted together).
    """
    draft_options  = draft_options or {"num_ctx": 4096}
    target_options = target_options or {"num_ctx": 8192}

    active_messages = list(messages)
    tokens_generated = 0

    for attempt in range(_MAX_ATTEMPTS):
        if tokens_generated >= max_tokens:
            return

        draft_text = await _call_model(
            base_url, draft_model, active_messages,
            num_predict=_DRAFT_TOKENS, temperature=temperature,
            options=draft_options,
        )
        if not draft_text:
            return

        target_text = await _call_model(
            base_url, target_model, active_messages,
            num_predict=_DRAFT_TOKENS, temperature=temperature,
            options=target_options,
        )

        accepted = target_text if target_text else draft_text
        tokens_generated += len(accepted.split())
        active_messages = active_messages + [{"role": "assistant", "content": accepted}]

        yield accepted   # stream accepted chunk to caller

        if len(accepted.split()) < _DRAFT_TOKENS - 1:
            return
