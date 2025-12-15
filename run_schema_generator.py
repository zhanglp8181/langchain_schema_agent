#!/usr/bin/env python3
"""
智能Schema生成系统启动脚本
"""

import sys
import os

def main():
    """主函数"""
    print("="*70)
    print("🚀 智能Schema自动生成系统")
    print("="*70)
    print("\n系统特点：")
    print("  ✨ 智能分析：自动识别文档领域，激活专业知识")
    print("  ✨ 结构化生成：基于分析报告生成精准Schema")
    print("  ✨ 可编辑流程：分析结果可手动编辑和确认")
    print("  ✨ 验证优化：自动验证并优化生成结果")
    print("\n" + "-"*70)
    
    # 检查环境
    try:
        from schema_ui import SchemaUI
        print("✅ 环境检查通过")
    except ImportError as e:
        print(f"❌ 环境检查失败: {e}")
        print("请确保已安装所有依赖：pip install -r requirements.txt")
        sys.exit(1)
    
    # 启动UI
    print("\n🌐 正在启动Web界面...")
    print("   访问地址: http://localhost:7863")
    print("   按 Ctrl+C 停止服务")
    print("-"*70 + "\n")
    
    try:
        ui = SchemaUI()
        demo = ui.create_interface()
        
        demo.launch(
            server_name="0.0.0.0",
            server_port=8888,
            share=False,
            inbrowser=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 系统已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
