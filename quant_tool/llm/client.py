# LLM接口配置模块
# 用于配置OpenAI兼容API

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM配置"""
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-3.5-turbo"
    module_id: str = ""  # 可选，用于区分不同用途
    timeout: int = 30
    max_tokens: int = 1000


class LLMClient:
    """LLM客户端"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client = None
    
    @classmethod
    def from_env(cls) -> "LLMClient":
        """从环境变量加载配置"""
        config = LLMConfig(
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            module_id=os.getenv("LLM_MODULE_ID", "")
        )
        return cls(config)
    
    def analyze_sentiment(self, text: str) -> dict:
        """
        使用LLM分析文本情感
        
        Returns:
            {
                "sentiment": "positive/negative/neutral",
                "score": -1.0 ~ 1.0,
                "confidence": 0.0 ~ 1.0,
                "reason": "分析理由"
            }
        """
        if not self.config.api_key:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "reason": "未配置LLM API"
            }
        
        prompt = f"""分析以下财经文本的情感，返回JSON格式：
{{
    "sentiment": "positive/negative/neutral",
    "score": -1.0到1.0之间的分数，正数表示积极，负数表示消极，
    "confidence": 0.0到1.0之间的置信度，
    "reason": 一句话说明理由
}}

文本：{text[:500]}
        
只返回JSON，不要其他内容。"""
        
        try:
            response = self._call_llm(prompt)
            import json
            result = json.loads(response)
            return result
        except Exception as e:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "reason": f"LLM调用失败: {str(e)}"
            }
    
    def summarize_news(self, texts: list) -> dict:
        """
        使用LLM总结多条新闻的核心观点
        """
        if not self.config.api_key:
            return {"summary": "未配置LLM API", "key_points": []}
        
        combined = "\n".join([f"- {t[:200]}" for t in texts[:10]])
        
        prompt = f"""总结以下财经新闻的核心观点：

{combined}

返回JSON格式：
{{
    "summary": "一段话总结（不超过100字）",
    "key_points": ["要点1", "要点2", "要点3"],
    "overall_sentiment": "偏多/偏空/中性"
}}

只返回JSON。"""
        
        try:
            response = self._call_llm(prompt)
            import json
            result = json.loads(response)
            return result
        except Exception as e:
            return {"summary": f"LLM调用失败: {str(e)}", "key_points": []}
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        import openai
        
        client = openai.OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        
        response = client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "你是一个专业的财经分析师。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.config.max_tokens,
            temperature=0.3
        )
        
        return response.choices[0].message.content


def create_llm_client(base_url: str = None, api_key: str = None, 
                       model: str = None, module_id: str = None) -> LLMClient:
    """
    创建LLM客户端的便捷函数
    
    Args:
        base_url: API地址，如 https://api.deepseek.com/v1
        api_key: API密钥
        model: 模型名称，如 gpt-3.5-turbo, deepseek-chat
        module_id: 模块ID，用于区分不同用途
    
    Example:
        client = create_llm_client(
            base_url="https://api.deepseek.com/v1",
            api_key="sk-xxx",
            model="deepseek-chat",
            module_id="sentiment"
        )
    """
    config = LLMConfig(
        base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=api_key or os.getenv("LLM_API_KEY", ""),
        model=model or os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
        module_id=module_id or os.getenv("LLM_MODULE_ID", "")
    )
    return LLMClient(config)


if __name__ == "__main__":
    import json
    
    client = create_llm_client(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-3.5-turbo"
    )
    
    test_text = "这家公司业绩大涨50%，超出市场预期，分析师纷纷上调评级"
    result = client.analyze_sentiment(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
