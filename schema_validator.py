"""
Schema验证器 - 验证和自动修复Schema
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple


class SchemaValidator:
    """Schema验证器 - 确保生成的Schema符合规范"""
    
    def __init__(self):
        """初始化验证器"""
        self.errors = []
        self.warnings = []
        self.suggestions = []
        
        # 定义验证规则
        self.rules = {
            "naming": {
                "type": "PascalCase",  # 类型命名规则
                "property": "camelCase",  # 属性命名规则
                "relation": "camelCase"  # 关系命名规则
            },
            "required_elements": ["namespace", "types"],  # 必需元素
            "min_confidence": 0.3,  # 最低置信度阈值
            "max_property_per_type": 50,  # 每个类型的最大属性数
            "reserved_words": ["class", "type", "def", "import", "from", "return"]  # 保留字
        }
    
    def validate(self, schema: str) -> Dict[str, Any]:
        """
        验证Schema语法和语义
        
        Args:
            schema: Schema文本
            
        Returns:
            验证结果字典
        """
        # 重置错误列表
        self.errors = []
        self.warnings = []
        self.suggestions = []
        
        # 执行各项验证
        self._validate_syntax(schema)
        self._validate_structure(schema)
        self._validate_semantics(schema)
        self._validate_naming_conventions(schema)
        self._validate_references(schema)
        self._check_best_practices(schema)
        
        # 汇总结果
        is_valid = len(self.errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "statistics": self._get_statistics(schema)
        }
    
    def auto_fix(self, schema: str, validation_results: Dict) -> str:
        """
        尝试自动修复Schema中的问题
        
        Args:
            schema: 原始Schema
            validation_results: 验证结果
            
        Returns:
            修复后的Schema
        """
        fixed_schema = schema
        
        # 修复各类问题
        for error in validation_results.get("errors", []):
            fixed_schema = self._fix_error(fixed_schema, error)
        
        # 应用建议的改进
        for warning in validation_results.get("warnings", []):
            fixed_schema = self._apply_suggestion(fixed_schema, warning)
        
        return fixed_schema
    
    # 验证方法
    
    def _validate_syntax(self, schema: str):
        """验证Schema语法"""
        if not schema or not schema.strip():
            self.errors.append({
                "type": "syntax",
                "message": "Schema为空",
                "line": 0,
                "severity": "error"
            })
            return
        
        lines = schema.split('\n')
        
        # 检查namespace声明
        if not any(line.strip().startswith("namespace") for line in lines[:5]):
            self.errors.append({
                "type": "syntax",
                "message": "缺少namespace声明",
                "line": 1,
                "severity": "error"
            })
        
        # 检查缩进一致性
        indent_sizes = set()
        for i, line in enumerate(lines):
            if line and line[0] == ' ':
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indent_sizes.add(indent)
        
        if len(indent_sizes) > 2:  # 允许两种缩进级别
            self.warnings.append({
                "type": "syntax",
                "message": f"缩进不一致，发现{len(indent_sizes)}种不同的缩进大小",
                "severity": "warning"
            })
        
        # 检查括号匹配
        open_brackets = 0
        for i, line in enumerate(lines):
            open_brackets += line.count('(') - line.count(')')
            if open_brackets < 0:
                self.errors.append({
                    "type": "syntax",
                    "message": "括号不匹配",
                    "line": i + 1,
                    "severity": "error"
                })
                break
        
        if open_brackets != 0:
            self.errors.append({
                "type": "syntax",
                "message": "括号未正确闭合",
                "severity": "error"
            })
    
    def _validate_structure(self, schema: str):
        """验证Schema结构"""
        lines = schema.split('\n')
        
        # 检查是否有实体定义
        has_entity = False
        entity_count = 0
        
        for line in lines:
            if ': EntityType' in line or ':EntityType' in line:
                has_entity = True
                entity_count += 1
        
        if not has_entity:
            self.errors.append({
                "type": "structure",
                "message": "未找到任何实体类型定义",
                "severity": "error"
            })
        
        if entity_count > 100:
            self.warnings.append({
                "type": "structure",
                "message": f"实体类型过多（{entity_count}个），可能影响性能",
                "severity": "warning"
            })
        
        # 检查属性定义
        in_properties = False
        property_count = 0
        
        for i, line in enumerate(lines):
            if 'properties:' in line:
                in_properties = True
                property_count = 0
            elif in_properties and line.strip() and not line.startswith(' '):
                in_properties = False
            elif in_properties and ':' in line and line.strip():
                property_count += 1
        
        if property_count > self.rules["max_property_per_type"]:
            self.warnings.append({
                "type": "structure",
                "message": f"某实体的属性过多（{property_count}个），建议拆分",
                "severity": "warning"
            })
    
    def _validate_semantics(self, schema: str):
        """验证Schema语义"""
        # 提取所有定义的类型
        defined_types = self._extract_defined_types(schema)
        
        # 提取所有引用的类型
        referenced_types = self._extract_referenced_types(schema)
        
        # 检查未定义的引用
        undefined_types = referenced_types - defined_types
        if undefined_types:
            for undefined in undefined_types:
                self.errors.append({
                    "type": "semantic",
                    "message": f"引用了未定义的类型: {undefined}",
                    "severity": "error"
                })
        
        # 检查循环依赖
        cycles = self._detect_circular_dependencies(schema)
        if cycles:
            for cycle in cycles:
                self.warnings.append({
                    "type": "semantic",
                    "message": f"检测到循环依赖: {' -> '.join(cycle)}",
                    "severity": "warning"
                })
        
        # 检查重复定义
        duplicates = self._find_duplicate_definitions(schema)
        if duplicates:
            for dup in duplicates:
                self.errors.append({
                    "type": "semantic",
                    "message": f"重复定义: {dup}",
                    "severity": "error"
                })
    
    def _validate_naming_conventions(self, schema: str):
        """验证命名规范"""
        lines = schema.split('\n')
        
        for i, line in enumerate(lines):
            # 检查类型命名（PascalCase）
            type_match = re.match(r'^(\w+)\s*\(.*\)\s*:\s*\w*Type', line)
            if type_match:
                type_name = type_match.group(1)
                if not self._is_pascal_case(type_name):
                    self.warnings.append({
                        "type": "naming",
                        "message": f"类型名 '{type_name}' 不符合PascalCase规范",
                        "line": i + 1,
                        "severity": "warning",
                        "suggestion": self._to_pascal_case(type_name)
                    })
                
                # 检查保留字
                if type_name.lower() in self.rules["reserved_words"]:
                    self.errors.append({
                        "type": "naming",
                        "message": f"类型名 '{type_name}' 是保留字",
                        "line": i + 1,
                        "severity": "error"
                    })
            
            # 检查属性命名（camelCase）
            prop_match = re.match(r'^\s+(\w+)\s*\(.*\)\s*:\s*\w+', line)
            if prop_match and 'properties:' not in line and 'relations:' not in line:
                prop_name = prop_match.group(1)
                if not self._is_camel_case(prop_name):
                    self.warnings.append({
                        "type": "naming",
                        "message": f"属性名 '{prop_name}' 不符合camelCase规范",
                        "line": i + 1,
                        "severity": "warning",
                        "suggestion": self._to_camel_case(prop_name)
                    })
    
    def _validate_references(self, schema: str):
        """验证引用完整性"""
        # 提取所有类型定义和引用
        type_graph = self._build_type_graph(schema)
        
        # 检查每个引用是否有效
        for source, targets in type_graph.items():
            for target in targets:
                if target not in type_graph and target not in ["string", "integer", "float", "date", "boolean", "decimal", "enum"]:
                    self.errors.append({
                        "type": "reference",
                        "message": f"类型 '{source}' 引用了未定义的类型 '{target}'",
                        "severity": "error"
                    })
    
    def _check_best_practices(self, schema: str):
        """检查最佳实践"""
        lines = schema.split('\n')
        
        # 检查是否有文档注释
        has_comments = any(line.strip().startswith('#') for line in lines)
        if not has_comments:
            self.suggestions.append({
                "type": "best_practice",
                "message": "建议添加注释以提高可读性",
                "severity": "info"
            })
        
        # 检查是否有主键定义
        has_primary_key = 'primary_key' in schema or 'primaryKey' in schema
        if not has_primary_key:
            self.suggestions.append({
                "type": "best_practice",
                "message": "建议为实体定义主键",
                "severity": "info"
            })
        
        # 检查是否有必需字段
        has_required = 'required' in schema
        if not has_required:
            self.suggestions.append({
                "type": "best_practice",
                "message": "建议标记必需的属性",
                "severity": "info"
            })
    
    # 辅助方法
    
    def _extract_defined_types(self, schema: str) -> set:
        """提取所有定义的类型"""
        types = set()
        pattern = r'^(\w+)\s*\(.*\)\s*:\s*\w*Type'
        
        for line in schema.split('\n'):
            match = re.match(pattern, line)
            if match:
                types.add(match.group(1))
        
        return types
    
    def _extract_referenced_types(self, schema: str) -> set:
        """提取所有引用的类型"""
        types = set()
        
        # 在关系中引用的类型
        relation_pattern = r':\s*(\w+)\s*(?:\[|$)'
        for line in schema.split('\n'):
            if 'relations:' not in line and ':' in line:
                matches = re.findall(relation_pattern, line)
                types.update(matches)
        
        return types
    
    def _detect_circular_dependencies(self, schema: str) -> List[List[str]]:
        """检测循环依赖"""
        graph = self._build_type_graph(schema)
        cycles = []
        
        def dfs(node, path, visited):
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path[:], visited)
        
        for node in graph:
            dfs(node, [], set())
        
        return cycles
    
    def _find_duplicate_definitions(self, schema: str) -> List[str]:
        """查找重复定义"""
        definitions = {}
        duplicates = []
        
        pattern = r'^(\w+)\s*\(.*\)\s*:\s*\w*Type'
        for i, line in enumerate(schema.split('\n')):
            match = re.match(pattern, line)
            if match:
                name = match.group(1)
                if name in definitions:
                    duplicates.append(name)
                else:
                    definitions[name] = i
        
        return duplicates
    
    def _build_type_graph(self, schema: str) -> Dict[str, List[str]]:
        """构建类型依赖图"""
        graph = {}
        current_type = None
        
        for line in schema.split('\n'):
            # 检测类型定义
            type_match = re.match(r'^(\w+)\s*\(.*\)\s*:\s*\w*Type', line)
            if type_match:
                current_type = type_match.group(1)
                graph[current_type] = []
            
            # 检测关系引用
            elif current_type and ':' in line:
                ref_match = re.search(r':\s*(\w+)', line)
                if ref_match:
                    ref_type = ref_match.group(1)
                    if ref_type not in ["string", "integer", "float", "date", "boolean", "decimal", "enum"]:
                        graph[current_type].append(ref_type)
        
        return graph
    
    def _is_pascal_case(self, name: str) -> bool:
        """检查是否符合PascalCase"""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))
    
    def _is_camel_case(self, name: str) -> bool:
        """检查是否符合camelCase"""
        return bool(re.match(r'^[a-z][a-zA-Z0-9]*$', name))
    
    def _to_pascal_case(self, name: str) -> str:
        """转换为PascalCase"""
        words = re.split(r'[_\s]+', name)
        return ''.join(word.capitalize() for word in words if word)
    
    def _to_camel_case(self, name: str) -> str:
        """转换为camelCase"""
        words = re.split(r'[_\s]+', name)
        if not words:
            return name
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:] if word)
    
    def _get_statistics(self, schema: str) -> Dict:
        """获取Schema统计信息"""
        lines = schema.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        stats = {
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "entity_count": len(self._extract_defined_types(schema)),
            "property_count": sum(1 for line in lines if re.match(r'^\s+\w+\s*\(.*\)\s*:', line)),
            "relation_count": sum(1 for line in lines if 'relations:' in line),
            "comment_count": sum(1 for line in lines if line.strip().startswith('#'))
        }
        
        return stats
    
    def _fix_error(self, schema: str, error: Dict) -> str:
        """修复单个错误"""
        error_type = error.get("type")
        
        if error_type == "syntax":
            if error["message"] == "缺少namespace声明":
                # 在开头添加namespace
                return f"namespace AutoGenerated\n\n{schema}"
            elif "括号" in error["message"]:
                # 尝试修复括号匹配
                return self._fix_brackets(schema)
        
        elif error_type == "naming":
            if "suggestion" in error:
                # 应用命名建议
                line_num = error.get("line", 0) - 1
                if 0 <= line_num < len(schema.split('\n')):
                    lines = schema.split('\n')
                    old_line = lines[line_num]
                    # 替换名称
                    pattern = r'\b\w+\b'
                    matches = list(re.finditer(pattern, old_line))
                    if matches:
                        old_name = matches[0].group()
                        new_name = error["suggestion"]
                        lines[line_num] = old_line.replace(old_name, new_name, 1)
                        return '\n'.join(lines)
        
        return schema
    
    def _apply_suggestion(self, schema: str, warning: Dict) -> str:
        """应用改进建议"""
        if warning.get("type") == "naming" and "suggestion" in warning:
            # 类似于修复错误
            return self._fix_error(schema, warning)
        
        return schema
    
    def _fix_brackets(self, schema: str) -> str:
        """修复括号匹配"""
        fixed = []
        open_count = 0
        
        for line in schema.split('\n'):
            open_count += line.count('(') - line.count(')')
            if open_count < 0:
                # 缺少开括号，添加一个
                line = '(' + line
                open_count = 0
            fixed.append(line)
        
        # 如果最后还有未闭合的括号，添加闭括号
        if open_count > 0:
            fixed[-1] += ')' * open_count
        
        return '\n'.join(fixed)


if __name__ == "__main__":
    # 测试验证器
    validator = SchemaValidator()
    
    # 测试Schema
    test_schema = """namespace ContractManagement

