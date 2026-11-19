"""Autonomous Multi-Step Tool-Chaining Agent Engine for J.A.R.V.I.S (Category 2)."""

import json
import re
from datetime import date

from core.brain import ask_jarvis
from core.memory import add_long_term_memory, save_message
from core.productivity import add_task, save_note, add_reminder, build_daily_summary_text
from core.scheduler import save_scheduled_task
from tools.web_search import web_search, format_search_results
from tools.rag import format_rag_context
from tools.cybersec import get_local_network_info, full_domain_security_report
from tools.computer import open_website, open_application, volume_up, volume_down, volume_mute_toggle, set_volume_percent
from tools.weather import fetch_weather
from tools.whatsapp import send_whatsapp_message, call_whatsapp_contact, open_whatsapp_web


AGENT_TOOL_DOCS = """
Available tools (return ONLY a JSON object when calling a tool, or a final answer):
1. web_search: {"tool": "web_search", "args": {"query": "search query"}}
2. rag_search: {"tool": "rag_search", "args": {"query": "question to look up in user's indexed local files"}}
3. add_task: {"tool": "add_task", "args": {"title": "task title", "priority": "High|Medium|Low", "category": "General|Work|Study|Coding|Personal", "due_date": "YYYY-MM-DD"}}
4. save_note: {"tool": "save_note", "args": {"title": "note title", "content": "note body", "tags": "comma,tags"}}
5. add_reminder: {"tool": "add_reminder", "args": {"title": "reminder text", "remind_at": "YYYY-MM-DD HH:MM"}}
6. remember_fact: {"tool": "remember_fact", "args": {"fact": "fact about user", "category": "profile|preference|project|general"}}
7. daily_summary: {"tool": "daily_summary", "args": {}}
8. local_net_info: {"tool": "local_net_info", "args": {}}
9. dns_ssl_check: {"tool": "dns_ssl_check", "args": {"domain": "example.com"}}
10. weather: {"tool": "weather", "args": {"city": "optional city name"}}
11. open_website: {"tool": "open_website", "args": {"url": "https://..."}}
12. open_app: {"tool": "open_app", "args": {"app_name": "notepad|calc|chrome|vscode|..."}}
13. whatsapp_send: {"tool": "whatsapp_send", "args": {"contact": "contact name or phone number", "message": "message body"}}
14. whatsapp_call: {"tool": "whatsapp_call", "args": {"contact": "contact name or phone number", "call_type": "voice|video"}}
15. whatsapp_open: {"tool": "whatsapp_open", "args": {}}
16. system_volume: {"tool": "system_volume", "args": {"level": "up|down|mute|0-100"}}
17. schedule_task: {"tool": "schedule_task", "args": {"name": "short name", "action_type": "ai_prompt|agent_goal|open_app|open_website|web_search|whatsapp_msg|daily_summary|notify", "payload": "task payload", "next_run_at": "YYYY-MM-DD HH:MM", "schedule_type": "once|daily|weekly|interval", "interval_minutes": 60}}
18. final: {"tool": "final", "args": {"answer": "Your complete final response to the user summarizing all actions taken and results."}}
"""


def _execute_tool(tool_name: str, args: dict) -> str:
    args = args or {}
    t = (tool_name or "").strip().lower()

    if t == "web_search":
        q = str(args.get("query", "")).strip()
        results = web_search(q, max_results=5)
        return format_search_results(q, results)

    if t == "rag_search":
        q = str(args.get("query", "")).strip()
        ctx = format_rag_context(q, top_k=5)
        return ctx or "No matching chunks found in local indexed knowledge base."

    if t == "add_task":
        tid = add_task(
            title=str(args.get("title", "")).strip(),
            priority=str(args.get("priority", "Medium")),
            category=str(args.get("category", "General")),
            due_date=str(args.get("due_date", "") or date.today().isoformat()),
        )
        return f"Task #{tid} added: {args.get('title')}"

    if t == "save_note":
        nid = save_note(
            title=str(args.get("title", "Agent Note")),
            content=str(args.get("content", "")),
            tags=str(args.get("tags", "agent")),
        )
        return f"Note #{nid} saved: {args.get('title')}"

    if t == "add_reminder":
        rid = add_reminder(
            title=str(args.get("title", "")),
            remind_at=str(args.get("remind_at", "")),
        )
        return f"Reminder #{rid} armed for {args.get('remind_at')}: {args.get('title')}"

    if t == "remember_fact":
        mid = add_long_term_memory(
            fact=str(args.get("fact", "")),
            category=str(args.get("category", "general")),
        )
        return f"Saved long-term memory #{mid}: {args.get('fact')}"

    if t == "daily_summary":
        return build_daily_summary_text()

    if t == "local_net_info":
        return get_local_network_info()

    if t == "dns_ssl_check":
        return full_domain_security_report(str(args.get("domain", "")))

    if t == "weather":
        return fetch_weather(str(args.get("city", "")))["summary"]

    if t == "open_website":
        return open_website(str(args.get("url", "")))

    if t == "open_app":
        return open_application(str(args.get("app_name", "")))

    if t == "whatsapp_send":
        return send_whatsapp_message(
            contact=str(args.get("contact", "")),
            message=str(args.get("message", "")),
            auto_send=True,
        )

    if t == "whatsapp_call":
        return call_whatsapp_contact(
            contact=str(args.get("contact", "")),
            call_type=str(args.get("call_type", "voice")),
        )

    if t == "whatsapp_open":
        return open_whatsapp_web()

    if t == "system_volume":
        lvl = str(args.get("level", "up")).strip().lower()
        if lvl == "up":
            return volume_up()
        elif lvl == "down":
            return volume_down()
        elif lvl == "mute":
            return volume_mute_toggle()
        elif lvl.isdigit():
            return set_volume_percent(int(lvl))
        return f"Unknown volume level: {lvl}"

    if t == "schedule_task":
        atype = str(args.get("action_type", "ai_prompt")).strip().lower()
        if atype == "terminal_command":
            raise PermissionError("Terminal commands require manual user approval in the Scheduled Tasks UI.")
        tid = save_scheduled_task(
            name=str(args.get("name", "Scheduled Job")),
            action_type=atype,
            payload=str(args.get("payload", "")),
            next_run_at=str(args.get("next_run_at", "")),
            schedule_type=str(args.get("schedule_type", "once")),
            interval_minutes=int(args.get("interval_minutes", 60) or 60),
        )
        return f"Scheduled task #{tid} ('{args.get('name')}') for {args.get('next_run_at')} ({args.get('schedule_type', 'once')})."

    raise ValueError(f"Unknown agent tool: {tool_name}")


