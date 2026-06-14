"""Quick test script for OpenAI Responses integration.

Run:
  python test_openai.py

It will call run_graph() with two sample prompts and print outputs.
"""
import os
import sys
from dotenv import load_dotenv

# load env vars from .env (if present)
load_dotenv()

sys.path.insert(0, ".")

from graph import run_graph

if __name__ == "__main__":
    samples = [
        "我的 body roll 重心往前，舞風是 street jazz",
        "明天下午有哪些練習室空著？",
    ]

    for s in samples:
        print(f"\n--- Prompt: {s}\n")
        out = run_graph(s)
        print(out)
