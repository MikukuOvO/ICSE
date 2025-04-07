import tiktoken
import glob
import os

# 选择模型对应的 tokenizer，例如 gpt-3.5-turbo
encoding = tiktoken.encoding_for_model("gpt-4")

folders = [f for f in glob.glob("results/train-ticket/*") if os.path.isdir(f)]

for folder in folders:
    print(f"Processing folder: {folder}")
    # 获取文件夹中的所有 .txt 文件
    files = glob.glob(os.path.join(folder, "logs/*.md"))
    token_count = 0
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            # 计算 token 数量
            token_count += len(encoding.encode(content))
    output_path = os.path.join(folder, "token_count.txt")
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"Token count: {token_count}")
