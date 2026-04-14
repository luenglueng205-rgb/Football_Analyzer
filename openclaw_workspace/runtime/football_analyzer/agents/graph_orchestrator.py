import asyncio
import time
import logging
from typing import Dict, Any, Callable, List

logger = logging.getLogger(__name__)

class AsyncStateGraph:
    """
    2026 版轻量级异步状态图编排器 (Lightweight Async StateGraph)
    取代传统的死循环 while handoff 和阻塞的 DAG。
    支持并发执行多个 Node（比如 14 场足球比赛的情报拉取）。
    """
    
    def __init__(self):
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, Callable[[Dict[str, Any]], str]] = {}
        self.entry_point: str = None
        self.state: Dict[str, Any] = {}
    
    def add_node(self, name: str, action: Callable):
        """添加一个处理节点 (通常是 Agent 的 process 方法)"""
        self.nodes[name] = action
        
    def add_edge(self, start_node: str, end_node: str):
        """添加确定性的边"""
        self.edges[start_node] = end_node
        
    def add_conditional_edge(self, start_node: str, condition: Callable[[Dict[str, Any]], str]):
        """添加条件边 (例如：RiskManager 决定是 End 还是打回重审)"""
        self.conditional_edges[start_node] = condition
        
    def set_entry_point(self, node_name: str):
        """设置入口节点"""
        self.entry_point = node_name
        
    async def compile_and_run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """编译并执行图状态机"""
        if not self.entry_point:
            raise ValueError("未设置入口节点 (entry_point)")
            
        self.state = initial_state
        current_node = self.entry_point
        max_steps = 20
        steps = 0
        
        start_time = time.time()
        print(f"\n[Graph Engine] 启动图状态机执行... 初始节点: {current_node}")
        
        while current_node and steps < max_steps:
            if current_node == "END":
                print("[Graph Engine] 到达 END 节点，执行完成。")
                break
                
            print(f"  -> [执行 Node] {current_node}")
            action = self.nodes.get(current_node)
            
            if not action:
                raise ValueError(f"未知的节点: {current_node}")
                
            # 执行节点操作 (可能是异步 Agent)
            state_delta = await action(self.state)
            
            # 状态更新 (字典浅合并，实际 2026 方案可用 Reducer 模式)
            if state_delta and isinstance(state_delta, dict):
                self.state.update(state_delta)
            
            # 决定下一个节点
            if current_node in self.conditional_edges:
                next_node = self.conditional_edges[current_node](self.state)
                print(f"  -> [条件路由] 根据状态，跳转至: {next_node}")
                current_node = next_node
            elif current_node in self.edges:
                next_node = self.edges[current_node]
                current_node = next_node
            else:
                # 没有出度，自动结束
                print(f"  -> [自动路由] 节点无出边，默认结束。")
                current_node = "END"
                
            steps += 1
            
        if steps >= max_steps:
            print("⚠️ [Graph Engine] 触发死循环保护机制，强制终止。")
            
        elapsed = time.time() - start_time
        print(f"[Graph Engine] 执行耗时: {elapsed:.2f} 秒\n")
        return self.state
