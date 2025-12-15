"""
智能Schema生成系统UI
"""

import gradio as gr
import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from schema_agent import SchemaAgent, DocumentAnalysisReport
from schema_validator import SchemaValidator
from schema_custom_validator import SchemaCustomValidator
from model_config import get_config_manager, ModelConfig, ModelConfigManager, reload_config_manager


class SchemaUI:
    """智能Schema生成系统的Gradio界面"""
    
    def __init__(self):
        """初始化UI"""
        self.config_manager = get_config_manager()
        self.agent = SchemaAgent()
        self.validator = SchemaValidator()
        self.custom_validator = SchemaCustomValidator()
        
        # 尝试加载验证规则
        try:
            self.custom_validator.load_rules_from_file()
        except:
            pass
        
        self.current_report = None
        self.current_schema = None
        
        # 设置文件保存路径
        self.input_dir = "data/input"
        self.output_dir = "data/output"
        
        # 确保目录存在
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _get_model_choices(self):
        """获取模型选择选项"""
        return self.config_manager.get_config_choices()
    
    def _get_default_model_id(self):
        """获取默认模型ID"""
        return self.config_manager.get_default_config_id()
    
    def create_interface(self) -> gr.Blocks:
        """创建Gradio界面"""
        
        # 自定义CSS样式，修复可视化区域高度问题
        custom_css = """
        /* 修复可视化区域被遮挡的问题 - 移除所有高度限制和overflow隐藏 */
        #schema-visualization {
            min-height: 700px !important;
            max-height: none !important;
            overflow: visible !important;
            height: auto !important;
        }
        #schema-visualization > div,
        #schema-visualization > div > div {
            max-height: none !important;
            overflow: visible !important;
            height: auto !important;
        }
        #schema-visualization .prose {
            max-height: none !important;
            overflow: visible !important;
        }
        #schema-visualization iframe {
            min-height: 550px !important;
            height: 550px !important;
        }
        
        /* 修复Gradio HTML组件的滚动区域问题 */
        .gradio-container #schema-visualization,
        .gradio-container #schema-visualization * {
            max-height: none !important;
        }
        
        /* 强制移除父级容器的overflow限制 */
        #schema-visualization,
        #schema-visualization ~ *,
        .contain #schema-visualization {
            overflow: visible !important;
            max-height: none !important;
        }
        
        /* 修复Tab内容区的高度限制 */
        .tabitem {
            overflow: visible !important;
        }
        
        /* 针对Gradio特定类的样式覆盖 */
        .block.svelte-90oupt,
        .wrap.svelte-90oupt {
            overflow: visible !important;
            max-height: none !important;
        }
        
        /* 确保Column容器不限制高度 */
        .col {
            overflow: visible !important;
        }
        
        /* 彻底移除HTML组件的所有overflow限制 */
        #schema-visualization,
        #schema-visualization > *,
        #schema-visualization > * > *,
        #schema-visualization > * > * > * {
            overflow: visible !important;
            max-height: none !important;
        }
        
        /* 移除Gradio prose class的限制 */
        .prose {
            max-height: none !important;
            overflow: visible !important;
        }
        
        /* 确保HTML内容区没有滚动限制 */
        .html {
            max-height: none !important;
            overflow: visible !important;
        }
        
        /* 移除所有gradio容器的overflow hidden */
        .gradio-container .block,
        .gradio-container .wrap,
        .gradio-container .contain {
            overflow: visible !important;
        }
        """
        
        with gr.Blocks(title="智能Schema生成系统", css=custom_css) as demo:
            # 标题和说明
            gr.Markdown("""
            # 🚀 智能Schema自动生成系统
            
            ### 📊 系统特点
            - **智能分析**：自动识别文档领域，激活专业知识
            - **结构化生成**：基于分析报告生成精准Schema
            - **可编辑流程**：分析结果可手动编辑和确认
            - **验证优化**：自动验证并优化生成结果
            
            ---
            """)
            
            # 存储状态
            state = gr.State({
                "report": None,
                "schema": None,
                "report_path": None
            })
            
            with gr.Tabs():
                # ========== Tab 1: 文档分析 ==========
                with gr.TabItem("📄 文档分析", id=0):
                    gr.Markdown("""
                    ### 📌 步骤说明
                    1. 上传或输入文档内容
                    2. 选择要使用的AI模型
                    3. 点击"分析文档"进行领域识别和结构分析
                    4. 查看并编辑分析报告
                    5. 确认报告后生成Schema
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            # 模型选择
                            gr.Markdown("### 🤖 模型选择")
                            analysis_model_select = gr.Dropdown(
                                label="选择分析模型",
                                choices=self._get_model_choices(),
                                value=self._get_default_model_id(),
                                info="选择用于文档分析的AI模型"
                            )
                            
                            # 文档输入区
                            gr.Markdown("### 📄 文档输入")
                            file_input = gr.File(
                                label="📁 上传文档",
                                file_types=[".txt", ".csv", ".pdf", ".docx", ".md"],
                                file_count="single"
                            )
                            
                            example_text = gr.Textbox(
                                label="📝 或直接输入文档内容",
                                placeholder="在这里粘贴或输入文档内容...",
                                lines=10
                            )
                            
                            # 分析按钮
                            analyze_btn = gr.Button(
                                "🔍 分析文档",
                                variant="primary",
                                size="lg"
                            )
                            
                            # 进度显示
                            progress_stage1 = gr.Textbox(
                                label="分析进度",
                                lines=3,
                                interactive=False
                            )
                        
                        with gr.Column(scale=2):
                            # 分析报告显示区
                            with gr.Tabs():
                                # 报告预览
                                with gr.TabItem("📊 报告预览"):
                                    report_preview = gr.Markdown(
                                        value="分析报告将在这里显示...",
                                        elem_classes="report-preview"
                                    )
                                
                                # 报告编辑
                                with gr.TabItem("✏️ 编辑报告"):
                                    gr.Markdown("""
                                    **编辑说明**：您可以修改以下JSON格式的分析报告，
                                    添加或删除实体、关系、属性等。修改后点击"更新报告"。
                                    """)
                                    
                                    report_editor = gr.Code(
                                        label="分析报告（JSON格式）",
                                        language="json",
                                        lines=20,
                                        interactive=True
                                    )
                                    
                                    with gr.Row():
                                        update_report_btn = gr.Button(
                                            "🔄 更新报告",
                                            size="sm"
                                        )
                                        save_report_btn = gr.Button(
                                            "💾 保存报告",
                                            size="sm"
                                        )
                                        load_report_btn = gr.Button(
                                            "📂 加载报告",
                                            size="sm"
                                        )
                                    
                                    # 报告文件选择器（隐藏）
                                    report_file_input = gr.File(
                                        label="选择报告文件",
                                        file_types=[".json"],
                                        visible=False
                                    )
                                
                                # 领域信息
                                with gr.TabItem("🏷️ 领域信息"):
                                    domain_info = gr.JSON(
                                        label="识别的领域信息",
                                        show_label=True
                                    )
                    
                    # 确认并进入第二阶段
                    with gr.Row():
                        gr.Markdown("""
                        ### ✅ 确认报告
                        确认分析报告无误后，点击下方按钮进入Schema生成阶段。
                        """)
                    
                    with gr.Row():
                        confirm_btn = gr.Button(
                            "✅ 确认报告，准备生成Schema",
                            variant="primary",
                            size="lg"
                        )
                
                # ========== Tab 2: Schema生成 ==========
                with gr.TabItem("🏗️ Schema生成", id=1):
                    gr.Markdown("""
                    ### 📌 步骤说明
                    1. 基于确认的分析报告生成Schema（或从历史记录加载）
                    2. 选择要使用的AI模型
                    3. 选择Schema模板格式
                    4. 生成并验证Schema
                    5. 导出最终Schema
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            # Schema生成控制
                            gr.Markdown("### 📋 当前报告信息")
                            report_summary = gr.Textbox(
                                label="报告摘要",
                                lines=6,
                                interactive=False,
                                value="请先完成文档分析或从历史记录加载"
                            )
                            
                            # 加载历史Schema按钮
                            gr.Markdown("### 📂 加载历史Schema")
                            with gr.Row():
                                schema_history_dropdown = gr.Dropdown(
                                    label="选择历史Schema",
                                    choices=[],
                                    interactive=True,
                                    info="选择要加载的历史Schema文件"
                                )
                                refresh_schema_history_btn = gr.Button("🔄", size="sm", scale=0)
                            
                            load_schema_history_btn = gr.Button(
                                "📂 加载选中Schema",
                                size="sm"
                            )
                            
                            # 模型选择
                            gr.Markdown("### 🤖 模型选择")
                            schema_model_select = gr.Dropdown(
                                label="选择生成模型",
                                choices=self._get_model_choices(),
                                value=self._get_default_model_id(),
                                info="选择用于Schema生成的AI模型"
                            )
                            
                            # 添加推测实体和关系开关
                            gr.Markdown("### ⚙️ 生成选项")
                            use_inferred = gr.Checkbox(
                                label="使用推测的实体和关系",
                                value=False,
                                info="将推测的实体和关系一起发送给模型生成Schema"
                            )
                            
                            # 模板选择
                            template_select = gr.Dropdown(
                                label="选择Schema模板",
                                choices=[
                                    ("OpenSPG/KAG声明式", "openspg_kag_v1"),
                                    ("JSON Schema标准", "json_schema_v1"),
                                    ("LLM抽取上下文", "llm_context_v1"),
                                    ("YAML格式", "yaml_v1")
                                ],
                                value="openspg_kag_v1"
                            )
                            
                            # 生成按钮
                            generate_btn = gr.Button(
                                "⚡ 生成Schema",
                                variant="primary",
                                size="lg"
                            )
                            
                            # 进度显示
                            progress_stage2 = gr.Textbox(
                                label="生成进度",
                                lines=3,
                                interactive=False
                            )
                        
                        with gr.Column(scale=2):
                            # Schema显示和编辑区
                            with gr.Tabs():
                                # Schema编辑器
                                with gr.TabItem("📝 Schema编辑器"):
                                    schema_editor = gr.Code(
                                        label="生成的Schema（可编辑）",
                                        language="yaml",
                                        lines=25,
                                        interactive=True,
                                        value=""
                                    )
                                    
                                    with gr.Row():
                                        validate_btn = gr.Button("✅ 验证", size="sm")
                                        format_btn = gr.Button("🎨 格式化", size="sm")
                                        save_schema_btn = gr.Button("💾 保存", size="sm")
                                
                                # 验证结果
                                with gr.TabItem("🔍 验证结果"):
                                    validation_result = gr.HTML(
                                        value="<p>Schema验证结果将在这里显示</p>"
                                    )
                                    
                                    validation_stats = gr.JSON(
                                        label="验证统计",
                                        show_label=True
                                    )
                                    
                                    # 添加重新生成按钮
                                    with gr.Row():
                                        regenerate_btn = gr.Button(
                                            "🔄 重新生成Schema（基于错误反馈）",
                                            variant="primary",
                                            visible=False  # 初始隐藏，有错误时显示
                                        )
                                    
                                    regenerate_progress = gr.Textbox(
                                        label="重新生成进度",
                                        lines=2,
                                        interactive=False,
                                        visible=False
                                    )
                
                # ========== Tab 3: 导出和可视化 ==========
                with gr.TabItem("📦 导出与可视化", id=2):
                    gr.Markdown("""
                    ### 📌 导出选项
                    选择导出格式并下载最终的Schema文件
                    """)
                    
                    with gr.Row():
                        with gr.Column():
                            # 导出格式选择
                            export_format = gr.Radio(
                                label="导出格式",
                                choices=[
                                    "OpenSPG/KAG",
                                    "JSON Schema",
                                    "YAML",
                                    "Markdown文档"
                                ],
                                value="OpenSPG/KAG"
                            )
                            
                            # 导出选项
                            include_report = gr.Checkbox(
                                label="包含分析报告",
                                value=True
                            )
                            
                            include_metadata = gr.Checkbox(
                                label="包含元数据",
                                value=True
                            )
                            
                            # 导出按钮
                            export_btn = gr.Button(
                                "📥 导出Schema",
                                variant="primary"
                            )
                            
                            # 下载链接
                            download_file = gr.File(
                                label="下载文件",
                                visible=False
                            )
                        
                        with gr.Column(scale=2):
                            # 导出预览
                            export_preview = gr.Code(
                                label="导出预览",
                                language="yaml",
                                lines=30,
                                interactive=False
                            )
                    
                    # Schema可视化区域
                    gr.Markdown("""
                    ---
                    ### 📊 Schema可视化
                    生成实体关系图（ER图），直观展示Schema中的实体、属性和关系
                    """)
                    
                    # 可视化控制选项（单行布局）
                    with gr.Row():
                        # 可视化选项
                        viz_options = gr.CheckboxGroup(
                            label="显示选项",
                            choices=[
                                "显示属性",
                                "显示中文名称",
                                "显示数据类型",
                                "知识图谱视图"
                            ],
                            value=["显示属性", "显示中文名称", "知识图谱视图"],
                            info="选择要在图表中显示的内容"
                        )
                        
                        # 布局方向
                        viz_direction = gr.Radio(
                            label="布局方向",
                            choices=["TB", "LR", "BT", "RL"],
                            value="TB",
                            info="TB=从上到下, LR=从左到右, BT=从下到上, RL=从右到左"
                        )
                        
                        # 生成可视化按钮
                        generate_viz_btn = gr.Button(
                            "🎨 生成实体关系图",
                            variant="primary",
                            scale=0
                        )
                    
                    # 可视化区域（独立一行，不与其他元素共享Row）
                    visualization = gr.HTML(
                        label="Schema可视化",
                        value=self._get_empty_visualization_html(),
                        elem_id="schema-visualization"
                    )
                    
                    # 统计信息和Mermaid代码（可折叠）
                    with gr.Row():
                        with gr.Column(scale=1):
                            viz_stats = gr.JSON(
                                label="Schema统计",
                                show_label=True
                            )
                        with gr.Column(scale=2):
                            with gr.Accordion("📝 Mermaid图表代码", open=False):
                                mermaid_code = gr.Code(
                                    label="Mermaid代码",
                                    language="markdown",
                                    lines=10,
                                    interactive=False
                                )
                
                # ========== Tab 4: 历史记录 ==========
                with gr.TabItem("📚 历史记录", id=3):
                    gr.Markdown("""
                    ### 📌 历史分析记录
                    查看和管理之前的分析报告和生成的Schema
                    """)
                    
                    with gr.Row():
                        # 刷新按钮
                        refresh_history_btn = gr.Button("🔄 刷新历史", size="sm")
                    
                    # 历史记录下拉选择
                    with gr.Row():
                        history_dropdown = gr.Dropdown(
                            label="选择历史记录",
                            choices=[],
                            interactive=True,
                            info="选择要加载的历史记录文件"
                        )
                    
                    # 历史记录表格（仅展示）
                    history_table = gr.Dataframe(
                        headers=["文件名", "类型", "领域", "创建时间"],
                        datatype=["str", "str", "str", "str"],
                        interactive=False,
                        label="历史记录列表"
                    )
                    
                    with gr.Row():
                        selected_file = gr.Textbox(
                            label="选中的文件路径",
                            interactive=False,
                            visible=True
                        )
                    
                    with gr.Row():
                        load_selected_btn = gr.Button(
                            "📂 加载选中记录",
                            variant="primary",
                            size="sm"
                        )
                        
                        delete_selected_btn = gr.Button(
                            "🗑️ 删除选中记录",
                            size="sm",
                            variant="stop"
                        )
                    
                    # 操作状态显示
                    history_status = gr.Textbox(
                        label="操作状态",
                        interactive=False
                    )
                
                # ========== Tab 5: 模型配置 ==========
                with gr.TabItem("⚙️ 模型配置", id=4):
                    gr.Markdown("""
                    ### 📌 模型配置管理
                    在这里管理AI模型配置，可以添加、编辑、删除模型配置
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("### ➕ 添加/编辑模型")
                            
                            config_id_input = gr.Textbox(
                                label="配置ID",
                                placeholder="自动生成或手动输入",
                                info="唯一标识符，留空自动生成"
                            )
                            
                            config_name_input = gr.Textbox(
                                label="配置名称",
                                placeholder="例如: GPT-4 生产环境",
                                info="便于识别的名称"
                            )
                            
                            provider_select = gr.Dropdown(
                                label="提供商",
                                choices=ModelConfigManager.get_all_providers(),
                                value="dashscope",
                                info="选择模型提供商"
                            )
                            
                            model_name_input = gr.Dropdown(
                                label="模型名称",
                                choices=ModelConfigManager.get_provider_models("dashscope"),
                                value="qwen-turbo",
                                allow_custom_value=True,
                                info="选择或输入模型名称"
                            )
                            
                            api_key_input = gr.Textbox(
                                label="API Key",
                                placeholder="输入API密钥",
                                type="password",
                                info="API访问密钥"
                            )
                            
                            api_base_input = gr.Textbox(
                                label="API Base URL",
                                placeholder="可选，使用默认值",
                                info="API基础URL，留空使用默认"
                            )
                            
                            with gr.Row():
                                temperature_input = gr.Slider(
                                    label="Temperature",
                                    minimum=0,
                                    maximum=2,
                                    value=0.7,
                                    step=0.1,
                                    info="控制输出的随机性"
                                )
                                
                                max_tokens_input = gr.Number(
                                    label="Max Tokens",
                                    value=4096,
                                    info="最大输出token数"
                                )
                            
                            with gr.Row():
                                is_enabled_input = gr.Checkbox(
                                    label="启用",
                                    value=True
                                )
                                is_default_input = gr.Checkbox(
                                    label="设为默认",
                                    value=False
                                )
                            
                            config_description_input = gr.Textbox(
                                label="描述",
                                placeholder="模型配置的描述信息",
                                lines=2
                            )
                            
                            with gr.Row():
                                save_config_btn = gr.Button("💾 保存配置", variant="primary")
                                clear_config_btn = gr.Button("🔄 清空表单")
                            
                            config_status = gr.Textbox(
                                label="操作状态",
                                interactive=False
                            )
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### 📋 现有配置")
                            
                            refresh_configs_btn = gr.Button("🔄 刷新列表", size="sm")
                            
                            config_list = gr.Dataframe(
                                headers=["ID", "名称", "提供商", "模型", "默认", "启用"],
                                datatype=["str", "str", "str", "str", "str", "str"],
                                interactive=False,
                                label="模型配置列表"
                            )
                            
                            with gr.Row():
                                edit_config_btn = gr.Button("✏️ 编辑选中", size="sm")
                                delete_config_btn = gr.Button("🗑️ 删除选中", size="sm", variant="stop")
                            
                            selected_config_id = gr.Textbox(
                                label="选中的配置ID",
                                visible=False
                            )
                    
                    # 模型配置事件处理
                    def update_model_choices(provider):
                        models = ModelConfigManager.get_provider_models(provider)
                        provider_info = ModelConfigManager.get_provider_info(provider)
                        default_base = provider_info.get("api_base_default", "")
                        return gr.update(choices=models, value=models[0] if models else ""), default_base
                    
                    provider_select.change(
                        fn=update_model_choices,
                        inputs=[provider_select],
                        outputs=[model_name_input, api_base_input]
                    )
                    
                    def refresh_config_list():
                        configs = self.config_manager.get_all_configs()
                        data = []
                        for c in configs:
                            data.append([
                                c.id,
                                c.name,
                                c.provider,
                                c.model_name,
                                "✓" if c.is_default else "",
                                "✓" if c.enabled else ""
                            ])
                        return data
                    
                    refresh_configs_btn.click(
                        fn=refresh_config_list,
                        outputs=[config_list]
                    )
                    
                    def select_config(evt: gr.SelectData, data):
                        if data is not None and evt.index[0] < len(data):
                            # 处理 DataFrame 和 list 两种情况
                            if hasattr(data, 'iloc'):
                                # pandas DataFrame
                                return data.iloc[evt.index[0], 0]
                            else:
                                # list
                                return data[evt.index[0]][0]
                        return ""
                    
                    config_list.select(
                        fn=select_config,
                        inputs=[config_list],
                        outputs=[selected_config_id]
                    )
                    
                    def load_config_for_edit(config_id):
                        if not config_id:
                            return [""] * 10 + ["未选择配置"]
                        config = self.config_manager.get_config(config_id)
                        if not config:
                            return [""] * 10 + ["配置不存在"]
                        return [
                            config.id,
                            config.name,
                            config.provider,
                            config.model_name,
                            config.api_key,
                            config.api_base,
                            config.temperature,
                            config.max_tokens,
                            config.enabled,
                            config.is_default,
                            config.description,
                            f"已加载配置: {config.name}"
                        ]
                    
                    edit_config_btn.click(
                        fn=load_config_for_edit,
                        inputs=[selected_config_id],
                        outputs=[
                            config_id_input, config_name_input, provider_select,
                            model_name_input, api_key_input, api_base_input,
                            temperature_input, max_tokens_input, is_enabled_input,
                            is_default_input, config_description_input, config_status
                        ]
                    )
                    
                    def save_model_config(config_id, name, provider, model_name, api_key,
                                         api_base, temperature, max_tokens, enabled, is_default, description):
                        try:
                            if not name:
                                return "❌ 请输入配置名称", refresh_config_list()
                            
                            # 生成ID
                            if not config_id:
                                config_id = f"{provider}-{model_name}-{uuid.uuid4().hex[:8]}"
                            
                            config = ModelConfig(
                                id=config_id,
                                name=name,
                                provider=provider,
                                model_name=model_name,
                                api_key=api_key,
                                api_base=api_base,
                                temperature=float(temperature),
                                max_tokens=int(max_tokens),
                                enabled=enabled,
                                is_default=is_default,
                                description=description
                            )
                            
                            self.config_manager.add_config(config)
                            return f"✅ 配置已保存: {name}", refresh_config_list()
                        except Exception as e:
                            return f"❌ 保存失败: {str(e)}", refresh_config_list()
                    
                    save_config_btn.click(
                        fn=save_model_config,
                        inputs=[
                            config_id_input, config_name_input, provider_select,
                            model_name_input, api_key_input, api_base_input,
                            temperature_input, max_tokens_input, is_enabled_input,
                            is_default_input, config_description_input
                        ],
                        outputs=[config_status, config_list]
                    )
                    
                    def clear_config_form():
                        return "", "", "dashscope", "qwen-turbo", "", "", 0.7, 4096, True, False, "", "表单已清空"
                    
                    clear_config_btn.click(
                        fn=clear_config_form,
                        outputs=[
                            config_id_input, config_name_input, provider_select,
                            model_name_input, api_key_input, api_base_input,
                            temperature_input, max_tokens_input, is_enabled_input,
                            is_default_input, config_description_input, config_status
                        ]
                    )
                    
                    def delete_model_config(config_id):
                        if not config_id:
                            return "❌ 请先选择配置", refresh_config_list()
                        try:
                            self.config_manager.delete_config(config_id)
                            return f"✅ 已删除配置: {config_id}", refresh_config_list()
                        except Exception as e:
                            return f"❌ 删除失败: {str(e)}", refresh_config_list()
                    
                    delete_config_btn.click(
                        fn=delete_model_config,
                        inputs=[selected_config_id],
                        outputs=[config_status, config_list]
                    )
                
                # ========== Tab 6: 使用帮助 ==========
                with gr.TabItem("❓ 使用帮助", id=5):
                    gr.Markdown("""
                    ## 📖 使用指南
                    
                    ### 系统概述
                    
                    智能Schema生成系统是一个基于AI的自动化工具，能够从各种文档中提取结构化信息并生成标准Schema定义。
                    系统采用两阶段处理流程，先分析文档内容生成结构化报告，再基于报告生成Schema。
                    
                    ### 🔄 工作流程
                    
                    #### 🔍 第一阶段：文档分析
                    1. **文档输入**：上传文档（.txt, .csv, .pdf, .docx, .md）或直接粘贴文本内容
                    2. **AI分析**：系统使用选定的大语言模型自动分析文档内容
                    3. **领域识别**：智能识别文档所属的专业领域（如法律、医疗、金融等）
                    4. **结构提取**：识别文档中的实体、关系、属性等结构化信息
                    5. **报告生成**：生成包含所有分析结果的详细JSON格式报告
                    6. **人工审核**：用户可编辑分析报告，确认或修正识别结果
                    
                    #### 🏗️ 第二阶段：Schema生成
                    1. **模板选择**：选择Schema输出格式（OpenSPG/KAG、JSON Schema、YAML等）
                    2. **AI生成**：基于分析报告和领域信息生成结构化Schema定义
                    3. **智能验证**：系统自动验证生成的Schema是否符合规范
                    4. **错误反馈**：如有问题，系统提供详细错误信息和修复建议
                    5. **迭代优化**：可根据验证结果重新生成和优化Schema
                    6. **导出使用**：支持多种格式导出最终Schema
                    
                    ### 🎛️ 核心功能说明
                    
                    #### 模型配置管理
                    - 支持多种大语言模型（如Qwen系列）
                    - 可配置API密钥、温度参数、最大token数等
                    - 支持设置默认模型和启用/禁用特定模型
                    
                    #### 分析报告编辑
                    - 可直接编辑JSON格式的分析报告
                    - 支持添加、删除或修改识别出的实体、关系、属性
                    - 可调整领域分类和关键词
                    
                    #### Schema生成选项
                    - **使用推测内容**：可选择是否包含AI推测的实体和关系
                    - **多种模板**：支持不同格式的Schema输出
                    - **模型选择**：可为Schema生成阶段单独选择AI模型
                    
                    #### 验证与优化
                    - 自动生成验证报告，包含错误、警告和提示信息
                    - 支持一键重新生成，基于错误反馈优化Schema
                    - 提供Schema格式化功能
                    
                    ### 📊 分析报告结构说明
                    
                    | 字段 | 说明 | 示例 |
                    |-----|------|-----|
                    | domain | 主要领域 | "供应链管理" |
                    | sub_domain | 子领域 | "采购管理" |
                    | keywords | 领域关键词 | ["供应商", "采购", "合同"] |
                    | entities | 实体类型列表 | [{"name": "Supplier", "cn_name": "供应商"}] |
                    | relations | 关系类型列表 | [{"name": "signs", "cn_name": "签署"}] |
                    | attributes | 属性列表 | [{"name": "amount", "cn_name": "金额"}] |
                    | inferred_entities | 推测的实体 | 需要用户确认的潜在实体 |
                    | inferred_relations | 推测的关系 | 需要用户确认的潜在关系 |
                    
                    ### 💡 最佳实践
                    
                    1. **文档准备**
                       - 提供结构清晰、内容完整的文档
                       - 包含丰富的实体和关系示例
                       - 尽量使用专业术语和规范表达
                    
                    2. **分析报告审核**
                       - 仔细检查AI识别的实体和关系
                       - 确认推测的内容是否准确
                       - 补充遗漏的重要元素
                       - 调整不准确的领域分类
                    
                    3. **Schema生成优化**
                       - 使用验证功能检查Schema质量
                       - 根据验证结果迭代优化
                       - 确保命名规范统一
                       - 导出前进行最终确认
                    
                    ### ⚠️ Schema规范与验证规则
                    
                    系统会对生成的Schema进行严格验证，确保符合以下规范：
                    
                    #### 命名规范
                    - **实体名称**：必须使用英文PascalCase格式（如：Project、Supplier、Contract）
                    - **属性和关系名称**：必须使用英文camelCase格式（如：projectName、belongsTo、contractAmount）
                    - **禁止使用下划线**：所有名称都不能包含下划线字符
                    - **禁止特殊字符**：名称中不能包含/、\\、|等特殊字符
                    
                    #### 中文要求
                    - 所有实体、属性和关系都必须包含中文名称（cn_name字段）
                    
                    #### 类型规范
                    - **允许的数据类型**：仅限Text、Integer和Float
                    - **数值属性**：金额、价格、数量等相关属性建议使用Float或Integer类型
                    - **日期属性**：日期和时间相关属性建议使用Text类型
                    
                    #### 结构要求
                    - 每个实体必须包含名称属性（xxxName格式）和description属性
                    - 不应包含名为"id"的属性
                    - 不应在Schema中包含"constraint"字段
                    - 实体如果没有关系，不应显示空的relations部分
                    - 同一个实体的属性和关系必须定义在同一处，禁止重复定义
                    
                    #### 验证结果说明
                    - **错误（红色）**：必须修复的问题，否则Schema无效
                    - **警告（黄色）**：建议修复的问题，不影响Schema基本使用
                    - **提示（蓝色）**：提供信息性建议
                    
                    ### 📤 导出与可视化
                    
                    - 支持多种导出格式：OpenSPG/KAG、JSON Schema、YAML、Markdown
                    - 可选择是否包含分析报告和元数据
                    - 提供导出预览功能
                    - 支持Schema可视化展示（开发中）
                    
                    ### 🔧 常见问题解答
                    
                    **Q: 领域识别不准确怎么办？**
                    A: 可在报告编辑界面手动修改domain和keywords字段，然后保存更新。
                    
                    **Q: 如何添加新的实体类型？**
                    A: 在报告编辑器的entities数组中添加新的实体对象，格式参考现有实体。
                    
                    **Q: Schema验证失败如何处理？**
                    A: 查看详细的错误信息，根据提示修改分析报告或直接编辑Schema，然后重新验证。
                    
                    **Q: 如何提高生成质量？**
                    A: 选择更强大的AI模型，提供更高质量的输入文档，仔细审核中间产物。
                    
                    **Q: 生成的Schema不完整怎么办？**
                    A: 检查分析报告中的entities、relations和attributes是否完整，必要时手动补充。
                    
                    **Q: 如何复用之前的工作成果？**
                    A: 使用历史记录功能加载之前保存的分析报告或Schema文件。
                    """)
            
            # ========== 事件处理 ==========
            self._setup_event_handlers(
                # 第一阶段组件
                file_input, example_text, analyze_btn,
                report_preview, report_editor, domain_info,
                update_report_btn, save_report_btn, load_report_btn,
                report_file_input, confirm_btn, progress_stage1,
                analysis_model_select,  # 添加模型选择
                # 第二阶段组件
                report_summary, use_inferred, template_select, generate_btn,
                schema_editor, validate_btn, format_btn,
                save_schema_btn, validation_result, validation_stats,
                progress_stage2, regenerate_btn, regenerate_progress,
                schema_model_select,  # Schema生成模型选择
                schema_history_dropdown, refresh_schema_history_btn, load_schema_history_btn,  # Schema页面历史记录组件
                # 导出组件
                export_format, include_report, include_metadata,
                export_btn, download_file, export_preview,
                visualization,
                # 可视化组件
                viz_options, viz_direction, generate_viz_btn, viz_stats, mermaid_code,
                # 历史记录组件
                refresh_history_btn, history_table, selected_file,
                load_selected_btn, delete_selected_btn, history_dropdown,
                # 状态
                state
            )
        
        return demo
    
    def _setup_event_handlers(self, *components):
        """设置事件处理器"""
        # 解构组件
        (file_input, example_text, analyze_btn,
         report_preview, report_editor, domain_info,
         update_report_btn, save_report_btn, load_report_btn,
         report_file_input, confirm_btn, progress_stage1,
         analysis_model_select,  # 分析模型选择
         report_summary, use_inferred, template_select, generate_btn,
         schema_editor, validate_btn, format_btn,
         save_schema_btn, validation_result, validation_stats,
         progress_stage2, regenerate_btn, regenerate_progress,
         schema_model_select,  # Schema生成模型选择
         schema_history_dropdown, refresh_schema_history_btn, load_schema_history_btn,  # Schema页面历史记录组件
         export_format, include_report, include_metadata,
         export_btn, download_file, export_preview,
         visualization,
         # 可视化组件
         viz_options, viz_direction, generate_viz_btn, viz_stats, mermaid_code,
         refresh_history_btn, history_table, selected_file,
         load_selected_btn, delete_selected_btn, history_dropdown,
         state) = components
        
        # 存储验证结果用于重新生成
        validation_errors_state = gr.State([])
        
        # ===== 第一阶段事件 =====
        
        # 分析文档（包含模型选择）
        analyze_btn.click(
            fn=self.analyze_document_with_model,
            inputs=[file_input, example_text, state, analysis_model_select],
            outputs=[
                report_preview, report_editor, domain_info,
                progress_stage1, state
            ]
        )
        
        # 更新报告
        update_report_btn.click(
            fn=self.update_report,
            inputs=[report_editor, state],
            outputs=[report_preview, state, progress_stage1]
        )
        
        # 保存报告
        save_report_btn.click(
            fn=self.save_report,
            inputs=[state],
            outputs=[progress_stage1]
        )
        
        # 加载报告按钮点击
        load_report_btn.click(
            fn=lambda: gr.update(visible=True),
            outputs=[report_file_input]
        )
        
        # 实际加载报告文件
        report_file_input.change(
            fn=self.load_report,
            inputs=[report_file_input, state],
            outputs=[
                report_preview, report_editor, domain_info,
                state, progress_stage1
            ]
        )
        
        # 确认报告，进入第二阶段
        confirm_btn.click(
            fn=self.confirm_report,
            inputs=[state],
            outputs=[report_summary, progress_stage1, state]
        )
        
        # ===== 第二阶段事件 =====
        
        # 生成Schema
        generate_btn.click(
            fn=self.generate_schema,
            inputs=[template_select, use_inferred, state],
            outputs=[schema_editor, progress_stage2, state]
        )
        
        # 验证Schema - 增强版本，控制重新生成按钮显示
        def validate_and_show_regenerate(schema_text, state):
            html, stats = self.validate_schema(schema_text, state)
            
            # 收集错误信息
            errors = []
            if stats and stats.get("errors", 0) > 0:
                # 从验证结果中提取错误信息
                # 这里简化处理，实际应该从validate_schema返回更详细的错误列表
                errors = self.last_validation_errors if hasattr(self, 'last_validation_errors') else []
            
            # 根据是否有错误决定是否显示重新生成按钮
            regenerate_visible = len(errors) > 0
            regenerate_progress_visible = regenerate_visible
            
            return (
                html,
                stats,
                gr.update(visible=regenerate_visible),
                gr.update(visible=regenerate_progress_visible),
                errors  # 存储错误信息
            )
        
        validate_btn.click(
            fn=validate_and_show_regenerate,
            inputs=[schema_editor, state],
            outputs=[
                validation_result, validation_stats,
                regenerate_btn, regenerate_progress,
                validation_errors_state
            ]
        )
        
        # 重新生成Schema（基于错误反馈）
        regenerate_btn.click(
            fn=self.regenerate_schema_with_errors,
            inputs=[schema_editor, template_select, state, validation_errors_state],
            outputs=[schema_editor, regenerate_progress, state]
        )
        
        # 格式化Schema
        format_btn.click(
            fn=self.format_schema,
            inputs=[schema_editor],
            outputs=[schema_editor]
        )
        
        # 保存Schema
        save_schema_btn.click(
            fn=self.save_schema,
            inputs=[schema_editor, state],
            outputs=[progress_stage2]
        )
        
        # ===== 导出事件 =====
        
        # 导出Schema
        export_btn.click(
            fn=self.export_schema,
            inputs=[
                export_format, include_report,
                include_metadata, state
            ],
            outputs=[export_preview, download_file]
        )
        
        # ===== 历史记录事件 =====
        
        # 刷新历史 - 同时更新下拉菜单
        def refresh_and_update_dropdown():
            records = self.refresh_history()
            # 生成下拉菜单选项 - 只包含报告文件（可加载的）
            dropdown_choices = []
            first_report = None
            for record in records:
                if len(record) >= 5:
                    # 只添加报告文件（包含report且是json）
                    if "report" in record[0].lower() and record[0].endswith(".json"):
                        choice_value = record[4]  # 完整路径
                        dropdown_choices.append(choice_value)
                        if first_report is None:
                            first_report = choice_value
            # 返回只有4列的表格数据
            table_data = [[r[0], r[1], r[2], r[3]] for r in records]
            print(f"[刷新历史] 找到 {len(dropdown_choices)} 个报告文件")
            print(f"[刷新历史] 选项: {dropdown_choices}")
            # 如果有报告文件，设置默认值
            return table_data, gr.update(choices=dropdown_choices, value=first_report)
        
        refresh_history_btn.click(
            fn=refresh_and_update_dropdown,
            outputs=[history_table, history_dropdown]
        )
        
        # 下拉菜单选择更新selected_file
        def on_dropdown_change(selected_value):
            print(f"[下拉菜单选择] 值: {selected_value}")
            return selected_value if selected_value else ""
        
        history_dropdown.change(
            fn=on_dropdown_change,
            inputs=[history_dropdown],
            outputs=[selected_file]
        )
        
        # 加载选中记录 - 使用selected_file的值（由dropdown.change更新）
        def load_from_selected(file_path, state):
            print(f"[加载历史记录] file_path: {file_path}")
            if not file_path:
                return "", "", {}, state, "❌ 请先从下拉菜单选择历史记录", "请先完成文档分析"
            return self.load_selected_history(file_path, state)
        
        load_selected_btn.click(
            fn=load_from_selected,
            inputs=[selected_file, state],
            outputs=[
                report_preview, report_editor, domain_info,
                state, progress_stage1, report_summary
            ]
        )
        
        # 删除选中记录
        def delete_and_refresh(file_path):
            result_msg = ""
            try:
                if not file_path or not os.path.exists(file_path):
                    result_msg = "❌ 文件不存在"
                else:
                    os.remove(file_path)
                    # 如果是JSON报告，同时删除对应的MD文件
                    if file_path.endswith(".json"):
                        md_path = file_path.replace(".json", ".md")
                        if os.path.exists(md_path):
                            os.remove(md_path)
                    result_msg = f"✅ 已删除: {os.path.basename(file_path)}"
            except Exception as e:
                result_msg = f"❌ 删除失败: {str(e)}"
            
            # 刷新并返回新数据
            records = self.refresh_history()
            dropdown_choices = []
            for record in records:
                if len(record) >= 5:
                    display = f"{record[0]} ({record[1]}, {record[2]})"
                    dropdown_choices.append((display, record[4]))
            table_data = [[r[0], r[1], r[2], r[3]] for r in records]
            return table_data, gr.update(choices=dropdown_choices), result_msg
        
        delete_selected_btn.click(
            fn=delete_and_refresh,
            inputs=[selected_file],
            outputs=[history_table, history_dropdown, progress_stage1]
        )
        
        # ===== Schema页面历史记录事件 =====
        
        # 刷新Schema页面的历史记录下拉菜单 - 只包含Schema文件
        def refresh_schema_history():
            records = self.refresh_history()
            # 生成下拉菜单选项 - 只包含Schema文件
            dropdown_choices = []
            first_schema = None
            for record in records:
                if len(record) >= 5:
                    # 只添加Schema文件（包含schema且是yaml文件）
                    filename = record[0].lower()
                    if "schema" in filename and (filename.endswith(".yaml") or filename.endswith(".yml")):
                        choice_value = record[4]  # 完整路径
                        dropdown_choices.append(choice_value)
                        if first_schema is None:
                            first_schema = choice_value
            print(f"[Schema页面刷新历史] 找到 {len(dropdown_choices)} 个Schema文件")
            return gr.update(choices=dropdown_choices, value=first_schema)
        
        refresh_schema_history_btn.click(
            fn=refresh_schema_history,
            outputs=[schema_history_dropdown]
        )
        
        # Schema页面加载历史Schema到编辑器
        def load_schema_history(file_path, state):
            print(f"[Schema页面加载历史] file_path: {file_path}")
            if not file_path:
                return "", "❌ 请先选择历史Schema", state
            
            try:
                if not os.path.exists(file_path):
                    return "", "❌ 文件不存在", state
                
                # 判断文件类型 - 加载Schema文件
                filename = os.path.basename(file_path).lower()
                if "schema" in filename and (filename.endswith(".yaml") or filename.endswith(".yml")):
                    # 读取Schema文件内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        schema_content = f.read()
                    
                    # 更新当前Schema
                    self.current_schema = schema_content
                    state["schema"] = schema_content
                    
                    return (
                        schema_content,
                        f"✅ 已加载Schema: {os.path.basename(file_path)}",
                        state
                    )
                else:
                    return "", "❌ 不支持的文件类型，请选择Schema文件", state
                    
            except Exception as e:
                return "", f"❌ 加载失败: {str(e)}", state
        
        load_schema_history_btn.click(
            fn=load_schema_history,
            inputs=[schema_history_dropdown, state],
            outputs=[schema_editor, progress_stage2, state]
        )
        
        # ===== Schema页面模型选择事件 =====
        
        # 切换Schema生成模型
        def on_schema_model_change(model_id):
            if model_id:
                success = self.agent.set_model(model_id)
                if success:
                    print(f"[Schema模型切换] 成功切换到: {model_id}")
                else:
                    print(f"[Schema模型切换] 切换失败: {model_id}")
        
        schema_model_select.change(
            fn=on_schema_model_change,
            inputs=[schema_model_select]
        )
        
        # ===== 可视化事件 =====
        
        # 生成实体关系图
        generate_viz_btn.click(
            fn=self.generate_visualization,
            inputs=[viz_options, viz_direction, state],
            outputs=[visualization, viz_stats, mermaid_code]
        )
    
    # ========== 事件处理方法 ==========
    
    def analyze_document_with_model(self, file_obj, text_content, state, model_id=None):
        """第一阶段：分析文档（支持模型选择）"""
        # 如果指定了模型，切换模型
        if model_id:
            self.agent.set_model(model_id)
        return self.analyze_document(file_obj, text_content, state)
    
    def analyze_document(self, file_obj, text_content, state):
        """第一阶段：分析文档"""
        try:
            progress = "🔄 开始文档分析..."
            
            # 确定输入源
            original_filename = None
            if file_obj:
                # 处理上传的文件
                if hasattr(file_obj, 'name'):
                    doc_path = file_obj.name
                else:
                    doc_path = file_obj
                
                # 获取原始文件名
                original_filename = os.path.basename(doc_path)
                
                # 复制到输入目录
                import shutil
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.basename(doc_path)
                saved_path = os.path.join(self.input_dir, f"{timestamp}_{filename}")
                shutil.copy2(doc_path, saved_path)
                doc_path = saved_path
                progress += f"\n📁 文件已保存: {saved_path}"
                
            elif text_content:
                # 处理文本输入
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_path = os.path.join(self.input_dir, f"text_input_{timestamp}.txt")
                original_filename = f"text_input_{timestamp}.txt"
                with open(doc_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                progress += f"\n📝 文本已保存: {doc_path}"
                
            else:
                return "", "", {}, "❌ 请上传文档或输入文本", state
            
            progress += "\n🔍 正在进行领域识别和文档分析..."
            
            # 执行分析
            report = self.agent.stage1_analyze_document(doc_path)
            self.current_report = report
            
            # 更新状态，包含原始文件名
            state["report"] = report.to_dict()
            state["report_path"] = doc_path
            state["original_filename"] = original_filename
            
            # 提取领域信息
            domain_info = {
                "domain": report.domain,
                "sub_domain": report.sub_domain,
                "keywords": report.keywords,
                "confidence": report.confidence
            }
            
            progress += f"\n✅ 分析完成！"
            progress += f"\n  - 领域: {report.domain}"
            progress += f"\n  - 实体: {len(report.entities)}个"
            progress += f"\n  - 关系: {len(report.relations)}个"
            
            return (
                report.to_markdown(),
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                domain_info,
                progress,
                state
            )
            
        except Exception as e:
            error_msg = f"❌ 分析失败: {str(e)}"
            return "", "", {}, error_msg, state
    
    def update_report(self, report_json, state):
        """更新报告内容"""
        try:
            # 解析JSON
            report_dict = json.loads(report_json)
            
            # 更新报告
            report = self.agent.edit_report(report_dict)
            self.current_report = report
            
            # 更新状态
            state["report"] = report.to_dict()
            
            return (
                report.to_markdown(),
                state,
                "✅ 报告已更新"
            )
            
        except json.JSONDecodeError as e:
            return "", state, f"❌ JSON格式错误: {str(e)}"
        except Exception as e:
            return "", state, f"❌ 更新失败: {str(e)}"
    
    def save_report(self, state):
        """保存当前报告"""
        try:
            if not self.current_report:
                return "❌ 没有可保存的报告"
            
            # 获取原始文件名
            original_filename = state.get("original_filename")
            
            # 保存报告，传入原始文件名以生成标准化的输出文件名
            path = self.agent.save_report(self.current_report, original_filename=original_filename)
            return f"✅ 报告已保存: {path}"
            
        except Exception as e:
            return f"❌ 保存失败: {str(e)}"
    
    def load_report(self, file_obj, state):
        """加载报告文件"""
        try:
            if not file_obj:
                return "", "", {}, state, "请选择报告文件"
            
            # 获取文件路径
            if hasattr(file_obj, 'name'):
                report_path = file_obj.name
            else:
                report_path = file_obj
            
            # 加载报告
            report = self.agent.load_report(report_path)
            self.current_report = report
            
            # 更新状态
            state["report"] = report.to_dict()
            
            # 提取领域信息
            domain_info = {
                "domain": report.domain,
                "sub_domain": report.sub_domain,
                "keywords": report.keywords,
                "confidence": report.confidence
            }
            
            return (
                report.to_markdown(),
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                domain_info,
                state,
                f"✅ 已加载报告: {os.path.basename(report_path)}"
            )
            
        except Exception as e:
            return "", "", {}, state, f"❌ 加载失败: {str(e)}"
    
    def confirm_report(self, state):
        """确认报告，准备进入第二阶段"""
        try:
            if not state.get("report"):
                return "", "❌ 请先完成文档分析", state
            
            report_dict = state["report"]
            
            # 生成摘要，包括推测的实体和关系
            inferred_entities = report_dict.get('inferred_entities', [])
            inferred_relations = report_dict.get('inferred_relations', [])
            
            summary = f"""📊 分析报告摘要
领域: {report_dict.get('domain', '未知')}
子领域: {report_dict.get('sub_domain', '未知')}
实体类型: {len(report_dict.get('entities', []))} 个
关系类型: {len(report_dict.get('relations', []))} 个
属性: {len(report_dict.get('attributes', []))} 个
推测的实体: {len(inferred_entities)} 个
推测的关系: {len(inferred_relations)} 个
置信度: {report_dict.get('confidence', 0):.2%}
"""
            
            return summary, "✅ 报告已确认，可以进行Schema生成", state
            
        except Exception as e:
            return "", f"❌ 确认失败: {str(e)}", state
    
    def generate_schema(self, template_id, use_inferred, state):
        """第二阶段：生成Schema"""
        try:
            if not self.current_report:
                if state.get("report"):
                    # 从状态恢复报告
                    self.current_report = DocumentAnalysisReport()
                    self.current_report.from_dict(state["report"])
                else:
                    return "", "❌ 请先完成文档分析并确认报告", state
            
            # 如果选择使用推测的实体和关系，则合并到报告中
            if use_inferred:
                progress = "⚡ 正在生成Schema（包含推测的实体和关系）..."
                # 创建一个临时报告副本，将推测的内容合并进去
                temp_report = DocumentAnalysisReport()
                temp_report.from_dict(self.current_report.to_dict())
                
                # 合并推测的实体到实体列表
                for inferred_entity in temp_report.inferred_entities:
                    # 检查是否已存在同名实体
                    exists = any(e['name'] == inferred_entity.get('name') for e in temp_report.entities)
                    if not exists:
                        temp_report.entities.append({
                            'name': inferred_entity.get('name'),
                            'cn_name': inferred_entity.get('cn_name', inferred_entity.get('name')),
                            'description': f"推测的实体: {inferred_entity.get('reason', '')}",
                            'confidence': 0.7
                        })
                
                # 合并推测的关系到关系列表
                for inferred_relation in temp_report.inferred_relations:
                    # 检查是否已存在同名关系
                    exists = any(r['name'] == inferred_relation.get('name') for r in temp_report.relations)
                    if not exists:
                        temp_report.relations.append({
                            'name': inferred_relation.get('name'),
                            'cn_name': inferred_relation.get('cn_name', inferred_relation.get('name')),
                            'source': inferred_relation.get('source'),
                            'target': inferred_relation.get('target'),
                            'description': f"推测的关系: {inferred_relation.get('reason', '')}",
                            'confidence': 0.7
                        })
                
                # 使用合并后的报告生成Schema
                schema = self.agent.stage2_generate_schema(
                    temp_report,
                    template_id
                )
            else:
                progress = "⚡ 正在生成Schema..."
                # 使用原始报告生成Schema
                schema = self.agent.stage2_generate_schema(
                    self.current_report,
                    template_id
                )
            
            self.current_schema = schema
            state["schema"] = schema
            
            progress = "✅ Schema生成完成！"
            
            return schema, progress, state
            
        except Exception as e:
            return "", f"❌ 生成失败: {str(e)}", state
    
    def validate_schema(self, schema_text, state):
        """验证Schema - 使用validation_rules.json中定义的规则"""
        try:
            # 检查Schema是否为空
            if not schema_text or not schema_text.strip():
                return (
                    "<p style='color:orange'>⚠️ 请先生成或输入Schema后再进行验证</p>",
                    {
                        "total_rules": 0,
                        "passed": 0,
                        "failed": 0,
                        "errors": 0,
                        "warnings": 0,
                        "info": 0,
                        "is_valid": False
                    }
                )
            
            # 使用新的Schema解析器直接解析编辑器中的内容
            from schema_parser import SchemaParser
            
            # 验证并解析Schema文本
            is_valid_format, ast, parse_error = SchemaParser.validate_and_parse(schema_text)
            
            if not is_valid_format:
                return (
                    f"<p style='color:red'>❌ Schema格式错误: {parse_error}</p>",
                    {
                        "total_rules": 0,
                        "passed": 0,
                        "failed": 1,
                        "errors": 1,
                        "warnings": 0,
                        "info": 0,
                        "is_valid": False,
                        "format_error": parse_error
                    }
                )
            
            # 确保自定义验证器已加载规则文件
            if not hasattr(self.custom_validator, 'rules') or not self.custom_validator.rules:
                self.custom_validator.load_rules_from_file()
            
            # 使用自定义验证器验证（传入AST和Schema文本）
            results = self.custom_validator.validate(ast, schema_text)
            
            # 保存错误信息用于重新生成
            self.last_validation_errors = []
            if results.get("errors"):
                for error in results["errors"]:
                    error_dict = {
                        "message": error.message if hasattr(error, 'message') else str(error),
                        "rule_name": error.rule_name if hasattr(error, 'rule_name') else "",
                        "details": error.details if hasattr(error, 'details') else ""
                    }
                    self.last_validation_errors.append(error_dict)
            
            # 生成增强的HTML报告
            html = self._generate_validation_html_enhanced(results)
            
            # 统计信息
            stats = {
                "total_rules": results.get("total_rules", 0),
                "passed": results.get("passed", 0),
                "failed": results.get("failed", 0),
                "errors": len(results.get("errors", [])),
                "warnings": len(results.get("warnings", [])),
                "info": len(results.get("info", [])),
                "is_valid": results.get("is_valid", False)
            }
            
            return html, stats
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"验证错误详情: {error_detail}")
            return f"<p style='color:red'>❌ 验证失败: {str(e)}</p>", {}
    
    def regenerate_schema_with_errors(self, previous_schema, template_id, state, validation_errors):
        """基于验证错误重新生成Schema"""
        try:
            if not self.current_report:
                if state.get("report"):
                    # 从状态恢复报告
                    self.current_report = DocumentAnalysisReport()
                    self.current_report.from_dict(state["report"])
                else:
                    return "", "❌ 请先完成文档分析并确认报告", state
            
            progress = "🔄 正在基于错误反馈重新生成Schema..."
            
            # 调用增强的生成方法，传入之前的schema和错误信息
            schema = self.agent.stage2_generate_schema(
                self.current_report,
                template_id,
                previous_schema=previous_schema,
                validation_errors=self.last_validation_errors if hasattr(self, 'last_validation_errors') else []
            )
            
            self.current_schema = schema
            state["schema"] = schema
            
            progress = "✅ Schema重新生成完成！请再次验证以确认错误已修复。"
            
            return schema, progress, state
            
        except Exception as e:
            return "", f"❌ 重新生成失败: {str(e)}", state
    
    def _generate_validation_html_enhanced(self, results: Dict) -> str:
        """生成增强的验证结果HTML - 使用自定义验证器的结果格式"""
        html = "<div style='font-family: Arial, sans-serif;'>"
        
        # 总体状态
        is_valid = results.get("is_valid", False)
        summary = results.get("summary", "")
        
        if is_valid:
            html += f"<h3 style='color: green;'>✅ {summary if summary else 'Schema验证通过'}</h3>"
        else:
            html += f"<h3 style='color: #d9534f;'>❌ {summary if summary else 'Schema验证失败'}</h3>"
        
        # 统计信息
        html += f"<p><strong>规则总数:</strong> {results.get('total_rules', 0)}, "
        html += f"<strong style='color: green;'>通过:</strong> {results.get('passed', 0)}, "
        html += f"<strong style='color: red;'>失败:</strong> {results.get('failed', 0)}</p>"
        
        # 错误列表
        errors = results.get("errors", [])
        if errors:
            html += "<h4 style='color: #d9534f;'>❌ 错误（必须修复）:</h4><ul>"
            for error in errors:
                if hasattr(error, 'rule_name') and hasattr(error, 'message'):
                    html += f"<li style='color: #d9534f;'><strong>[{error.rule_name}]</strong> {error.message}"
                    if hasattr(error, 'details') and error.details:
                        html += f"<br><small style='color: #666;'>详情: {error.details}</small>"
                    html += "</li>"
                else:
                    html += f"<li style='color: #d9534f;'>{str(error)}</li>"
            html += "</ul>"
        
        # 警告列表
        warnings = results.get("warnings", [])
        if warnings:
            html += "<h4 style='color: #f0ad4e;'>⚠️ 警告（建议修复）:</h4><ul>"
            for warning in warnings:
                if hasattr(warning, 'rule_name') and hasattr(warning, 'message'):
                    html += f"<li style='color: #f0ad4e;'><strong>[{warning.rule_name}]</strong> {warning.message}"
                    if hasattr(warning, 'details') and warning.details:
                        html += f"<br><small style='color: #666;'>详情: {warning.details}</small>"
                    html += "</li>"
                else:
                    html += f"<li style='color: #f0ad4e;'>{str(warning)}</li>"
            html += "</ul>"
        
        # 信息列表
        info = results.get("info", [])
        if info:
            html += "<h4 style='color: #5bc0de;'>ℹ️ 提示信息:</h4><ul>"
            for item in info:
                if hasattr(item, 'rule_name') and hasattr(item, 'message'):
                    html += f"<li style='color: #5bc0de;'><strong>[{item.rule_name}]</strong> {item.message}</li>"
                else:
                    html += f"<li style='color: #5bc0de;'>{str(item)}</li>"
            html += "</ul>"
        
        # 显示所有执行的规则（可折叠）
        if results.get("results"):
            html += """
            <details>
            <summary style='cursor: pointer; font-weight: bold; margin-top: 10px;'>
            查看所有规则执行详情 ▼
            </summary>
            <div style='margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 5px;'>
            """
            
            for result in results.get("results", []):
                if hasattr(result, 'passed') and hasattr(result, 'rule_name'):
                    if result.passed:
                        color = "green"
                        icon = "✅"
                    else:
                        color = "#d9534f" if result.severity == "error" else "#f0ad4e" if result.severity == "warning" else "#5bc0de"
                        icon = "❌" if result.severity == "error" else "⚠️" if result.severity == "warning" else "ℹ️"
                    
                    html += f"<div style='margin: 5px 0;'>"
                    html += f"<span style='color: {color};'>{icon} <strong>{result.rule_name}:</strong> {result.message}</span>"
                    html += "</div>"
            
            html += "</div></details>"
        
        html += "</div>"
        return html
    
    def format_schema(self, schema_text):
        """格式化Schema"""
        try:
            from schema_parser import SchemaParser
            return SchemaParser.format_schema(schema_text)
        except Exception as e:
            return schema_text
    
    def save_schema(self, schema_text, state):
        """保存Schema"""
        try:
            # 获取原始文件名
            original_filename = state.get("original_filename")
            
            # 使用agent的save_schema方法，传入原始文件名
            filepath = self.agent.save_schema(schema_text, original_filename=original_filename)
            
            return f"✅ Schema已保存: {filepath}"
            
        except Exception as e:
            return f"❌ 保存失败: {str(e)}"
    
    def export_schema(self, export_format, include_report, include_metadata, state):
        """导出Schema"""
        try:
            if not self.current_schema:
                return "", None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 准备导出内容
            export_content = ""
            
            # 添加元数据
            if include_metadata:
                export_content += f"""# Schema Export
# Generated: {datetime.now().isoformat()}
# Format: {export_format}
"""
                if state.get("report"):
                    report = state["report"]
                    export_content += f"""# Domain: {report.get('domain', 'Unknown')}
# Sub-domain: {report.get('sub_domain', 'Unknown')}

"""
            
            # 添加报告
            if include_report and self.current_report:
                export_content += "# Analysis Report\n"
                export_content += "# " + "="*50 + "\n"
                export_content += "# " + self.current_report.to_markdown().replace("\n", "\n# ") + "\n"
                export_content += "# " + "="*50 + "\n\n"
            
            # 添加Schema内容
            if export_format == "JSON Schema":
                schema_data = {
                    "schema": self.current_schema,
                    "metadata": {
                        "generated": datetime.now().isoformat(),
                        "domain": state.get("report", {}).get("domain", "Unknown")
                    }
                }
                export_content = json.dumps(schema_data, indent=2, ensure_ascii=False)
                file_ext = "json"
            elif export_format == "YAML":
                export_content += self.current_schema
                file_ext = "yaml"
            elif export_format == "Markdown文档":
                export_content += f"""
## Generated Schema

```yaml
{self.current_schema}
```
"""
                file_ext = "md"
            else:  # OpenSPG/KAG
                export_content += self.current_schema
                file_ext = "txt"
            
            # 保存文件
            filename = f"export_{timestamp}.{file_ext}"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(export_content)
            
            return export_content, gr.File(value=filepath, visible=True)
            
        except Exception as e:
            return f"导出失败: {str(e)}", None
    
    def refresh_history(self):
        """刷新历史记录"""
        try:
            records = []
            
            # 扫描output目录
            for filename in os.listdir(self.output_dir):
                filepath = os.path.join(self.output_dir, filename)
                if os.path.isfile(filepath):
                    # 判断文件类型
                    if "report" in filename:
                        file_type = "分析报告"
                        # 尝试读取领域信息
                        domain = "未知"
                        if filename.endswith(".json"):
                            try:
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    domain = data.get("domain", "未知")
                            except:
                                pass
                    elif "schema" in filename:
                        file_type = "Schema"
                        domain = "-"
                    else:
                        file_type = "其他"
                        domain = "-"
                    
                    # 获取文件时间
                    mtime = os.path.getmtime(filepath)
                    time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    records.append([filename, file_type, domain, time_str, filepath])
            
            # 按时间排序
            records.sort(key=lambda x: x[3], reverse=True)
            
            return records
            
        except Exception as e:
            print(f"刷新历史记录失败: {str(e)}")
            return []
    
    def select_history(self, evt: gr.SelectData, data):
        """选择历史记录"""
        try:
            print(f"选择事件: index={evt.index}, value={evt.value}")
            print(f"数据类型: {type(data)}, 数据内容: {data}")
            
            row_index = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            
            if data is not None:
                # 处理 DataFrame 和 list 两种情况
                if hasattr(data, 'iloc'):
                    # pandas DataFrame - 路径在第5列（索引4）
                    if row_index < len(data):
                        result = str(data.iloc[row_index, 4])
                        print(f"从DataFrame获取路径: {result}")
                        return result
                elif hasattr(data, 'values'):
                    # DataFrame with values
                    if row_index < len(data.values):
                        result = str(data.values[row_index][4])
                        print(f"从DataFrame.values获取路径: {result}")
                        return result
                else:
                    # list
                    if row_index < len(data):
                        result = str(data[row_index][4])
                        print(f"从list获取路径: {result}")
                        return result
        except Exception as e:
            import traceback
            print(f"选择历史记录失败: {str(e)}")
            print(traceback.format_exc())
        return ""
    
    def load_selected_history(self, file_path, state):
        """加载选中的历史记录"""
        try:
            if not file_path or not os.path.exists(file_path):
                return "", "", {}, state, "❌ 文件不存在", "请先完成文档分析"
            
            # 判断文件类型
            if "report" in os.path.basename(file_path) and file_path.endswith(".json"):
                # 加载报告
                report = self.agent.load_report(file_path)
                self.current_report = report
                
                # 更新状态
                state["report"] = report.to_dict()
                
                # 提取领域信息
                domain_info = {
                    "domain": report.domain,
                    "sub_domain": report.sub_domain,
                    "keywords": report.keywords,
                    "confidence": report.confidence
                }
                
                # 生成报告摘要（与confirm_report相同的格式）
                report_dict = report.to_dict()
                inferred_entities = report_dict.get('inferred_entities', [])
                inferred_relations = report_dict.get('inferred_relations', [])
                
                report_summary = f"""📊 分析报告摘要
领域: {report_dict.get('domain', '未知')}
子领域: {report_dict.get('sub_domain', '未知')}
实体类型: {len(report_dict.get('entities', []))} 个
关系类型: {len(report_dict.get('relations', []))} 个
属性: {len(report_dict.get('attributes', []))} 个
推测的实体: {len(inferred_entities)} 个
推测的关系: {len(inferred_relations)} 个
置信度: {report_dict.get('confidence', 0):.2%}
"""
                
                return (
                    report.to_markdown(),
                    json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
                    domain_info,
                    state,
                    f"✅ 已加载: {os.path.basename(file_path)}",
                    report_summary
                )
            else:
                return "", "", {}, state, "❌ 不支持的文件类型", "请先完成文档分析"
                
        except Exception as e:
            return "", "", {}, state, f"❌ 加载失败: {str(e)}", "请先完成文档分析"
    
    def delete_selected_history(self, file_path):
        """删除选中的历史记录"""
        try:
            if not file_path or not os.path.exists(file_path):
                return self.refresh_history(), "❌ 文件不存在"
            
            os.remove(file_path)
            
            # 如果是JSON报告，同时删除对应的MD文件
            if file_path.endswith(".json"):
                md_path = file_path.replace(".json", ".md")
                if os.path.exists(md_path):
                    os.remove(md_path)
            
            return self.refresh_history(), f"✅ 已删除: {os.path.basename(file_path)}"
            
        except Exception as e:
            return self.refresh_history(), f"❌ 删除失败: {str(e)}"
    
    def _generate_validation_html(self, results: Dict) -> str:
        """生成验证结果HTML"""
        html = "<div style='font-family: Arial, sans-serif;'>"
        
        # 总体状态
        is_valid = results.get("is_valid", False)
        
        if is_valid:
            html += "<h3 style='color: green;'>✅ Schema验证通过</h3>"
        else:
            html += "<h3 style='color: red;'>❌ Schema验证失败</h3>"
        
        # 错误列表
        errors = results.get("errors", [])
        if errors:
            html += "<h4>错误:</h4><ul>"
            for error in errors:
                if hasattr(error, 'message'):
                    html += f"<li style='color: red;'>{error.message}</li>"
                else:
                    html += f"<li style='color: red;'>{str(error)}</li>"
            html += "</ul>"
        
        # 警告列表
        warnings = results.get("warnings", [])
        if warnings:
            html += "<h4>警告:</h4><ul>"
            for warning in warnings:
                if hasattr(warning, 'message'):
                    html += f"<li style='color: orange;'>{warning.message}</li>"
                else:
                    html += f"<li style='color: orange;'>{str(warning)}</li>"
            html += "</ul>"
        
        html += "</div>"
        return html
    
    def _get_empty_visualization_html(self) -> str:
        """返回空的可视化HTML占位符"""
        return """
        <div style="
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 60px 20px;
            text-align: center;
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
            min-height: 400px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        ">
            <div style="font-size: 64px; margin-bottom: 20px;">📊</div>
            <h3 style="color: #666; margin: 0 0 10px 0;">实体关系图</h3>
            <p style="color: #999; margin: 0;">
                请先生成或加载Schema，然后点击"生成实体关系图"按钮
            </p>
        </div>
        """
    
    def generate_visualization(self, viz_options: List[str], viz_direction: str, state: Dict) -> Tuple[str, Dict, str]:
        """生成Schema的实体关系图可视化"""
        try:
            # 检查是否有Schema
            schema_text = self.current_schema or state.get("schema", "")
            if not schema_text:
                return (
                    self._get_empty_visualization_html(),
                    {"error": "没有可用的Schema"},
                    ""
                )
            
            # 解析Schema
            from schema_parser import SchemaParser
            is_valid, ast, error = SchemaParser.validate_and_parse(schema_text)
            
            if not is_valid:
                return (
                    f"""<div style="color: red; padding: 20px; border: 1px solid red; border-radius: 5px;">
                        <h4>❌ Schema解析失败</h4>
                        <p>{error}</p>
                    </div>""",
                    {"error": error},
                    ""
                )
            
            # 解析选项
            show_attributes = "显示属性" in viz_options
            show_cn_names = "显示中文名称" in viz_options
            show_data_types = "显示数据类型" in viz_options
            show_kg_view = "知识图谱视图" in viz_options
            
            # 生成Mermaid代码
            mermaid_code = self._generate_mermaid_er_diagram(
                ast, 
                direction=viz_direction,
                show_attributes=show_attributes,
                show_cn_names=show_cn_names,
                show_data_types=show_data_types
            )
            
            # 统计信息
            entity_count = len(ast.get("types", []))
            relation_count = sum(len(t.get("relations", [])) for t in ast.get("types", []))
            attribute_count = sum(len(t.get("properties", [])) for t in ast.get("types", []))
            
            stats = {
                "namespace": ast.get("namespace", "Unknown"),
                "实体数量": entity_count,
                "关系数量": relation_count,
                "属性总数": attribute_count,
                "平均属性数": round(attribute_count / entity_count, 1) if entity_count > 0 else 0
            }
            
            # 根据选项决定显示哪种视图
            if show_kg_view:
                # 生成知识图谱视图
                visualization_html = self._generate_knowledge_graph_html(ast, stats)
            else:
                # 生成包含Mermaid渲染的HTML
                visualization_html = self._generate_mermaid_html(mermaid_code, stats)
            
            return visualization_html, stats, mermaid_code
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"可视化生成错误: {error_detail}")
            return (
                f"""<div style="color: red; padding: 20px; border: 1px solid red; border-radius: 5px;">
                    <h4>❌ 可视化生成失败</h4>
                    <p>{str(e)}</p>
                </div>""",
                {"error": str(e)},
                ""
            )
    
    def _generate_mermaid_er_diagram(self, ast: Dict, direction: str = "TB", 
                                      show_attributes: bool = True,
                                      show_cn_names: bool = True,
                                      show_data_types: bool = True) -> str:
        """根据AST生成Mermaid ER图代码"""
        lines = [f"erDiagram"]
        
        entities = ast.get("types", [])
        
        # 收集所有关系
        all_relations = []
        for entity in entities:
            entity_name = entity.get("name", "Unknown")
            for rel in entity.get("relations", []):
                rel_name = rel.get("name", "relates")
                rel_cn_name = rel.get("cn_name", rel_name)
                target = rel.get("target", "Unknown")
                
                # 使用中文名称作为关系标签
                label = rel_cn_name if show_cn_names else rel_name
                all_relations.append((entity_name, target, label))
        
        # 添加关系定义
        for source, target, label in all_relations:
            # 使用 ||--o{ 表示一对多关系
            lines.append(f"    {source} ||--o{{ {target} : \"{label}\"")
        
        # 添加实体定义（带属性）
        for entity in entities:
            entity_name = entity.get("name", "Unknown")
            entity_cn_name = entity.get("cn_name", entity_name)
            
            # 实体开始
            display_name = f"{entity_name}"
            lines.append(f"    {display_name} {{")
            
            # 添加属性
            if show_attributes:
                for prop in entity.get("properties", []):
                    prop_name = prop.get("name", "unknown")
                    prop_cn_name = prop.get("cn_name", prop_name)
                    data_type = prop.get("data_type", "Text")
                    
                    # 简化数据类型显示
                    type_map = {
                        "Text": "string",
                        "Integer": "int",
                        "Float": "float"
                    }
                    simple_type = type_map.get(data_type, "string")
                    
                    if show_cn_names and prop_cn_name != prop_name:
                        if show_data_types:
                            lines.append(f"        {simple_type} {prop_name} \"{prop_cn_name}\"")
                        else:
                            lines.append(f"        string {prop_name} \"{prop_cn_name}\"")
                    else:
                        if show_data_types:
                            lines.append(f"        {simple_type} {prop_name}")
                        else:
                            lines.append(f"        string {prop_name}")
            
            lines.append("    }")
        
        return "\n".join(lines)
    
    def _generate_knowledge_graph_html(self, ast: Dict, stats: Dict) -> str:
        """生成Neo4j风格的知识图谱可视化HTML - 使用iframe确保脚本正常执行"""
        entities = ast.get("types", [])
        
        # 构建节点和边的数据
        nodes = []
        edges = []
        
        # 为不同实体类型定义颜色
        colors = [
            "#4C8BF5", "#34A853", "#FBBC04", "#EA4335", "#9334E6",
            "#00ACC1", "#FF7043", "#8E24AA", "#43A047", "#1E88E5",
        ]
        
        # 创建实体节点
        for i, entity in enumerate(entities):
            entity_name = entity.get("name", "Unknown")
            entity_cn_name = entity.get("cn_name", entity_name)
            node_color = colors[i % len(colors)]
            
            nodes.append({
                "id": entity_name,
                "label": entity_cn_name,
                "title": f"{entity_cn_name} ({entity_name})",
                "color": {"background": node_color, "border": node_color},
                "font": {"color": "#ffffff", "size": 14},
                "shape": "dot",
                "size": 30,
                "borderWidth": 2
            })
        
        # 添加关系边
        edge_id = 0
        for entity in entities:
            source_name = entity.get("name", "Unknown")
            for rel in entity.get("relations", []):
                target_name = rel.get("target", "")
                rel_cn_name = rel.get("cn_name", rel.get("name", "relates"))
                target_exists = any(e.get("name") == target_name for e in entities)
                if target_exists:
                    edges.append({
                        "id": f"edge_{edge_id}",
                        "from": source_name,
                        "to": target_name,
                        "label": rel_cn_name,
                        "arrows": "to",
                        "color": {"color": "#848484"},
                        "font": {"size": 11, "background": "white"},
                        "smooth": {"type": "curvedCW", "roundness": 0.2},
                        "width": 2
                    })
                    edge_id += 1
        
        import json
        nodes_json = json.dumps(nodes, ensure_ascii=False)
        edges_json = json.dumps(edges, ensure_ascii=False)
        
        # 构建图例
        legend_items = ""
        for i, entity in enumerate(entities):
            color = colors[i % len(colors)]
            cn_name = entity.get("cn_name", entity.get("name"))
            legend_items += f'<span style="display:inline-flex;align-items:center;margin-right:12px;"><span style="width:12px;height:12px;border-radius:50%;background:{color};display:inline-block;margin-right:4px;"></span>{cn_name}</span>'
        
        # 使用srcdoc创建独立的iframe来确保JavaScript正确执行
        iframe_content = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; background: transparent; width: 100%; height: 100%; overflow: hidden; }}
        #graph {{ width: 100%; height: 100%; min-height: 500px; }}
    </style>
</head>
<body>
    <div id="graph"></div>
    <script>
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});
        var container = document.getElementById("graph");
        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
            physics: {{
                enabled: true,
                solver: "forceAtlas2Based",
                forceAtlas2Based: {{
                    gravitationalConstant: -80,
                    centralGravity: 0.02,
                    springLength: 120,
                    springConstant: 0.08,
                    damping: 0.4,
                    avoidOverlap: 0.5
                }},
                stabilization: {{ enabled: true, iterations: 150, updateInterval: 20 }}
            }},
            interaction: {{ 
                hover: true, 
                tooltipDelay: 200, 
                zoomView: true,
                dragNodes: true,
                dragView: true
            }},
            edges: {{ selectionWidth: 2, smooth: {{ type: "curvedCW", roundness: 0.2 }} }},
            nodes: {{ scaling: {{ min: 20, max: 40 }} }}
        }};
        var network = new vis.Network(container, data, options);
        
        // 稳定后禁用物理引擎
        network.on("stabilizationIterationsDone", function() {{
            network.setOptions({{ physics: {{ enabled: false }} }});
            // 居中显示所有节点
            network.fit({{
                animation: {{
                    duration: 500,
                    easingFunction: "easeInOutQuad"
                }}
            }});
        }});
        
        // 限制节点拖动范围 - 拖动后自动调整视图
        network.on("dragEnd", function(params) {{
            if (params.nodes.length > 0) {{
                // 获取所有节点位置，检查是否需要调整视图
                var positions = network.getPositions();
                var needsFit = false;
                var viewPosition = network.getViewPosition();
                var scale = network.getScale();
                
                // 如果节点被拖动到边缘，自动调整视图
                for (var nodeId in positions) {{
                    var pos = positions[nodeId];
                    var canvasPos = network.canvasToDOM(pos);
                    if (canvasPos.x < 50 || canvasPos.x > container.clientWidth - 50 ||
                        canvasPos.y < 50 || canvasPos.y > container.clientHeight - 50) {{
                        needsFit = true;
                        break;
                    }}
                }}
                
                if (needsFit) {{
                    network.fit({{
                        animation: {{
                            duration: 300,
                            easingFunction: "easeInOutQuad"
                        }}
                    }});
                }}
            }}
        }});
    </script>
</body>
</html>'''
        
        # 对iframe内容进行HTML转义（用于srcdoc属性）
        import html as html_module
        iframe_srcdoc = html_module.escape(iframe_content)
        
        html = f'''
<div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);padding:20px;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,0.3);overflow:visible;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,0.1);">
        <h3 style="margin:0;color:#fff;font-weight:500;">🧠 {stats.get('namespace', 'Schema')} 知识图谱</h3>
        <div style="font-size:12px;color:rgba(255,255,255,0.7);">
            <span style="margin-right:15px;">🔵 实体: {stats.get('实体数量', 0)}</span>
            <span>➡️ 关系: {stats.get('关系数量', 0)}</span>
        </div>
    </div>
    <div style="background:rgba(255,255,255,0.02);border-radius:8px;padding:8px;margin-bottom:10px;">
        <span style="font-size:11px;color:rgba(255,255,255,0.6);">💡 拖拽节点调整位置 | 滚轮缩放 | 点击节点高亮关系</span>
    </div>
    <iframe srcdoc="{iframe_srcdoc}" style="width:100%;height:550px;border:none;border-radius:8px;background:rgba(0,0,0,0.2);display:block;"></iframe>
    <div style="margin-top:15px;padding:12px;background:rgba(255,255,255,0.05);border-radius:8px;min-height:50px;">
        <div style="font-size:12px;color:rgba(255,255,255,0.5);margin-bottom:10px;">图例：</div>
        <div style="display:flex;flex-wrap:wrap;color:rgba(255,255,255,0.8);font-size:12px;gap:8px;">{legend_items}</div>
    </div>
</div>'''
        
        return html
    
    def _generate_mermaid_html(self, mermaid_code: str, stats: Dict) -> str:
        """生成包含Mermaid渲染的HTML"""
        # 转义特殊字符
        escaped_code = mermaid_code.replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n")
        
        html = f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee;">
                <h3 style="margin: 0; color: #333;">
                    📊 {stats.get('namespace', 'Schema')} 实体关系图
                </h3>
                <div style="font-size: 12px; color: #666;">
                    实体: {stats.get('实体数量', 0)} | 
                    关系: {stats.get('关系数量', 0)} | 
                    属性: {stats.get('属性总数', 0)}
                </div>
            </div>
            <div class="mermaid" style="text-align: center; overflow-x: auto;">
{mermaid_code}
            </div>
        </div>
        
        <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function() {{
            function initializeMermaid() {{
                if (typeof mermaid !== 'undefined') {{
                    mermaid.initialize({{ 
                        startOnLoad: true,
                        theme: 'default',
                        securityLevel: 'loose',
                        er: {{
                            diagramPadding: 20,
                            layoutDirection: '{stats.get('layoutDirection', 'TB')}',
                            minEntityWidth: 100,
                            minEntityHeight: 75,
                            entityPadding: 15,
                            useMaxWidth: true
                        }},
                        themeVariables: {{
                            primaryColor: '#4a90d9',
                            primaryTextColor: '#fff',
                            primaryBorderColor: '#2d6cb5',
                            lineColor: '#666',
                            secondaryColor: '#f0f4f8',
                            tertiaryColor: '#fff'
                        }}
                    }});
                    try {{
                        mermaid.init(undefined, '.mermaid');
                    }} catch (e) {{
                        console.error('Mermaid initialization failed:', e);
                    }}
                }} else {{
                    setTimeout(initializeMermaid, 100);
                }}
            }}
            
            // Load mermaid dynamically if not already loaded
            if (typeof mermaid === 'undefined') {{
                var script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js';
                script.onload = initializeMermaid;
                document.head.appendChild(script);
            }} else {{
                initializeMermaid();
            }}
        }});
        </script>
        """
        
        return html


# 此模块作为库被 run_schema_generator.py 导入使用
# 也可以通过 python run_schema_generator.py 启动系统

def main():
    """启动UI"""
    ui = SchemaUI()
    demo = ui.create_interface()
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=8888,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft()
    )


if __name__ == "__main__":
    main()
