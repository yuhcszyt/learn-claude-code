#!/usr/bin/env python3
# Harness: team mailboxes -- multiple models, coordinated through files.
"""
s09_agent_teams.py - Agent Teams（智能体团队）

这一课演示“长期存在的命名队友”：每个 teammate 都在独立线程里运行自己的
agent loop，并通过文件形式的 JSONL inbox 互相通信。

    Subagent (s04):  spawn -> execute -> return summary -> destroyed
    Teammate (s09):  spawn -> work -> idle -> work -> ... -> shutdown

    .team/config.json                   .team/inbox/
    +----------------------------+      +------------------+
    | {"team_name": "default",   |      | alice.jsonl      |
    |  "members": [              |      | bob.jsonl        |
    |    {"name":"alice",        |      | lead.jsonl       |
    |     "role":"coder",        |      +------------------+
    |     "status":"idle"}       |
    |  ]}                        |      send_message("alice", "修复 bug"):
    +----------------------------+        open("alice.jsonl", "a").write(msg)

                                        read_inbox("alice"):
    spawn_teammate("alice","coder",...)   msgs = [json.loads(l) for l in ...]
         |                                open("alice.jsonl", "w").close()
         v                                return msgs  # drain
    Thread: alice             Thread: bob
    +------------------+      +------------------+
    | agent_loop       |      | agent_loop       |
    | status: working  |      | status: idle     |
    | ... runs tools   |      | ... waits ...    |
    | status -> idle   |      |                  |
    +------------------+      +------------------+

    5 种消息类型（这里全部声明，但不是每一种都在本课完整处理）：
    +-------------------------+-----------------------------------+
    | message                 | 普通文本消息                      |
    | broadcast               | 发给所有队友的广播                |
    | shutdown_request        | 请求优雅关闭（s10 会继续展开）    |
    | shutdown_response       | 同意/拒绝关闭（s10 会继续展开）   |
    | plan_approval_response  | 同意/拒绝计划（s10 会继续展开）   |
    +-------------------------+-----------------------------------+

关键思想：让多个 agent 不只是一次性调用，而是变成“可以互相说话的队友”。

中文学习提示：
    这一课把“单个 agent loop”扩展成“多个长期存活的队友”。
    如果你来自 Java，可以把每个 teammate 理解成一个 Runnable；
    MessageBus 则像一个非常轻量的文件版消息队列。
"""

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

try:
    from .openai_compat import OpenAICompatibleClient
except ImportError:
    from openai_compat import OpenAICompatibleClient

load_dotenv(override=True)

WORKDIR = Path.cwd()
# Path.cwd() 类似 Java 里的 Paths.get("").toAbsolutePath()。
# 后续所有文件读写都会以这个目录作为工作区边界。

# 每个队友线程都复用这个 OpenAI 兼容客户端配置。这里为了课程简洁，
# 没有做客户端池或依赖注入，重点放在 harness 结构本身。
client = OpenAICompatibleClient.from_env()
MODEL = client.model
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"

SYSTEM = (
    f"你是工作区 {WORKDIR} 中的团队负责人。"
    "你可以创建长期存在的队友，并通过文件 inbox 与他们通信。"
    "优先用中文说明你的计划、工具调用原因和最终结果；除非用户明确要求其他语言。"
)

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}


# MessageBus：每个队友一个 JSONL inbox，类似用文件系统实现极简消息队列。
#
# JSONL = JSON Lines：一行一个 JSON 对象。相比保存一个大 JSON 数组，
# 追加一条消息只需要往文件末尾写一行，适合演示“append-only inbox”。
class MessageBus:
    def __init__(self, inbox_dir: Path):
        self.dir = inbox_dir
        # exist_ok=True 类似 Java Files.createDirectories：目录存在也不报错。
        self.dir.mkdir(parents=True, exist_ok=True)

    def send(self, sender: str, to: str, content: str,
             msg_type: str = "message", extra: dict = None) -> str:
        # Python 的默认参数可以直接写在函数签名里；extra=None 表示可选参数。
        # 注意：不要用 extra={} 作为默认值，因为可变默认值会在多次调用间共享。
        if msg_type not in VALID_MSG_TYPES:
            return f"错误：消息类型 '{msg_type}' 无效。可用类型：{VALID_MSG_TYPES}"
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            # dict.update 类似 Java Map.putAll，把 extra 字段并入消息。
            msg.update(extra)
        inbox_path = self.dir / f"{to}.jsonl"
        # "a" 是 append 模式；每次发送只追加一行，不读取旧内容。
        with open(inbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return f"已发送 {msg_type} 消息给 {to}"

    def read_inbox(self, name: str) -> list:
        inbox_path = self.dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return []
        messages = []
        for line in inbox_path.read_text(encoding="utf-8").strip().splitlines():
            if line:
                messages.append(json.loads(line))
        # 读完后清空 inbox，这叫 drain。语义上像从 BlockingQueue 里 take 掉消息。
        inbox_path.write_text("", encoding="utf-8")
        return messages

    def broadcast(self, sender: str, content: str, teammates: list) -> str:
        count = 0
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, "broadcast")
                count += 1
        return f"已广播给 {count} 个队友"


