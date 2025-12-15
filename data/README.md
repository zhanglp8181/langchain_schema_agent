# 数据目录说明

本目录用于存储Schema生成系统的输入输出文件。

## 目录结构

```
data/
├── input/       # 用户上传的原始文档
│   ├── 上传的文档文件（.txt, .csv, .pdf, .docx）
│   └── 临时文本文件（temp_document_*.txt）
│
└── output/      # 系统生成的Schema文件
    ├── schema_draft_*.txt       # Schema草稿
    ├── schema_published_*.txt   # 已发布的Schema
    └── schema_export_*.*        # 导出的Schema（各种格式）
```

## 文件命名规则

- **输入文件**：`{时间戳}_{原始文件名}`
  - 示例：`20251213_120000_contract.txt`

- **输出文件**：`{类型}_{时间戳}.{扩展名}`
  - 草稿：`schema_draft_20251213_120000.txt`
  - 发布：`schema_published_20251213_120000.txt`
  - 导出：`schema_export_20251213_120000.json`

## 使用说明

1. **上传文档**：用户上传的文档会自动保存到 `input/` 目录
2. **生成Schema**：生成的Schema文件会保存到 `output/` 目录
3. **文件清理**：建议定期清理旧文件，保留重要版本

## 注意事项

- 所有文件都会带上时间戳，避免覆盖
- 系统会自动创建这些目录，无需手动创建
- 文件编码统一使用 UTF-8
