#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Harness: protocols -- structured handshakes between models.
"""
s10_team_protocols.py - 团队协议

本课在 s09 的团队消息基础上，加入两个结构化协议：

1. 关闭协议：pending -> approved | rejected
2. 计划审批协议：pending -> approved | rejected

两个协议共用同一种 request_id 关联模式。它和 Java 后端里常见的
correlation id 很像：请求发出去以后，响应不一定马上回来，所以要用 id
把异步响应找回对应的请求状态。

    关闭协议：

    负责人                              队友
    +---------------------+          +---------------------+
    | shutdown_request     |          |                     |
    | {request_id: abc}    | -------> | 收到关闭请求        |
    +---------------------+          | 决定是否同意        |
                                     +---------------------+
                                             |
    +---------------------+          +-------v-------------+
    | shutdown_response    | <------- | shutdown_response   |
    | {                    |          | {                   |
    |   request_id: abc    |          |   request_id: abc   |
    |   approve: true      |          |   approve: true     |
    | }                    |          | }                   |
    +---------------------+          +---------------------+
            |
            v
    status -> "shutdown"，线程结束

    计划审批协议：

    队友                                负责人
    +---------------------+          +---------------------+
    | plan_approval        |          |                     |
    | submit: {plan:"..."}| -------> | 阅读计划文本        |
    +---------------------+          | 批准或拒绝          |
                                     +---------------------+
                                             |
    +---------------------+          +-------v-------------+
    | plan_approval_resp   | <------- | plan_approval       |
    | {approve: true}      |          | review: {req_id,    |
    +---------------------+          |   approve: true}     |
                                     +---------------------+

核心理解：不是增加很多工具，而是把“消息”升级成“协议”。
"""

import json
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

try:
    from .openai_compat import OpenAICompatibleClient
except ImportError:
    from openai_compat import OpenAICompatibleClient

load_dotenv(override=True)

WORKDIR = Path.cwd()
# 协议状态保存在本地内存和 .team 文件中；模型通过 OpenAI 兼容接口调用工具。
# 为了保持课程代码轻量，这里没有引入数据库或消息中间件。
client = OpenAICompatibleClient.from_env()
MODEL = client.model
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"

SYSTEM = (
    f"你是位于 {WORKDIR} 的团队负责人。"
    "请用中文回答，并通过工具管理队友。"
    "关闭队友时使用 shutdown_request 协议；"
    "查看关闭结果时使用 shutdown_response；"
    "审批队友计划时使用 plan_approval。"
)

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}

# 请求追踪器：用 request_id 把请求和响应关联起来，类似简化版 RPC correlation id。
# shutdown_requests 和 plan_requests 是模块级 dict，类似 Java 里的 static Map。
# 多个线程都可能读写它们，所以配一个 Lock 做最小同步保护。
shutdown_requests = {}
plan_requests = {}
_tracker_lock = threading.Lock()


# MessageBus 仍然使用 JSONL inbox，只是消息类型更结构化。
# s09 里的消息主要是聊天；s10 里的消息还承担“请求 / 响应”的协议语义。
class MessageBus:
    def __init__(self, inbox_dir: Path):
        self.dir = inbox_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def send(self, sender: str, to: str, content: str,
             msg_type: str = "message", extra: dict = None) -> str:
        # msg_type 白名单让协议更可控，避免模型随手发出拼错的类型。
        if msg_type not in VALID_MSG_TYPES:
            return f"错误：无效消息类型 '{msg_type}'。可用类型：{sorted(VALID_MSG_TYPES)}"
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            # extra 用来携带 request_id、approve、feedback 这类协议字段。
            msg.update(extra)
        inbox_path = self.dir / f"{to}.jsonl"
        with open(inbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return f"已发送 {msg_type} 给 {to}"

    def read_inbox(self, name: str) -> list:
        inbox_path = self.dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return []
        messages = []
        for line in inbox_path.read_text(encoding="utf-8").strip().splitlines():
            if line:
                messages.append(json.loads(line))
        inbox_path.write_text("", encoding="utf-8")
        return messages

    def broadcast(self, sender: str, content: str, teammates: list) -> str:
        count = 0
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, "broadcast")
                count += 1
        return f"已广播给 {count} 名队友"


BUS = MessageBus(INBOX_DIR)