Contract(合同): EntityType
    properties:
        contract_number(合同编号): string  [required, primary_key]
        sign_date(签订日期): date  [required]
        Amount(金额): decimal
    relations:
        signedBy(签署方): company

company(公司): EntityType
    properties:
        Name(公司名称): string  [required]
"""
    
    # 验证Schema
    results = validator.validate(test_schema)
    
    # 打印结果
    print("验证结果:")
    print(f"是否有效: {results['is_valid']}")
    
    if results['errors']:
        print("\n错误:")
        for error in results['errors']:
            print(f"  - [{error['severity']}] {error['message']}")
    
    if results['warnings']:
        print("\n警告:")
        for warning in results['warnings']:
            print(f"  - [{warning['severity']}] {warning['message']}")
            if 'suggestion' in warning:
                print(f"    建议: {warning['suggestion']}")
    
    if results['suggestions']:
        print("\n建议:")
        for suggestion in results['suggestions']:
            print(f"  - {suggestion['message']}")
    
    print("\n统计信息:")
    for key, value in results['statistics'].items():
        print(f"  {key}: {value}")
    
    # 尝试自动修复
    if not results['is_valid']:
        print("\n尝试自动修复...")
        fixed_schema = validator.auto_fix(test_schema, results)
        print("修复后的Schema:")
        print(fixed_schema)
