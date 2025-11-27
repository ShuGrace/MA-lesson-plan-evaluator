# app/utils/evaluation_helpers.py
"""
Evaluation Helper Functions - Framework v3.0
评估辅助函数

✅ v3.0 Updates:
- Added support for 'lesson_design' score extraction
- Updated to handle 4 dimensions (PBL, CRMP, CP, LDQ)
- Improved score extraction patterns
"""
import re
import json
from typing import List, Dict, Any, Optional


def extract_score_from_response(response: str, score_type: str = "general") -> int:
    """
    从Agent响应中提取分数，将5分制转换为100分制
    
    ✅ Framework v3.0: Supports all 4 dimensions
    - place_based / place
    - cultural / cultural_responsiveness
    - critical / critical_pedagogy
    - design / lesson_design / lesson_design_quality  # ✅ v3.0 new
    
    Args:
        response: Agent的原始响应文本
        score_type: 分数类型（用于日志和特定模式匹配）
    
    Returns:
        int: 0-100的分数
    
    Examples:
        >>> extract_score_from_response("Overall Score: 4.5/5", "test")
        90
        >>> extract_score_from_response("Score: 3/5.0", "test")
        60
        >>> extract_score_from_response("Converted to 100-point scale: 85/100", "test")
        85
    """
    try:
        if not response or not isinstance(response, str):
            print(f"⚠️ Invalid response for {score_type}")
            return 0
        
        # ✅ v3.0: 扩展的模式列表（优先匹配已转换的100分制分数）
        patterns = [
            # 100-point scale patterns (highest priority)
            r'(?:overall|composite|final|total|integrated)\s*(?:score|rating)?\s*:?\s*(\d+)\s*(?:/\s*100)?',
            r'(?:convert(?:ed)?|scale|100-point)\s*(?:score|rating)?\s*:?\s*(\d+)\s*(?:/\s*100)?',
            r'\*\*(?:convert(?:ed)?|100-point)\s*(?:score|rating)?\*\*\s*:?\s*(\d+)',
            
            # Dimension-specific patterns (100-point)
            r'place[- ]?based\s+learning\s*:?\s*(\d+)\s*(?:/\s*100)?',
            r'cultural\s+responsiveness\s*(?:integrated)?\s*:?\s*(\d+)\s*(?:/\s*100)?',
            r'critical\s+pedagogy\s*:?\s*(\d+)\s*(?:/\s*100)?',
            r'lesson\s+design\s+quality\s*:?\s*(\d+)\s*(?:/\s*100)?',  # ✅ v3.0 new
            r'design\s+quality\s*:?\s*(\d+)\s*(?:/\s*100)?',  # ✅ v3.0 new
            
            # Generic 100-point patterns
            r'score\s*:?\s*(\d+)\s*(?:/\s*100)',
            r'rating\s*:?\s*(\d+)\s*(?:/\s*100)',
            
            # 5-point scale patterns (will be converted)
            r'overall.*?score\s*:?\s*(\d+\.?\d*)\s*/\s*5',
            r'score\s*:?\s*(\d+\.?\d*)\s*/\s*5',
            r'(\d+\.?\d*)\s*/\s*5\.0',
            r'(\d+\.?\d*)\s*/\s*5\s*(?:\)|$)',
            
            # Conversion calculation patterns
            r'(\d+\.?\d*)\s*/\s*5\.?0?\s*\*\s*100',
            r'\((\d+\.?\d*)\s*/\s*5\.?0?\s*\)\s*\*\s*100',
            
            # Fallback: any number followed by /100
            r'(\d+)\s*/\s*100'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    score_str = match.group(1)
                    score = float(score_str)
                    
                    # If score looks like it's on 5-point scale, convert
                    if score <= 5.0:
                        score = (score / 5.0) * 100
                    
                    # Clamp to valid range
                    score = max(0, min(100, int(round(score))))
                    
                    # Only return if score is reasonable (> 0)
                    if score > 0:
                        return score
                        
                except (ValueError, IndexError):
                    continue
        
        # If no score found, log and return 0
        print(f"⚠️ Could not extract {score_type} score from response")
        print(f"   Response preview: {response[:300]}...")
        return 0
        
    except Exception as e:
        print(f"❌ Error extracting {score_type} score: {e}")
        return 0


def extract_recommendations_from_response(response: str, max_recommendations: int = 10) -> List[str]:
    """
    从Agent响应中提取推荐建议
    
    Args:
        response: Agent的原始响应文本
        max_recommendations: 最多返回的推荐数量
    
    Returns:
        List[str]: 推荐建议列表
    
    Examples:
        >>> text = "Recommendations:\\n- Add local examples\\n- Include Te Reo Māori"
        >>> extract_recommendations_from_response(text)
        ['Add local examples', 'Include Te Reo Māori']
    """
    try:
        if not response or not isinstance(response, str):
            return []
        
        recommendations = []
        
        # Pattern 1: 查找 "Recommendations" 或 "Suggestions" 部分
        section_patterns = [
            r'recommendations?\s*(?:for\s+improvement)?:?\s*\n((?:[-•*\d].*\n?)+)',
            r'suggestions?\s*(?:for\s+improvement)?:?\s*\n((?:[-•*\d].*\n?)+)',
            r'improvements?:?\s*\n((?:[-•*\d].*\n?)+)',
            r'areas?\s+for\s+improvement:?\s*\n((?:[-•*\d].*\n?)+)',
            r'priority\s+recommendations?:?\s*\n((?:[-•*\d].*\n?)+)',
        ]
        
        for pattern in section_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                recs_text = match.group(1)
                lines = recs_text.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    # 清理列表标记 (-, *, 1., 2., etc.)
                    line = re.sub(r'^[\-\*•]+\s*', '', line)
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    
                    # 过滤太短的行和空行
                    if line and len(line) > 15:
                        recommendations.append(line)
                
                # 如果找到了推荐，就停止搜索其他模式
                if recommendations:
                    break
        
        # Pattern 2: 如果没找到，尝试匹配单独的列表项
        if not recommendations:
            list_item_pattern = r'^\s*[-•*]\s+(.+?)(?=\n|$)'
            matches = re.finditer(list_item_pattern, response, re.MULTILINE)
            
            for match in matches:
                rec = match.group(1).strip()
                if rec and len(rec) > 15:
                    recommendations.append(rec)
        
        # 去重和限制数量
        seen = set()
        unique_recommendations = []
        
        for rec in recommendations:
            rec_lower = rec.lower()
            if rec_lower not in seen:
                seen.add(rec_lower)
                unique_recommendations.append(rec)
                
                if len(unique_recommendations) >= max_recommendations:
                    break
        
        return unique_recommendations
        
    except Exception as e:
        print(f"❌ Error extracting recommendations: {e}")
        return []


def parse_json_response(response_text: str, attempt: int = 0) -> Dict[str, Any]:
    """
    解析LLM返回的JSON响应，自动处理markdown代码块和常见格式问题
    
    Args:
        response_text: 原始响应文本
        attempt: 递归尝试次数
    
    Returns:
        dict: 解析后的JSON对象，解析失败返回空字典
    
    Examples:
        >>> parse_json_response('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}
        >>> parse_json_response('{"key": "value"}')
        {'key': 'value'}
    """
    try:
        if not response_text:
            return {}
        
        # 移除markdown代码块标记
        cleaned = response_text.strip()
        
        # 移除 ```json 开头
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        # 移除 ``` 开头
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        # 移除 ``` 结尾
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # 尝试解析
        parsed = json.loads(cleaned)
        
        # 验证返回的是字典
        if not isinstance(parsed, dict):
            print(f"⚠️ Parsed JSON is not a dict: {type(parsed)}")
            return {}
        
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse error (attempt {attempt}): {e}")
        
        # 尝试提取花括号之间的内容（递归）
        if attempt < 2:
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return parse_json_response(match.group(0), attempt + 1)
        
        print(f"❌ Failed to parse JSON after {attempt + 1} attempts")
        print(f"   Response preview: {response_text[:200]}...")
        return {}
    
    except Exception as e:
        print(f"❌ Unexpected error parsing JSON: {e}")
        return {}


def merge_and_deduplicate_recommendations(
    recommendations_lists: List[List[str]], 
    max_total: int = 12  # ✅ v3.0: increased from 10 to 12 for 4 agents
) -> List[str]:
    """
    合并多个推荐列表并去重
    
    ✅ Framework v3.0: Increased default max to 12 (3 per agent × 4 agents)
    
    Args:
        recommendations_lists: 多个推荐列表（来自不同Agent）
        max_total: 最多返回的总推荐数
    
    Returns:
        List[str]: 合并去重后的推荐列表
    
    Examples:
        >>> lists = [['Add local context'], ['Add local context', 'Use Te Reo']]
        >>> merge_and_deduplicate_recommendations(lists)
        ['Add local context', 'Use Te Reo']
    """
    # 合并所有推荐
    all_recommendations = []
    for recs in recommendations_lists:
        if isinstance(recs, list):
            all_recommendations.extend(recs)
    
    # 去重（保持顺序，基于标准化的文本比较）
    seen = set()
    unique_recommendations = []
    
    for rec in all_recommendations:
        if not isinstance(rec, str):
            continue
        
        rec = rec.strip()
        
        # 标准化比较（小写，去除多余空格）
        normalized = ' '.join(rec.lower().split())
        
        # Check similarity with existing recommendations
        is_duplicate = False
        for seen_rec in seen:
            # 如果新推荐是旧推荐的子串，或者旧推荐是新推荐的子串，视为重复
            if normalized in seen_rec or seen_rec in normalized:
                is_duplicate = True
                break
        
        if not is_duplicate and len(rec) > 15:
            seen.add(normalized)
            unique_recommendations.append(rec)
            
            if len(unique_recommendations) >= max_total:
                break
    
    return unique_recommendations


def calculate_weighted_score(
    scores: Dict[str, int], 
    weights: Dict[str, float]
) -> int:
    """
    计算加权平均分
    
    ✅ Framework v3.0: Supports 4 dimensions with dynamic weighting
    
    Args:
        scores: 各维度的分数 (0-100)
        weights: 各维度的权重 (总和应为1.0)
    
    Returns:
        int: 加权平均分 (0-100)
    
    Examples:
        >>> scores = {'place_based_learning': 80, 'cultural_responsiveness_integrated': 70}
        >>> weights = {'place_based_learning': 0.25, 'cultural_responsiveness_integrated': 0.35}
        >>> calculate_weighted_score(scores, weights)
        # Returns normalized weighted average
    """
    try:
        if not scores or not weights:
            return 0
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for dimension, score in scores.items():
            weight = weights.get(dimension, 0.0)
            
            # Only include dimensions with positive score and weight
            if weight > 0 and score > 0:
                weighted_sum += score * weight
                total_weight += weight
        
        # 归一化（防止权重总和不为1.0，例如某些API被禁用）
        if total_weight > 0:
            # If total weight is not 1.0, normalize it
            if abs(total_weight - 1.0) > 0.01:
                normalized_score = weighted_sum / total_weight
            else:
                normalized_score = weighted_sum
        else:
            # If no valid weights, return simple average
            if scores:
                normalized_score = sum(scores.values()) / len(scores)
            else:
                normalized_score = 0.0
        
        return max(0, min(100, int(round(normalized_score))))
        
    except Exception as e:
        print(f"❌ Error calculating weighted score: {e}")
        return 0


def format_agent_response(
    agent_name: str,
    role: str,
    response_text: str,
    score: int,
    execution_time: float,
    dimension: Optional[str] = None,  # ✅ v3.0: singular dimension
    model: Optional[str] = None  # ✅ v3.0: add model info
) -> Dict[str, Any]:
    """
    格式化Agent响应为标准结构
    
    ✅ Framework v3.0: Updated to use singular 'dimension' and add 'model'
    
    Args:
        agent_name: Agent名称 ('DeepSeek', 'Claude', 'GPT-Critical', 'GPT-Design')
        role: Agent角色
        response_text: 原始响应
        score: 评估分数 (0-100)
        execution_time: 执行时间（秒）
        dimension: 评估的维度 (singular, not list)
        model: 模型名称 (e.g., 'gpt-4o', 'claude-sonnet-4-20250514')
    
    Returns:
        dict: 格式化的响应对象
    """
    response_obj = {
        "agent": agent_name,
        "role": role,
        "dimension": dimension,  # ✅ v3.0: singular
        "response": response_text,
        "score": score,
        "time": round(execution_time, 2),
        "response_length": len(response_text),
    }
    
    # ✅ v3.0: Add model if provided
    if model:
        response_obj["model"] = model
    
    return response_obj


def validate_framework_scores(scores: Dict[str, int]) -> bool:
    """
    验证分数是否符合 Framework v3.0 的结构
    
    ✅ v3.0: Check for 4 required dimensions
    
    Args:
        scores: 分数字典
    
    Returns:
        bool: 是否有效
    """
    # ✅ v3.0: Required dimensions (at least 2 should be present)
    v3_dimensions = {
        'place_based_learning',
        'cultural_responsiveness_integrated',
        'critical_pedagogy',
        'lesson_design_quality'
    }
    
    if not isinstance(scores, dict):
        return False
    
    # Count how many v3.0 dimensions are present
    present_dimensions = set(scores.keys()) & v3_dimensions
    
    # At least 2 dimensions should have valid scores
    valid_scores = sum(1 for dim in present_dimensions if scores.get(dim, 0) > 0)
    
    return valid_scores >= 2


if __name__ == "__main__":
    # 测试代码
    print("="*60)
    print("Testing Evaluation Helper Functions - Framework v3.0")
    print("="*60)
    
    # 测试分数提取
    print("\n1. Testing score extraction (v3.0):")
    test_responses = [
        "Overall Score: 4.5/5",
        "Converted to 100-point scale: 85/100",
        "Lesson Design Quality: 78/100",  # ✅ v3.0 new
        "Score: 3/5.0",
        "Cultural Responsiveness (Integrated): 68/100",  # ✅ v3.0
    ]
    
    for resp in test_responses:
        score = extract_score_from_response(resp, "test")
        print(f"   '{resp}' -> {score}/100")
    
    # 测试推荐提取
    print("\n2. Testing recommendation extraction:")
    test_rec = """
    Strengths: Good local integration.
    
    Recommendations:
    - Add more specific local examples with named places
    - Include Te Reo Māori vocabulary throughout
    - Strengthen community partnerships with local iwi
    - Add explicit assessment rubrics
    
    Overall, this is a solid lesson plan with room for growth.
    """
    
    recs = extract_recommendations_from_response(test_rec)
    print(f"   Found {len(recs)} recommendations:")
    for i, rec in enumerate(recs, 1):
        print(f"   {i}. {rec}")
    
    # 测试JSON解析
    print("\n3. Testing JSON parsing:")
    test_json = '```json\n{"key": "value", "number": 42, "array": [1, 2, 3]}\n```'
    parsed = parse_json_response(test_json)
    print(f"   Parsed: {parsed}")
    
    # 测试加权分数 (v3.0)
    print("\n4. Testing weighted score calculation (v3.0):")
    scores = {
        "place_based_learning": 72,
        "cultural_responsiveness_integrated": 68,
        "critical_pedagogy": 75,
        "lesson_design_quality": 78
    }
    weights = {
        "place_based_learning": 0.25,
        "cultural_responsiveness_integrated": 0.35,
        "critical_pedagogy": 0.25,
        "lesson_design_quality": 0.15
    }
    weighted = calculate_weighted_score(scores, weights)
    print(f"   Scores: {scores}")
    print(f"   Weights: {weights}")
    print(f"   Weighted average: {weighted}/100")
    
    # 测试推荐去重
    print("\n5. Testing recommendation deduplication:")
    lists = [
        ["Add local context", "Use Te Reo Māori"],
        ["Add local context integration", "Include iwi partnerships"],
        ["Use Te Reo Māori vocabulary", "Add assessment rubrics"]
    ]
    merged = merge_and_deduplicate_recommendations(lists, max_total=5)
    print(f"   Original lists: {sum(len(l) for l in lists)} items")
    print(f"   After deduplication: {len(merged)} items")
    for i, rec in enumerate(merged, 1):
        print(f"   {i}. {rec}")
    
    # 测试框架验证 (v3.0)
    print("\n6. Testing framework v3.0 validation:")
    valid_scores = {
        "place_based_learning": 72,
        "cultural_responsiveness_integrated": 68,
        "critical_pedagogy": 75
    }
    invalid_scores = {
        "old_dimension": 50
    }
    print(f"   Valid v3.0 scores: {validate_framework_scores(valid_scores)}")
    print(f"   Invalid scores: {validate_framework_scores(invalid_scores)}")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)


    # 在文件末尾添加这两个函数

