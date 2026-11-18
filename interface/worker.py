"""Background QThread worker for JARVIS streaming chat, health checks, summaries, web/YouTube, and assistant tasks."""

from PySide6.QtCore import QThread, Signal

from core.brain import (
    stream_jarvis,
    ask_jarvis,
    check_provider_health,
    summarize_conversation,
)


class JarvisWorker(QThread):

    # Compatibility + streaming signals
    response_received = Signal(str)
    chunk_received = Signal(str)
    stream_reset = Signal()
    stream_finished = Signal(str, str)

    # Error & health-check signals
    error_occurred = Signal(str)
    health_check_completed = Signal(str, bool, str)

    # Generic async result signal (title, body)
    task_completed = Signal(str, str)

    def __init__(
        self,
        message=None,
        task="chat",
        provider=None,
        image_path=None,
        document_context=None,
        web_context=None,
        personality_override=None,
        style_override=None,
        include_history=True,
        save_to_memory=True,
        extra=None,
    ):
        super().__init__()
        self.message = message
        self.task = task
        self.provider = provider
        self.image_path = image_path
        self.document_context = document_context
        self.web_context = web_context
        self.personality_override = personality_override
        self.style_override = style_override
        self.include_history = include_history
        self.save_to_memory = save_to_memory
        self.extra = extra or {}

    def run(self):
        try:
            if self.task == "chat":
                provider_name, full_response = stream_jarvis(
                    self.message,
                    self.chunk_received.emit,
                    self.stream_reset.emit,
                    image_path=self.image_path,
                    document_context=self.document_context,
                    web_context=self.web_context,
                    personality_override=self.personality_override,
                    style_override=self.style_override,
                    include_history=self.include_history,
                    save_to_memory=self.save_to_memory,
                )
                self.stream_finished.emit(provider_name, full_response)
                self.response_received.emit(full_response)

            elif self.task == "health_check":
                provider_name, is_healthy, details = check_provider_health(self.provider)
                self.health_check_completed.emit(provider_name, is_healthy, details)

            elif self.task == "summarize":
                session_id = self.extra.get("session_id")
                summary = summarize_conversation(session_id=session_id)
                self.task_completed.emit("CONVERSATION SUMMARY", summary)

            elif self.task == "web_search":
                from tools.web_search import web_search, format_search_results

                results = web_search(self.message)
                formatted = format_search_results(self.message, results)
                if self.extra.get("synthesize", True) and results:
                    provider_name, full_response = stream_jarvis(
                        f"Answer this user query using the web search results below and cite URLs: {self.message}",
                        self.chunk_received.emit,
                        self.stream_reset.emit,
                        web_context=formatted,
                        include_history=True,
                        save_to_memory=True,
                    )
                    self.stream_finished.emit(provider_name, full_response)
                    self.response_received.emit(full_response)
                else:
                    self.task_completed.emit("WEB SEARCH", formatted)

            elif self.task == "youtube_summary":
                from tools.web_search import fetch_youtube_video_info, build_youtube_context

                info = fetch_youtube_video_info(self.message)
                yt_context = build_youtube_context(info)
                prompt = (
                    "Provide a clear, structured summary of this YouTube video including:\n"
                    "1. Overview\n2. Key Takeaways & Insights\n3. Notable Topics Covered"
                )
                if self.extra.get("stream_to_chat", False):
                    provider_name, full_response = stream_jarvis(
                        prompt,
                        self.chunk_received.emit,
                        self.stream_reset.emit,
                        document_context=yt_context,
                        include_history=False,
                        save_to_memory=True,
                    )
                    self.stream_finished.emit(provider_name, full_response)
                    self.response_received.emit(full_response)
                else:
                    answer = ask_jarvis(
                        prompt,
                        document_context=yt_context,
                        include_history=False,
                        save_to_memory=False,
                    )
                    self.task_completed.emit(f"YOUTUBE SUMMARY: {info['title']}", answer)

            elif self.task == "assistant_prompt":
                # Used by Coding Assistant, Cybersecurity Assistant, Productivity AI Summary
                answer = ask_jarvis(
                    self.message,
                    document_context=self.document_context,
                    web_context=self.web_context,
                    personality_override=self.personality_override,
                    style_override=self.style_override,
                    include_history=False,
                    save_to_memory=False,
                )
                prefix = self.extra.get("prefix", "")
                final_text = f"{prefix}\n\n{answer}".strip() if prefix else answer
                self.task_completed.emit(self.extra.get("title", "AI RESULT"), final_text)

            else:
                self.error_occurred.emit(f"Unknown worker task: {self.task}")

        except Exception as error:
            if self.task == "health_check":
                self.health_check_completed.emit(
                    self.provider or "Unknown",
                    False,
                    str(error),
                )
            else:
                self.error_occurred.emit(str(error))
