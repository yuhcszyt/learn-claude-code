#!/usr/bin/env python3
# Harness: MCP-shaped tools -- wrapping external tool servers as model tools.
"""
s13_mcp_tools_demo.py - MCP Tools Demo（MCP 工具接入原理）

这个文件不接真实 MCP SDK，而是用一个“长得像 MCP 的假 server/client”
演示核心结构：MCP server 暴露工具，harness 把它们转换成模型能看到的 tools，
模型请求 tool_use 后，harness 再把调用转发给 MCP server。

真实 MCP 大致是：

    MCP Server                 Harness / Client                  Model
    +------------+             +----------------+                +-------+
    | tools/list | ----------> | list_tools()   | -------------> | tools |
    | tools/call | <---------- | call_tool(...) | <------------- | use   |
    +------------+             +----------------+                +-------+

本课关键思想：
    MCP 不在模型里面，也不是模型直接调用 MCP。
    MCP 接在 harness 的工具层里，最终仍然表现为普通 tool calling。
"""

from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class MCPTool:
    """一个 MCP server 暴露出来的工具定义。"""

    name: str
    description: str
    input_schema: dict


class FakeNotesMCPServer:
    """
    一个最小 MCP server 模拟器。

    真实 MCP server 通常跑在另一个进程里，通过 stdio/HTTP 等方式通信。
    这里为了讲清楚原理，直接用 Python 方法模拟 tools/list 和 tools/call。
    """

    def __init__(self):
        self.notes = {
            "agent": "Agent loop = 调模型、执行工具、把 tool_result 喂回模型。",
            "mcp": "MCP = 外部工具/上下文接入协议，放在 harness 的工具层。",
            "team": "s09 里队友通过 .team/inbox/*.jsonl 文件通信。",
        }

    def list_tools(self) -> list[MCPTool]:
        """对应真实 MCP 的 tools/list。"""
        return [
            MCPTool(
                name="search_note",
                description="在课程笔记里按关键词搜索一条说明。",
                input_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"],
                },
            ),
            MCPTool(
                name="add_note",
                description="向课程笔记里写入一条说明。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["keyword", "content"],
                },
            ),
        ]

    def call_tool(self, name: str, arguments: dict) -> str:
        """对应真实 MCP 的 tools/call。"""
        if name == "search_note":
            keyword = arguments["keyword"]
            return self.notes.get(keyword, f"没有找到笔记：{keyword}")

        if name == "add_note":
            keyword = arguments["keyword"]
            content = arguments["content"]
            self.notes[keyword] = content
            return f"已写入笔记：{keyword}"

        return f"未知 MCP 工具：{name}"


class MCPToolAdapter:
    """
    把 MCP server 包装成 harness 里的工具注册表。

    注意工具名加了 mcp__notes__ 前缀。真实项目里经常要做命名空间，
    避免多个 MCP server 都有 search、query 之类的同名工具。
    """

    def __init__(self, server_name: str, server: FakeNotesMCPServer):
        self.server_name = server_name
        self.server = server
        self.remote_tools = {
            self._public_name(tool.name): tool
            for tool in server.list_tools()
        }

    def _public_name(self, tool_name: str) -> str:
        return f"mcp__{self.server_name}__{tool_name}"

    def list_tools_for_model(self) -> list[dict]:
        """把 MCP tools/list 的结果转换成模型 API 需要的 tools schema。"""
        tools = []
        for public_name, tool in self.remote_tools.items():
            tools.append({
                "name": public_name,
                "description": f"[MCP:{self.server_name}] {tool.description}",
                "input_schema": tool.input_schema,
            })
        return tools

    def can_call(self, public_name: str) -> bool:
        return public_name in self.remote_tools

    def call(self, public_name: str, arguments: dict) -> str:
        """把模型看到的工具名翻译回 MCP server 原始工具名，再调用 server。"""
        tool = self.remote_tools[public_name]
        print(f"  harness -> MCP tools/call: {self.server_name}.{tool.name}({arguments})")
        return self.server.call_tool(tool.name, arguments)


class ToolRegistry:
    """
    harness 的统一工具层。

    模型只看到 list_tools_for_model() 返回的 tools。
    执行时，registry 决定这是本地工具，还是要转发给 MCP。
    """

    def __init__(self, mcp_adapters: list[MCPToolAdapter]):
        self.local_tools = [
            {
                "name": "echo",
                "description": "本地工具：原样返回输入文本。",
                "input_schema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            }
        ]
        self.local_handlers = {
            "echo": lambda **kw: f"本地 echo：{kw['text']}",
        }
        self.mcp_adapters = mcp_adapters

    def list_tools_for_model(self) -> list[dict]:
        tools = list(self.local_tools)
        for adapter in self.mcp_adapters:
            tools.extend(adapter.list_tools_for_model())
        return tools

    def call(self, name: str, arguments: dict) -> str:
        if name in self.local_handlers:
            print(f"  harness -> local handler: {name}({arguments})")
            return self.local_handlers[name](**arguments)

        for adapter in self.mcp_adapters:
            if adapter.can_call(name):
                return adapter.call(name, arguments)

        return f"未知工具：{name}"


class FakeModel:
    """
    一个假模型：它不真的思考，只是按脚本产生 tool_use。

    这样 demo 不需要 API key，也能看清楚 harness 如何处理 tool calling。
    """

    def __init__(self):
        self.step = 0

    def create(self, messages: list, tools: list[dict]):
        self.step += 1

        if self.step == 1:
            return SimpleNamespace(
                stop_reason="tool_use",
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        id="toolu_1",
                        name="mcp__notes__search_note",
                        input={"keyword": "mcp"},
                    )
                ],
            )

        if self.step == 2:
            return SimpleNamespace(
                stop_reason="tool_use",
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        id="toolu_2",
                        name="echo",
                        input={"text": "MCP 调用结果已经进入 messages，模型现在可以继续总结。"},
                    )
                ],
            )

        last_tool_results = messages[-1]["content"]
        summary = (
            "最终回答：我通过 MCP 工具查到了 mcp 笔记，又调用了本地 echo。"
            f"最后一批 tool_result 是：{last_tool_results}"
        )
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(text=summary)])


def agent_loop(user_prompt: str, registry: ToolRegistry):
    messages = [{"role": "user", "content": user_prompt}]
    model = FakeModel()

    tools = registry.list_tools_for_model()
    print("模型本轮能看到的工具：")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    for _ in range(10):
        response = model.create(messages=messages, tools=tools)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            print()
            for block in response.content:
                if hasattr(block, "text"):
                    print(block.text)
            return

        results = []
        for block in response.content:
            if block.type == "tool_use":
                print()
                print(f"模型请求 tool_use: {block.name} {block.input}")
                output = registry.call(block.name, block.input)
                print(f"  tool_result: {output}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    notes_server = FakeNotesMCPServer()
    notes_adapter = MCPToolAdapter("notes", notes_server)
    tool_registry = ToolRegistry([notes_adapter])

    agent_loop("请解释 MCP 是怎么接入 tools 的。", tool_registry)
