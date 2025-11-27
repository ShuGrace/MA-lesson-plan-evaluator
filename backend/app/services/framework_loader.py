# app/services/framework_loader.py
"""
Theoretical Framework and Prompt Loader - Framework v3.0
✅ 4 Dimensions: PBL, CRMP (Integrated), CP, LDQ
✅ 4 Agents: DeepSeek, Claude, GPT-Critical, GPT-Design
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

class FrameworkLoader:
    """
    加载和管理理论框架配置 - Framework v3.0
    
    Key Changes in v3.0:
    - Fully integrated Cultural Responsiveness and Māori Perspectives (CRMP)
    - Added Lesson Design Quality dimension (LDQ)
    - Updated weights: PBL=0.25, CRMP=0.35, CP=0.25, LDQ=0.15
    - Added GPT-Design agent
    """
    
    def __init__(self, backend_path: Optional[str] = None):
        """
        初始化框架加载器
        
        Args:
            backend_path: backend文件夹路径，默认自动检测
        """
        if backend_path is None:
            # 从当前文件位置推断backend路径
            # 当前文件在: backend/app/services/framework_loader.py
            current_file = Path(__file__).resolve()
            # 向上3层到backend
            self.backend_path = current_file.parent.parent.parent

            # ✅ 添加调试输出
            print(f"[Framework] DEBUG: current_file = {current_file}")
            print(f"[Framework] DEBUG: current_file.parent = {current_file.parent}")
            print(f"[Framework] DEBUG: current_file.parent.parent = {current_file.parent.parent}")
            print(f"[Framework] DEBUG: current_file.parent.parent.parent = {current_file.parent.parent.parent}")
        else:
            self.backend_path = Path(backend_path)
        
        # 设置各个资源路径
        self.config_path = self.backend_path / "framework"  #  使用 framework 文件夹
        self.prompts_path = self.backend_path / "prompts"
        
        print(f"[Framework] Backend path: {self.backend_path}")
        print(f"[Framework] Config path: {self.config_path}")
        print(f"[Framework] Prompts path: {self.prompts_path}")
        
        # ✅ 添加路径存在性检查
        if not self.backend_path.exists():
            print(f"❌ ERROR: Backend path does not exist: {self.backend_path}")
        if not self.prompts_path.exists():
            print(f"❌ ERROR: Prompts path does not exist: {self.prompts_path}")
        else:
            print(f"✅ Prompts path exists: {self.prompts_path}")
            # 列出目录内容
            try:
                files = list(self.prompts_path.glob("*.txt"))
                print(f"   Found {len(files)} .txt files:")
                for f in files:
                    print(f"   - {f.name}")
            except Exception as e:
                print(f"   Could not list files: {e}")

        # 缓存加载的内容
        self._framework = None
        self._agent_design = None
        self._prompts = {}
    
    def load_theoretical_framework(self) -> Dict:
        """
        加载理论框架JSON - Framework v3.0
        
        Returns:
            Dict: 理论框架完整配置
        """
        if self._framework is None:
            framework_file = self.config_path / "theoretical_framework.json"
            
            if not framework_file.exists():
                print(f"⚠️ Warning: Framework file not found at {framework_file}")
                print("   Using default framework v3.0.")
                return self._get_default_framework()
            
            try:
                with open(framework_file, 'r', encoding='utf-8') as f:
                    self._framework = json.load(f)
                version = self._framework.get('framework_metadata', {}).get('version', 'unknown')
                print(f"✅ Loaded theoretical framework v{version}")
            except Exception as e:
                print(f"❌ Error loading framework: {e}")
                return self._get_default_framework()
        
        return self._framework
    
    def load_agent_design(self) -> Dict:
        """
        加载Agent设计配置 - Framework v3.0
        
        Returns:
            Dict: Agent角色分配和设计
        """
        if self._agent_design is None:
            design_file = self.config_path / "agent_design.json"
            
            if not design_file.exists():
                print(f"⚠️ Warning: Agent design file not found at {design_file}")
                print("   Using default agent design v3.0.")
                return self._get_default_agent_design()
            
            try:
                with open(design_file, 'r', encoding='utf-8') as f:
                    self._agent_design = json.load(f)
                version = self._agent_design.get('version', 'unknown')
                print(f"✅ Loaded agent design v{version}")
            except Exception as e:
                print(f"❌ Error loading agent design: {e}")
                return self._get_default_agent_design()
        
        return self._agent_design
    
    def load_prompt(self, agent_name: str) -> str:
        """
        加载指定Agent的prompt模板 - Framework v3.0
        
        ✅ Supported agent_name (v3.0):
        - 'deepseek' -> deepseek_place_based.txt
        - 'claude' -> claude_cultural_integrated.txt  # ✅ v3.0 updated
        - 'gpt' or 'chatgpt' -> gpt_critical_pedagogy.txt (default for backward compatibility)
        - 'gpt_critical' -> gpt_critical_pedagogy.txt  # ✅ v3.0 explicit
        - 'gpt_design' -> gpt_lesson_design.txt  # ✅ v3.0 new
        
        Args:
            agent_name: Agent名称
        
        Returns:
            str: Prompt文本内容
        """
        if agent_name in self._prompts:
            return self._prompts[agent_name]
        
        #  Framework v3.0: 更新 prompt 文件映射
        prompt_files = {
            'deepseek': 'deepseek_place_based.txt',
            'claude': 'claude_cultural_maori.txt',  #  v3.0: integrated cultural + Māori
            'gpt': 'gpt_critical_pedagogy.txt',  # 默认/兼容旧代码
            'chatgpt': 'gpt_critical_pedagogy.txt',  # 别名
            'gpt_critical': 'gpt_critical_pedagogy.txt',  #  v3.0: explicit
            'gpt_design': 'gpt_lesson_design.txt'  #  v3.0: new agent
        }
        
        filename = prompt_files.get(agent_name.lower())
        if not filename:
            print(f"⚠️ Unknown agent name: {agent_name}")
            return self._get_default_prompt(agent_name)
        
        prompt_file = self.prompts_path / filename
        
        if not prompt_file.exists():
            print(f"⚠️ Warning: Prompt file not found at {prompt_file}")
            print(f"   Using default prompt for {agent_name}.")
            return self._get_default_prompt(agent_name)
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            self._prompts[agent_name] = prompt_content
            print(f"✅ Loaded prompt for {agent_name}: {filename} ({len(prompt_content)} chars)")
            return prompt_content
        except Exception as e:
            print(f"❌ Error loading prompt for {agent_name}: {e}")
            return self._get_default_prompt(agent_name)
    
    def get_dimension_indicators(self, dimension_code: str) -> List[Dict]:
        """
        获取特定维度的所有指标
        
        Args:
            dimension_code: 维度代码 (e.g., 'place_based_learning', 'cultural_responsiveness_integrated')
        
        Returns:
            List[Dict]: 指标列表
        """
        framework = self.load_theoretical_framework()
        dimensions = framework.get('dimensions', {})
        
        if dimension_code not in dimensions:
            print(f"⚠️ Dimension '{dimension_code}' not found in framework")
            return []
        
        return dimensions[dimension_code].get('indicators', [])
    
    def get_scoring_weights(self) -> Dict[str, float]:
        """
        获取各维度的评分权重 - Framework v3.0
        
        ✅ v3.0 Weights:
        - place_based_learning: 0.25
        - cultural_responsiveness_integrated: 0.35  # ✅ Integrated
        - critical_pedagogy: 0.25
        - lesson_design_quality: 0.15  # ✅ New
        
        Returns:
            Dict[str, float]: 维度名称到权重的映射
        """
        framework = self.load_theoretical_framework()
        composite_scoring = framework.get('composite_scoring', {})
        
        # ✅ v3.0 默认权重
        default_weights = {
            'place_based_learning': 0.25,
            'cultural_responsiveness_integrated': 0.35,  # ✅ v3.0: unified
            'critical_pedagogy': 0.25,
            'lesson_design_quality': 0.15  # ✅ v3.0: new
        }
        
        weights = composite_scoring.get('weights', default_weights)
        
        # ✅ 兼容性处理：如果框架使用旧 key，转换为新 key
        if 'cultural_responsiveness' in weights and 'cultural_responsiveness_integrated' not in weights:
            weights['cultural_responsiveness_integrated'] = weights.pop('cultural_responsiveness')
            print("[Framework] ℹ️  Converted 'cultural_responsiveness' to 'cultural_responsiveness_integrated'")
        
        if 'maori_perspectives' in weights:
            print("[Framework] ⚠️  Found deprecated 'maori_perspectives' key - ignoring (now integrated)")
            weights.pop('maori_perspectives', None)
        
        return weights
    
    def get_agent_dimensions(self, agent_name: str) -> List[str]:
        """
        获取指定Agent负责评估的维度
        
        Args:
            agent_name: Agent名称 ('DeepSeek', 'Claude', 'GPT-Critical', 'GPT-Design')
        
        Returns:
            List[str]: 维度代码列表
        """
        agent_design = self.load_agent_design()
        agents = agent_design.get('agents', {})
        
        for agent_id, agent_info in agents.items():
            if agent_info.get('name', '').lower() == agent_name.lower():
                return agent_info.get('assigned_dimensions', [])
        
        print(f"⚠️ Agent '{agent_name}' not found in design")
        return []
    
    def _get_default_framework(self) -> Dict:
        """返回默认的 Framework v3.0"""
        return {
            "framework_metadata": {
                "name": "Default Framework v3.0 (Fallback)",
                "version": "3.0",
                "description": "Fallback framework with 4 integrated dimensions",
                "note": "Please add theoretical_framework.json to backend/framework/"
            },
            "dimensions": {
                "place_based_learning": {
                    "label": "Place-Based Learning",
                    "definition": "Learning grounded in local context and community",
                    "indicators": []
                },
                "cultural_responsiveness_integrated": {  # ✅ v3.0: unified
                    "label": "Cultural Responsiveness & Māori Perspectives (Integrated)",
                    "definition": "Culturally responsive teaching with integrated Māori perspectives",
                    "indicators": []
                },
                "critical_pedagogy": {
                    "label": "Critical Pedagogy & Student Engagement",
                    "definition": "Critical consciousness, student agency, and active learning",
                    "indicators": []
                },
                "lesson_design_quality": {  # ✅ v3.0: new
                    "label": "Lesson Design Quality",
                    "definition": "Instructional design quality and structural coherence",
                    "indicators": []
                }
            },
            "composite_scoring": {
                "method": "weighted_average",
                "weights": {
                    "place_based_learning": 0.25,
                    "cultural_responsiveness_integrated": 0.35,
                    "critical_pedagogy": 0.25,
                    "lesson_design_quality": 0.15
                }
            }
        }
    
    def _get_default_agent_design(self) -> Dict:
        """返回默认的 Agent 设计 v3.0"""
        return {
            "system_name": "Default Multi-Agent System v3.0 (Fallback)",
            "version": "3.0",
            "description": "4-agent system with integrated cultural dimension",
            "agents": {
                "agent_1": {
                    "name": "DeepSeek",
                    "model": "deepseek-chat",
                    "role": "Place-based Learning Specialist",
                    "assigned_dimensions": ["place_based_learning"]
                },
                "agent_2": {
                    "name": "Claude",
                    "model": "claude-sonnet-4-20250514",
                    "role": "Cultural Responsiveness & Māori Perspectives Specialist (Integrated)",
                    "assigned_dimensions": ["cultural_responsiveness_integrated"]
                },
                "agent_3": {
                    "name": "GPT-Critical",  # ✅ v3.0: distinct name
                    "model": "gpt-4o",
                    "role": "Critical Pedagogy & Student Engagement Specialist",
                    "assigned_dimensions": ["critical_pedagogy"]
                },
                "agent_4": {  # ✅ v3.0: new agent
                    "name": "GPT-Design",
                    "model": "gpt-4o",
                    "role": "Lesson Design & Quality Specialist",
                    "assigned_dimensions": ["lesson_design_quality"]
                }
            }
        }
    
    def _get_default_prompt(self, agent_name: str) -> str:
        """返回默认的简化 prompt - Framework v3.0"""
        prompts = {
            'deepseek': """You are a place-based learning expert (Framework v3.0). Evaluate this lesson plan for:
            1. Local context integration (Score: 1-5)
            2. Community engagement (Score: 1-5)
            3. Authentic problem-solving (Score: 1-5)
            4. Indigenous knowledge integration (Score: 1-5)

            Overall Score (convert to /100): [X]/100

            Provide detailed analysis and recommendations.

            Lesson Plan:
            {lesson_plan_text}
            """,
                        'claude': """You are a cultural responsiveness and Māori perspectives expert (Framework v3.0 - INTEGRATED DIMENSION). Evaluate this lesson plan for:

            INTEGRATED CULTURAL RESPONSIVENESS & MĀORI PERSPECTIVES:
            1. Cultural knowledge validation (Score: 1-5)
            2. Te Reo Māori integration (Score: 1-5)
            3. Mātauranga Māori depth (Score: 1-5)
            4. Tikanga and cultural protocols (Score: 1-5)
            5. Multicultural perspectives (Score: 1-5)

            Overall Score (convert to /100): [X]/100

            Provide detailed analysis covering both general cultural responsiveness AND Māori perspectives as a unified dimension.

            Lesson Plan:
            {lesson_plan_text}
            """,
                        'gpt': """You are a critical pedagogy expert (Framework v3.0). Evaluate this lesson plan for:
            1. Power structure analysis (Score: 1-5)
            2. Student agency and voice (Score: 1-5)
            3. Social justice orientation (Score: 1-5)
            4. Dialogic teaching (Score: 1-5)

            Overall Score (convert to /100): [X]/100

            Provide detailed analysis and recommendations.

            Lesson Plan:
            {lesson_plan_text}
            """,
                        'chatgpt': """You are a critical pedagogy expert (Framework v3.0). Evaluate this lesson plan for:
            1. Power structure analysis (Score: 1-5)
            2. Student agency and voice (Score: 1-5)
            3. Social justice orientation (Score: 1-5)
            4. Dialogic teaching (Score: 1-5)

            Overall Score (convert to /100): [X]/100

            Provide detailed analysis and recommendations.

            Lesson Plan:
            {lesson_plan_text}
            """,
                        'gpt_critical': """You are a critical pedagogy expert (Framework v3.0). Evaluate this lesson plan for:
            1. Power structure analysis (Score: 1-5)
            2. Student agency and voice (Score: 1-5)
            3. Social justice orientation (Score: 1-5)
            4. Dialogic teaching (Score: 1-5)

            Overall Score (convert to /100): [X]/100

            Provide detailed analysis and recommendations.

            Lesson Plan:
            {lesson_plan_text}
            """,
                        'gpt_design': """You are a lesson design quality expert (Framework v3.0 - NEW DIMENSION). Evaluate this lesson plan for:
            1. Clear learning objectives (Score: 1-5)
            2. Instructional coherence and flow (Score: 1-5)
            3. Assessment alignment (Score: 1-5)
            4. Differentiation strategies (Score: 1-5)

            Overall Score (convert to /100): [X]/100

            Provide detailed analysis of instructional design quality.

            Lesson Plan:
            {lesson_plan_text}
            """
                    }
        
        return prompts.get(agent_name.lower(), 
                          "Evaluate this lesson plan (Framework v3.0):\n{lesson_plan_text}")


# 全局单例实例
_framework_loader_instance = None

def get_framework_loader(backend_path: Optional[str] = None) -> FrameworkLoader:
    """
    获取FrameworkLoader的单例实例
    
    Args:
        backend_path: backend目录路径（可选）
    
    Returns:
        FrameworkLoader: 框架加载器实例
    """
    global _framework_loader_instance
    
    if _framework_loader_instance is None:
        _framework_loader_instance = FrameworkLoader(backend_path)
    
    return _framework_loader_instance


if __name__ == "__main__":
    # 测试代码
    print("\n" + "="*60)
    print("Testing Framework Loader v3.0")
    print("="*60 + "\n")
    
    loader = get_framework_loader()
    
    # 测试加载理论框架
    print("1. Loading Theoretical Framework v3.0...")
    framework = loader.load_theoretical_framework()
    print(f"   Framework name: {framework.get('framework_metadata', {}).get('name')}")
    print(f"   Version: {framework.get('framework_metadata', {}).get('version')}")
    print(f"   Dimensions: {list(framework.get('dimensions', {}).keys())}")
    
    # 测试加载权重
    print("\n2. Loading Scoring Weights (v3.0)...")
    weights = loader.get_scoring_weights()
    for dim, weight in weights.items():
        print(f"   {dim}: {weight*100:.0f}%")
    
    # 测试加载Agent设计
    print("\n3. Loading Agent Design v3.0...")
    agent_design = loader.load_agent_design()
    for agent_id, agent_info in agent_design.get('agents', {}).items():
        print(f"   {agent_info['name']}: {agent_info['role']}")
    
    # 测试加载prompts
    print("\n4. Loading Prompts (v3.0)...")
    for agent in ['deepseek', 'claude', 'gpt_critical', 'gpt_design']:
        prompt = loader.load_prompt(agent)
        print(f"   {agent}: {len(prompt)} characters")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")