# TeammateManager 在 s09 的队友模型上增加 shutdown 和 plan approval 协议。
# 注意：这不是让外部线程直接 kill teammate，而是通过消息请求它“优雅退出”。
# 这种设计更像 Java 服务里的 graceful shutdown。
class TeammateManager:
    def __init__(self, team_dir: Path):
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
        # 教学简化：调用方会把 None 当成“不存在”处理。
        return None

    def spawn(self, name: str, role: str, prompt: str) -> str:
        # 启动逻辑基本沿用 s09；本课的增量主要在消息协议，而不是线程模型。
        member = self._find_member(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"错误：'{name}' 当前状态为 {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save_config()
        thread = threading.Thread(
            target=self._teammate_loop,
            args=(name, role, prompt),
            daemon=True,
        )
        self.threads[name] = thread
        thread.start()
        return f"已启动队友 '{name}'（角色：{role}）"

    def _teammate_loop(self, name: str, role: str, prompt: str):
        # sys_prompt 明确要求队友遵守两个协议：
        # 1. 大动作前提交 plan_approval
        # 2. 收到 shutdown_request 时用 shutdown_response 回应
        sys_prompt = (
            f"你是队友 '{name}'，角色是 {role}，工作目录是 {WORKDIR}。"
            "请用中文思考和回复。"
            "执行重要工作前，先用 plan_approval 工具提交计划。"
            "收到 shutdown_request 消息后，必须用 shutdown_response 工具回应。"
            "工具名称保持英文，工具参数按 schema 填写。"
        )
        messages = [{"role": "user", "content": prompt}]
        tools = self._teammate_tools()
        should_exit = False
        # should_exit 是线程内部状态；只有队友批准 shutdown 后才会变成 True。
        for _ in range(50):
            inbox = BUS.read_inbox(name)
            for msg in inbox:
                messages.append({
                    "role": "user",
                    "content": json.dumps(msg, ensure_ascii=False),
                })
            if should_exit:
                break
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
                break
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = self._exec(name, block.name, block.input)
                    print(f"  [{name}] 调用 {block.name}: {str(output)[:120]}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(output),
                    })
                    if block.name == "shutdown_response" and block.input.get("approve"):
                        # 模型用工具表达“我同意关闭”；真正停止线程的是 Python 控制流。
                        should_exit = True
            messages.append({"role": "user", "content": results})
        member = self._find_member(name)
        if member:
            # 最终状态落盘到 .team/config.json，方便 CLI 的 /team 查看。
            member["status"] = "shutdown" if should_exit else "idle"
            self._save_config()

    def _exec(self, sender: str, tool_name: str, args: dict) -> str:
        # 基础工具沿用前几课；下面两个分支是本课新增的协议工具。
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
        if tool_name == "shutdown_response":
            req_id = args["request_id"]
            approve = args["approve"]
            # with lock 类似 Java try/finally 里的 lock.lock()/unlock()。
            # 离开 with 代码块时会自动释放锁。
            with _tracker_lock:
                if req_id in shutdown_requests:
                    shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
            BUS.send(
                sender, "lead", args.get("reason", ""),
                "shutdown_response", {"request_id": req_id, "approve": approve},
            )
            return f"关闭请求已{'批准' if approve else '拒绝'}"
        if tool_name == "plan_approval":
            plan_text = args.get("plan", "")
            # uuid4 生成全局随机 id；[:8] 是为了课堂输出短一点。
            req_id = str(uuid.uuid4())[:8]
            with _tracker_lock:
                plan_requests[req_id] = {"from": sender, "plan": plan_text, "status": "pending"}
            BUS.send(
                sender, "lead", plan_text, "plan_approval_response",
                {"request_id": req_id, "plan": plan_text},
            )
            return f"计划已提交（request_id={req_id}），等待负责人审批。"
        return f"未知工具：{tool_name}"

    def _teammate_tools(self) -> list:
        # teammate 现在多了 shutdown_response 和 plan_approval 两个协议工具。
        # 工具名就是协议动作，参数 schema 就是协议字段。
        return [
            {"name": "bash", "description": "运行一个 shell 命令。",
             "input_schema": {"type": "object", "properties": {"command": {"type": "string", "description": "要执行的命令"}}, "required": ["command"]}},
            {"name": "read_file", "description": "读取文件内容。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "相对工作目录的文件路径"}}, "required": ["path"]}},
            {"name": "write_file", "description": "把内容写入文件。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "相对工作目录的文件路径"}, "content": {"type": "string", "description": "要写入的内容"}}, "required": ["path", "content"]}},
            {"name": "edit_file", "description": "在文件中替换一段完全匹配的文本。",
             "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "相对工作目录的文件路径"}, "old_text": {"type": "string", "description": "要替换的原文"}, "new_text": {"type": "string", "description": "替换后的新文本"}}, "required": ["path", "old_text", "new_text"]}},
            {"name": "send_message", "description": "给某个队友发送消息。",
             "input_schema": {"type": "object", "properties": {"to": {"type": "string", "description": "收件队友名称"}, "content": {"type": "string", "description": "消息内容"}, "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES), "description": "消息类型，默认 message"}}, "required": ["to", "content"]}},
            {"name": "read_inbox", "description": "读取并清空自己的收件箱。",
             "input_schema": {"type": "object", "properties": {}}},
            {"name": "shutdown_response", "description": "回应关闭请求。同意则进入关闭流程，拒绝则继续工作。",
             "input_schema": {"type": "object", "properties": {"request_id": {"type": "string", "description": "关闭请求 id"}, "approve": {"type": "boolean", "description": "是否同意关闭"}, "reason": {"type": "string", "description": "同意或拒绝的原因"}}, "required": ["request_id", "approve"]}},
            {"name": "plan_approval", "description": "向负责人提交计划审批。请提供清晰的计划文本。",
             "input_schema": {"type": "object", "properties": {"plan": {"type": "string", "description": "待审批的计划"}}, "required": ["plan"]}},
        ]

    def list_all(self) -> str:
        if not self.config["members"]:
            return "暂无队友。"
        lines = [f"团队：{self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']}（{m['role']}）：{m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]


TEAM = TeammateManager(TEAM_DIR)


# -- 基础工具实现：这些基础工具和 s02 的思路一致 --
def _safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    # pathlib 的 / 运算符用于拼路径，不是字符串拼接；
    # 它会按当前操作系统选择正确的分隔符。
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径越过工作目录：{p}")
    return path


def _run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot"]
    if any(d in command for d in dangerous):
        return "错误：危险命令已拦截"
    try:
        r = subprocess.run(
            command, shell=True, cwd=WORKDIR,
            capture_output=True, text=True, timeout=120,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "（无输出）"
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
            return f"错误：在 {path} 中没有找到要替换的文本"
        fp.write_text(c.replace(old_text, new_text, 1), encoding="utf-8")
        return f"已编辑 {path}"
    except Exception as e:
        return f"错误：{e}"


# Lead 专属协议处理：创建请求、记录状态、向目标队友投递消息。
def handle_shutdown_request(teammate: str) -> str:
    # lead 发起 shutdown 时先登记 pending，再发消息。
    # 这样即使响应稍后才到，也能通过 request_id 找回上下文。
    req_id = str(uuid.uuid4())[:8]
    with _tracker_lock:
        shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    BUS.send(
        "lead", teammate, "请优雅退出当前工作。",
        "shutdown_request", {"request_id": req_id},
    )
    return f"已向 '{teammate}' 发送关闭请求 {req_id}（状态：pending）"


def handle_plan_review(request_id: str, approve: bool, feedback: str = "") -> str:
    # plan review 是反方向协议：teammate 先提交计划，lead 后审批。
    with _tracker_lock:
        req = plan_requests.get(request_id)
    if not req:
        return f"错误：未知计划 request_id '{request_id}'"
    with _tracker_lock:
        req["status"] = "approved" if approve else "rejected"
    BUS.send(
        "lead", req["from"], feedback, "plan_approval_response",
        {"request_id": request_id, "approve": approve, "feedback": feedback},
    )
    return f"已{'批准' if approve else '拒绝'} '{req['from']}' 的计划"


def _check_shutdown_status(request_id: str) -> str:
    # 查询工具只读 tracker，不主动改变状态。
    with _tracker_lock:
        return json.dumps(
            shutdown_requests.get(request_id, {"error": "not found"}),
            ensure_ascii=False,
        )


# Lead 的工具分发表：基础工具 + 队伍工具 + 两个协议工具。
TOOL_HANDLERS = {
    # 注意 shutdown_request / shutdown_response 在 lead 和 teammate 侧含义不同：
    # lead 的 shutdown_response 是“查询状态”，teammate 的是“发送响应”。
    "bash":              lambda **kw: _run_bash(kw["command"]),
    "read_file":         lambda **kw: _run_read(kw["path"], kw.get("limit")),
    "write_file":        lambda **kw: _run_write(kw["path"], kw["content"]),
    "edit_file":         lambda **kw: _run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "spawn_teammate":    lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates":    lambda **kw: TEAM.list_all(),
    "send_message":      lambda **kw: BUS.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox":        lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=2, ensure_ascii=False),
    "broadcast":         lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names()),
    "shutdown_request":  lambda **kw: handle_shutdown_request(kw["teammate"]),
    "shutdown_response": lambda **kw: _check_shutdown_status(kw.get("request_id", "")),
    "plan_approval":     lambda **kw: handle_plan_review(kw["request_id"], kw["approve"], kw.get("feedback", "")),
}

# 工具名保持英文，便于和代码里的 handler 对应；工具描述和参数说明改成中文。
TOOLS = [
    {"name": "bash", "description": "运行一个 shell 命令。",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string", "description": "要执行的命令"}}, "required": ["command"]}},
    {"name": "read_file", "description": "读取文件内容。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "相对工作目录的文件路径"}, "limit": {"type": "integer", "description": "最多读取的行数，可选"}}, "required": ["path"]}},
    {"name": "write_file", "description": "把内容写入文件。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "相对工作目录的文件路径"}, "content": {"type": "string", "description": "要写入的内容"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "在文件中替换一段完全匹配的文本。",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string", "description": "相对工作目录的文件路径"}, "old_text": {"type": "string", "description": "要替换的原文"}, "new_text": {"type": "string", "description": "替换后的新文本"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "spawn_teammate", "description": "启动一个持续运行的队友。",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string", "description": "队友名称"}, "role": {"type": "string", "description": "队友角色"}, "prompt": {"type": "string", "description": "启动后交给队友的任务提示词"}}, "required": ["name", "role", "prompt"]}},
    {"name": "list_teammates", "description": "列出全部队友和状态。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "send_message", "description": "给某个队友发送消息。",
     "input_schema": {"type": "object", "properties": {"to": {"type": "string", "description": "收件队友名称"}, "content": {"type": "string", "description": "消息内容"}, "msg_type": {"type": "string", "enum": list(VALID_MSG_TYPES), "description": "消息类型，默认 message"}}, "required": ["to", "content"]}},
    {"name": "read_inbox", "description": "读取并清空负责人的收件箱。",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "broadcast", "description": "给所有队友广播一条消息。",
     "input_schema": {"type": "object", "properties": {"content": {"type": "string", "description": "广播内容"}}, "required": ["content"]}},
    {"name": "shutdown_request", "description": "请求某个队友优雅退出。返回 request_id 供后续查询。",
     "input_schema": {"type": "object", "properties": {"teammate": {"type": "string", "description": "目标队友名称"}}, "required": ["teammate"]}},
    {"name": "shutdown_response", "description": "按 request_id 查询关闭请求的当前状态。",
     "input_schema": {"type": "object", "properties": {"request_id": {"type": "string", "description": "关闭请求 id"}}, "required": ["request_id"]}},
    {"name": "plan_approval", "description": "批准或拒绝队友提交的计划。需要 request_id、approve 和可选反馈。",
     "input_schema": {"type": "object", "properties": {"request_id": {"type": "string", "description": "计划请求 id"}, "approve": {"type": "boolean", "description": "是否批准"}, "feedback": {"type": "string", "description": "给队友的反馈，可选"}}, "required": ["request_id", "approve"]}},
]


def agent_loop(messages: list):
    while True:
        inbox = BUS.read_inbox("lead")
        if inbox:
            # lead 收到的协议消息用 <inbox> 包起来，提醒模型这是外部事件。
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
                    # 统一分发让新增协议只需要：
                    # 1. 写 handler
                    # 2. 在 TOOL_HANDLERS 注册
                    # 3. 在 TOOLS 暴露 schema
                    output = handler(**block.input) if handler else f"未知工具：{block.name}"
                except Exception as e:
                    output = f"错误：{e}"
                print(f"> 调用工具 {block.name}:")
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
            query = input("\033[36ms10 >> \033[0m")
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