def _extract_json_action(raw_text: str):
    """Extract first valid JSON tool call object from LLM output."""
    text = re.sub(r"^\[[^\]]+\]\s*", "", (raw_text or "").strip())
    # Try fenced json block first
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    candidates = [m.group(1)] if m else []
    # Also try raw brace span
    first_b = text.find("{")
    last_b = text.rfind("}")
    if first_b != -1 and last_b > first_b:
        candidates.append(text[first_b : last_b + 1])

    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and "tool" in obj:
                return obj
        except Exception:
            continue
    return None


def run_agent_goal(goal: str, on_step=None, max_steps: int = 5) -> str:
    """Autonomously plan and execute up to max_steps tool calls to achieve the user's goal."""
    goal = (goal or "").strip()
    if not goal:
        return "Please provide a goal for Agent Mode."

    today_str = date.today().isoformat()
    scratchpad = []
    step_logs = []

    for step_idx in range(1, max_steps + 1):
        history_block = "\n\n".join(scratchpad) if scratchpad else "(No tool calls made yet.)"
        prompt = (
            f"You are J.A.R.V.I.S Autonomous Agent Mode. Today's date is {today_str}.\n"
            f"USER GOAL: {goal}\n\n"
            f"{AGENT_TOOL_DOCS}\n\n"
            f"PREVIOUS STEPS & OBSERVATIONS:\n{history_block}\n\n"
            "INSTRUCTIONS:\n"
            "- Decide the next SINGLE tool call needed, OR call tool='final' once the goal is fully achieved.\n"
            "- Respond ONLY with a valid JSON object matching one of the schemas above."
        )

        raw = ask_jarvis(
            prompt,
            personality_override="ULTRON",
            style_override="Concise",
            include_history=False,
            save_to_memory=False,
        )

        action = _extract_json_action(raw)
        if not action:
            # Model replied directly with prose — treat as final answer
            clean = re.sub(r"^\[[^\]]+\]\s*", "", raw).strip()
            save_message("user", f"[AGENT] {goal}")
            save_message("assistant", clean)
            return clean

        tool_name = str(action.get("tool", "")).strip().lower()
        tool_args = action.get("args") if isinstance(action.get("args"), dict) else {}

        if tool_name == "final":
            answer = str(tool_args.get("answer", "")).strip() or "Goal completed."
            prefix = ""
            if step_logs:
                prefix = "### Agent Execution Trace\n" + "\n".join(f"- {s}" for s in step_logs) + "\n\n"
            final_output = prefix + answer
            save_message("user", f"[AGENT] {goal}")
            save_message("assistant", final_output)
            return final_output

        step_desc = f"Step {step_idx}: `{tool_name}`({json.dumps(tool_args, ensure_ascii=False)[:120]})"
        if on_step:
            on_step(f"▸ {step_desc}\n")

        try:
            observation = _execute_tool(tool_name, tool_args)
            step_logs.append(f"**{tool_name}** ✓")
        except Exception as err:
            observation = f"[TOOL ERROR] {type(err).__name__}: {err}"
            step_logs.append(f"**{tool_name}** ✗ ({err})")

        scratchpad.append(f"STEP {step_idx} CALL: {tool_name} {json.dumps(tool_args)}\nOBSERVATION:\n{observation[:3500]}")

    # If max_steps reached, ask for concise final summary
    summary = ask_jarvis(
        f"Summarize the completed agent actions and final answer for goal: {goal}\n\n" + "\n\n".join(scratchpad),
        include_history=False,
        save_to_memory=False,
    )
    clean_sum = re.sub(r"^\[[^\]]+\]\s*", "", summary).strip()
    prefix = "### Agent Execution Trace\n" + "\n".join(f"- {s}" for s in step_logs) + "\n\n"
    final_output = prefix + clean_sum
    save_message("user", f"[AGENT] {goal}")
    save_message("assistant", final_output)
    return final_output

