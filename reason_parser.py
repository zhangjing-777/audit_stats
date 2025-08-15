"""
违规原因解析器模块
负责解析reason字段中的违规类型信息
支持用户自定义违规类型分类
"""

import re
import logging
from typing import List, Dict, Set, Optional, Union
from collections import defaultdict, Counter
import jieba
from dataclasses import dataclass
import json
import os

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
    
    def __init__(self, custom_patterns: Optional[Dict[str, List[str]]] = None):
        """初始化解析器
        
        Args:
            custom_patterns: 用户自定义的违规模式字典，格式与 VIOLATION_PATTERNS 相同
                           如果提供，将替换默认的违规模式
        """
        # 使用用户自定义模式或默认模式
        self.violation_patterns = custom_patterns if custom_patterns is not None else VIOLATION_PATTERNS.copy()
        self.default_patterns = VIOLATION_PATTERNS.copy()  # 保存默认模式用于重置
        self.is_using_custom_patterns = custom_patterns is not None
        self.violation_cache = {}
        self._init_jieba()
        
        logger.info(f"违规原因解析器初始化完成，使用{'自定义' if self.is_using_custom_patterns else '默认'}违规模式")
        logger.info(f"当前违规类型: {list(self.violation_patterns.keys())}")
    
    def set_custom_patterns(self, custom_patterns: Dict[str, List[str]]) -> bool:
        """设置自定义违规模式
        
        Args:
            custom_patterns: 自定义违规模式字典
            
        Returns:
            设置是否成功
        """
        try:
            if not isinstance(custom_patterns, dict):
                raise ValueError("自定义模式必须是字典格式")
            
            # 验证模式格式
            for violation_type, patterns in custom_patterns.items():
                if not isinstance(violation_type, str) or not violation_type.strip():
                    raise ValueError(f"违规类型必须是非空字符串: {violation_type}")
                
                if not isinstance(patterns, list):
                    raise ValueError(f"违规模式必须是列表格式: {violation_type}")
                
                for pattern in patterns:
                    if not isinstance(pattern, str):
                        raise ValueError(f"违规模式必须是字符串: {pattern}")
                    
                    # 验证正则表达式是否有效
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        raise ValueError(f"无效的正则表达式 '{pattern}': {e}")
            
            # 设置新的模式
            self.violation_patterns = custom_patterns.copy()
            self.is_using_custom_patterns = True
            
            # 清空缓存，因为模式已更改
            self.clear_cache()
            
            # 重新初始化jieba（添加新的自定义词）
            self._init_jieba()
            
            logger.info(f"成功设置自定义违规模式，包含 {len(custom_patterns)} 个违规类型")
            logger.info(f"新的违规类型: {list(custom_patterns.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"设置自定义违规模式失败: {e}")
            return False
    
    def add_violation_type(self, violation_type: str, patterns: List[str], description: str = None) -> bool:
        """添加新的违规类型
        
        Args:
            violation_type: 违规类型名称
            patterns: 匹配模式列表
            description: 类型描述（可选）
            
        Returns:
            添加是否成功
        """
        try:
            if not isinstance(violation_type, str) or not violation_type.strip():
                raise ValueError("违规类型必须是非空字符串")
            
            if not isinstance(patterns, list) or not patterns:
                raise ValueError("违规模式必须是非空列表")
            
            # 验证正则表达式
            for pattern in patterns:
                if not isinstance(pattern, str):
                    raise ValueError(f"违规模式必须是字符串: {pattern}")
                try:
                    re.compile(pattern)
                except re.error as e:
                    raise ValueError(f"无效的正则表达式 '{pattern}': {e}")
            
            # 添加违规类型
            self.violation_patterns[violation_type] = patterns.copy()
            self.is_using_custom_patterns = True
            
            # 添加到jieba词典
            jieba.add_word(violation_type)
            for pattern in patterns:
                # 提取模式中的关键词添加到jieba
                keywords = self._extract_keywords_from_pattern(pattern)
                for keyword in keywords:
                    jieba.add_word(keyword)
            
            # 如果提供了描述，添加到内部描述映射中
            if description:
                if not hasattr(self, '_custom_descriptions'):
                    self._custom_descriptions = {}
                self._custom_descriptions[violation_type] = description
            
            # 清空缓存
            self.clear_cache()
            
            logger.info(f"成功添加违规类型: {violation_type}，包含 {len(patterns)} 个模式")
            return True
            
        except Exception as e:
            logger.error(f"添加违规类型失败: {e}")
            return False
    
    def remove_violation_type(self, violation_type: str) -> bool:
        """移除违规类型
        
        Args:
            violation_type: 要移除的违规类型
            
        Returns:
            移除是否成功
        """
        try:
            if violation_type not in self.violation_patterns:
                logger.warning(f"违规类型不存在: {violation_type}")
                return False
            
            del self.violation_patterns[violation_type]
            
            # 移除自定义描述
            if hasattr(self, '_custom_descriptions') and violation_type in self._custom_descriptions:
                del self._custom_descriptions[violation_type]
            
            # 清空缓存
            self.clear_cache()
            
            logger.info(f"成功移除违规类型: {violation_type}")
            return True
            
        except Exception as e:
            logger.error(f"移除违规类型失败: {e}")
            return False
    
    def update_violation_patterns(self, violation_type: str, patterns: List[str]) -> bool:
        """更新指定违规类型的模式
        
        Args:
            violation_type: 违规类型
            patterns: 新的模式列表
            
        Returns:
            更新是否成功
        """
        try:
            if violation_type not in self.violation_patterns:
                logger.warning(f"违规类型不存在: {violation_type}")
                return False
            
            # 验证新模式
            for pattern in patterns:
                if not isinstance(pattern, str):
                    raise ValueError(f"违规模式必须是字符串: {pattern}")
                try:
                    re.compile(pattern)
                except re.error as e:
                    raise ValueError(f"无效的正则表达式 '{pattern}': {e}")
            
            # 更新模式
            self.violation_patterns[violation_type] = patterns.copy()
            self.is_using_custom_patterns = True
            
            # 清空缓存
            self.clear_cache()
            
            logger.info(f"成功更新违规类型 {violation_type} 的模式，包含 {len(patterns)} 个模式")
            return True
            
        except Exception as e:
            logger.error(f"更新违规模式失败: {e}")
            return False
    
    def reset_to_default_patterns(self):
        """重置为默认违规模式"""
        self.violation_patterns = self.default_patterns.copy()
        self.is_using_custom_patterns = False
        
        # 清除自定义描述
        if hasattr(self, '_custom_descriptions'):
            self._custom_descriptions = {}
        
        # 清空缓存
        self.clear_cache()
        
        # 重新初始化jieba
        self._init_jieba()
        
        logger.info("已重置为默认违规模式")
    
    def get_current_patterns(self) -> Dict[str, List[str]]:
        """获取当前使用的违规模式
        
        Returns:
            当前违规模式字典
        """
        return self.violation_patterns.copy()
    
    def get_pattern_info(self) -> Dict[str, any]:
        """获取模式信息
        
        Returns:
            模式信息字典
        """
        return {
            'is_using_custom_patterns': self.is_using_custom_patterns,
            'total_violation_types': len(self.violation_patterns),
            'violation_types': list(self.violation_patterns.keys()),
            'pattern_counts': {vtype: len(patterns) for vtype, patterns in self.violation_patterns.items()},
            'cache_stats': self.get_cache_stats()
        }
    
    def save_custom_patterns(self, filepath: str) -> bool:
        """保存自定义模式到文件
        
        Args:
            filepath: 保存路径
            
        Returns:
            保存是否成功
        """
        try:
            pattern_data = {
                'patterns': self.violation_patterns,
                'descriptions': getattr(self, '_custom_descriptions', {}),
                'is_custom': self.is_using_custom_patterns,
                'created_at': str(logger.info("当前时间")),  # 简化时间戳
                'version': '1.0'
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(pattern_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存自定义模式到: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"保存自定义模式失败: {e}")
            return False
    
    def load_custom_patterns(self, filepath: str) -> bool:
        """从文件加载自定义模式
        
        Args:
            filepath: 文件路径
            
        Returns:
            加载是否成功
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"文件不存在: {filepath}")
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                pattern_data = json.load(f)
            
            # 验证数据格式
            if 'patterns' not in pattern_data:
                raise ValueError("文件格式错误：缺少 patterns 字段")
            
            # 设置模式
            if self.set_custom_patterns(pattern_data['patterns']):
                # 加载描述信息
                if 'descriptions' in pattern_data:
                    self._custom_descriptions = pattern_data['descriptions']
                
                logger.info(f"成功从文件加载自定义模式: {filepath}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"加载自定义模式失败: {e}")
            return False
    
    def _extract_keywords_from_pattern(self, pattern: str) -> List[str]:
        """从正则表达式模式中提取关键词"""
        keywords = []
        
        # 简单的关键词提取：移除正则特殊字符
        cleaned = re.sub(r'[.*+?^${}()|[\]\\]', '', pattern)
        
        # 按常见分隔符分割
        parts = re.split(r'[、，,\s]+', cleaned)
        
        for part in parts:
            part = part.strip()
            if len(part) >= 2:  # 只保留长度大于等于2的词
                keywords.append(part)
        
        return keywords
    
    def _init_jieba(self):
        """初始化jieba分词器"""
        try:
            # 添加默认自定义词典
            default_words = [
                '涉黄', '涉政', '涉恐', '恶意辱骂', '虚假诈骗',
                '广告推广', '违禁词', '舆情极端', '黑名单词', '地图问题',
                '夜场招聘', '成人交友', '政治敏感', '台湾独立', '港独',
                '六四', '八九', '法轮大法', '暴力', '危险现场', '恐怖组织',
                '制造装置', '爆炸', '辱骂', '诈骗', '中奖', '转账',
                '投资理财', '零风险', '限时秒杀', '立即抢购', '全网最低价',
                '白粉批发', '军用枪械', '枪支', '毒品', '违禁物品',
                '社会不公', '民不聊生', '推翻暴政', '极端情绪'
            ]
            
            for word in default_words:
                jieba.add_word(word)
            
            # 添加当前违规类型到词典
            for violation_type in self.violation_patterns.keys():
                jieba.add_word(violation_type)
            
            # 从当前模式中提取关键词
            for patterns in self.violation_patterns.values():
                for pattern in patterns:
                    keywords = self._extract_keywords_from_pattern(pattern)
                    for keyword in keywords:
                        jieba.add_word(keyword)
            
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
        
        # 动态生成关键词映射表
        keyword_mapping = {}
        
        # 如果使用默认模式，使用预定义的关键词映射
        if not self.is_using_custom_patterns:
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
        else:
            # 为自定义模式动态生成关键词映射
            for violation_type, patterns in self.violation_patterns.items():
                keywords = []
                for pattern in patterns:
                    keywords.extend(self._extract_keywords_from_pattern(pattern))
                if keywords:
                    keyword_mapping[violation_type] = list(set(keywords))
        
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
        
        # 动态生成语义模式
        semantic_patterns = {}
        
        if not self.is_using_custom_patterns:
            # 使用默认语义模式
            semantic_patterns = {
                '涉黄': ['招聘.*?美女', '交友.*?刺激', '私聊.*?微信'],
                '涉政': ['推翻.*?政权', '政府.*?腐败', '人民.*?反抗'],
                '涉恐': ['制造.*?装置', '恐怖.*?组织', '暴力.*?袭击'],
                '虚假诈骗': ['中奖.*?万', '零风险.*?高回报', '转账.*?手续费'],
                '广告推广': ['限时.*?秒杀', '全网.*?最低价', '立即.*?抢购']
            }
        else:
            # 为自定义模式生成语义模式（使用原始模式的子集）
            for violation_type, patterns in self.violation_patterns.items():
                # 选择包含.*?的模式作为语义模式
                semantic_patterns[violation_type] = [p for p in patterns if '.*?' in p]
        
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
        # 首先检查自定义描述
        if hasattr(self, '_custom_descriptions') and violation_type in self._custom_descriptions:
            return self._custom_descriptions[violation_type]
        
        # 使用默认描述
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
        
        return descriptions.get(violation_type, f'自定义违规类型: {violation_type}')
    
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
            'violation_rate': len([t for t in reason_texts if self.parse_reason(t)]) / len(reason_texts) if reason_texts else 0,
            'pattern_info': self.get_pattern_info()  # 添加模式信息
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
        tips = [
            "考虑添加更多特定领域的关键词",
            "优化正则表达式模式以提高匹配准确性",
            "增加语义分析能力以处理复杂表达",
            "定期更新违规模式库以适应新的违规形式"
        ]
        
        if self.is_using_custom_patterns:
            tips.extend([
                "验证自定义模式的匹配效果",
                "考虑为新的违规类型添加描述信息",
                "定期保存自定义模式配置"
            ])
        
        suggestions['optimization_tips'] = tips
        
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

def create_reason_parser(custom_patterns: Optional[Dict[str, List[str]]] = None) -> ReasonParser:
    """创建违规原因解析器实例
    
    Args:
        custom_patterns: 可选的自定义违规模式
        
    Returns:
        ReasonParser实例
    """
    return ReasonParser(custom_patterns)

def test_reason_parser():
    """测试违规原因解析器"""
    logger.info("开始测试违规原因解析器")
    
    # 测试默认模式
    parser = create_reason_parser()
    logger.info("=== 测试默认模式 ===")
    
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
    
    # 测试自定义模式
    logger.info("=== 测试自定义模式 ===")
    
    # 定义自定义违规模式
    custom_patterns = {
        '网络暴力': [
            r'网络.*?暴力', r'恶意.*?攻击', r'人肉.*?搜索', r'恶意.*?传播',
            r'造谣.*?传谣', r'网络.*?霸凌', r'恶意.*?骚扰'
        ],
        '版权侵犯': [
            r'盗版', r'侵权', r'非法.*?复制', r'未经.*?授权', 
            r'盗用.*?作品', r'抄袭', r'剽窃'
        ],
        '金融风险': [
            r'非法.*?集资', r'庞氏.*?骗局', r'传销', r'非法.*?放贷',
            r'高利贷', r'洗钱', r'非法.*?融资'
        ],
        '食品安全': [
            r'有毒.*?食品', r'过期.*?食品', r'三无.*?产品', r'食品.*?添加剂',
            r'地沟油', r'食物.*?中毒', r'不合格.*?食品'
        ]
    }
    
    # 创建使用自定义模式的解析器
    custom_parser = create_reason_parser(custom_patterns)
    
    # 自定义模式测试用例
    custom_test_cases = [
        "该用户在网络上恶意传播他人隐私信息，进行人肉搜索",
        "发布的视频内容涉嫌盗版，未经版权方授权擅自使用",
        "推广非法集资项目，涉嫌庞氏骗局欺骗投资者",
        "销售过期食品，存在严重的食品安全隐患",
        "这是一个正常的内容，不应该匹配任何违规类型"
    ]
    
    for i, text in enumerate(custom_test_cases, 1):
        violations = custom_parser.parse_reason(text)
        details = custom_parser.extract_violation_details(text)
        
        logger.info(f"自定义测试用例 {i}:")
        logger.info(f"  文本: {text}")
        logger.info(f"  违规类型: {violations}")
        logger.info(f"  详细信息: {[f'{d.type}({d.confidence:.2f})' for d in details]}")
        print()
    
    # 测试动态添加违规类型
    logger.info("=== 测试动态添加违规类型 ===")
    
    success = custom_parser.add_violation_type(
        '环境污染', 
        [r'环境.*?污染', r'排放.*?废料', r'破坏.*?生态', r'污染.*?环境'],
        '涉及环境污染、生态破坏等内容'
    )
    
    if success:
        test_text = "该工厂非法排放废料，严重污染环境"
        violations = custom_parser.parse_reason(test_text)
        logger.info(f"添加新类型后测试: '{test_text}' -> {violations}")
    
    # 测试模式信息获取
    logger.info("=== 模式信息 ===")
    pattern_info = custom_parser.get_pattern_info()
    logger.info(f"模式信息: {pattern_info}")
    
    # 测试统计功能
    logger.info("=== 统计测试 ===")
    all_test_texts = test_cases + custom_test_cases + [test_text]
    stats = custom_parser.get_violation_statistics(all_test_texts)
    logger.info(f"统计结果: {stats}")
    
    # 测试改进建议
    suggestions = custom_parser.suggest_improvements(all_test_texts)
    logger.info(f"改进建议: {suggestions}")
    
    # 测试保存和加载
    logger.info("=== 测试保存和加载 ===")
    
    # 保存自定义模式
    if custom_parser.save_custom_patterns('test_patterns.json'):
        logger.info("自定义模式保存成功")
        
        # 创建新的解析器并加载模式
        new_parser = create_reason_parser()
        if new_parser.load_custom_patterns('test_patterns.json'):
            logger.info("自定义模式加载成功")
            
            # 验证加载的模式
            loaded_patterns = new_parser.get_current_patterns()
            logger.info(f"加载的模式包含 {len(loaded_patterns)} 个违规类型")
        else:
            logger.error("自定义模式加载失败")
    else:
        logger.error("自定义模式保存失败")
    
    # 测试重置为默认模式
    logger.info("=== 测试重置为默认模式 ===")
    custom_parser.reset_to_default_patterns()
    reset_info = custom_parser.get_pattern_info()
    logger.info(f"重置后模式信息: {reset_info}")
    
    logger.info("违规原因解析器测试完成")

if __name__ == "__main__":
    test_reason_parser()