BUS = MessageBus(INBOX_DIR)


# TeammateManager：管理“持久队友”的生命周期和线程。
#
# 和前几课的 subagent 不同，teammate 不是一次性函数调用：
# 它会被记录到 .team/config.json，然后在自己的线程里运行 agent loop。
class TeammateManager:
    def __init__(self, team_dir: Path):
        # Python 的 self 类似 Java 的 this；实例字段通常在 __init__ 中创建。
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}

    def _load_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        return {"team_name": "default", "members": []}

    def _save_config(self):
        self.config_path.write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _find_member(self, name: str) -> dict:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        # 这里返回 None，但类型标注写的是 dict，是为了保持课程代码短。
        # 生产代码里可以写 dict | None，让类型含义更精确。
        return None

    def spawn(self, name: str, role: str, prompt: str) -> str:
        # spawn 既负责“登记队友”，也负责“启动线程”。
        # 如果队友已存在且空闲，就复用名字；如果正在工作，就拒绝重复启动。
        member = self._find_member(name)
        if member:
            # if member["status"] not in ("idle", "shutdown"):
            #     return f"错误：'{name}' 当前状态是 {member['status']}，不能重复启动"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save_config()
        thread = threading.Thread(
            target=self._teammate_loop,
            args=(name, role, prompt),
            # daemon=True 表示主程序退出时不强制等待这个线程。
            # Java 里也有 daemon thread，适合这种教学用后台 worker。
            daemon=True,
        )
        self.threads[name] = thread
        thread.start()
        return f"已启动队友 '{name}'（角色：{role}）"

    def _teammate_loop(self, name: str, role: str, prompt: str):
        # 每个队友都有自己的 system prompt 和 messages 历史。
        # 这相当于每个线程持有自己的会话状态，不和 lead 的 history 混在一起。
        sys_prompt = (
            f"你是队友 '{name}'，角色是：{role}，工作区是 {WORKDIR}。"
            "你通过 send_message 与 lead 或其他队友沟通。"
            "完成分配给你的任务；需要读写文件或执行命令时使用工具。"
            "最终请用中文简要汇报结果。"
        )
        messages = [{"role": "user", "content": prompt}]
        tools = self._teammate_tools()
        for _ in range(50):
            # for _ in range(50) 是 Python 里常见的“最多循环 N 次”写法。
            # 下划线变量表示这个循环计数值本身不会被使用。
            inbox = BUS.read_inbox(name)
            for msg in inbox:
                # inbox 消息被塞回 messages，让模型在下一轮看到“别人对我说了什么”。
                messages.append({"role": "user", "content": json.dumps(msg, ensure_ascii=False)})
            try:
                response = client.messages.create(
                    model=MODEL,
                    system=sys_prompt,
                    messages=messages,
                    tools=tools,
                    max_tokens=8000,
                )
            except Exception:
                break
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                # 没有工具调用时，说明模型这一轮已经给出最终回复，队友可以回到 idle。
                break
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = self._exec(name, block.name, block.input)
                    print(f"  [{name}] {block.name}: {str(output)[:120]}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    })
            # Anthropic/OpenAI 风格的工具协议通常是：
            # assistant 请求 tool_use，user 再把 tool_result 送回去。
            messages.append({"role": "user", "content": results})
        member = self._find_member(name)
        if member and member["status"] != "shutdown":
            member["status"] = "idle"
            self._save_config()

    def _exec(self, sender: str, tool_name: str, args: dict) -> str:
        # 工具分发：根据模型请求的 tool_name 调用对应 Python 函数。
        # 这里用 if 链保持可读；Java 里可能会用 switch 或 Map<String, Handler>。
        if tool_name == "bash":
            return _run_bash(args["command"])
        if tool_name == "read_file":
            return _run_read(args["path"])
        if tool_name == "write_file":
            return _run_write(args["path"], args["content"])
        if tool_name == "edit_file":
            return _run_edit(args["path"], args["old_text"], args["new_text"])
        if tool_name == "send_message":
            return BUS.send(sender, args["to"], args["content"], args.get("msg_type", "message"))
        if tool_name == "read_inbox":
            return json.dumps(BUS.read_inbox(sender), indent=2, ensure_ascii=False)
        return f"未知工具：{tool_name}"

    def _teammate_tools(self) -> list:
        # 工具 schema 本质上是普通的 list/dict 字面量。
        # Python 字典很适合表达 JSON-like 配置，不需要先定义一堆 POJO。
        return [
            {"name": "bash", "description": "运行一条 shell 命令，用于检查环境、查看文件或执行测试。",
             "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
            {"name": "read_file", "description": "读取工作区内的文件内容。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "write_file", "description": "把内容写入工作区内的文件；如果目录不存在会创建目录。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
            {"name": "edit_file", "description": "在文件中查找一段完全匹配的文本，并只替换第一处。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
            {"name": "send_message", "description": "向某个队友或 lead 的 inbox 发送消息。",
             "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES)}}, "required": ["to", "content"]}},
            {"name": "read_inbox", "description": "读取并清空自己的 inbox。",
             "input_schema": {"type": "object", "properties": {}}},
        ]

    def list_all(self) -> str:
        if not self.config["members"]:
            return "当前没有队友。"
        lines = [f"团队：{self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']}（{m['role']}）：{m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]


TEAM = TeammateManager(TEAM_DIR)


# 基础工具实现：队友和 lead 都通过这些函数访问 shell/文件。
def _safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    # resolve() 会把相对路径、.. 等归一化；is_relative_to 防止工具逃出仓库。
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径逃出了工作区：{p}")
    return path


def _run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot"]
    if any(d in command for d in dangerous):
        return "错误：危险命令已被拦截"
    try:
        # subprocess.run 类似 Java ProcessBuilder.start() + waitFor()。
        # capture_output=True 会收集 stdout/stderr，text=True 返回字符串而不是 bytes。
        r = subprocess.run(
            command, shell=True, cwd=WORKDIR,
            capture_output=True, text=True, timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "（没有输出）"
    except subprocess.TimeoutExpired:
        return "错误：命令超时（120 秒）"


def _run_read(path: str, limit: int = None) -> str:
    try:
        lines = _safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"...（还有 {len(lines) - limit} 行）"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"错误：{e}"


def _run_write(path: str, content: str) -> str:
    try:
        fp = _safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
        return f"已写入 {len(content)} 个字符"
    except Exception as e:
        return f"错误：{e}"


def _run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = _safe_path(path)
        c = fp.read_text(encoding="utf-8")
        if old_text not in c:
            return f"错误：在 {path} 中没有找到指定文本"
        # replace(..., 1) 只替换第一处，避免一次误改多个相同片段。
        fp.write_text(c.replace(old_text, new_text, 1), encoding="utf-8")
        return f"已编辑 {path}"
    except Exception as e:
        return f"错误：{e}"


# Lead 的工具分发表：包含基础工具、队友管理和消息通信。
TOOL_HANDLERS = {
    # lambda **kw 接收“任意关键字参数”，类似把 JSON 参数包解成方法入参。
    # 这让 agent_loop 可以统一写 handler(**block.input)。
    "bash":            lambda **kw: _run_bash(kw["command"]),
    "read_file":       lambda **kw: _run_read(kw["path"], kw.get("limit")),
    "write_file":      lambda **kw: _run_write(kw["path"], kw["content"]),
    "edit_file":       lambda **kw: _run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "spawn_teammate":  lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates":  lambda **kw: TEAM.list_all(),
    "send_message":    lambda **kw: BUS.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox":      lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=2, ensure_ascii=False),
    "broadcast":       lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names()),
}

# 这些基础工具来自 s02；本课额外加入队友管理和 inbox 通信工具。
TOOLS = [
    {"name": "bash", "description": "运行一条 shell 命令，用于检查环境、查看文件或执行测试。",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "读取工作区内的文件内容，可用 limit 限制最多读取的行数。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "把内容写入工作区内的文件；如果目录不存在会创建目录。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "在文件中查找一段完全匹配的文本，并只替换第一处。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "spawn_teammate", "description": "启动一个长期存在的队友；队友会在自己的线程里运行 agent loop。",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "role": {"type": "string"}, "prompt": {"type": "string"}}, "required": ["name", "role", "prompt"]}},
    {"name": "list_teammates", "description": "列出所有队友的名字、角色和当前状态。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "send_message", "description": "向某个队友的 inbox 发送消息。",
     "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES)}}, "required": ["to", "content"]}},
    {"name": "read_inbox", "description": "读取并清空 lead 自己的 inbox。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "broadcast", "description": "向所有队友广播一条消息。",
     "input_schema": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}},
]


def agent_loop(messages: list):
    # lead 的主循环和队友循环形状相同：
    # 读取 inbox -> 调模型 -> 执行工具 -> 把结果喂回模型。
    while True:
        inbox = BUS.read_inbox("lead")
        if inbox:
            messages.append({
                "role": "user",
                "content": f"<inbox>{json.dumps(inbox, indent=2, ensure_ascii=False)}</inbox>",
            })
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                try:
                    # **block.input 是 Python 的关键字参数展开：
                    # {"path": "a.txt"} 会变成 handler(path="a.txt")。
                    output = handler(**block.input) if handler else f"未知工具：{block.name}"
                except Exception as e:
                    output = f"错误：{e}"
                print(f"> {block.name}:")
                print(str(output)[:200])
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output),
                })
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            # input() 是最小 CLI 入口；每一轮用户输入都会追加到同一个 history。
            query = input("\033[36ms09 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/team":
            print(TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            print(json.dumps(BUS.read_inbox("lead"), indent=2, ensure_ascii=False))
            continue
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
