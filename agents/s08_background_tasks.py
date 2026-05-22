#!/usr/bin/env python3
# Harness: background execution -- the model thinks while the harness waits.
"""
s08_background_tasks.py - Background Tasks

Run commands in background threads. A notification queue is drained
before each LLM call to deliver results.

    Main thread                Background thread
    +-----------------+        +-----------------+
    | agent loop      |        | task executes   |
    | ...             |        | ...             |
    | [LLM call] <---+------- | enqueue(result) |
    |  ^drain queue   |        +-----------------+
    +-----------------+

    Timeline:
    Agent ----[spawn A]----[spawn B]----[other work]----
                 |              |
                 v              v
              [A runs]      [B runs]        (parallel)
                 |              |
                 +-- notification queue --> [results injected]

Key insight: "Fire and forget -- the agent doesn't block while the command runs."
"""

import os
import subprocess
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv

try:
    from .openai_compat import OpenAICompatibleClient
except ImportError:
    from openai_compat import OpenAICompatibleClient

load_dotenv(override=True)

# 模块级常量：Python 没有 Java 的 static final 关键字约束，约定用全大写变量名表示“常量”。
WORKDIR = Path.cwd()
# 模型调用走 OpenAI 兼容接口；后台任务只是在本地线程里执行 shell。
client = OpenAICompatibleClient.from_env()
MODEL = client.model

SYSTEM = f"You are a coding agent at {WORKDIR}. Use background_run for long-running commands."


# BackgroundManager：用线程执行长任务，用队列把完成通知送回下一轮模型调用。
class BackgroundManager:
    def __init__(self):
        # __init__ 类似 Java 构造方法；self 类似 this，但 Python 必须显式写出来。
        # 这里直接给实例挂字段，不需要像 Java 一样先声明成员变量类型。
        self.tasks = {}  # task_id -> {status, result, command}
        self._notification_queue = []  # completed task results
        # 前导下划线表示“内部使用”的约定；不像 Java private 那样由编译器强制。
        self._lock = threading.Lock()

    def run(self, command: str) -> str:
        """Start a background thread, return task_id immediately."""
        # command: str 和 -> str 是类型提示，帮助编辑器/读者理解；运行时默认不强制检查。
        task_id = str(uuid.uuid4())[:8]
        # Python dict 类似 Java 的 Map；None 类似 Java 的 null。
        self.tasks[task_id] = {"status": "running", "result": None, "command": command}
        # threading.Thread 类似 new Thread(...)；target 是要在线程里调用的函数。
        thread = threading.Thread(
            target=self._execute, args=(task_id, command), daemon=True
        )
        # daemon=True 表示主程序结束时不用等待这个后台线程，适合教学版“后台任务”。
        thread.start()
        return f"Background task {task_id} started: {command[:80]}"

    def _execute(self, task_id: str, command: str):
        """Thread target: run subprocess, capture output, push to queue."""
        try:
            # subprocess.run 类似 Java 的 ProcessBuilder：启动外部命令并收集 stdout/stderr。
            print(f"[Background] {task_id}: {command} start")
            r = subprocess.run(
                command, shell=True, cwd=WORKDIR,
                capture_output=True, text=True, timeout=300
            )
            print(f"[Background] {task_id}: {command} end")
            # 字符串切片 [:50000] 表示最多保留前 50000 个字符。
            output = (r.stdout + r.stderr).strip()[:50000]
            status = "completed"
        except subprocess.TimeoutExpired:
            output = "Error: Timeout (300s)"
            status = "timeout"
        except Exception as e:
            # Python 没有 Java 的 checked exception；这里用宽泛异常兜底，避免后台线程静默失败。
            output = f"Error: {e}"
            status = "error"
        self.tasks[task_id]["status"] = status
        self.tasks[task_id]["result"] = output or "(no output)"
        # with 会在代码块结束时自动释放锁，作用类似 Java try-finally 里的 unlock。
        with self._lock:
            self._notification_queue.append({
                "task_id": task_id,
                "status": status,
                "command": command[:80],
                "result": (output or "(no output)")[:500],
            })

    def check(self, task_id: str = None) -> str:
        """Check status of one task or list all."""
        # 参数默认值 None 表示可以不传；这里等价于 Java 里重载一个无参版本的效果。
        if task_id:
            # dict.get 找不到 key 时返回 None，不会像 [] 访问那样抛 KeyError。
            t = self.tasks.get(task_id)
            if not t:
                return f"Error: Unknown task {task_id}"
            return f"[{t['status']}] {t['command'][:60]}\n{t.get('result') or '(running)'}"
        lines = []
        # items() 同时遍历 key/value，类似 Java Map.entrySet()。
        for tid, t in self.tasks.items():
            lines.append(f"{tid}: [{t['status']}] {t['command'][:60]}")
        # Python 的三元表达式写作 A if condition else B。
        return "\n".join(lines) if lines else "No background tasks."

    def drain_notifications(self) -> list:
        """Return and clear all pending completion notifications."""
        # 教学重点：后台线程不会直接“打断”模型；结果只会在下一次循环开始前被取出并注入上下文。
        with self._lock:
            # 先复制一份再 clear，避免调用者拿到的列表随后被清空。
            notifs = list(self._notification_queue)
            self._notification_queue.clear()
        return notifs


