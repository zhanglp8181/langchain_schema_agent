"""
Schema文本解析器 - 将Schema文本直接解析为AST
"""

import re
from typing import Dict, List, Any, Optional


class SchemaParser:
    """Schema文本解析器"""
    
    @staticmethod
    def parse_schema_text(schema_text: str) -> Dict:
        """
        直接从Schema文本解析为AST格式
        
        Args:
            schema_text: Schema文本内容
            
        Returns:
            AST字典
        """
        lines = schema_text.strip().split('\n')
        ast = {
            "namespace": "",
            "types": [],
            "relations": []
        }
        
        current_entity = None
        current_section = None
        indent_stack = []
        
        for line in lines:
            # 保留缩进信息
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            
            if not stripped or stripped.startswith('#'):
                continue
            
            # 解析namespace
            if stripped.startswith('namespace '):
                ast["namespace"] = stripped.replace('namespace ', '').strip()
                continue
            
            # 解析实体定义 - 格式: EntityName(中文名): EntityType
            entity_match = re.match(r'^(\w+)\(([^)]*)\):\s*EntityType\s*$', stripped)
            if entity_match:
                entity_name = entity_match.group(1)
                cn_name = entity_match.group(2) if entity_match.group(2) else entity_name
                
                current_entity = {
                    "name": entity_name,
                    "cn_name": cn_name,
                    "properties": [],
                    "relations": []
                }
                ast["types"].append(current_entity)
                current_section = None
                indent_stack = [indent]
                continue
            
            # 检查缩进级别
            if current_entity:
                # 解析properties或relations部分
                if stripped == 'properties:':
                    current_section = 'properties'
                    indent_stack.append(indent)
                    continue
                elif stripped == 'relations:':
                    current_section = 'relations'
                    indent_stack.append(indent)
                    continue
                
                # 解析属性或关系 - 格式: name(中文名): Type
                if current_section and ':' in stripped:
                    # 使用更灵活的正则表达式
                    item_match = re.match(r'^(\w+)(?:\(([^)]*)\))?\s*:\s*(.+)\s*$', stripped)
                    if item_match:
                        name = item_match.group(1)
                        cn_name = item_match.group(2) if item_match.group(2) else name
                        type_or_target = item_match.group(3).strip()
                        
                        if current_section == 'properties':
                            # 属性
                            current_entity["properties"].append({
                                "name": name,
                                "cn_name": cn_name,
                                "data_type": type_or_target
                            })
                        elif current_section == 'relations':
                            # 关系
                            current_entity["relations"].append({
                                "name": name,
                                "cn_name": cn_name,
                                "target": type_or_target
                            })
        
        return ast
    
    @staticmethod
    def validate_and_parse(schema_text: str) -> tuple[bool, Dict, str]:
        """
        验证并解析Schema文本
        
        Returns:
            (is_valid, ast, error_message)
        """
        try:
            # 基本格式检查
            if not schema_text or not schema_text.strip():
                return False, {}, "Schema文本为空"
            
            # 检查必要的关键字
            if 'namespace' not in schema_text:
                return False, {}, "缺少namespace声明"
            
            if 'EntityType' not in schema_text:
                return False, {}, "没有定义任何实体类型"
            
            # 解析Schema
            ast = SchemaParser.parse_schema_text(schema_text)
            
            # 检查解析结果
            if not ast.get("namespace"):
                return False, ast, "namespace为空"
            
            if not ast.get("types"):
                return False, ast, "没有解析出任何实体"
            
            return True, ast, ""
            
        except Exception as e:
            return False, {}, f"解析错误: {str(e)}"
    
    @staticmethod
    def format_schema(schema_text: str) -> str:
        """
        格式化Schema文本
        """
        lines = schema_text.split('\n')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatted_lines.append("")
                continue
            
            # namespace行不缩进
            if stripped.startswith('namespace'):
                formatted_lines.append(stripped)
                formatted_lines.append("")  # 添加空行
                continue
            
            # 实体定义行不缩进
            if ': EntityType' in stripped:
                if formatted_lines and formatted_lines[-1] != "":
                    formatted_lines.append("")  # 在实体前添加空行
                formatted_lines.append(stripped)
                indent_level = 1
                continue
            
            # properties和relations缩进一级
            if stripped in ['properties:', 'relations:']:
                formatted_lines.append(' ' * 4 + stripped)
                indent_level = 2
                continue
            
            # 属性和关系项缩进两级
            if ':' in stripped and indent_level == 2:
                formatted_lines.append(' ' * 8 + stripped)
                continue
            
            # 默认处理
            formatted_lines.append(' ' * (indent_level * 4) + stripped)
        
        return '\n'.join(formatted_lines)


if __name__ == "__main__":
    # 测试Schema解析
    test_schema = """namespace Legal

Contract(合同): EntityType
    properties:
        entityName(实体名称): Text
        description(描述): Text
        contractName(合同名称): Text
        contractNumber(合同编号): Text
        totalAmount(总金额): Float
    relations:
        hasParty(有甲方): PartyA
        hasClause(包含条款): ContractClause

PartyA(甲方): EntityType
    properties:
        entityName(实体名称): Text
        description(描述): Text
        partyName(甲方名称): Text"""
    
    print("测试Schema解析")
    print("=" * 60)
    
    # 验证并解析
    is_valid, ast, error = SchemaParser.validate_and_parse(test_schema)
    
    if is_valid:
        print("✅ Schema解析成功")
        print(f"命名空间: {ast['namespace']}")
        print(f"实体数量: {len(ast['types'])}")
        
        for entity in ast['types']:
            print(f"\n实体: {entity['name']} ({entity['cn_name']})")
            print(f"  属性: {len(entity['properties'])}个")
            for prop in entity['properties']:
                print(f"    - {prop['name']}({prop['cn_name']}): {prop['data_type']}")
            if entity['relations']:
                print(f"  关系: {len(entity['relations'])}个")
                for rel in entity['relations']:
                    print(f"    - {rel['name']}({rel['cn_name']}): {rel['target']}")
    else:
        print(f"❌ Schema解析失败: {error}")
    
    # 测试格式化
    print("\n" + "=" * 60)
    print("测试Schema格式化")
    print("=" * 60)
    
    messy_schema = """namespace Test
TestEntity(测试): EntityType
properties:
name(名称): Text
value(值): Float
relations:
relatedTo(关联): OtherEntity"""
    
    formatted = SchemaParser.format_schema(messy_schema)
    print("格式化后:")
    print(formatted)
