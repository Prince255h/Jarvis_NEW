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

            elif self.task == "http_audit":
                from tools.cybersec import fetch_and_analyze_url_headers

                report = fetch_and_analyze_url_headers(self.message)
                self.task_completed.emit("HTTP HEADER AUDIT", report)

            elif self.task == "run_command":
                from tools.computer import run_approved_command

                res = run_approved_command(self.message)
                parts = [f"$ {self.message}\n[Exit Code: {res['returncode']}]"]
                if res["stdout"]:
                    parts.append(res["stdout"])
                if res["stderr"]:
                    parts.append(f"[STDERR]\n{res['stderr']}")
                self.task_completed.emit("TERMINAL", "\n".join(parts))

            elif self.task == "agent_mode":
                from core.agent import run_agent_goal

                answer = run_agent_goal(self.message, on_step=self.chunk_received.emit)
                self.stream_finished.emit("AGENT MODE", answer)
                self.response_received.emit(answer)

            elif self.task == "rag_index":
                from tools.rag import index_folder

                stats = index_folder(self.message)
                summary = (
                    f"Indexed folder: {stats['folder']}\n"
                    f"Files indexed: {stats['files_indexed']} | Chunks created: {stats['chunks_added']} | Skipped: {stats['skipped']}"
                )
                self.task_completed.emit("KNOWLEDGE BASE", summary)

            elif self.task == "rag_ask":
                from tools.rag import format_rag_context

                ctx = format_rag_context(self.message, top_k=5)
                if not ctx:
                    self.task_completed.emit("KNOWLEDGE BASE", "No indexed documents matched your query. Index a folder first in 05 // AUTOMATION -> Knowledge Base.")
                elif self.extra.get("stream_to_chat", False):
                    provider_name, full_response = stream_jarvis(
                        f"Answer the user's question using ONLY the local knowledge base excerpts below, citing source file names:\n\nQuestion: {self.message}",
                        self.chunk_received.emit,
                        self.stream_reset.emit,
                        document_context=ctx,
                        include_history=False,
                        save_to_memory=True,
                    )
                    self.stream_finished.emit(f"{provider_name} [RAG]", full_response)
                else:
                    ans = ask_jarvis(
                        f"Answer using the local knowledge base excerpts below and cite source filenames:\n\nQuestion: {self.message}",
                        document_context=ctx,
                        include_history=False,
                        save_to_memory=False,
                    )
                    self.task_completed.emit("KNOWLEDGE BASE ANSWER", ans)

            elif self.task == "python_run":
                from tools.cybersec import run_python_snippet

                res = run_python_snippet(self.message, timeout=10)
                lines = [f"[Python Runner — Exit Code: {res['returncode']}]"]
                if res["stdout"]:
                    lines.append("\n--- STDOUT ---\n" + res["stdout"])
                if res["stderr"]:
                    lines.append("\n--- STDERR ---\n" + res["stderr"])
                if not res["stdout"] and not res["stderr"]:
                    lines.append("(No output)")
                self.task_completed.emit("PYTHON RUN", "\n".join(lines))

            elif self.task == "dns_ssl_audit":
                from tools.cybersec import full_domain_security_report

                rep = full_domain_security_report(self.message)
                self.task_completed.emit("DNS & SSL REPORT", rep)

            elif self.task == "weather_fetch":
                from tools.weather import fetch_weather

                w = fetch_weather(self.message or "")
                self.task_completed.emit("WEATHER", w["summary"])

            elif self.task == "run_scheduled_task":
                from core.scheduler import execute_scheduled_task

                task_dict = self.extra.get("task_dict")
                if not task_dict:
                    raise ValueError("Missing scheduled task payload.")
                res = execute_scheduled_task(task_dict)
                self.extra["result"] = res
                header = f"SCHEDULED TASK: {res['name']} [{res['status']}]"
                self.task_completed.emit(header, res["output"])

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
