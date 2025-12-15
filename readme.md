# 智能Schema自动生成系统

一个基于 **LangChain**、**大型语言模型** 和 **结构化分析技术** 的智能Schema生成系统，能够自动分析文档内容并生成对应的结构化Schema定义。

## 🌟 项目特点

- **智能文档分析**：自动识别文档领域和关键信息
- **结构化Schema生成**：基于分析结果自动生成标准Schema定义
- **可视化界面**：提供友好的Web界面进行操作和结果预览
- **可编辑流程**：分析结果和Schema均可手动编辑和调整
- **自动验证优化**：内置验证机制确保生成Schema的质量

## 🚀 快速开始

### 安装依赖

```bash
git clone <repository-url>
cd langchain-schema-agent

# 建议使用虚拟环境
python -m venv venv 
source venv/bin/activate  # Linux/Mac: source venv/bin/activate, Windows: venv\Scripts\activate

pip install -r requirements.txt
```
###  conda 安装示例
```bash
conda create -n newschema python=3.11
conda activate newschema

cd langchain-schema-agent
pip install -r requirements.txt

python schema_ui.py
```
### 配置模型

系统支持多种大语言模型，包括但不限于通义千问系列。配置方法：

1. 复制 `.env.example` 为 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，添加您的模型API密钥和其他配置参数

3. 配置模型参数：
   - 编辑 `model_configs.json` 文件来添加或修改模型配置
   - 在 `model_config.py` 中可以定义默认模型

### 启动系统

```bash
python run_schema_generator.py
```

启动后访问 `http://localhost:8888` 使用Web界面。

## 🧠 核心功能

### 1. 文档分析
- 自动识别文档所属领域和子领域
- 提取关键实体、关系和属性
- 生成详细的文档分析报告

### 2. Schema生成
- 基于分析报告自动生成结构化Schema
- 支持YAML格式输出
- 符合标准命名规范和结构要求

### 3. Schema验证
- 内置多种验证规则确保Schema质量
- 自动检测并提示潜在问题
- 支持自定义验证规则

### 4. 可视化展示
- 提供图表化展示Schema结构
- 支持多种可视化形式（ER图、知识图谱等）

## 📁 目录结构

```
.
├── data/                  # 数据目录
│   ├── input/             # 输入文档
│   └── output/            # 生成的Schema和报告
├── schema_agent.py        # 核心分析代理
├── schema_parser.py       # Schema解析器
├── schema_validator.py    # Schema验证器
├── schema_custom_validator.py  # 自定义验证器
├── schema_ui.py           # Web界面
├── llm_service.py         # LLM服务封装
├── model_config.py        # 模型配置管理
├── run_schema_generator.py # 系统启动入口
└── ...
```

## ⚙️ 技术架构

1. **用户界面层**：基于Gradio构建的Web界面
2. **业务逻辑层**：SchemaAgent负责文档分析和Schema生成
3. **模型服务层**：LLMService封装不同大模型的调用接口
4. **验证层**：SchemaValidator和SchemaCustomValidator确保输出质量
5. **数据层**：文件系统存储输入文档和输出结果

## 🔧 配置说明

系统通过以下配置文件进行定制：

- `model_configs.json`：定义可用的大语言模型配置,web服务启动时会自动加载,项目启动后，页面上“模型配置”也可以配置模型
- `validation_rules.json`：定义Schema验证规则
- `.env`：环境变量配置（API密钥等敏感信息）

## 📝 使用流程

1. 启动系统并打开Web界面
2. 上传或粘贴需要分析的文档内容
3. 选择合适的分析模型并开始分析
4. 查看并编辑生成的分析报告
5. 基于报告生成Schema定义
6. 验证并导出最终的Schema文件

## 📈 应用场景

- 法律文书结构化处理
- 合同条款分析与建模
- 业务文档标准化
- 知识图谱构建前置处理
- 数据库设计辅助工具

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

[Apache License Version 2.0]