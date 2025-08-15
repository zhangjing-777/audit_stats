
"""
违规原因解析器模块
负责解析reason字段中的违规类型信息
"""

import re
import logging
from typing import List, Dict, Set, Optional
from collections import defaultdict, Counter
import jieba
from dataclasses import dataclass

from config import VIOLATION_PATTERNS

logger = logging.getLogger(__name__)

@dataclass
class ViolationInfo:
    """违规信息数据类"""
    type: str
    description: str
    count: int = 0
    confidence: float = 0.0
    evidence: Optional[str] = None

class ReasonParser:
    """违规原因解析器"""
    
    def __init__(self):
        """初始化解析器"""
        self.violation_patterns = VIOLATION_PATTERNS
        self.violation_cache = {}
        self._init_jieba()
        logger.info("违规原因解析器初始化完成")
    
    def _init_jieba(self):
        """初始化jieba分词器"""
        try:
            # 添加自定义词典
            custom_words = [
                '涉黄', '涉政', '涉恐', '恶意辱骂', '虚假诈骗',
                '广告推广', '违禁词', '舆情极端', '黑名单词', '地图问题',
                '夜场招聘', '成人交友', '政治敏感', '台湾独立', '港独',
                '六四', '八九', '法轮大法', '暴力', '危险现场', '恐怖组织',
                '制造装置', '爆炸', '辱骂', '诈骗', '中奖', '转账',
                '投资理财', '零风险', '限时秒杀', '立即抢购', '全网最低价',
                '白粉批发', '军用枪械', '枪支', '毒品', '违禁物品',
                '社会不公', '民不聊生', '推翻暴政', '极端情绪'
            ]
            
            for word in custom_words:
                jieba.add_word(word)
            
            logger.debug("jieba分词器初始化完成，添加自定义词典")
        except Exception as e:
            logger.warning(f"jieba初始化失败: {e}")
    
    def parse_reason(self, reason_text: str) -> List[str]:
        """解析违规原因文本，返回违规类型列表
        
        Args:
            reason_text: 违规原因文本
            
        Returns:
            违规类型列表
        """
        if not reason_text or not reason_text.strip():
            return []
        
        # 使用缓存提高性能
        cache_key = hash(reason_text)
        if cache_key in self.violation_cache:
            return self.violation_cache[cache_key]
        
        violations = set()
        reason_lower = reason_text.lower()
        
        # 基于正则表达式的模式匹配
        for violation_type, patterns in self.violation_patterns.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, reason_text, re.IGNORECASE):
                        violations.add(violation_type)
                        break  # 找到一个匹配就跳出内层循环
                except re.error as e:
                    logger.warning(f"正则表达式错误: {pattern}, 错误: {e}")
        
        # 基于关键词的补充匹配
        violations.update(self._keyword_matching(reason_text))
        
        # 基于语义的匹配（简单版本）
        violations.update(self._semantic_matching(reason_text))
        
        result = list(violations)
        
        # 缓存结果
        self.violation_cache[cache_key] = result
        
        logger.debug(f"解析违规原因完成: '{reason_text[:50]}...' -> {result}")
        return result
    
    def _keyword_matching(self, text: str) -> Set[str]:
        """基于关键词的匹配"""
        violations = set()
        
        # 关键词映射表
        keyword_mapping = {
            '涉黄': ['色情', '黄色', '性感', '诱惑', '裸体', '暴露', '成人', '情色'],
            '涉政': ['政治', '政府', '官员', '党', '选举', '民主', '独立', '抗议'],
            '涉恐': ['恐怖', '暴力', '袭击', '爆炸', '武器', '杀害', '血腥'],
            '恶意辱骂': ['骂', '侮辱', '羞辱', '诽谤', '恶毒', '诅咒'],
            '虚假诈骗': ['诈骗', '欺骗', '虚假', '假冒', '伪造', '骗取'],
            '广告推广': ['广告', '推广', '营销', '促销', '优惠', '折扣'],
            '违禁词': ['毒品', '枪支', '军火', '违禁', '管制'],
            '舆情极端': ['极端', '激进', '偏激', '煽动', '仇恨'],
            '黑名单词': ['分裂', '颠覆', '反动', '邪教'],
            '地图问题': ['地图', '边界', '领土', '主权']
        }
        
        # 使用jieba进行分词
        try:
            words = jieba.lcut(text)
            word_set = set(word.lower() for word in words)
            
            for violation_type, keywords in keyword_mapping.items():
                for keyword in keywords:
                    if keyword in text.lower() or keyword in word_set:
                        violations.add(violation_type)
                        break
        except Exception as e:
            logger.warning(f"关键词匹配失败: {e}")
        
        return violations
    
    def _semantic_matching(self, text: str) -> Set[str]:
        """基于语义的匹配（简化版本）"""
        violations = set()
        
        # 语义模式匹配
        semantic_patterns = {
            '涉黄': ['招聘.*?美女', '交友.*?刺激', '私聊.*?微信'],
            '涉政': ['推翻.*?政权', '政府.*?腐败', '人民.*?反抗'],
            '涉恐': ['制造.*?装置', '恐怖.*?组织', '暴力.*?袭击'],
            '虚假诈骗': ['中奖.*?万', '零风险.*?高回报', '转账.*?手续费'],
            '广告推广': ['限时.*?秒杀', '全网.*?最低价', '立即.*?抢购']
        }
        
        for violation_type, patterns in semantic_patterns.items():
            for pattern in patterns:
                try:
                    if re.search(pattern, text, re.IGNORECASE):
                        violations.add(violation_type)
                        break
                except re.error as e:
                    logger.warning(f"语义模式匹配错误: {pattern}, 错误: {e}")
        
        return violations
    
    def extract_violation_details(self, reason_text: str) -> List[ViolationInfo]:
        """提取详细的违规信息
        
        Args:
            reason_text: 违规原因文本
            
        Returns:
            违规信息列表
        """
        if not reason_text:
            return []
        
        violations = self.parse_reason(reason_text)
        violation_details = []
        
        for violation_type in violations:
            # 计算该违规类型在文本中的置信度
            confidence = self._calculate_confidence(reason_text, violation_type)
            
            # 提取相关证据文本
            evidence = self._extract_evidence(reason_text, violation_type)
            
            violation_info = ViolationInfo(
                type=violation_type,
                description=self._get_violation_description(violation_type),
                count=1,
                confidence=confidence,
                evidence=evidence
            )
            
            violation_details.append(violation_info)
        
        return violation_details
    
    def _calculate_confidence(self, text: str, violation_type: str) -> float:
        """计算违规类型的置信度"""
        if violation_type not in self.violation_patterns:
            return 0.0
        
        patterns = self.violation_patterns[violation_type]
        matches = 0
        
        for pattern in patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    matches += 1
            except re.error:
                continue
        
        # 简单的置信度计算：匹配的模式数 / 总模式数
        confidence = min(matches / len(patterns) * 2, 1.0)  # 乘以2增加敏感度，最大为1
        return confidence
    
    def _extract_evidence(self, text: str, violation_type: str) -> str:
        """提取违规证据文本"""
        if violation_type not in self.violation_patterns:
            return ""
        
        patterns = self.violation_patterns[violation_type]
        evidence_parts = []
        
        for pattern in patterns:
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # 提取匹配周围的上下文
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].strip()
                    if context and context not in evidence_parts:
                        evidence_parts.append(context)
            except re.error:
                continue
        
        return " | ".join(evidence_parts[:3])  # 最多返回3个证据片段
    
    def _get_violation_description(self, violation_type: str) -> str:
        """获取违规类型的描述"""
        descriptions = {
            '涉黄': '包含色情、低俗、性暗示等不当内容',
            '涉政': '包含政治敏感、分裂国家等内容',
            '涉恐': '包含暴力、恐怖主义、危险行为等内容',
            '恶意辱骂': '包含人身攻击、恶意辱骂等内容',
            '虚假诈骗': '包含虚假信息、诈骗、误导性宣传等内容',
            '广告推广': '包含商业广告、营销推广等内容',
            '违禁词': '包含违禁物品、管制物品等内容',
            '舆情极端': '包含极端言论、煽动性内容等',
            '黑名单词': '包含敏感词汇、禁用词语等内容',
            '地图问题': '包含错误地图信息、领土争议等内容'
        }
        
        return descriptions.get(violation_type, '未知违规类型')
    
    def get_violation_statistics(self, reason_texts: List[str]) -> Dict[str, Dict[str, int]]:
        """获取违规统计信息
        
        Args:
            reason_texts: 违规原因文本列表
            
        Returns:
            违规统计字典
        """
        violation_counter = Counter()
        pattern_counter = defaultdict(Counter)
        
        for text in reason_texts:
            if not text:
                continue
            
            violations = self.parse_reason(text)
            for violation in violations:
                violation_counter[violation] += 1
                
                # 统计匹配的具体模式
                if violation in self.violation_patterns:
                    for pattern in self.violation_patterns[violation]:
                        try:
                            if re.search(pattern, text, re.IGNORECASE):
                                pattern_counter[violation][pattern] += 1
                        except re.error:
                            continue
        
        # 构建统计结果
        statistics = {
            'violation_counts': dict(violation_counter),
            'pattern_matches': {vtype: dict(patterns) for vtype, patterns in pattern_counter.items()},
            'total_texts': len(reason_texts),
            'violation_rate': len([t for t in reason_texts if self.parse_reason(t)]) / len(reason_texts) if reason_texts else 0
        }
        
        return statistics
    
    def suggest_improvements(self, reason_texts: List[str]) -> Dict[str, List[str]]:
        """根据解析结果建议改进
        
        Args:
            reason_texts: 违规原因文本列表
            
        Returns:
            改进建议字典
        """
        suggestions = {
            'low_confidence_patterns': [],
            'missing_patterns': [],
            'optimization_tips': []
        }
        
        # 分析低置信度的文本
        low_confidence_texts = []
        for text in reason_texts:
            if text:
                violations = self.extract_violation_details(text)
                if violations and any(v.confidence < 0.5 for v in violations):
                    low_confidence_texts.append(text)
        
        if low_confidence_texts:
            suggestions['low_confidence_patterns'] = low_confidence_texts[:5]  # 前5个示例
        
        # 分析可能遗漏的模式
        unmatched_texts = [text for text in reason_texts if text and not self.parse_reason(text)]
        if unmatched_texts:
            suggestions['missing_patterns'] = unmatched_texts[:5]  # 前5个示例
        
        # 提供优化建议
        suggestions['optimization_tips'] = [
            "考虑添加更多特定领域的关键词",
            "优化正则表达式模式以提高匹配准确性",
            "增加语义分析能力以处理复杂表达",
            "定期更新违规模式库以适应新的违规形式"
        ]
        
        return suggestions
    
    def clear_cache(self):
        """清空解析缓存"""
        self.violation_cache.clear()
        logger.info("违规解析缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self.violation_cache),
            'cache_hit_rate': getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_attempts', 1), 1)
        }

