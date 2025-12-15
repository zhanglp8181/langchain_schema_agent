"""
模型配置管理模块
支持多模型配置的存储、加载和管理
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


# 配置文件路径
CONFIG_FILE = "model_configs.json"


@dataclass
class ModelConfig:
    """模型配置类"""
    id: str                          # 唯一标识符
    name: str                        # 显示名称
    provider: str                    # 提供商 (dashscope, openai, azure, ollama等)
    model_name: str                  # 模型名称 (qwen-turbo, gpt-4, etc.)
    api_key: str = ""                # API密钥
    api_base: str = ""               # API基础URL
    temperature: float = 0.7         # 温度参数
    max_tokens: int = 4096           # 最大token数
    enabled: bool = True             # 是否启用
    is_default: bool = False         # 是否为默认模型
    description: str = ""            # 模型描述
    extra_params: Dict[str, Any] = field(default_factory=dict)  # 额外参数
    created_at: str = ""             # 创建时间
    updated_at: str = ""             # 更新时间
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelConfig':
        """从字典创建"""
        return cls(**data)
    
    def get_display_name(self) -> str:
        """获取显示名称"""
        return f"{self.name} ({self.provider}/{self.model_name})"


class ModelConfigManager:
    """模型配置管理器"""
    
    # 预定义的模型提供商配置
    PROVIDERS = {
        "dashscope": {
            "name": "阿里云DashScope",
            "api_base_default": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext", "qwen-vl-plus", "qwen-vl-max"],
            "requires_api_key": True
        },
        "openai": {
            "name": "OpenAI",
            "api_base_default": "https://api.openai.com/v1",
            "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"],
            "requires_api_key": True
        },
        "azure": {
            "name": "Azure OpenAI",
            "api_base_default": "",
            "models": ["gpt-35-turbo", "gpt-4", "gpt-4-turbo"],
            "requires_api_key": True
        },
        "ollama": {
            "name": "Ollama (本地)",
            "api_base_default": "http://localhost:11434/v1",
            "models": ["llama2", "llama3", "mistral", "codellama", "qwen2"],
            "requires_api_key": False
        },
        "deepseek": {
            "name": "DeepSeek",
            "api_base_default": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-coder"],
            "requires_api_key": True
        },
        "zhipu": {
            "name": "智谱AI",
            "api_base_default": "https://open.bigmodel.cn/api/paas/v4",
            "models": ["glm-4", "glm-4-flash", "glm-3-turbo"],
            "requires_api_key": True
        },
        "moonshot": {
            "name": "Moonshot AI",
            "api_base_default": "https://api.moonshot.cn/v1",
            "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            "requires_api_key": True
        }
    }
    
    def __init__(self, config_file: str = CONFIG_FILE):
        """初始化配置管理器"""
        self.config_file = config_file
        self.configs: Dict[str, ModelConfig] = {}
        self._load_configs()
        
        # 如果没有配置，创建默认配置
        if not self.configs:
            self._create_default_configs()
    
    def _load_configs(self):
        """从文件加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for config_data in data.get("models", []):
                        config = ModelConfig.from_dict(config_data)
                        self.configs[config.id] = config
                print(f"✅ 已加载 {len(self.configs)} 个模型配置")
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}")
                self.configs = {}
    
    def _save_configs(self):
        """保存配置到文件"""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "models": [config.to_dict() for config in self.configs.values()]
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存到 {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def _create_default_configs(self):
        """创建默认配置"""
        # 从环境变量读取API密钥
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")
        dashscope_base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        
        # 创建默认的Qwen配置
        default_config = ModelConfig(
            id="qwen-turbo-default",
            name="Qwen Turbo (默认)",
            provider="dashscope",
            model_name="qwen-turbo",
            api_key=dashscope_api_key,
            api_base=dashscope_base_url,
            temperature=0.7,
            max_tokens=4096,
            enabled=True,
            is_default=True,
            description="阿里云通义千问Turbo模型，速度快，适合日常使用"
        )
        self.configs[default_config.id] = default_config
        
        # 创建Qwen Plus配置
        plus_config = ModelConfig(
            id="qwen-plus-default",
            name="Qwen Plus",
            provider="dashscope",
            model_name="qwen-plus",
            api_key=dashscope_api_key,
            api_base=dashscope_base_url,
            temperature=0.7,
            max_tokens=8192,
            enabled=True,
            is_default=False,
            description="阿里云通义千问Plus模型，能力更强"
        )
        self.configs[plus_config.id] = plus_config
        
        # 创建Qwen Max配置
        max_config = ModelConfig(
            id="qwen-max-default",
            name="Qwen Max",
            provider="dashscope",
            model_name="qwen-max",
            api_key=dashscope_api_key,
            api_base=dashscope_base_url,
            temperature=0.7,
            max_tokens=8192,
            enabled=True,
            is_default=False,
            description="阿里云通义千问Max模型，能力最强"
        )
        self.configs[max_config.id] = max_config
        
        self._save_configs()
    
    def add_config(self, config: ModelConfig) -> bool:
        """添加模型配置"""
        # 如果设置为默认，取消其他配置的默认状态
        if config.is_default:
            for c in self.configs.values():
                c.is_default = False
        
        config.updated_at = datetime.now().isoformat()
        self.configs[config.id] = config
        return self._save_configs()
    
    def update_config(self, config_id: str, updates: Dict) -> bool:
        """更新模型配置"""
        if config_id not in self.configs:
            return False
        
        config = self.configs[config_id]
        
        # 如果设置为默认，取消其他配置的默认状态
        if updates.get("is_default", False):
            for c in self.configs.values():
                c.is_default = False
        
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        config.updated_at = datetime.now().isoformat()
        return self._save_configs()
    
    def delete_config(self, config_id: str) -> bool:
        """删除模型配置"""
        if config_id not in self.configs:
            return False
        
        del self.configs[config_id]
        return self._save_configs()
    
    def get_config(self, config_id: str) -> Optional[ModelConfig]:
        """获取指定配置"""
        return self.configs.get(config_id)
    
    def get_default_config(self) -> Optional[ModelConfig]:
        """获取默认配置"""
        for config in self.configs.values():
            if config.is_default and config.enabled:
                return config
        
        # 如果没有默认配置，返回第一个启用的配置
        for config in self.configs.values():
            if config.enabled:
                return config
        
        return None
    
    def get_all_configs(self) -> List[ModelConfig]:
        """获取所有配置"""
        return list(self.configs.values())
    
    def get_enabled_configs(self) -> List[ModelConfig]:
        """获取所有启用的配置"""
        return [c for c in self.configs.values() if c.enabled]
    
    def get_config_choices(self) -> List[tuple]:
        """获取配置选项（用于下拉框）"""
        choices = []
        for config in self.get_enabled_configs():
            display = config.get_display_name()
            if config.is_default:
                display += " ★"
            choices.append((display, config.id))
        return choices
    
    def get_default_config_id(self) -> Optional[str]:
        """获取默认配置ID"""
        default = self.get_default_config()
        return default.id if default else None
    
    @classmethod
    def get_provider_info(cls, provider: str) -> Dict:
        """获取提供商信息"""
        return cls.PROVIDERS.get(provider, {})
    
    @classmethod
    def get_all_providers(cls) -> List[tuple]:
        """获取所有提供商选项"""
        return [(info["name"], key) for key, info in cls.PROVIDERS.items()]
    
    @classmethod
    def get_provider_models(cls, provider: str) -> List[str]:
        """获取指定提供商的模型列表"""
        return cls.PROVIDERS.get(provider, {}).get("models", [])


# 全局配置管理器实例
_config_manager: Optional[ModelConfigManager] = None


def get_config_manager() -> ModelConfigManager:
    """获取配置管理器实例（单例）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ModelConfigManager()
    return _config_manager


def reload_config_manager():
    """重新加载配置管理器"""
    global _config_manager
    _config_manager = ModelConfigManager()
    return _config_manager


if __name__ == "__main__":
    # 测试配置管理器
    manager = get_config_manager()
    
    print("\n所有配置:")
    for config in manager.get_all_configs():
        print(f"  - {config.get_display_name()}")
    
    print("\n默认配置:")
    default = manager.get_default_config()
    if default:
        print(f"  {default.get_display_name()}")
    
    print("\n配置选项（用于下拉框）:")
    for display, config_id in manager.get_config_choices():
        print(f"  {display}: {config_id}")
