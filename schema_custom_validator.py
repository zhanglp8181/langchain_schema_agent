"""
Schema自定义验证器 - 支持用户定义的验证规则
"""

from typing import Dict, List, Any, Callable, Optional, Tuple
from dataclasses import dataclass
import re
import json
from datetime import datetime


@dataclass
class ValidationRule:
    """验证规则定义"""
    name: str  # 规则名称
    description: str  # 规则描述
    validator: Callable  # 验证函数
    severity: str = "error"  # 严重级别: error, warning, info
    enabled: bool = True  # 是否启用


@dataclass
class ValidationResult:
    """验证结果"""
    rule_name: str  # 规则名称
    passed: bool  # 是否通过
    message: str  # 结果消息
    severity: str  # 严重级别
    details: Optional[Dict] = None  # 详细信息


class SchemaCustomValidator:
    """Schema自定义验证器"""
    
    def __init__(self):
        """初始化验证器"""
        self.rules: Dict[str, ValidationRule] = {}
    
    def load_rules_from_file(self, file_path: str = "validation_rules.json") -> bool:
        """从JSON文件加载验证规则"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 先清除现有规则
            self.rules.clear()
            
            # 加载规则
            for rule_config in config.get("rules", []):
                rule_id = rule_config["id"]
                rule_name = rule_config["name"]
                description = rule_config["description"]
                enabled = rule_config["enabled"]
                severity = rule_config["severity"]
                rule_config_data = rule_config.get("config", {})
                
                # 根据rule_id创建对应的验证函数
                validator = self._create_validator_from_config(rule_id, rule_config_data)
                if validator:
                    self.rules[rule_id] = ValidationRule(
                        name=rule_name,
                        description=description,
                        validator=validator,
                        severity=severity,
                        enabled=enabled
                    )
            
            return True
        except Exception as e:
            print(f"加载规则文件失败: {str(e)}")
            # 加载失败时使用默认规则
            self._init_default_rules()
            return False
    
    def save_rules_to_file(self, file_path: str = "validation_rules.json") -> bool:
        """将当前规则保存到JSON文件"""
        try:
            # 转换当前规则为JSON格式
            rule_configs = []
            for rule_id, rule in self.rules.items():
                # 获取规则配置
                config = self._get_config_from_rule(rule_id)
                if config:
                    rule_configs.append({
                        "id": rule_id,
                        "name": rule.name,
                        "description": rule.description,
                        "enabled": rule.enabled,
                        "severity": rule.severity,
                        "config": config
                    })
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "rules": rule_configs,
                    "version": "1.0.0",
                    "last_modified": datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"保存规则文件失败: {str(e)}")
            return False
    
    def _create_validator_from_config(self, rule_id: str, config: Dict) -> Optional[Callable]:
        """根据规则ID和配置创建验证函数"""
        # 根据不同的rule_id返回对应的验证函数
        if rule_id == "allowed_types":
            allowed_types = config.get("allowed_types", ["Text", "Float"])
            return lambda ast, text: self._validate_allowed_types_with_config(ast, text, allowed_types)
        elif rule_id == "entity_naming":
            pattern = config.get("pattern", "^[A-Z][a-zA-Z0-9]*$")
            return lambda ast, text: self._validate_entity_naming_with_pattern(ast, text, pattern)
        elif rule_id == "property_naming":
            pattern = config.get("pattern", "^[a-z][a-zA-Z0-9]*$")
            return lambda ast, text: self._validate_property_naming_with_pattern(ast, text, pattern)
        elif rule_id == "chinese_names":
            return self._validate_chinese_names
        elif rule_id == "relation_naming":
            pattern = config.get("pattern", "^[a-z][a-zA-Z0-9]*$")
            return lambda ast, text: self._validate_relation_naming_with_pattern(ast, text, pattern)
        elif rule_id == "numeric_types":
            keywords = config.get("numeric_keywords", [])
            return lambda ast, text: self._validate_numeric_types_with_keywords(ast, text, keywords)
        elif rule_id == "date_types":
            keywords = config.get("date_keywords", [])
            return lambda ast, text: self._validate_date_types_with_keywords(ast, text, keywords)
        elif rule_id == "required_entities":
            required = config.get("required", [])
            return CustomRuleBuilder.create_required_entity_rule(required)
        elif rule_id == "property_count":
            min_props = config.get("min", 1)
            max_props = config.get("max", 20)
            return CustomRuleBuilder.create_property_count_rule(min_props, max_props)
        elif rule_id == "namespace_pattern":
            pattern = config.get("pattern")
            allowed = config.get("allowed", [])
            return CustomRuleBuilder.create_namespace_rule(allowed, pattern)
        elif rule_id == "no_id_property":
            forbidden_names = config.get("forbidden_names", ["id"])
            return lambda ast, text: self._validate_no_forbidden_properties(ast, text, forbidden_names)
        elif rule_id == "no_constraint":
            return self._validate_no_constraint
        elif rule_id == "required_base_properties":
            # 新增：必需的基础属性规则
            required_properties = config.get("required_properties", [])
            return lambda ast, text: self._validate_required_base_properties(ast, text, required_properties)
        elif rule_id == "relations_only_when_needed":
            # 新增：关系按需显示规则
            return lambda ast, text: self._validate_relations_only_when_needed(ast, text)
        elif rule_id == "no_underscore":
            # 新增：禁止下划线规则
            pattern = config.get("pattern", "^[a-zA-Z][a-zA-Z0-9]*$")
            message = config.get("message", "名称不能包含下划线")
            return lambda ast, text: self._validate_no_underscore(ast, text, pattern, message)
        elif rule_id == "no_duplicate_entity_definition":
            # 新增：禁止重复定义实体规则
            message = config.get("message", "实体被重复定义，properties和relations必须写在同一个实体定义块中")
            return lambda ast, text: self._validate_no_duplicate_entity_definition(ast, text, message)
        elif rule_id == "no_special_characters_in_names":
            # 新增：禁止名称包含特殊字符规则
            forbidden_chars = config.get("forbidden_chars", ["/", "\\", "|"])
            message = config.get("message", "名称不能包含特殊字符")
            return lambda ast, text: self._validate_no_special_characters_in_names(ast, text, forbidden_chars, message)
        else:
            return None
    
    def _get_config_from_rule(self, rule_id: str) -> Optional[Dict]:
        """从规则ID获取配置信息（用于保存）"""
        # 这是一个简化的实现，实际应该从规则中提取配置
        default_configs = {
            "allowed_types": {"allowed_types": ["Text", "Float"]},
            "entity_naming": {"pattern": "^[A-Z][a-zA-Z0-9]*$"},
            "property_naming": {"pattern": "^[a-z][a-zA-Z0-9]*$"},
            "chinese_names": {"require_chinese": True},
            "relation_naming": {"pattern": "^[a-z][a-zA-Z0-9]*$"},
            "numeric_types": {"numeric_keywords": ["amount", "price", "金额", "价格", "quantity", "数量", "cost", "费用"]},
            "date_types": {"date_keywords": ["date", "time", "日期", "时间"]},
            "required_entities": {"required": []},
            "property_count": {"min": 1, "max": 20},
            "namespace_pattern": {"pattern": ".*", "allowed": []}
        }
        return default_configs.get(rule_id)
    
    def _init_default_rules(self):
        """初始化默认验证规则"""
        # 尝试从文件加载，如果失败则使用硬编码的默认规则
        if not self.load_rules_from_file():
            # 规则1: 只能使用Text和Float类型
            self.add_rule(
                name="allowed_types",
                description="属性类型只能使用Text和Float",
                validator=self._validate_allowed_types
            )
        
        # 规则2: 实体名称必须是英文PascalCase
        self.add_rule(
            name="entity_naming",
            description="实体名称必须是英文且符合PascalCase规范",
            validator=self._validate_entity_naming
        )
        
        # 规则3: 属性名称必须是英文camelCase
        self.add_rule(
            name="property_naming",
            description="属性名称必须是英文且符合camelCase规范",
            validator=self._validate_property_naming
        )
        
        # 规则4: 必须包含中文名称
        self.add_rule(
            name="chinese_names",
            description="实体和属性必须包含中文名称",
            validator=self._validate_chinese_names
        )
        
        # 规则5: 关系名称规范
        self.add_rule(
            name="relation_naming",
            description="关系名称必须是英文且符合camelCase规范",
            validator=self._validate_relation_naming
        )
        
        # 规则6: 数值属性类型检查
        self.add_rule(
            name="numeric_types",
            description="数值相关属性必须使用Float类型",
            validator=self._validate_numeric_types,
            severity="warning"
        )
        
        # 规则7: 日期属性类型检查
        self.add_rule(
            name="date_types",
            description="日期相关属性必须使用Text类型",
            validator=self._validate_date_types,
            severity="warning"
        )
    
    def add_rule(self, name: str, description: str, validator: Callable,
                 severity: str = "error", enabled: bool = True):
        """
        添加验证规则
        
        Args:
            name: 规则名称
            description: 规则描述
            validator: 验证函数，接收(ast, schema_text)参数，返回(passed, message, details)
            severity: 严重级别
            enabled: 是否启用
        """
        self.rules[name] = ValidationRule(
            name=name,
            description=description,
            validator=validator,
            severity=severity,
            enabled=enabled
        )
    
    def remove_rule(self, name: str):
        """移除验证规则"""
        if name in self.rules:
            del self.rules[name]
    
    def enable_rule(self, name: str):
        """启用规则"""
        if name in self.rules:
            self.rules[name].enabled = True
    
    def disable_rule(self, name: str):
        """禁用规则"""
        if name in self.rules:
            self.rules[name].enabled = False
    
    def validate(self, ast: Dict, schema_text: str = "") -> Dict:
        """
        验证Schema
        
        Args:
            ast: Schema的AST表示
            schema_text: Schema文本
            
        Returns:
            验证结果字典
        """
        results = []
        errors = []
        warnings = []
        info = []
        
        # 执行所有启用的规则
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            try:
                passed, message, details = rule.validator(ast, schema_text)
                result = ValidationResult(
                    rule_name=rule.name,
                    passed=passed,
                    message=message,
                    severity=rule.severity,
                    details=details
                )
                results.append(result)
                
                if not passed:
                    if rule.severity == "error":
                        errors.append(result)
                    elif rule.severity == "warning":
                        warnings.append(result)
                    else:
                        info.append(result)
                        
            except Exception as e:
                # 规则执行失败
                result = ValidationResult(
                    rule_name=rule.name,
                    passed=False,
                    message=f"规则执行失败: {str(e)}",
                    severity="error"
                )
                results.append(result)
                errors.append(result)
        
        # 汇总结果
        total_passed = len([r for r in results if r.passed])
        total_failed = len([r for r in results if not r.passed])
        
        return {
            "is_valid": len(errors) == 0,
            "total_rules": len(results),
            "passed": total_passed,
            "failed": total_failed,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "results": results,
            "summary": self._generate_summary(results)
        }
    
    def _generate_summary(self, results: List[ValidationResult]) -> str:
        """生成验证摘要"""
        if not results:
            return "没有执行任何验证规则"
        
        errors = [r for r in results if not r.passed and r.severity == "error"]
        warnings = [r for r in results if not r.passed and r.severity == "warning"]
        
        if not errors and not warnings:
            return "✅ 所有验证规则通过"
        
        summary = []
        if errors:
            summary.append(f"❌ {len(errors)} 个错误")
        if warnings:
            summary.append(f"⚠️ {len(warnings)} 个警告")
        
        return ", ".join(summary)
    
    # ========== 默认验证规则实现 ==========
    
    def _validate_allowed_types(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证是否只使用Text和Float类型（默认）"""
        return self._validate_allowed_types_with_config(ast, schema_text, ["Text", "Float"])
    
    def _validate_allowed_types_with_config(self, ast: Dict, schema_text: str, allowed_types: List[str]) -> Tuple[bool, str, Optional[Dict]]:
        """验证是否只使用指定的类型"""
        allowed_types = set(allowed_types)
        found_types = set()
        invalid_properties = []
        
        # 检查所有实体的属性类型
        for entity_type in ast.get("types", []):
            for prop in entity_type.get("properties", []):
                data_type = prop.get("data_type", "")
                found_types.add(data_type)
                
                if data_type not in allowed_types:
                    invalid_properties.append({
                        "entity": entity_type["name"],
                        "property": prop["name"],
                        "type": data_type
                    })
        
        # 检查关系的属性类型
        for relation in ast.get("relations", []):
            for prop in relation.get("properties", []):
                data_type = prop.get("data_type", "")
                found_types.add(data_type)
                
                if data_type not in allowed_types:
                    invalid_properties.append({
                        "relation": relation["name"],
                        "property": prop["name"],
                        "type": data_type
                    })
        
        if invalid_properties:
            return False, f"发现非法类型: {found_types - allowed_types}", {"invalid": invalid_properties}
        
        return True, f"类型检查通过，只使用了 {found_types}", {"types": list(found_types)}
    
    def _validate_entity_naming(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证实体命名规范（默认）"""
        return self._validate_entity_naming_with_pattern(ast, schema_text, r'^[A-Z][a-zA-Z0-9]*$')
    
    def _validate_entity_naming_with_pattern(self, ast: Dict, schema_text: str, pattern: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证实体命名规范（使用指定模式）"""
        pascal_case_pattern = re.compile(pattern)
        invalid_entities = []
        
        for entity_type in ast.get("types", []):
            name = entity_type.get("name", "")
            if not pascal_case_pattern.match(name):
                invalid_entities.append(name)
        
        if invalid_entities:
            return False, f"实体名称不符合PascalCase规范: {invalid_entities}", {"invalid": invalid_entities}
        
        return True, "所有实体名称符合PascalCase规范", None
    
    def _validate_property_naming(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证属性命名规范（默认）"""
        return self._validate_property_naming_with_pattern(ast, schema_text, r'^[a-z][a-zA-Z0-9]*$')
    
    def _validate_property_naming_with_pattern(self, ast: Dict, schema_text: str, pattern: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证属性命名规范（使用指定模式）"""
        camel_case_pattern = re.compile(pattern)
        invalid_properties = []
        
        for entity_type in ast.get("types", []):
            for prop in entity_type.get("properties", []):
                name = prop.get("name", "")
                if not camel_case_pattern.match(name):
                    invalid_properties.append(f"{entity_type['name']}.{name}")
        
        if invalid_properties:
            return False, f"属性名称不符合camelCase规范: {invalid_properties[:5]}", {"invalid": invalid_properties}
        
        return True, "所有属性名称符合camelCase规范", None
    
    def _validate_chinese_names(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证是否包含中文名称"""
        missing_chinese = []
        
        for entity_type in ast.get("types", []):
            if not entity_type.get("cn_name"):
                missing_chinese.append(f"实体 {entity_type['name']}")
            
            for prop in entity_type.get("properties", []):
                if not prop.get("cn_name"):
                    missing_chinese.append(f"属性 {entity_type['name']}.{prop['name']}")
        
        if missing_chinese:
            return False, f"缺少中文名称: {missing_chinese[:5]}", {"missing": missing_chinese}
        
        return True, "所有实体和属性都包含中文名称", None
    
    def _validate_relation_naming(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证关系命名规范（默认）"""
        return self._validate_relation_naming_with_pattern(ast, schema_text, r'^[a-z][a-zA-Z0-9]*$')
    
    def _validate_relation_naming_with_pattern(self, ast: Dict, schema_text: str, pattern: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证关系命名规范（使用指定模式）"""
        camel_case_pattern = re.compile(pattern)
        invalid_relations = []
        
        for relation in ast.get("relations", []):
            name = relation.get("name", "")
            if not camel_case_pattern.match(name):
                invalid_relations.append(name)
        
        if invalid_relations:
            return False, f"关系名称不符合camelCase规范: {invalid_relations}", {"invalid": invalid_relations}
        
        return True, "所有关系名称符合camelCase规范", None
    
    def _validate_numeric_types(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证数值属性是否使用Float类型（默认）"""
        return self._validate_numeric_types_with_keywords(ast, schema_text, 
            ["amount", "price", "金额", "价格", "quantity", "数量", "cost", "费用"])
    
    def _validate_numeric_types_with_keywords(self, ast: Dict, schema_text: str, numeric_keywords: List[str]) -> Tuple[bool, str, Optional[Dict]]:
        """验证数值属性是否使用Float或Integer类型（使用指定关键词）"""
        issues = []
        
        # 排除词列表 - 这些词表明属性不是数值类型
        exclude_suffixes = ["name", "名称", "名字", "description", "描述", "type", "类型", "code", "编码", "id"]
        
        for entity_type in ast.get("types", []):
            for prop in entity_type.get("properties", []):
                prop_name = prop.get("name", "").lower()
                prop_cn = prop.get("cn_name", "").lower()
                data_type = prop.get("data_type", "")
                
                # 跳过名称类、描述类属性
                is_excluded = False
                for suffix in exclude_suffixes:
                    if prop_name.endswith(suffix.lower()) or suffix in prop_cn:
                        is_excluded = True
                        break
                
                if is_excluded:
                    continue
                
                # 检查是否为数值属性但没使用Float或Integer或Text
                # Text也是允许的，因为有些数值可能需要以文本形式存储
                for keyword in numeric_keywords:
                    keyword_lower = keyword.lower()
                    # 使用更严格的匹配：完整单词匹配或中文关键词匹配
                    is_numeric_prop = False
                    
                    # 英文：检查是否作为完整单词或单词边界存在
                    if keyword_lower.isascii():
                        # 检查是否为完整单词匹配
                        import re
                        if re.search(r'\b' + re.escape(keyword_lower) + r'\b', prop_name):
                            is_numeric_prop = True
                    else:
                        # 中文关键词直接包含匹配
                        if keyword in prop_cn:
                            is_numeric_prop = True
                    
                    if is_numeric_prop and data_type not in ["Float", "Integer", "Text"]:
                        issues.append(f"{entity_type['name']}.{prop['name']} 应该使用Float或Integer类型")
                        break
        
        if issues:
            return False, f"数值属性类型不正确", {"issues": issues}
        
        return True, "数值属性类型正确", None
    
    def _validate_date_types(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证日期属性是否使用Text类型（默认）"""
        return self._validate_date_types_with_keywords(ast, schema_text, ["date", "time", "日期", "时间"])
    
    def _validate_date_types_with_keywords(self, ast: Dict, schema_text: str, date_keywords: List[str]) -> Tuple[bool, str, Optional[Dict]]:
        """验证日期属性是否使用Date或Text类型（使用指定关键词）"""
        issues = []
        
        for entity_type in ast.get("types", []):
            for prop in entity_type.get("properties", []):
                prop_name = prop.get("name", "").lower()
                prop_cn = prop.get("cn_name", "").lower()
                data_type = prop.get("data_type", "")
                
                # 检查是否为日期属性但没使用Date或Text  
                for keyword in date_keywords:
                    if (keyword in prop_name or keyword in prop_cn) and data_type not in ["Date", "Text"]:
                        issues.append(f"{entity_type['name']}.{prop['name']} 应该使用Date或Text类型")
                        break
        
        if issues:
            return False, f"日期属性类型不正确", {"issues": issues}
        
        return True, "日期属性类型正确", None
    
    def _validate_no_forbidden_properties(self, ast: Dict, schema_text: str, forbidden_names: List[str]) -> Tuple[bool, str, Optional[Dict]]:
        """验证是否存在禁止的属性名"""
        found_forbidden = []
        
        for entity_type in ast.get("types", []):
            for prop in entity_type.get("properties", []):
                prop_name = prop.get("name", "")
                if prop_name.lower() in [name.lower() for name in forbidden_names]:
                    found_forbidden.append(f"{entity_type['name']}.{prop_name}")
        
        if found_forbidden:
            return False, f"发现禁止的属性名: {found_forbidden}", {"forbidden": found_forbidden}
        
        return True, f"没有使用禁止的属性名", None
    
    def _validate_no_constraint(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证Schema文本中是否包含constraint字段"""
        if "constraint:" in schema_text or "constraint :" in schema_text:
            # 计算出现次数
            count = schema_text.count("constraint:")
            return False, f"Schema中包含constraint字段（{count}处），应该移除", {"count": count}
        
        return True, "Schema中没有constraint字段", None
    
    def _validate_required_base_properties(self, ast: Dict, schema_text: str, required_properties: List[Dict]) -> Tuple[bool, str, Optional[Dict]]:
        """验证实体是否包含必需的基础属性"""
        issues = []
        
        for entity_type in ast.get("types", []):
            entity_name = entity_type.get("name", "")
            properties = entity_type.get("properties", [])
            property_names = [prop.get("name", "") for prop in properties]
            
            # 检查每个必需的属性模式
            for req_prop in required_properties:
                pattern = req_prop.get("pattern", "")
                description = req_prop.get("description", "")
                
                # 检查是否有属性匹配这个模式
                matched = False
                for prop_name in property_names:
                    if re.match(pattern, prop_name, re.IGNORECASE):
                        matched = True
                        break
                
                if not matched:
                    issues.append(f"{entity_name} 缺少必需的属性: {description}")
        
        if issues:
            return False, f"实体缺少必需的基础属性", {"issues": issues}
        
        return True, "所有实体都包含必需的基础属性", None
    
    def _validate_relations_only_when_needed(self, ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证是否只在有关系时才显示relations部分"""
        issues = []
        
        # 只检查Schema文本中实际存在的空relations部分
        # 首先按实体分割schema文本，然后检查每个实体是否有空的relations:部分
        
        # 使用正则表达式匹配实体定义块，查找有空relations的情况
        # 空的relations定义：relations: 后面直到下一个实体定义或文件结束，没有任何关系定义
        
        # 分割成行进行分析
        lines = schema_text.split('\n')
        current_entity = None
        in_relations = False
        relations_has_content = False
        entities_with_empty_relations = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 检测实体定义行
            entity_match = re.match(r'^(\w+)\([^)]*\):\s*EntityType\s*$', stripped)
            if entity_match:
                # 如果之前在处理relations部分且为空，记录问题
                if current_entity and in_relations and not relations_has_content:
                    entities_with_empty_relations.append(current_entity)
                
                current_entity = entity_match.group(1)
                in_relations = False
                relations_has_content = False
                continue
            
            # 检测relations:行
            if stripped == 'relations:':
                in_relations = True
                relations_has_content = False
                continue
            
            # 检测properties:行（退出relations部分）
            if stripped == 'properties:':
                # 如果之前在处理relations部分且为空，记录问题
                if current_entity and in_relations and not relations_has_content:
                    entities_with_empty_relations.append(current_entity)
                in_relations = False
                continue
            
            # 在relations部分检测是否有内容
            if in_relations and stripped and ':' in stripped:
                # 这是一个关系定义
                relations_has_content = True
        
        # 检查最后一个实体
        if current_entity and in_relations and not relations_has_content:
            entities_with_empty_relations.append(current_entity)
        
        # 生成问题报告
        if entities_with_empty_relations:
            issues.append("发现空的relations部分，应该移除")
            for entity_name in entities_with_empty_relations:
                issues.append(f"{entity_name} 有空的relations部分")
        
        if issues:
            return False, "实体没有关系时不应包含relations部分", {"issues": issues}
        
        return True, "relations部分使用正确", None
    
    def _validate_no_underscore(self, ast: Dict, schema_text: str, pattern: str, message: str) -> Tuple[bool, str, Optional[Dict]]:
        """验证实体名、属性名、关系名不能包含下划线"""
        issues = []
        no_underscore_pattern = re.compile(pattern)
        
        # 检查实体名
        for entity_type in ast.get("types", []):
            entity_name = entity_type.get("name", "")
            if "_" in entity_name or not no_underscore_pattern.match(entity_name):
                issues.append(f"实体名 '{entity_name}' 包含下划线")
            
            # 检查属性名
            for prop in entity_type.get("properties", []):
                prop_name = prop.get("name", "")
                if "_" in prop_name or not no_underscore_pattern.match(prop_name):
                    issues.append(f"属性名 '{entity_name}.{prop_name}' 包含下划线")
            
            # 检查关系名
            for relation in entity_type.get("relations", []):
                rel_name = relation.get("name", "")
                if "_" in rel_name or not no_underscore_pattern.match(rel_name):
                    issues.append(f"关系名 '{entity_name}.{rel_name}' 包含下划线")
        
        # 也检查全局关系
        for relation in ast.get("relations", []):
            rel_name = relation.get("name", "")
            if "_" in rel_name or not no_underscore_pattern.match(rel_name):
                issues.append(f"关系名 '{rel_name}' 包含下划线")
        
        if issues:
            return False, message, {"issues": issues[:10]}  # 只显示前10个问题
        
        return True, "命名规范检查通过，没有使用下划线", None
    
    def _validate_no_duplicate_entity_definition(self, ast: Dict, schema_text: str, message: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        验证同一个实体是否被重复定义
        检测schema文本中同一个实体名称出现多次定义的情况
        正确的写法是properties和relations写在同一个实体定义块中
        """
        issues = []
        
        # 方法1: 通过解析schema_text检测重复的实体定义
        # 使用正则表达式查找所有实体定义行: EntityName(中文名): EntityType
        entity_definition_pattern = re.compile(r'^(\w+)\([^)]*\):\s*EntityType\s*$', re.MULTILINE)
        matches = entity_definition_pattern.findall(schema_text)
        
        # 统计每个实体名称出现的次数
        entity_counts = {}
        for entity_name in matches:
            entity_counts[entity_name] = entity_counts.get(entity_name, 0) + 1
        
        # 找出重复定义的实体
        duplicate_entities = [name for name, count in entity_counts.items() if count > 1]
        
        if duplicate_entities:
            for entity_name in duplicate_entities:
                count = entity_counts[entity_name]
                issues.append(f"实体 '{entity_name}' 被定义了 {count} 次，properties和relations必须写在同一个实体定义块中")
        
        # 方法2: 同时检查AST中是否有重复的实体名（作为备用检查）
        if ast.get("types"):
            ast_entity_names = [entity.get("name", "") for entity in ast.get("types", [])]
            ast_entity_counts = {}
            for name in ast_entity_names:
                ast_entity_counts[name] = ast_entity_counts.get(name, 0) + 1
            
            ast_duplicates = [name for name, count in ast_entity_counts.items() if count > 1]
            for entity_name in ast_duplicates:
                if entity_name not in duplicate_entities:  # 避免重复报告
                    count = ast_entity_counts[entity_name]
                    issues.append(f"AST中实体 '{entity_name}' 出现了 {count} 次")
        
        if issues:
            return False, message, {"duplicate_entities": duplicate_entities, "issues": issues}
        
        return True, "没有重复定义的实体", None
    
    def _validate_no_special_characters_in_names(self, ast: Dict, schema_text: str, forbidden_chars: List[str], message: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        验证实体名称（中英文）不能包含特殊字符
        例如：'合同/主合同' 是错误的，应该是 '合同' 或 '主合同'
        英文名称如 'Contract/MainContract' 也是错误的
        """
        issues = []
        forbidden_set = set(forbidden_chars)
        
        def contains_forbidden_char(name: str, allow_ellipsis: bool = False) -> Tuple[bool, str]:
            """检查名称是否包含禁止的字符，返回(是否包含, 包含的字符)
            
            Args:
                name: 要检查的名称
                allow_ellipsis: 是否允许省略号"..."，在中文名称中常用于表示省略
            """
            # 如果允许省略号，先将"..."替换掉再检查
            check_name = name
            if allow_ellipsis:
                check_name = name.replace("...", "")
            
            for char in check_name:
                if char in forbidden_set:
                    return True, char
            return False, ""
        
        # 检查实体
        for entity_type in ast.get("types", []):
            # 检查英文名称
            entity_name = entity_type.get("name", "")
            has_forbidden, char = contains_forbidden_char(entity_name)
            if has_forbidden:
                issues.append(f"实体英文名 '{entity_name}' 包含特殊字符 '{char}'，如需表示多个概念请分别定义为独立实体")
            
            # 检查中文名称
            cn_name = entity_type.get("cn_name", "")
            has_forbidden, char = contains_forbidden_char(cn_name)
            if has_forbidden:
                issues.append(f"实体中文名 '{cn_name}' 包含特殊字符 '{char}'，如需表示多个概念请分别定义为独立实体")
            
            # 检查属性名称
            for prop in entity_type.get("properties", []):
                prop_name = prop.get("name", "")
                has_forbidden, char = contains_forbidden_char(prop_name)
                if has_forbidden:
                    issues.append(f"属性英文名 '{entity_name}.{prop_name}' 包含特殊字符 '{char}'")
                
                prop_cn_name = prop.get("cn_name", "")
                has_forbidden, char = contains_forbidden_char(prop_cn_name)
                if has_forbidden:
                    issues.append(f"属性中文名 '{entity_name}.{prop_cn_name}' 包含特殊字符 '{char}'")
            
            # 检查关系名称
            for relation in entity_type.get("relations", []):
                rel_name = relation.get("name", "")
                has_forbidden, char = contains_forbidden_char(rel_name)
                if has_forbidden:
                    issues.append(f"关系英文名 '{entity_name}.{rel_name}' 包含特殊字符 '{char}'")
                
                # 关系中文名允许省略号"..."，因为常用于表达如"为...提出"这样的语义
                rel_cn_name = relation.get("cn_name", "")
                has_forbidden, char = contains_forbidden_char(rel_cn_name, allow_ellipsis=True)
                if has_forbidden:
                    issues.append(f"关系中文名 '{entity_name}.{rel_cn_name}' 包含特殊字符 '{char}'")
        
        # 也检查全局关系
        for relation in ast.get("relations", []):
            rel_name = relation.get("name", "")
            has_forbidden, char = contains_forbidden_char(rel_name)
            if has_forbidden:
                issues.append(f"关系英文名 '{rel_name}' 包含特殊字符 '{char}'")
            
            # 关系中文名允许省略号"..."，因为常用于表达如"为...提出"这样的语义
            rel_cn_name = relation.get("cn_name", "")
            has_forbidden, char = contains_forbidden_char(rel_cn_name, allow_ellipsis=True)
            if has_forbidden:
                issues.append(f"关系中文名 '{rel_cn_name}' 包含特殊字符 '{char}'")
        
        if issues:
            return False, message, {"issues": issues[:15]}  # 只显示前15个问题
        
        return True, "名称检查通过，没有使用特殊字符", None


class CustomRuleBuilder:
    """自定义规则构建器 - 帮助用户创建验证规则"""
    
    @staticmethod
    def create_type_restriction_rule(allowed_types: List[str]) -> Callable:
        """创建类型限制规则"""
        def validator(ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
            allowed = set(allowed_types)
            found_types = set()
            
            for entity_type in ast.get("types", []):
                for prop in entity_type.get("properties", []):
                    found_types.add(prop.get("data_type", ""))
            
            invalid = found_types - allowed
            if invalid:
                return False, f"发现不允许的类型: {invalid}", {"invalid": list(invalid)}
            
            return True, f"类型检查通过: {found_types}", {"types": list(found_types)}
        
        return validator
    
    @staticmethod
    def create_required_entity_rule(required_entities: List[str]) -> Callable:
        """创建必需实体规则"""
        def validator(ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
            entity_names = {e["name"] for e in ast.get("types", [])}
            missing = set(required_entities) - entity_names
            
            if missing:
                return False, f"缺少必需的实体: {missing}", {"missing": list(missing)}
            
            return True, "包含所有必需的实体", None
        
        return validator
    
    @staticmethod
    def create_property_count_rule(min_props: int = 1, max_props: int = 100) -> Callable:
        """创建属性数量规则"""
        def validator(ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
            issues = []
            
            for entity_type in ast.get("types", []):
                prop_count = len(entity_type.get("properties", []))
                if prop_count < min_props:
                    issues.append(f"{entity_type['name']} 属性太少 ({prop_count} < {min_props})")
                elif prop_count > max_props:
                    issues.append(f"{entity_type['name']} 属性太多 ({prop_count} > {max_props})")
            
            if issues:
                return False, "属性数量不符合要求", {"issues": issues}
            
            return True, f"属性数量符合要求 ({min_props}-{max_props})", None
        
        return validator
    
    @staticmethod
    def create_namespace_rule(allowed_namespaces: List[str] = None, 
                            pattern: str = None) -> Callable:
        """创建命名空间规则"""
        def validator(ast: Dict, schema_text: str) -> Tuple[bool, str, Optional[Dict]]:
            namespace = ast.get("namespace", "")
            
            if allowed_namespaces and namespace not in allowed_namespaces:
                return False, f"命名空间 '{namespace}' 不在允许列表中", {
                    "namespace": namespace,
                    "allowed": allowed_namespaces
                }
            
            if pattern and not re.match(pattern, namespace):
                return False, f"命名空间 '{namespace}' 不符合模式 '{pattern}'", {
                    "namespace": namespace,
                    "pattern": pattern
                }
            
            return True, f"命名空间 '{namespace}' 符合要求", None
        
        return validator


if __name__ == "__main__":
    # 测试示例
    print("=" * 50)
    print("Schema自定义验证器测试")
    print("=" * 50)
    
    # 创建验证器
    validator = SchemaCustomValidator()
    
    # 创建测试AST
    test_ast = {
        "namespace": "TestProject",
        "types": [
            {
                "name": "Project",
                "cn_name": "项目",
                "properties": [
                    {"name": "projectName", "cn_name": "项目名称", "data_type": "Text"},
                    {"name": "amount", "cn_name": "金额", "data_type": "Float"},
                    {"name": "startDate", "cn_name": "开始日期", "data_type": "Text"}
                ]
            },
            {
                "name": "invalidEntity",  # 故意的错误命名
                "cn_name": "测试实体",
                "properties": [
                    {"name": "InvalidProp", "cn_name": "测试属性", "data_type": "string"}  # 故意的错误
                ]
            }
        ],
        "relations": []
    }
    
    # 执行验证
    result = validator.validate(test_ast)
    
    print(f"\n验证结果: {'✅ 通过' if result['is_valid'] else '❌ 失败'}")
    print(f"摘要: {result['summary']}")
    print(f"执行规则数: {result['total_rules']}")
    print(f"通过: {result['passed']}, 失败: {result['failed']}")
    
    if result['errors']:
        print("\n错误:")
        for error in result['errors']:
            print(f"  - [{error.rule_name}] {error.message}")
    
    if result['warnings']:
        print("\n警告:")
        for warning in result['warnings']:
            print(f"  - [{warning.rule_name}] {warning.message}")
    
    # 测试自定义规则
    print("\n" + "=" * 50)
    print("测试自定义规则")
    print("=" * 50)
    
    # 添加自定义规则
    custom_rule = CustomRuleBuilder.create_required_entity_rule(["Project", "User", "Task"])
    validator.add_rule(
        name="required_entities",
        description="必须包含Project、User和Task实体",
        validator=custom_rule
    )
    
    # 再次验证
    result2 = validator.validate(test_ast)
    print(f"\n添加自定义规则后的验证结果: {result2['summary']}")