def extract_strengths_from_response(response: str, max_strengths: int = 10) -> List[str]:
    """
    从 Agent 响应中提取 Strengths (优点)
    
    ✅ 支持两种格式:
    1. COMPREHENSIVE STRENGTHS SUMMARY (优先)
    2. 每个 Indicator 内的 Strengths (备选)
    
    Args:
        response: Agent 的原始响应文本
        max_strengths: 最多返回的优点数量
    
    Returns:
        List[str]: 优点列表
    """
    try:
        if not response or not isinstance(response, str):
            return []
        
        strengths = []
        
        # ========== 方法 1: 提取 COMPREHENSIVE STRENGTHS SUMMARY ==========
        comprehensive_patterns = [
            r'\*\*COMPREHENSIVE\s+STRENGTHS\s+SUMMARY:?\*\*\s*(.*?)(?=\n\*\*COMPREHENSIVE\s+AREAS|\n\*\*PRIORITY|\n\*\*TRANSFORMATIVE|\n---|\Z)',
            r'(?:comprehensive\s+)?strengths?(?:\s+summary)?:?\s*\n((?:[✅\-•*\d].*\n?){2,})',
        ]
        
        for pattern in comprehensive_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                strengths_text = match.group(1)
                lines = strengths_text.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    # 清理列表标记和 emoji
                    line = re.sub(r'^[✅\-\*•]+\s*', '', line)
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'\*\*', '', line)
                    line = line.strip()
                    
                    # 过滤太短的行和包含其他标题的行
                    if (line and 
                        len(line) > 20 and 
                        not re.match(r'^(areas?|recommendations?|gaps?|weaknesses?|provide|write)[\s:]', line, re.IGNORECASE) and
                        not line.startswith('[') and  # 忽略 [Strength 1: ...]
                        not line.startswith('Provide')):
                        strengths.append(line)
                
                if strengths:
                    print(f"   ✅ Found {len(strengths)} strengths from COMPREHENSIVE SUMMARY")
                    break
        
        # ========== 方法 2: 如果没有找到总结，提取每个 Indicator 的 Strengths ==========
        if not strengths:
            indicator_pattern = r'\*\*Strengths:?\*\*\s*(.*?)(?=\n\*\*Areas\s+for\s+Improvement:?|\n\*\*Recommendations?:?|\n\*\*INDICATOR|\n---|\Z)'
            indicator_matches = re.findall(indicator_pattern, response, re.DOTALL | re.IGNORECASE)
            
            for match in indicator_matches:
                lines = match.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # 清理列表标记
                    line = re.sub(r'^[-•*]+\s*', '', line)
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'\*\*', '', line)
                    line = line.strip()
                    
                    # 过滤太短的行
                    if line and len(line) > 20:
                        strengths.append(line)
            
            if strengths:
                print(f"   ✅ Found {len(strengths)} strengths from individual indicators")
        
        # 去重并保持顺序
        seen = set()
        unique_strengths = []
        
        for strength in strengths:
            strength_lower = strength.lower()
            if strength_lower not in seen and len(strength) > 20:
                seen.add(strength_lower)
                unique_strengths.append(strength)
                
                if len(unique_strengths) >= max_strengths:
                    break
        
        return unique_strengths
        
    except Exception as e:
        print(f"❌ Error extracting strengths: {e}")
        return []


