#!/usr/bin/env python3
import os
import glob
import yaml

def process_yaml_file(filepath):
    with open(filepath, 'r') as f:
        try:
            # 加载 YAML 文件（支持多文档）
            docs = list(yaml.safe_load_all(f))
        except Exception as e:
            print(f"解析 {filepath} 时出错: {e}")
            return

    modified = False
    new_docs = []
    for doc in docs:
        # 如果文档为空则跳过
        if doc is None:
            new_docs.append(doc)
            continue
        # 如果没有 metadata 节点则创建
        if 'metadata' not in doc or doc['metadata'] is None:
            doc['metadata'] = {}
        # 如果 namespace 字段不存在或者不是 social-network，则设置它
        if doc['metadata'].get('namespace') != 'social-network':
            doc['metadata']['namespace'] = 'social-network'
            modified = True
        new_docs.append(doc)

    if modified:
        with open(filepath, 'w') as f:
            # 写入所有文档到同一文件中
            yaml.dump_all(new_docs, f, default_flow_style=False, sort_keys=False)
        print(f"已修改 {filepath}")
    else:
        print(f"{filepath} 无需修改")

def main():
    # 获取当前目录下所有 .yaml 和 .yml 文件
    yaml_files = glob.glob("*.yaml") + glob.glob("*.yml")
    for file in yaml_files:
        process_yaml_file(file)

if __name__ == '__main__':
    main()
