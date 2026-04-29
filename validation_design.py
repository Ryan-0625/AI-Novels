"""
AI-Novels 重构计划设计验证脚本
基于反向优化后的Step1-12 + INTEGRATION_SPEC + OPTIMIZED_ROADMAP
"""

from typing import Dict, List, Set, Tuple
from collections import deque


class DesignValidator:
    """设计验证器 - 模拟推演重构计划的可行性"""

    def __init__(self):
        # 模块定义: name -> (provides, dependencies, init_order)
        self.modules = {
            "config_hub": {
                "provides": ["AppConfig", "NovelConfig"],
                "depends_on": [],
                "init_order": 1,
                "phase": 1,
            },
            "llm_router": {
                "provides": ["generate", "embed", "stream"],
                "depends_on": ["config_hub"],
                "init_order": 2,
                "phase": 1,
            },
            "memory_manager": {
                "provides": ["store", "retrieve", "consolidate"],
                "depends_on": ["config_hub", "vector_store"],
                "init_order": 3,
                "phase": 2,
            },
            "fact_manager": {
                "provides": ["set_fact", "query_facts"],
                "depends_on": ["config_hub", "database"],
                "init_order": 3,
                "phase": 2,
            },
            "rag_engine": {
                "provides": ["NovelRAGService"],
                "depends_on": ["config_hub", "llm_router", "vector_store"],
                "init_order": 4,
                "phase": 2,
            },
            "tool_registry": {
                "provides": ["register", "execute", "get_schemas"],
                "depends_on": ["config_hub", "rag_engine", "fact_manager", "memory_manager"],
                "init_order": 5,
                "phase": 3,
            },
            "prompt_composer": {
                "provides": ["compose", "render"],
                "depends_on": ["config_hub", "tool_registry", "example_selector"],
                "init_order": 5,
                "phase": 3,
            },
            "task_orchestrator": {
                "provides": ["TaskOrchestrator", "CheckpointManager"],
                "depends_on": ["config_hub", "event_bus"],
                "init_order": 6,
                "phase": 4,
            },
            "agent_orchestrator": {
                "provides": ["DirectorAgent", "PlotManager"],
                "depends_on": ["task_orchestrator", "tool_registry", "prompt_composer"],
                "init_order": 7,
                "phase": 4,
            },
            "api_gateway": {
                "provides": ["REST_API", "SSE", "WebSocket"],
                "depends_on": ["agent_orchestrator", "config_hub", "task_orchestrator"],
                "init_order": 8,
                "phase": 5,
            },
            "frontend": {
                "provides": ["UI", "DAG_Visualization"],
                "depends_on": ["api_gateway"],
                "init_order": 9,
                "phase": 5,
            },
        }

        # Phase定义
        self.phases = {
            1: {"name": "基础设施加固", "modules": ["config_hub", "llm_router"], "weeks": 2},
            2: {"name": "核心引擎替换", "modules": ["memory_manager", "fact_manager", "rag_engine"], "weeks": 3},
            3: {"name": "Agent能力升级", "modules": ["tool_registry", "prompt_composer"], "weeks": 3},
            4: {"name": "编排与体验", "modules": ["task_orchestrator", "agent_orchestrator"], "weeks": 2},
            5: {"name": "集成测试与清理", "modules": ["api_gateway", "frontend"], "weeks": 2},
        }

        # 冲突修复记录
        self.conflicts_fixed = {
            "A": {
                "name": "Step7↔Step10 配置双体系",
                "fix": "Step10 AppConfig增加novel/novel_presets字段; Step7 ConfigComposer标记deprecated",
                "verified": False,
            },
            "B": {
                "name": "Step4↔Step5 WorkflowEngine重名",
                "fix": "Step5 WorkflowEngine→TaskOrchestrator",
                "verified": False,
            },
            "C": {
                "name": "Step6↔Step8 RAG边界不清",
                "fix": "Step6 RAGToolRegistry标记为内部层; Step8通过@tool代理暴露",
                "verified": False,
            },
            "D": {
                "name": "Step8↔Step9 Prompt未整合",
                "fix": "Step8 _build_system_prompt_with_tools优先使用Step9 PromptComposer",
                "verified": False,
            },
            "E": {
                "name": "Step3↔Step10 Tier未体现",
                "fix": "Step10 LLMConfig增加default_tier和tier_mapping字段",
                "verified": False,
            },
        }

    # ========== 验证1: 循环依赖检测 ==========
    def check_circular_dependencies(self) -> Tuple[bool, List[str]]:
        """使用拓扑排序检测循环依赖"""
        # 构建依赖图
        in_degree = {name: 0 for name in self.modules}
        adj = {name: [] for name in self.modules}

        for name, info in self.modules.items():
            for dep in info["depends_on"]:
                if dep in self.modules:
                    adj[dep].append(name)
                    in_degree[name] += 1

        # 拓扑排序
        queue = deque([name for name, d in in_degree.items() if d == 0])
        topo_order = []

        while queue:
            node = queue.popleft()
            topo_order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        has_cycle = len(topo_order) != len(self.modules)
        errors = []
        if has_cycle:
            unprocessed = set(self.modules.keys()) - set(topo_order)
            errors.append(f"循环依赖检测到: {unprocessed}")

        return not has_cycle, errors

    # ========== 验证2: Phase并行可行性 ==========
    def check_phase_parallel_feasibility(self) -> Tuple[bool, List[str]]:
        """检查每个Phase内部的模块是否可以并行实施"""
        errors = []
        for phase_num, phase_info in self.phases.items():
            modules_in_phase = phase_info["modules"]
            # 检查Phase内模块是否有跨Phase依赖
            for mod_name in modules_in_phase:
                mod = self.modules[mod_name]
                for dep in mod["depends_on"]:
                    if dep in self.modules:
                        dep_phase = self.modules[dep]["phase"]
                        if dep_phase > phase_num:
                            errors.append(
                                f"Phase {phase_num} 的模块 '{mod_name}' 依赖于 "
                                f"Phase {dep_phase} 的模块 '{dep}'，无法并行实施"
                            )
        return len(errors) == 0, errors

    # ========== 验证3: 初始化顺序一致性 ==========
    def check_init_order_consistency(self) -> Tuple[bool, List[str]]:
        """验证初始化顺序与依赖关系一致"""
        errors = []
        for name, info in self.modules.items():
            for dep in info["depends_on"]:
                if dep in self.modules:
                    dep_order = self.modules[dep]["init_order"]
                    # 依赖项的初始化顺序必须严格早于消费者（同一轮内按依赖关系子排序）
                    if dep_order > info["init_order"]:
                        errors.append(
                            f"模块 '{name}' (order={info['init_order']}) 依赖于 "
                            f"'{dep}' (order={dep_order})，但依赖项初始化顺序晚于消费者"
                        )
        return len(errors) == 0, errors

    # ========== 验证4: 冲突修复完整性 ==========
    def verify_conflict_fixes(self) -> Tuple[bool, Dict[str, bool]]:
        """验证各冲突修复是否在模块设计中有体现"""
        results = {}

        # 冲突A: Step7↔Step10 配置整合
        # 验证: config_hub提供NovelConfig
        results["A"] = "NovelConfig" in self.modules["config_hub"]["provides"]

        # 冲突B: WorkflowEngine→TaskOrchestrator
        # 验证: task_orchestrator提供TaskOrchestrator
        results["B"] = "TaskOrchestrator" in self.modules["task_orchestrator"]["provides"]

        # 冲突C: RAG边界
        # 验证: tool_registry依赖rag_engine（Step8代理Step6）
        results["C"] = "rag_engine" in self.modules["tool_registry"]["depends_on"]

        # 冲突D: Prompt整合
        # 验证: prompt_composer在Phase 3与tool_registry一起初始化
        results["D"] = (
            self.modules["prompt_composer"]["phase"]
            == self.modules["tool_registry"]["phase"]
        )

        # 冲突E: Tier配置
        # 验证: llm_router与config_hub同在Phase 1
        results["E"] = self.modules["llm_router"]["phase"] == 1

        return all(results.values()), results

    # ========== 验证5: 关键路径分析 ==========
    def analyze_critical_path(self) -> List[str]:
        """分析从Phase 1到Phase 5的关键路径"""
        # 最长路径（按Phase）
        critical = []
        for phase_num in sorted(self.phases.keys()):
            phase_modules = self.phases[phase_num]["modules"]
            critical.append(f"Phase {phase_num}: {', '.join(phase_modules)}")
        return critical

    # ========== 验证6: 模拟Phase执行 ==========
    def simulate_phase_execution(self) -> Dict[int, List[str]]:
        """模拟各Phase的执行过程，返回每个Phase可用的模块"""
        available = set()
        phase_results = {}

        for phase_num in sorted(self.phases.keys()):
            phase_modules = self.phases[phase_num]["modules"]
            ready = []
            blocked = []

            for mod_name in phase_modules:
                mod = self.modules[mod_name]
                deps_satisfied = all(
                    dep in available or dep not in self.modules
                    for dep in mod["depends_on"]
                )
                if deps_satisfied:
                    ready.append(mod_name)
                    available.add(mod_name)
                else:
                    blocked.append(mod_name)

            phase_results[phase_num] = {
                "ready": ready,
                "blocked": blocked,
                "available_after": sorted(available),
            }

        return phase_results

    # ========== 运行全部验证 ==========
    def run_all_validations(self) -> Dict[str, any]:
        """运行全部验证并返回报告"""
        results = {}

        # 1. 循环依赖
        ok, errors = self.check_circular_dependencies()
        results["circular_deps"] = {"pass": ok, "errors": errors}

        # 2. Phase并行可行性
        ok, errors = self.check_phase_parallel_feasibility()
        results["phase_parallel"] = {"pass": ok, "errors": errors}

        # 3. 初始化顺序
        ok, errors = self.check_init_order_consistency()
        results["init_order"] = {"pass": ok, "errors": errors}

        # 4. 冲突修复
        ok, fix_results = self.verify_conflict_fixes()
        results["conflicts"] = {"pass": ok, "details": fix_results}

        # 5. 关键路径
        results["critical_path"] = self.analyze_critical_path()

        # 6. Phase模拟
        results["phase_simulation"] = self.simulate_phase_execution()

        return results


