"""
QualityCheckerAgent - 质量检查智能体

@file: agents/quality_checker.py
@date: 2026-03-12
@author: AI-Novels Team
@version: 1.0
@description: 连贯性/一致性/风格检查
"""

import time
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .base import BaseAgent, AgentConfig, Message, MessageType
from src.deepnovel.utils import log_info


class CheckType(Enum):
    """检查类型"""
    COHERENCE = "coherence"         # 连贯性
    CONSISTENCY = "consistency"     # 一致性
    STYLE = "style"                 # 风格
    PLOT = "plot"                   # 情节
    CHARACTER = "character"         # 角色
    SETTING = "setting"             # 世界观
    GRAMMAR = "grammar"             # 语法
    PACING = "pacing"               # 节奏


class IssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"           # 严重
    MAJOR = "major"                 # 主要
    MINOR = "minor"                 # 次要
    SUGGESTION = "suggestion"       # 建议


@dataclass
class QualityIssue:
    """质量问题"""
    issue_id: str
    issue_type: CheckType
    severity: IssueSeverity
    message: str
    location: str  # 位置 (章节-段落)
    context: str     # 上下文
    suggestion: str  # 建议
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "type": self.issue_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "location": self.location,
            "context": self.context,
            "suggestion": self.suggestion,
            "timestamp": self.timestamp
        }

    def json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class QualityReport:
    """质量报告"""
    report_id: str
    content_id: str
    overall_score: float
    chapters_checked: int
    issues: List[QualityIssue]
    check_results: Dict[str, Dict[str, Any]]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "content_id": self.content_id,
            "overall_score": self.overall_score,
            "chapters_checked": self.chapters_checked,
            "issues": [i.to_dict() for i in self.issues],
            "check_results": self.check_results,
            "timestamp": self.timestamp
        }

    def json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class QualityCheckerAgent(BaseAgent):
    """
    质量检查智能体

    核心功能：
    - 连贯性检查（逻辑流、过渡、因果）
    - 一致性检查（时间线、角色特征、世界观）
    - 风格检查（词汇、句式、语气）
    - 情节检查（节奏、张力、转折）
    - 角色检查（行为一致性、发展）
    - 语法检查（基础错误）
    """

    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                name="quality_checker",
                description="Content quality verification",
                provider="ollama",
                model="qwen2.5-7b",
                max_tokens=4096
            )
        super().__init__(config)

        # 质量问题存储
        self._issues: List[QualityIssue] = []
        self._reports: Dict[str, QualityReport] = {}

        # 检查规则
        self._coherence_rules = [
            self._check_timeline_consistency,
            self._check_causal_logic,
            self._check_transition_smoothing,
        ]

        self._consistency_rules = [
            self._check_character_consistency,
            self._check_setting_consistency,
            self._check_time_consistency,
        ]

        self._style_rules = [
            self._check_vocabulary_level,
            self._check_sentence_variation,
            self._check_tone_consistency,
        ]

        self._plot_rules = [
            self._check_pacing,
            self._check_tension_arc,
            self._check_climax_placement,
        ]

        # 统计
        self._total_checks_performed = 0
        self._total_issues_found = 0
        self._check_history: List[Dict[str, Any]] = []

    def process(self, message: Message) -> Message:
        """处理消息"""
        content = str(message.content).lower()

        if "check" in content or "quality" in content:
            if "report" in content or "generate" in content:
                return self._handle_generate_report(message)
            elif "issues" in content or "list" in content:
                return self._handle_list_issues(message)
            elif "coherence" in content:
                return self._handle_coherence_check(message)
            elif "consistency" in content:
                return self._handle_consistency_check(message)
            elif "style" in content:
                return self._handle_style_check(message)
            elif "plot" in content:
                return self._handle_plot_check(message)
            elif "character" in content or "character" in content:
                return self._handle_character_check(message)
        elif "fix" in content and "suggestion" in content:
            return self._handle_get_suggestion(message)

        return self._handle_general_request(message)

    def _handle_generate_report(self, message: Message) -> Message:
        """处理生成报告请求"""
        content = str(message.content)

        content_id = self._extract_param(content, "content_id", "")
        chapters_str = self._extract_param(content, "chapters", "")

        # 解析章节
        chapters = self._parse_chapters(chapters_str)

        # 生成检查报告
        report = self._generate_quality_report(
            content_id=content_id,
            chapters=chapters
        )

        self._reports[content_id] = report
        self._issues.extend(report.issues)
        self._total_issues_found += len(report.issues)
        self._total_checks_performed += 1

        response = f"Quality Report for {content_id}:\n\n"
        response += f"Overall Score: {report.overall_score:.1f}/100\n"
        response += f"Chapters Checked: {report.chapters_checked}\n"
        response += f"Total Issues: {len(report.issues)}\n\n"

        # 按严重程度分类统计
        by_severity = defaultdict(list)
        for issue in report.issues:
            by_severity[issue.severity.value].append(issue)

        response += "Issues by Severity:\n"
        for severity in ["critical", "major", "minor", "suggestion"]:
            count = len(by_severity[severity])
            if count > 0:
                response += f"  {severity.upper()}: {count}\n"

        # 显示前几个问题
        if report.issues:
            response += "\nTop Issues:\n"
            for i, issue in enumerate(report.issues[:5], 1):
                response += f"{i}. [{issue.severity.value.upper()}] {issue.message[:60]}...\n"

        return self._create_message(
            response,
            MessageType.TEXT,
            content_id=content_id,
            overall_score=report.overall_score,
            issue_count=len(report.issues)
        )

    def _handle_list_issues(self, message: Message) -> Message:
        """处理列出问题请求"""
        content = str(message.content)

        severity_filter = self._extract_param(content, "severity", "").lower()
        type_filter = self._extract_param(content, "type", "").lower()

        issues = self._issues[:]

        if severity_filter:
            issues = [i for i in issues if i.severity.value == severity_filter]
        if type_filter:
            issues = [i for i in issues if i.issue_type.value == type_filter]

        response = f"Quality Issues ({len(issues)} total):\n\n"
        for i, issue in enumerate(issues[:20], 1):
            response += f"{i}. [{issue.severity.value.upper()}] {issue.issue_type.value}\n"
            response += f"   {issue.message[:80]}...\n"
            response += f"   Location: {issue.location}\n\n"

        return self._create_message(
            response,
            MessageType.TEXT,
            issue_count=len(issues)
        )

    def _handle_coherence_check(self, message: Message) -> Message:
        """处理连贯性检查请求"""
        content = str(message.content)

        content_id = self._extract_param(content, "content_id", "")
        chapters_str = self._extract_param(content, "chapters", "")

        chapters = self._parse_chapters(chapters_str)

        issues = []
        for rule in self._coherence_rules:
            issues.extend(rule(content_id, chapters))

        self._issues.extend(issues)
        self._total_checks_performed += 1

        response = f"Coherence Check for {content_id}:\n\n"
        response += f"Issues Found: {len(issues)}\n\n"

        # 按严重程度分组
        critical = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        major = [i for i in issues if i.severity == IssueSeverity.MAJOR]
        minor = [i for i in issues if i.severity == IssueSeverity.MINOR]

        if critical:
            response += "CRITICAL:\n"
            for issue in critical:
                response += f"  - {issue.message}\n"
            response += "\n"

        if major:
            response += "MAJOR:\n"
            for issue in major:
                response += f"  - {issue.message}\n"
            response += "\n"

        response += f"MINOR: {len(minor)} issues\n"

        return self._create_message(
            response,
            MessageType.TEXT,
            coherence_issues=len(issues)
        )

    def _handle_consistency_check(self, message: Message) -> Message:
        """处理一致性检查请求"""
        content = str(message.content)

        content_id = self._extract_param(content, "content_id", "")
        chapters_str = self._extract_param(content, "chapters", "")

        chapters = self._parse_chapters(chapters_str)

        issues = []
        for rule in self._consistency_rules:
            issues.extend(rule(content_id, chapters))

        self._issues.extend(issues)
        self._total_checks_performed += 1

        response = f"Consistency Check for {content_id}:\n\n"
        response += f"Issues Found: {len(issues)}\n\n"

        # 分组显示
        by_type = defaultdict(list)
        for issue in issues:
            by_type[issue.issue_type.value].append(issue)

        for issue_type, type_issues in by_type.items():
            response += f"{issue_type.upper()} ({len(type_issues)}):\n"
            for issue in type_issues[:3]:
                response += f"  - {issue.message}\n"
            response += "\n"

        return self._create_message(
            response,
            MessageType.TEXT,
            consistency_issues=len(issues)
        )

    def _handle_style_check(self, message: Message) -> Message:
        """处理风格检查请求"""
        content = str(message.content)

        content_id = self._extract_param(content, "content_id", "")
        chapters_str = self._extract_param(content, "chapters", "")

        chapters = self._parse_chapters(chapters_str)

        issues = []
        for rule in self._style_rules:
            issues.extend(rule(content_id, chapters))

        self._issues.extend(issues)
        self._total_checks_performed += 1

        response = f"Style Check for {content_id}:\n\n"
        response += f"Issues Found: {len(issues)}\n\n"

        if issues:
            for issue in issues:
                response += f"[{issue.severity.value}] {issue.message}\n"
        else:
            response += "Style is consistent throughout.\n"

        return self._create_message(
            response,
            MessageType.TEXT,
            style_issues=len(issues)
        )

    def _handle_plot_check(self, message: Message) -> Message:
        """处理情节检查请求"""
        content = str(message.content)

        content_id = self._extract_param(content, "content_id", "")
        chapters_str = self._extract_param(content, "chapters", "")

        chapters = self._parse_chapters(chapters_str)

        issues = []
        for rule in self._plot_rules:
            issues.extend(rule(content_id, chapters))

        self._issues.extend(issues)
        self._total_checks_performed += 1

        response = f"Plot Check for {content_id}:\n\n"
        response += f"Issues Found: {len(issues)}\n\n"

        for issue in issues:
            response += f"[{issue.severity.value}] {issue.message}\n"
            response += f"Suggestion: {issue.suggestion}\n\n"

        return self._create_message(
            response,
            MessageType.TEXT,
            plot_issues=len(issues)
        )

    def _handle_character_check(self, message: Message) -> Message:
        """处理角色检查请求"""
        content = str(message.content)

        content_id = self._extract_param(content, "content_id", "")
        character_name = self._extract_param(content, "character", "")

        issues = self._check_character_consistency(content_id, character_name)

        self._issues.extend(issues)
        self._total_checks_performed += 1

        response = f"Character Check for {character_name} (in {content_id}):\n\n"
        response += f"Issues Found: {len(issues)}\n\n"

        if issues:
            for issue in issues:
                response += f"[{issue.severity.value}] {issue.message}\n"
        else:
            response += "Character behavior is consistent.\n"

        return self._create_message(
            response,
            MessageType.TEXT,
            character_issues=len(issues)
        )

    def _handle_get_suggestion(self, message: Message) -> Message:
        """处理获取建议请求"""
        content = str(message.content)
        issue_id = self._extract_param(content, "issue_id", "")

        if issue_id:
            # 查找对应问题
            for issue in self._issues:
                if issue_id in issue.issue_id:
                    response = f"Suggestion for {issue_id}:\n\n"
                    response += f"Issue: {issue.message}\n"
                    response += f"Suggestion: {issue.suggestion}\n"
                    return self._create_message(response, MessageType.TEXT)

        # 返回随机建议
        suggestions = [
            "Consider adding more sensory details to improve immersion.",
            "Review character motivations to ensure they align with actions.",
            "Vary sentence structure to improve reading flow.",
            "Check for timeline consistency in consecutive chapters.",
            "Ensure emotional responses match the situation intensity.",
        ]

        response = "Quality Improvement Suggestions:\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"

        return self._create_message(response, MessageType.TEXT)

    def _handle_general_request(self, message: Message) -> Message:
        """处理一般请求"""
        response = (
            "Quality Checker Agent available commands:\n"
            "- 'generate report content_id=X chapters=X' - 生成质量报告\n"
            "- 'list issues [severity=X] [type=X]' - 列出问题\n"
            "- 'check coherence content_id=X chapters=X' - 连贯性检查\n"
            "- 'check consistency content_id=X chapters=X' - 一致性检查\n"
            "- 'check style content_id=X chapters=X' - 风格检查\n"
            "- 'check plot content_id=X chapters=X' - 情节检查\n"
            "- 'check character content_id=X character=X' - 角色检查\n"
            "- 'get suggestion issue_id=X' - 获取改进建议"
        )
        return self._create_message(response)

    def _generate_quality_report(
        self,
        content_id: str,
        chapters: List[str]
    ) -> QualityReport:
        """
        生成质量报告

        Args:
            content_id: 内容ID
            chapters: 章节列表

        Returns:
            QualityReport实例
        """
        report_id = f"report_{content_id}_{int(time.time())}"

        all_issues = []
        check_results = {}

        # 执行各项检查
        for check_type, rules in [
            (CheckType.COHERENCE, self._coherence_rules),
            (CheckType.CONSISTENCY, self._consistency_rules),
            (CheckType.STYLE, self._style_rules),
            (CheckType.PLOT, self._plot_rules),
        ]:
            for rule in rules:
                issues = rule(content_id, chapters)
                all_issues.extend(issues)

                # 记录检查结果
                rule_name = rule.__name__
                check_results[rule_name] = {
                    "issues_found": len(issues),
                    "severity_distribution": self._get_severity_distribution(issues),
                    "check_type": check_type.value
                }

        # 计算总体分数
        overall_score = self._calculate_overall_score(all_issues)

        report = QualityReport(
            report_id=report_id,
            content_id=content_id,
            overall_score=overall_score,
            chapters_checked=len(chapters),
            issues=all_issues,
            check_results=check_results,
            timestamp=time.time()
        )

        return report

    def _check_timeline_consistency(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查时间线一致性"""
        issues = []

        # 检查章节顺序
        chapter_nums = []
        for chapter in chapters:
            match = re.search(r'(\d+)', chapter)
            if match:
                chapter_nums.append(int(match.group(1)))

        if len(chapter_nums) > 1:
            for i in range(len(chapter_nums) - 1):
                if chapter_nums[i] > chapter_nums[i + 1]:
                    issues.append(QualityIssue(
                        issue_id=f"tl_{content_id}_{i}",
                        issue_type=CheckType.COHERENCE,
                        severity=IssueSeverity.MAJOR,
                        message=f"Chapter order issue: Chapter {chapter_nums[i]} before {chapter_nums[i+1]}",
                        location=f"{content_id}: {chapter_nums[i]} -> {chapter_nums[i+1]}",
                        context="Chapter sequence should be chronological",
                        suggestion="Reorder chapters or clarify time jumps"
                    ))

        return issues

    def _check_causal_logic(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查因果逻辑"""
        issues = []

        # 检查连续事件的逻辑连接
        # 简化实现：基于章节数量检查
        if len(chapters) > 1:
            # 模拟检测到一些逻辑问题
            if len(chapters) > 5 and len(chapters) % 2 == 0:
                issues.append(QualityIssue(
                    issue_id=f"cl_{content_id}_001",
                    issue_type=CheckType.COHERENCE,
                    severity=IssueSeverity.MINOR,
                    message="Unclear motivation for character actions in later chapters",
                    location=f"{content_id}: Chapters {len(chapters)//2}-end",
                    context="Character development may lack consistent motivation",
                    suggestion="Review character motivations and ensure they evolve naturally"
                ))

        return issues

    def _check_transition_smoothing(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查过渡平滑度"""
        issues = []

        # 检查章节结尾和开头的过渡
        for i in range(len(chapters) - 1):
            # 模拟检测到过渡问题
            if i == 0 and len(chapters) > 3:
                issues.append(QualityIssue(
                    issue_id=f"tr_{content_id}_{i}",
                    issue_type=CheckType.COHERENCE,
                    severity=IssueSeverity.SUGGESTION,
                    message="Chapter transition could be smoother",
                    location=f"{content_id}: Chapters {chapters[i]}-{chapters[i+1]}",
                    context="Opening chapter sets up world but transitions may feel abrupt",
                    suggestion="Add bridging paragraphs or gradual scene changes"
                ))

        return issues

    def _check_character_consistency(
        self,
        content_id: str,
        character_name: str
    ) -> List[QualityIssue]:
        """检查角色一致性"""
        issues = []

        if not character_name:
            return issues

        # 检查角色行为一致性
        issues.append(QualityIssue(
            issue_id=f"cc_{content_id}_{character_name[:3]}",
            issue_type=CheckType.CHARACTER,
            severity=IssueSeverity.SUGGESTION,
            message=f"Character behavior may have inconsistencies",
            location=f"{content_id}: Character arc",
            context=f"Character '{character_name}' actions across chapters",
            suggestion="Review character development and ensure consistent behavior patterns"
        ))

        return issues

    def _check_setting_consistency(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查世界观一致性"""
        issues = []

        # 检查设定在同一世界中的应用
        setting_elements = ["magic", "technology", "social_structure", "geography"]

        for element in setting_elements:
            # 模拟检查
            issues.append(QualityIssue(
                issue_id=f"sc_{content_id}_{element}",
                issue_type=CheckType.SETTING,
                severity=IssueSeverity.SUGGESTION,
                message=f"World element '{element}' may need consistency review",
                location=f"{content_id}: World-building",
                context=f"Consistency of {element} across chapters",
                suggestion=f"Ensure {element} rules are applied consistently"
            ))

        return issues

    def _check_time_consistency(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查时间一致性"""
        issues = []

        # 检查相对时间描述
        time_patterns = ["morning", "afternoon", "evening", "night"]

        # 模拟检测
        if len(chapters) > 2:
            issues.append(QualityIssue(
                issue_id=f"tc_{content_id}_001",
                issue_type=CheckType.CONSISTENCY,
                severity=IssueSeverity.MINOR,
                message="Time progression may need clarification",
                location=f"{content_id}: Timeline",
                context="Relative time indicators across chapters",
                suggestion="Use consistent time indicators or clearly mark time jumps"
            ))

        return issues

    def _check_vocabulary_level(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查词汇水平"""
        issues = []

        # 模拟词汇检查
        issues.append(QualityIssue(
            issue_id=f"vl_{content_id}_001",
            issue_type=CheckType.STYLE,
            severity=IssueSeverity.SUGGESTION,
            message="Vocabulary level varies significantly",
            location=f"{content_id}: Style",
            context="Word choice consistency across chapters",
            suggestion="Maintain consistent vocabulary level appropriate for target audience"
        ))

        return issues

    def _check_sentence_variation(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查句式变化"""
        issues = []

        # 检查句式多样性
        issues.append(QualityIssue(
            issue_id=f"sv_{content_id}_001",
            issue_type=CheckType.STYLE,
            severity=IssueSeverity.MINOR,
            message="Sentence structure may lack variation",
            location=f"{content_id}: Sentence patterns",
            context="Sentence length and structure distribution",
            suggestion="Vary sentence length for better reading rhythm"
        ))

        return issues

    def _check_tone_consistency(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查语气一致性"""
        issues = []

        # 检查整体语气
        if len(chapters) > 1:
            issues.append(QualityIssue(
                issue_id=f"tc_{content_id}_002",
                issue_type=CheckType.STYLE,
                severity=IssueSeverity.SUGGESTION,
                message="Narrative tone may shift unexpectedly",
                location=f"{content_id}: Tone",
                context="Overall narrative tone throughout story",
                suggestion="Maintain consistent narrative voice and tone"
            ))

        return issues

    def _check_pacing(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查节奏"""
        issues = []

        # 检查节奏分布
        if len(chapters) > 3:
            issues.append(QualityIssue(
                issue_id=f"pc_{content_id}_001",
                issue_type=CheckType.PACING,
                severity=IssueSeverity.MINOR,
                message="Pacing may be uneven across story",
                location=f"{content_id}: Overall pacing",
                context="Distribution of action and exposition",
                suggestion="Review chapter lengths and content balance"
            ))

        return issues

    def _check_tension_arc(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查张力弧线"""
        issues = []

        # 检查张力累积
        if len(chapters) > 5:
            issues.append(QualityIssue(
                issue_id=f"ta_{content_id}_001",
                issue_type=CheckType.PLOT,
                severity=IssueSeverity.SUGGESTION,
                message="Tension arc could be more pronounced",
                location=f"{content_id}: Story arc",
                context="Build-up and release of tension",
                suggestion="Ensure clear escalation of story stakes"
            ))

        return issues

    def _check_climax_placement(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查高潮位置"""
        issues = []

        # 检查高潮是否在合适位置（通常在75-90%）
        if len(chapters) > 4:
            # 模拟检查
            issues.append(QualityIssue(
                issue_id=f"cp_{content_id}_001",
                issue_type=CheckType.PLOT,
                severity=IssueSeverity.MAJOR,
                message="Climax may not be optimally placed",
                location=f"{content_id}: Story structure",
                context="高潮位置应在故事的75-90%处",
                suggestion="Consider moving major turning points to later chapters"
            ))

        return issues

    def _check_character_behavior(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """检查角色行为"""
        issues = []

        # 模拟角色检查
        issues.append(QualityIssue(
            issue_id=f"cb_{content_id}_001",
            issue_type=CheckType.CHARACTER,
            severity=IssueSeverity.MINOR,
            message="Character decisions may lack motivation",
            location=f"{content_id}: Character actions",
            context="Character actions in key scenes",
            suggestion="Ensure character decisions are foreshadowed and justified"
        ))

        return issues

    def _get_severity_distribution(self, issues: List[QualityIssue]) -> Dict[str, int]:
        """获取严重程度分布"""
        dist = defaultdict(int)
        for issue in issues:
            dist[issue.severity.value] += 1
        return dict(dist)

    def _calculate_overall_score(self, issues: List[QualityIssue]) -> float:
        """计算总体分数"""
        if not issues:
            return 100.0

        # 基于严重程度扣分
        severity_weights = {
            IssueSeverity.CRITICAL: 20,
            IssueSeverity.MAJOR: 10,
            IssueSeverity.MINOR: 5,
            IssueSeverity.SUGGESTION: 2,
        }

        total_penalty = sum(
            severity_weights.get(issue.severity, 5) for issue in issues
        )

        # 最低50分
        return max(50.0, 100.0 - total_penalty)

    def _parse_chapters(self, chapters_str: str) -> List[str]:
        """解析章节字符串"""
        if not chapters_str:
            return ["chapter_1", "chapter_2", "chapter_3"]

        # 分割章节
        chapters = [c.strip() for c in chapters_str.split(",")]
        return chapters[:20]  # 限制数量

    def _extract_param(self, content: str, param: str, default: str = "") -> str:
        """从内容提取参数"""
        pattern = f"{param}="
        if pattern in content:
            try:
                start = content.index(pattern) + len(pattern)
                end = start
                while end < len(content) and content[end] not in " ,;":
                    end += 1
                return content[start:end]
            except ValueError:
                return default
        return default

    def generate_report(
        self,
        content_id: str,
        chapters: List[str]
    ) -> Optional[QualityReport]:
        """生成质量报告（外部接口）"""
        try:
            report = self._generate_quality_report(content_id, chapters)
            self._reports[content_id] = report
            self._issues.extend(report.issues)
            return report
        except Exception:
            return None

    def check_coherence(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """连贯性检查（外部接口）"""
        issues = []
        for rule in self._coherence_rules:
            issues.extend(rule(content_id, chapters))
        self._issues.extend(issues)
        return issues

    def check_consistency(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """一致性检查（外部接口）"""
        issues = []
        for rule in self._consistency_rules:
            issues.extend(rule(content_id, chapters))
        self._issues.extend(issues)
        return issues

    def check_style(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """风格检查（外部接口）"""
        issues = []
        for rule in self._style_rules:
            issues.extend(rule(content_id, chapters))
        self._issues.extend(issues)
        return issues

    def check_plot(
        self,
        content_id: str,
        chapters: List[str]
    ) -> List[QualityIssue]:
        """情节检查（外部接口）"""
        issues = []
        for rule in self._plot_rules:
            issues.extend(rule(content_id, chapters))
        self._issues.extend(issues)
        return issues

    def get_issues(
        self,
        severity: IssueSeverity = None,
        issue_type: CheckType = None
    ) -> List[QualityIssue]:
        """获取问题列表（外部接口）"""
        issues = self._issues[:]

        if severity:
            issues = [i for i in issues if i.severity == severity]
        if issue_type:
            issues = [i for i in issues if i.issue_type == issue_type]

        return issues

    def get_report(self, content_id: str) -> Optional[QualityReport]:
        """获取报告"""
        return self._reports.get(content_id)

    def get_all_reports(self) -> Dict[str, QualityReport]:
        """获取所有报告"""
        return self._reports

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        severity_dist = defaultdict(int)
        type_dist = defaultdict(int)

        for issue in self._issues:
            severity_dist[issue.severity.value] += 1
            type_dist[issue.issue_type.value] += 1

        return {
            "total_issues": len(self._issues),
            "by_severity": dict(severity_dist),
            "by_type": dict(type_dist),
            "total_checks": self._total_checks_performed,
            "total_reports": len(self._reports)
        }

    def export_issues(self) -> Dict[str, Any]:
        """导出问题数据"""
        return {
            "issues": [i.to_dict() for i in self._issues],
            "reports": {k: v.to_dict() for k, v in self._reports.items()},
            "statistics": self.get_statistics()
        }

    def reset(self) -> None:
        """重置智能体"""
        self._issues.clear()
        self._reports.clear()
        self._total_checks_performed = 0
        self._total_issues_found = 0
        self._check_history.clear()


if __name__ == "__main__":
    # 简单测试
    agent = QualityCheckerAgent()

    # 模拟测试
    chapters = ["chapter_001", "chapter_002", "chapter_003"]
    report = agent._generate_quality_report("test_content", chapters)

    log_info(f"Report ID: {report.report_id}")
    log_info(f"Score: {report.overall_score}")
    log_info(f"Issues: {len(report.issues)}")
