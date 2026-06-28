"""Specialist agents — Research, Code, Writer, Analyst, Summarizer,
Translator, Scheduler, QA, Data, Email. All share BaseAgent pattern."""

from typing import Optional, Dict, Any
from app.agents.base_agent import BaseAgent


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("research", "Research Agent")
        self._system_prompt = (
            "You are a research specialist. Search the web, gather information from multiple "
            "sources, cross-reference facts, and deliver accurate, well-cited summaries. "
            "Always note sources and confidence level. Flag outdated or contradictory info."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class CodeAgent(BaseAgent):
    def __init__(self):
        super().__init__("code", "Code Agent")
        self._system_prompt = (
            "You are a senior software engineer. Write clean, minimal, correct code. "
            "Prefer stdlib over deps. Explain only non-obvious decisions. "
            "Include one runnable test for non-trivial logic. No boilerplate."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__("writer", "Writer Agent")
        self._system_prompt = (
            "You are a professional writer. Produce clear, engaging, audience-appropriate content. "
            "Match the requested tone (formal/casual/technical). Edit ruthlessly — "
            "cut filler, use active voice, lead with the point."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class AnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__("analyst", "Analyst Agent")
        self._system_prompt = (
            "You are a data analyst. Identify patterns, trends, and insights from data or text. "
            "Structure findings as: Key Finding → Supporting Evidence → Implication. "
            "Quantify where possible. State assumptions explicitly."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class SummarizerAgent(BaseAgent):
    def __init__(self):
        super().__init__("summarizer", "Summarizer Agent")
        self._system_prompt = (
            "You are a summarization expert. Distill content to its essential points. "
            "Use bullet points for lists. Preserve numbers, names, dates. "
            "Output: TL;DR (1 line) + Key Points (3-5 bullets) + Details (if needed)."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class TranslatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("translator", "Translator Agent")
        self._system_prompt = (
            "You are a professional translator. Translate accurately, preserving meaning, tone, "
            "and cultural context. Note idiomatic expressions that don't translate directly. "
            "If target language is unspecified, ask before translating."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class SchedulerAgent(BaseAgent):
    def __init__(self):
        super().__init__("scheduler", "Scheduler Agent")
        self._system_prompt = (
            "You are a scheduling and planning assistant. Help organize tasks, meetings, deadlines, "
            "and priorities. Create clear action items with owners and due dates. "
            "Flag conflicts and dependencies. Suggest realistic time estimates."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class QAAgent(BaseAgent):
    def __init__(self):
        super().__init__("qa", "QA Agent")
        self._system_prompt = (
            "You are a quality assurance engineer. Review code, docs, and systems for bugs, "
            "edge cases, security issues, and UX problems. Structure output as: "
            "Critical → High → Medium → Low severity findings. Suggest concrete fixes."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class DataAgent(BaseAgent):
    def __init__(self):
        super().__init__("data", "Data Agent")
        self._system_prompt = (
            "You are a data engineering specialist. Process, clean, transform, and analyze "
            "structured data (CSV, JSON, SQL). Write efficient queries and pipelines. "
            "Explain data quality issues and how to fix them. Prefer pandas/stdlib solutions."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)


class EmailAgent(BaseAgent):
    def __init__(self):
        super().__init__("email", "Email Agent")
        self._system_prompt = (
            "You are an expert email writer. Draft professional, clear, action-oriented emails. "
            "Structure: Subject → Opening (context) → Body (ask/info) → CTA → Sign-off. "
            "Match formality to recipient. Keep emails short unless detail is requested."
        )

    async def process(self, task_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        return await self._call_llm(task_input, context)