def create_reason_parser() -> ReasonParser:
    """创建违规原因解析器实例"""
    return ReasonParser()

def test_reason_parser():
    """测试违规原因解析器"""
    logger.info("开始测试违规原因解析器")
    
    parser = create_reason_parser()
    
    # 测试用例
    test_cases = [
        "内容展示平台展示各类涉黄、涉政、涉恐内容",
        "夜场招聘，高薪兼职，美女优先，有意者私聊微信",
        "政府腐败无能，人民要自己站起来推翻暴政",
        "制造爆炸装置的详细教程，复仇计划即将开始",
        "你就是个废物，全家都不得好死，垃圾东西",
        "恭喜您中奖500万，请立即转账手续费激活奖金",
        "独家秘籍！限时秒杀！错过再等一年！立即抢购",
        "高纯度白粉批发，货源稳定，支持全国发货",
        "社会不公，民不聊生，是时候起来反抗了",
        "台湾独立万岁，自由民主的台湾国"
    ]
    
    for i, text in enumerate(test_cases, 1):
        violations = parser.parse_reason(text)
        details = parser.extract_violation_details(text)
        
        logger.info(f"测试用例 {i}:")
        logger.info(f"  文本: {text}")
        logger.info(f"  违规类型: {violations}")
        logger.info(f"  详细信息: {[f'{d.type}({d.confidence:.2f})' for d in details]}")
        print()
    
    # 测试统计功能
    stats = parser.get_violation_statistics(test_cases)
    logger.info(f"统计结果: {stats}")
    
    # 测试改进建议
    suggestions = parser.suggest_improvements(test_cases)
    logger.info(f"改进建议: {suggestions}")
    
    logger.info("违规原因解析器测试完成")

if __name__ == "__main__":
    test_reason_parser()