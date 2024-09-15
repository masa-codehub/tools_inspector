# ベースイメージとしてPythonを使用
FROM python:3.12.4-slim-bullseye

# 最新版のgitのインストール  
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# 必要なPythonパッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pythonが.pycファイルを生成しないようにします。
ENV PYTHONDONTWRITEBYTECODE=1
# Pythonの出力がバッファリングされないようにします。
ENV PYTHONUNBUFFERED=1