# 创建一个全局后台任务管理器；这个脚本很小，所以用单例对象保持示例直观。
BG = BackgroundManager()


# 工具实现：background_run 立即返回 task_id，避免代理循环被长命令卡住。
def safe_path(p: str) -> Path:
    # pathlib.Path 是面向对象的路径 API，接近 Java 的 java.nio.file.Path。
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        # raise 类似 Java 的 throw。
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    # any(...) 会在生成器表达式中遇到第一个 True 就停止，类似 Java stream().anyMatch(...)。
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"

def run_read(path: str, limit: int = None) -> str:
    try:
        # read_text().splitlines() 一次性读入并按行切开；教学版优先简单直观。
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"

def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes"
    except Exception as e:
        return f"Error: {e}"

def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        c = fp.read_text()
        if old_text not in c:
            return f"Error: Text not found in {path}"
        fp.write_text(c.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


TOOL_HANDLERS = {
    # 这个 dict 相当于 Java 的 Map<String, Function>：工具名 -> 处理函数。
    # lambda **kw 接收任意关键字参数；kw["command"] 从参数字典里取字段。
    "bash":             lambda **kw: run_bash(kw["command"]),
    "read_file":        lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file":       lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file":        lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "background_run":   lambda **kw: BG.run(kw["command"]),
    "check_background": lambda **kw: BG.check(kw.get("task_id")),
}

TOOLS = [
    # 这些是发给模型看的“工具说明书”：名字、描述、输入 JSON schema。
    {"name": "bash", "description": "Run a shell command (blocking).",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "background_run", "description": "Run command in background thread. Returns task_id immediately.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "check_background", "description": "Check background task status. Omit task_id to list all.",
     "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}}},
]


def agent_loop(messages: list):
    while True:
        # Drain background notifications and inject as system message before LLM call
        notifs = BG.drain_notifications()
        if notifs and messages:
            # 列表/生成器表达式让 Python 可以很紧凑地把多条通知拼成一段文本。
            notif_text = "\n".join(
                f"[bg:{n['task_id']}] {n['status']}: {n['result']}" for n in notifs
            )
            # append 会原地修改 list；Python 常直接传递可变对象，不需要包装成类字段。
            messages.append({"role": "user", "content": f"<background-results>\n{notif_text}\n</background-results>"})
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    # **block.input 把字典展开成关键字参数，类似按字段名调用函数。
                    output = handler(**block.input) if handler else f"Unknown tool: {block.name}"
                except Exception as e:
                    output = f"Error: {e}"
                print(f"> {block.name}:")
                print(str(output)[:200])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    # Python 的脚本入口：只有直接运行本文件时才执行，类似 Java public static void main。
    history = []
    while True:
        try:
            query = input("\033[36ms08 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
