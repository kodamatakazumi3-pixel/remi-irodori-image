FROM ghcr.io/kodamatakazumi3-pixel/irodori-tts-server:latest
RUN uv pip install --python /app/.venv/bin/python runpod
COPY handler.py /app/handler.py
CMD ["/app/.venv/bin/python", "/app/handler.py"]