def extract_areas_for_improvement_from_response(response: str, max_areas: int = 10) -> List[str]:
    """
    从 Agent 响应中提取 Areas for Improvement (需改进的领域)
    
    ✅ 支持两种格式:
    1. COMPREHENSIVE AREAS FOR IMPROVEMENT (优先)
    2. 每个 Indicator 内的 Areas for Improvement (备选)
    
    注意: 这与 Recommendations 不同
    - Areas: 指出问题/缺陷/差距
    - Recommendations: 提供解决方案
    
    Args:
        response: Agent 的原始响应文本
        max_areas: 最多返回的数量
    
    Returns:
        List[str]: 需改进领域列表
    """
    try:
        if not response or not isinstance(response, str):
            return []
        
        areas = []
        
        # ========== 方法 1: 提取 COMPREHENSIVE AREAS FOR IMPROVEMENT ==========
        comprehensive_patterns = [
            r'\*\*COMPREHENSIVE\s+AREAS\s+FOR\s+IMPROVEMENT:?\*\*\s*(.*?)(?=\n\*\*PRIORITY|\n\*\*TRANSFORMATIVE|\n---|\Z)',
            r'(?:comprehensive\s+)?areas?\s+for\s+improvement:?\s*\n((?:[🔧\-•*\d].*\n?){2,})',
        ]
        
        for pattern in comprehensive_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                areas_text = match.group(1)
                lines = areas_text.strip().split('\n')
                
                for line in lines:
                    line = line.strip()
                    # 清理列表标记、emoji 和警告符号
                    line = re.sub(r'^[🔧⚠️🚩❌\-\*•]+\s*', '', line)
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'^\*\*(MISSING|CRITICAL|LIMITED|WEAK)\*\*:?\s*', '', line, flags=re.IGNORECASE)
                    line = re.sub(r'\*\*', '', line)
                    line = line.strip()
                    
                    # 过滤太短的行和包含其他标题的行
                    if (line and 
                        len(line) > 20 and 
                        not re.match(r'^(strengths?|recommendations?|priority|provide|write)[\s:]', line, re.IGNORECASE) and
                        not line.startswith('[') and
                        not line.startswith('Provide')):
                        areas.append(line)
                
                if areas:
                    print(f"   🔧 Found {len(areas)} areas from COMPREHENSIVE SUMMARY")
                    break
        
        # ========== 方法 2: 如果没有找到总结，提取每个 Indicator 的 Areas ==========
        if not areas:
            indicator_pattern = r'\*\*Areas\s+for\s+Improvement:?\*\*\s*(.*?)(?=\n\*\*Recommendations?:?|\n\*\*INDICATOR|\n---|\Z)'
            indicator_matches = re.findall(indicator_pattern, response, re.DOTALL | re.IGNORECASE)
            
            for match in indicator_matches:
                lines = match.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # 清理列表标记
                    line = re.sub(r'^[-•*]+\s*', '', line)
                    line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    line = re.sub(r'\*\*', '', line)
                    line = line.strip()
                    
                    # 过滤太短的行
                    if line and len(line) > 20:
                        areas.append(line)
            
            if areas:
                print(f"   🔧 Found {len(areas)} areas from individual indicators")
        
        # 去重
        seen = set()
        unique_areas = []
        
        for area in areas:
            area_lower = area.lower()
            if area_lower not in seen and len(area) > 20:
                seen.add(area_lower)
                unique_areas.append(area)
                
                if len(unique_areas) >= max_areas:
                    break
        
        return unique_areas
        
    except Exception as e:
        print(f"❌ Error extracting areas for improvement: {e}")
        return []
    
