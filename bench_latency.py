#!/usr/bin/env python3
"""Per-model encoding latency benchmark for FlashRAG retrievers.

- Uses NQ test queries as input.
- Supports dense encoders and BM25.
- Reports average latency in milliseconds per query.
"""
import argparse
import json
import os
import random
import time
from typing import List, Dict, Any

import torch
import yaml

# FlashRAG modules
from flashrag.retriever.encoder import Encoder
from flashrag.retriever.retriever import BM25Retriever
from flashrag.config import Config
from flashrag.utils import get_device


def load_yaml_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_queries(nq_path: str, sample_size: int, seed: int = 42) -> List[str]:
    with open(nq_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    rng = random.Random(seed)
    rng.shuffle(lines)
    queries = [item["question"] for item in lines[:sample_size]]
    return queries


def torch_sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def measure_dense_latency(model_key: str, model_path: str, pooling: str, queries: List[str], max_length: int,
                           use_fp16: bool, batch_size: int) -> float:
    enc = Encoder(
        model_name=model_key,
        model_path=model_path,
        pooling_method=pooling,
        max_length=max_length,
        use_fp16=use_fp16,
        instruction=None,
        silent=True,
    )
    # warmup
    enc.encode(queries[:1], batch_size=1, is_query=True)

    torch_sync()
    t0 = time.perf_counter()
    for q in queries:
        enc.encode([q], batch_size=batch_size, is_query=True)
    torch_sync()
    t1 = time.perf_counter()
    avg_ms = (t1 - t0) * 1000.0 / len(queries)
    return avg_ms


def measure_bm25_latency(index_path: str, corpus_path: str, queries: List[str], topk: int, bm25_backend: str = "bm25s") -> float:
    cfg_dict = {
        "retrieval_method": "bm25",
        "index_path": index_path,
        "bm25_backend": bm25_backend,
        "corpus_path": corpus_path,
        "retrieval_topk": topk,
        "metrics": [],
        "split": ["test"],
        "data_dir": os.path.dirname(os.path.dirname(corpus_path)),
    }
    cfg = Config(config_dict=cfg_dict)
    retriever = BM25Retriever(cfg)
    retriever.topk = topk
    # warmup
    retriever.search(queries[0], num=topk)

    torch_sync()
    t0 = time.perf_counter()
    for q in queries:
        retriever.search(q, num=topk)
    torch_sync()
    t1 = time.perf_counter()
    avg_ms = (t1 - t0) * 1000.0 / len(queries)
    return avg_ms


def main():
    parser = argparse.ArgumentParser(description="Measure per-query encoding latency for FlashRAG retrievers.")
    parser.add_argument("--config", default="examples/methods/my_config.yaml", help="Path to FlashRAG YAML config.")
    parser.add_argument("--sample_size", type=int, default=32, help="Number of queries to test.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling queries.")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size for encoding.")
    parser.add_argument("--max_length", type=int, default=128, help="Max length for query encoding.")
    parser.add_argument("--nq_path", default="/data/tyc/datasets/FlashRAG_datasets/nq/test.jsonl",
                        help="Path to NQ test jsonl.")
    args = parser.parse_args()

    cfg = load_yaml_config(args.config)
    model2path = cfg.get("model2path", {})
    model2pool = cfg.get("model2pooling", {})
    method2index = cfg.get("method2index", {})
    corpus_path = cfg.get("corpus_path") or os.path.join(cfg.get("data_dir", ""), "retrieval-corpus/wiki18_100w.jsonl")

    models = [
        ("e5-base-v2-rag", "e5"),
        ("e5-large-rag", "e5-large"),
        ("bge-rag", "bge"),
        ("bge-large-rag", "bge-large"),
        ("bge-m3-rag", "bge-m3"),
        ("qwen3-embedding-0.6b", "qwen3-embedding-0.6B"),
        ("qwen3-embedding-4b", "qwen3-embedding-4B"),
        ("DIVER-Retriever-0.6B", "diver-retriever-0.6B"),
    ]

    bm25_entry = ("bm25-rag", "bm25")

    queries = load_queries(args.nq_path, args.sample_size, args.seed)

    results = []
    device = get_device()
    print(f"Running on device: {device}")
    print(f"Sample size: {len(queries)}, batch_size={args.batch_size}, max_length={args.max_length}")

    for display_name, key in models:
        path = model2path.get(key)
        pooling = model2pool.get(key)
        if path is None or pooling is None:
            print(f"[skip] {display_name}: missing path or pooling in config")
            continue
        try:
            avg_ms = measure_dense_latency(
                model_key=key,
                model_path=path,
                pooling=pooling,
                queries=queries,
                max_length=args.max_length,
                use_fp16=True,
                batch_size=args.batch_size,
            )
            results.append((display_name, avg_ms))
            print(f"{display_name}: {avg_ms:.2f} ms/query")
        except Exception as e:
            print(f"[error] {display_name}: {e}")

    # BM25 latency
    index_path = method2index.get("bm25")
    if index_path:
        try:
            bm25_ms = measure_bm25_latency(
                index_path=index_path,
                corpus_path=corpus_path,
                queries=queries,
                topk=5,
                bm25_backend="bm25s",
            )
            results.append((bm25_entry[0], bm25_ms))
            print(f"{bm25_entry[0]}: {bm25_ms:.2f} ms/query")
        except Exception as e:
            print(f"[error] {bm25_entry[0]}: {e}")
    else:
        print("[skip] bm25-rag: index path missing in config")

    print("\n=== Summary (ms/query) ===")
    for name, ms in results:
        print(f"{name}: {ms:.2f}")


if __name__ == "__main__":
    main()
