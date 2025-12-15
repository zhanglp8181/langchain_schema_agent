"""
LLM服务模块 - 统一的模型调用接口
提供模型配置管理和统一的调用接口
"""

import os
from typing import Dict, List, Any, Optional, Union
from langchain_community.chat_models import ChatTongyi
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel

from model_config import get_config_manager, ModelConfig, reload_config_manager

# 尝试从config导入，如果失败则从环境变量获取
try:
    from config import DASHSCOPE_API_KEY
except ImportError:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")


class LLMService:
    """
    LLM服务类 - 提供统一的模型调用接口
    
    功能:
    - 支持多种模型提供商（DashScope、OpenAI、Azure、Ollama等）
    - 动态切换模型
    - 统一的调用接口
    - 模型配置管理
    """
    
    def __init__(self, model_config_id: str = None):
        """
        初始化LLM服务
        
        Args:
            model_config_id: 模型配置ID，如果为None则使用默认配置
        """
        self.config_manager = get_config_manager()
        self.current_config: Optional[ModelConfig] = None
        self.llm: Optional[BaseChatModel] = None
        
        # 设置模型
        self.set_model(model_config_id)
    
    def set_model(self, model_config_id: str = None) -> bool:
        """
        设置使用的模型
        
        Args:
            model_config_id: 模型配置ID，如果为None则使用默认配置
            
        Returns:
            是否设置成功
        """
        # 获取配置
        if model_config_id:
            config = self.config_manager.get_config(model_config_id)
        else:
            config = self.config_manager.get_default_config()
        
        if not config:
            # 回退到默认的Qwen模型
            print("⚠️ 未找到模型配置，使用默认Qwen配置")
            self.llm = ChatTongyi(
                model="qwen-turbo",
                api_key=DASHSCOPE_API_KEY,
                temperature=0.7
            )
            self.current_config = None
            return False
        
        # 创建LLM实例
        try:
            self.llm = self._create_llm(config)
            self.current_config = config
            print(f"🤖 已切换模型: {config.get_display_name()}")
            return True
        except Exception as e:
            print(f"❌ 创建模型实例失败: {e}")
            # 回退到默认模型
            self.llm = ChatTongyi(
                model="qwen-turbo",
                api_key=DASHSCOPE_API_KEY,
                temperature=0.7
            )
            self.current_config = None
            return False
    
    def _create_llm(self, config: ModelConfig) -> BaseChatModel:
        """
        根据配置创建LLM实例
        
        Args:
            config: 模型配置
            
        Returns:
            LLM实例
        """
        if config.provider == "dashscope":
            return ChatTongyi(
                model=config.model_name,
                api_key=config.api_key or DASHSCOPE_API_KEY,
                temperature=config.temperature
            )
        elif config.provider in ["openai", "azure", "deepseek", "moonshot", "zhipu"]:
            # 使用OpenAI兼容的API
            return ChatOpenAI(
                model=config.model_name,
                api_key=config.api_key,
                base_url=config.api_base if config.api_base else None,
                temperature=config.temperature,
                max_tokens=config.max_tokens
            )
        elif config.provider == "ollama":
            # Ollama使用OpenAI兼容API
            return ChatOpenAI(
                model=config.model_name,
                api_key="ollama",  # Ollama不需要API key
                base_url=config.api_base or "http://localhost:11434/v1",
                temperature=config.temperature
            )
        else:
            # 默认使用OpenAI兼容API
            return ChatOpenAI(
                model=config.model_name,
                api_key=config.api_key,
                base_url=config.api_base if config.api_base else None,
                temperature=config.temperature
            )
    
    def invoke(self, messages: List[Union[BaseMessage, Dict]]) -> str:
        """
        调用LLM生成响应
        
        Args:
            messages: 消息列表，可以是BaseMessage对象或字典格式
            
        Returns:
            LLM响应内容
        """
        if self.llm is None:
            raise RuntimeError("LLM未初始化")
        
        # 转换消息格式
        formatted_messages = self._format_messages(messages)
        
        # 调用LLM
        response = self.llm.invoke(formatted_messages)
        return response.content
    
    def _format_messages(self, messages: List[Union[BaseMessage, Dict]]) -> List[BaseMessage]:
        """
        格式化消息列表
        
        Args:
            messages: 原始消息列表
            
        Returns:
            格式化后的消息列表
        """
        formatted = []
        for msg in messages:
            if isinstance(msg, BaseMessage):
                formatted.append(msg)
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    formatted.append(SystemMessage(content=content))
                else:
                    formatted.append(HumanMessage(content=content))
            else:
                # 假设是字符串，作为用户消息处理
                formatted.append(HumanMessage(content=str(msg)))
        return formatted
    
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        简化的聊天接口
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            
        Returns:
            LLM响应内容
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        return self.invoke(messages)
    
    def get_current_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息
        
        Returns:
            模型信息字典
        """
        if self.current_config:
            return {
                "id": self.current_config.id,
                "name": self.current_config.name,
                "provider": self.current_config.provider,
                "model_name": self.current_config.model_name,
                "display_name": self.current_config.get_display_name(),
                "temperature": self.current_config.temperature,
                "max_tokens": self.current_config.max_tokens
            }
        return {
            "id": "default",
            "name": "默认模型",
            "provider": "dashscope",
            "model_name": "qwen-turbo",
            "display_name": "默认模型 (qwen-turbo)",
            "temperature": 0.7,
            "max_tokens": 4096
        }
    
    def get_model_display_name(self) -> str:
        """获取当前模型显示名称"""
        if self.current_config:
            return self.current_config.get_display_name()
        return "默认模型 (qwen-turbo)"
    
    def reload_configs(self):
        """重新加载配置"""
        self.config_manager = reload_config_manager()
    
    def get_available_models(self) -> List[tuple]:
        """
        获取所有可用的模型选项
        
        Returns:
            模型选项列表，每个元素为(显示名称, 配置ID)
        """
        return self.config_manager.get_config_choices()
    
    def get_default_model_id(self) -> Optional[str]:
        """获取默认模型ID"""
        return self.config_manager.get_default_config_id()


# 全局LLM服务实例
_llm_service: Optional[LLMService] = None


def get_llm_service(model_config_id: str = None) -> LLMService:
    """
    获取LLM服务实例（单例）
    
    Args:
        model_config_id: 模型配置ID，首次调用时使用
        
    Returns:
        LLM服务实例
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(model_config_id)
    return _llm_service


def create_llm_service(model_config_id: str = None) -> LLMService:
    """
    创建新的LLM服务实例
    
    Args:
        model_config_id: 模型配置ID
        
    Returns:
        新的LLM服务实例
    """
    return LLMService(model_config_id)


def switch_model(model_config_id: str) -> bool:
    """
    切换全局LLM服务的模型
    
    Args:
        model_config_id: 模型配置ID
        
    Returns:
        是否切换成功
    """
    service = get_llm_service()
    return service.set_model(model_config_id)


if __name__ == "__main__":
    # 测试LLM服务
    print("="*60)
    print("🧪 LLM服务测试")
    print("="*60)
    
    # 获取服务实例
    service = get_llm_service()
    
    # 显示当前模型信息
    print("\n当前模型信息:")
    info = service.get_current_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # 显示可用模型
    print("\n可用模型:")
    for display, config_id in service.get_available_models():
        print(f"  {display}: {config_id}")
    
    # 测试调用
    print("\n测试调用...")
    try:
        response = service.chat(
            system_prompt="你是一个友好的助手。",
            user_prompt="请用一句话介绍自己。"
        )
        print(f"响应: {response}")
    except Exception as e:
        print(f"调用失败: {e}")