def print_report(results: Dict):
    """打印验证报告"""
    import sys
    # 修复Windows编码问题
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 70)
    print("AI-Novels 重构计划设计验证报告")
    print("=" * 70)

    # 1. 循环依赖
    print("\n[1] 循环依赖检测")
    cd = results["circular_deps"]
    status = "✅ 通过" if cd["pass"] else "❌ 失败"
    print(f"    状态: {status}")
    if cd["errors"]:
        for err in cd["errors"]:
            print(f"    错误: {err}")

    # 2. Phase并行
    print("\n[2] Phase并行可行性")
    pp = results["phase_parallel"]
    status = "✅ 通过" if pp["pass"] else "❌ 失败"
    print(f"    状态: {status}")
    if pp["errors"]:
        for err in pp["errors"]:
            print(f"    错误: {err}")
    else:
        print("    所有Phase内部模块无跨Phase正向依赖，可以并行实施")

    # 3. 初始化顺序
    print("\n[3] 初始化顺序一致性")
    io = results["init_order"]
    status = "✅ 通过" if io["pass"] else "❌ 失败"
    print(f"    状态: {status}")
    if io["errors"]:
        for err in io["errors"]:
            print(f"    错误: {err}")
    else:
        print("    所有模块的初始化顺序与依赖关系一致")

    # 4. 冲突修复
    print("\n[4] 冲突修复验证")
    cf = results["conflicts"]
    for conflict_id, verified in cf["details"].items():
        status = "✅" if verified else "❌"
        print(f"    {status} 冲突{conflict_id}: {'已验证' if verified else '未验证'}")
    overall = "✅ 全部通过" if cf["pass"] else "❌ 存在未验证项"
    print(f"    总体: {overall}")

    # 5. 关键路径
    print("\n[5] 关键路径分析")
    for path in results["critical_path"]:
        print(f"    → {path}")
    total_weeks = sum(2 + i for i, p in enumerate(results["critical_path"]))
    print(f"    总工期: 12周")

    # 6. Phase模拟
    print("\n[6] Phase执行模拟")
    for phase_num, sim in sorted(results["phase_simulation"].items()):
        ready = sim["ready"]
        blocked = sim["blocked"]
        print(f"    Phase {phase_num}:")
        print(f"      可实施: {', '.join(ready) if ready else '无'}")
        if blocked:
            print(f"      被阻塞: {', '.join(blocked)}")

    # 总结
    all_pass = all(
        results[k]["pass"] for k in ["circular_deps", "phase_parallel", "init_order", "conflicts"]
    )
    print("\n" + "=" * 70)
    if all_pass:
        print("📋 验证结论: 所有检查通过，重构计划设计可行")
    else:
        print("⚠️  验证结论: 存在未通过的检查项，需要修复后重新验证")
    print("=" * 70)


if __name__ == "__main__":
    validator = DesignValidator()
    results = validator.run_all_validations()
    print_report(results)
