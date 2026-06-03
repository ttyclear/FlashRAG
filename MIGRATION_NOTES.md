# 数据迁移记录 / Migration Notes

**迁移日期 (Date):** 2026-06-03
**源 (Source):** `/data/tyc/FlashRAG` — 本地 clone of `RUC-NLPIR/FlashRAG` @ `b560725`（含本地未提交的实验改动与产物）
**目标 (Target):** https://github.com/ttyclear/FlashRAG — 个人 fork，`main` @ `e0e7339`（领先上游若干提交：conda 安装脚本、项目目录结构、RAG failure-mode 文档等，本次迁移已保留这些提交）

---

## 1. 概述 / Overview

本仓库是 FlashRAG 的个人 fork，用于做 **检索器对比实验**（不同 embedding/检索模型 × 数据集 × 训练/测试 split，统一用 Qwen3-8B 作为生成器）。

本次迁移要解决的核心问题：本地工作目录里有 **32GB 的实验中间数据**（87 个 `intermediate_data.json`，单文件最大 1.4GB），**远超 GitHub 单文件 100MB 限制**，无法也不应该进入 Git。因此通过 `.gitignore` 排除这些可再生的大文件，**只保留代码改动、实验配置和最终指标**，再推送到个人仓库。

迁移策略：本地 HEAD (`b560725`) 是目标 `main` (`e0e7339`) 的祖先，因此把本地改动 **rebase 到 `origin/main` 之上**，不破坏 fork 已有提交（非 force-push）。

---

## 2. 保留 / Kept （已进入 Git）

| 类别 | 内容 | 说明 |
|------|------|------|
| 代码改动 | `flashrag/retriever/utils.py`、`index_builder.py`、`retriever.py` | 新增 **`lasttoken` 池化** 支持（用于 Qwen3-Embedding / Diver-Retriever 等 last-token 模型）的建索引与检索路径 |
| 代码改动 | `flashrag/prompt/base_prompt.py` | 识别 Qwen3 生成器并在 chat template 中关闭 thinking（`enable_thinking=False`），将 qwen3 视为 chat 模型 |
| 实验配置 | `examples/methods/my_config.yaml` | 模型路径（e5/e5-large/bge/bge-large/bge-m3/qwen3-embedding/diver）、index 路径、检索与生成参数、Qwen3-8B 生成器设置 |
| 脚本 | `bench_latency.py` | 检索/生成延迟基准脚本 |
| **实验结果** | 全部 **87 组实验**的 `config.yaml` + `metric_score.txt` | 每个实验目录的**完整实验设置 + 最终指标**（em/f1/acc/precision/recall），合计 ~0.7MB。逐样本中间数据被丢弃，但**结果与可复现配置完整保留** |
| 上游既有 | 源码、文档、`examples/quick_start/indexes/`（e5 demo index 44MB + general_knowledge.jsonl 6.5MB） | 上游本就跟踪，<100MB，保持不变 |

> 实验结果完整索引见本文 **第 5 节**。

---

## 3. 忽略 / 丢失 / Ignored & Lost （未进入 Git）

| 内容 | 体量 | 为什么忽略 | 能否恢复 |
|------|------|-----------|----------|
| `**/intermediate_data.json`（87 个文件） | **~32GB**，单文件最大 1.4GB | 每次实验 `run_exp.py` 生成的**逐样本中间数据**（检索到的文档、构造的 prompt、原始生成）。远超 GitHub 100MB 单文件硬限制 | ✅ 可由 `run_exp.py` 重新生成（见第 4 节） |
| `*.log`（`run_exp_log.log` 134KB、`run_exp_log_2.log` 630KB） | <1MB | 运行时 stdout 日志，噪声、可再生 | ✅ 重跑即得；如需保留可从 `.gitignore` 移除 `*.log` |
| `build/`、`flashrag_dev.egg-info/` | ~1MB | Python 构建产物 | ✅ `pip install -e .` 重新生成 |
| 本地 `datasets/`、`indexes/`、`models/`、`results/`、`webui_configs/` | 大（语料 / FAISS 索引 / 模型权重） | 外部大数据，按 fork 既定规则只保留 `.gitkeep` 占位 | ⬇️ 需按 `my_config.yaml` 中的路径另行下载/构建 |

**结论：丢失的全部是“可再生”或“需另行下载”的数据，没有丢失任何不可恢复的实验结论。** 每组实验的最终指标（`metric_score.txt`）和配置（`config.yaml`）均已保留。

---

## 4. 如何复现被忽略的中间数据 / Regeneration

被丢弃的 `intermediate_data.json` 可通过重跑实验生成：

```bash
# 前提：按 examples/methods/my_config.yaml 准备好
#   - 模型权重 (model2path)
#   - 检索 index (method2index)
#   - 语料 corpus_path、数据集 data_dir
cd examples/methods
python run_exp.py            # 配合 my_config.yaml；config 中 save_intermediate_data: True 会重新写出 intermediate_data.json
```

每个实验目录下 **保留的 `config.yaml` 就是该次实验的精确配置快照**，可据此原样复现对应的中间数据。

---

## 5. 保留的实验结果索引 / Retained Results Index

下表汇总全部 87 组实验的最终指标（数值取 4 位小数，完整精度见各目录 `metric_score.txt`）。
列含义：`EM` = exact match，`F1`，`Acc` = accuracy。

### 5.1 `examples/methods/output/`（早期 / 混合运行）

| 实验 (dir) | EM | F1 | Acc |
|------|----|----|-----|
| bge-hotpotqa | 0.2671 | 0.3710 | 0.3571 |
| bge-large-hotpotqa | 0.2754 | 0.3860 | 0.3695 |
| bge-m3-hotpotqa | 0.2473 | 0.3501 | 0.3334 |
| bge-m3-nq | 0.3352 | 0.4349 | 0.4720 |
| bge-m3-triviaqa | 0.5515 | 0.6421 | 0.6499 |
| bge-nq | 0.3371 | 0.4460 | 0.4834 |
| bge-triviaqa | 0.5632 | 0.6561 | 0.6637 |
| bm25-hotpotqa | 0.1787 | 0.2615 | 0.2501 |
| diver0.6b-hotpotqa | 0.2275 | 0.3278 | 0.3088 |
| diver0.6b-nq | 0.3066 | 0.4036 | 0.4313 |
| diver0.6b-triviaqa | 0.5556 | 0.6476 | 0.6542 |
| e5-large-hotpotqa | 0.2687 | 0.3787 | 0.3629 |
| e5basev2-hotpotqa | 0.2531 | 0.3575 | 0.3411 |
| e5basev2-nq | 0.3612 | 0.4735 | 0.5202 |
| e5basev2-triviaqa | 0.5883 | 0.6813 | 0.6901 |
| norag-hotpotqa | 0.1916 | 0.2696 | 0.2182 |
| nq_2025_12_30_03_31_naive | 0.1294 | 0.1822 | 0.1906 |
| qwen0.6b-hotpotqa | 0.2442 | 0.3463 | 0.3283 |
| qwen0.6b-nq | 0.3235 | 0.4271 | 0.4648 |
| qwen0.6b-triviaqa | 0.5589 | 0.6533 | 0.6594 |
| qwen4b-hotpotqa | 0.2664 | 0.3762 | 0.3604 |
| qwen4b-nq | 0.3449 | 0.4580 | 0.5061 |
| qwen4b-triviaqa | 0.5975 | 0.6938 | 0.7047 |
| train-diver0.6b-hotpotqa | 0.3323 | 0.4067 | 0.4019 |
| train-diver0.6b-nq | 0.2958 | 0.4099 | 0.4120 |
| train-qwen0.6b-hotpotqa | 0.3371 | 0.4140 | 0.4110 |
| train-qwen0.6b-nq | 0.3187 | 0.4373 | 0.4434 |
| train-qwen4b-hotpotqa | 0.3726 | 0.4540 | 0.4525 |
| train-qwen4b-nq | 0.3480 | 0.4755 | 0.4847 |

### 5.2 `examples/methods/qwen3-8b-output/test/`（Qwen3-8B 生成器，test split）

| 实验 (dir) | EM | F1 | Acc |
|------|----|----|-----|
| hotpotqa/bge-hotpotqa | 0.3151 | 0.4299 | 0.3864 |
| hotpotqa/bge-large-hotpotqa | 0.3249 | 0.4441 | 0.3966 |
| hotpotqa/bge-m3-hotpotqa | 0.2939 | 0.4052 | 0.3633 |
| hotpotqa/bm25-hotpotqa | 0.2261 | 0.3145 | 0.2858 |
| hotpotqa/diver0.6b-hotpotqa | 0.2744 | 0.3804 | 0.3384 |
| hotpotqa/e5-large-hotpotqa | 0.3198 | 0.4402 | 0.3951 |
| hotpotqa/e5basev2-hotpotqa | 0.2986 | 0.4121 | 0.3706 |
| hotpotqa/norag-hotpotqa | 0.1515 | 0.2473 | 0.2259 |
| hotpotqa/qwen0.6b-hotpotqa | 0.2886 | 0.3988 | 0.3561 |
| hotpotqa/qwen4b-hotpotqa | 0.3161 | 0.4335 | 0.3885 |
| nq/bge-large-nq | 0.3028 | 0.4319 | 0.5443 |
| nq/bge-m3-nq | 0.2809 | 0.4004 | 0.5036 |
| nq/bge-nq | 0.2900 | 0.4171 | 0.5324 |
| nq/bm25-nq | 0.1305 | 0.2054 | 0.2668 |
| nq/diver0.6b-nq | 0.2524 | 0.3708 | 0.4659 |
| nq/e5-large-nq | 0.3186 | 0.4498 | 0.5673 |
| nq/e5basev2-nq | 0.3091 | 0.4385 | 0.5590 |
| nq/norag-nq | 0.0881 | 0.1887 | 0.2828 |
| nq/qwen0.6b-nq | 0.2712 | 0.3937 | 0.4975 |
| nq/qwen4b-nq | 0.3006 | 0.4312 | 0.5402 |
| triviaqa/bge-large-tqa | 0.5638 | 0.6661 | 0.6893 |
| triviaqa/bge-m3-tqa | 0.5457 | 0.6452 | 0.6681 |
| triviaqa/bge-tqa | 0.5562 | 0.6568 | 0.6812 |
| triviaqa/bm25-tqa | 0.4078 | 0.4972 | 0.5201 |
| triviaqa/diver0.6b-tqa | 0.5457 | 0.6467 | 0.6692 |
| triviaqa/e5-large-tqa | 0.5945 | 0.6970 | 0.7224 |
| triviaqa/e5basev2-tqa | 0.5838 | 0.6826 | 0.7078 |
| triviaqa/norag-tqa | 0.3554 | 0.4581 | 0.5018 |
| triviaqa/qwen0.6b-tqa | 0.5524 | 0.6532 | 0.6775 |
| triviaqa/qwen4b-tqa | 0.5921 | 0.6947 | 0.7187 |

### 5.3 `examples/methods/qwen3-8b-output/train/`（Qwen3-8B 生成器，train split）

| 实验 (dir) | EM | F1 | Acc |
|------|----|----|-----|
| hotpotqa/bge-hotpotqa | 0.4257 | 0.5085 | 0.4913 |
| hotpotqa/bge-large-hotpotqa | 0.4420 | 0.5261 | 0.5071 |
| hotpotqa/bge-m3-hotpotqa | 0.3877 | 0.4689 | 0.4493 |
| hotpotqa/diver0.6b-hotpotqa | 0.3724 | 0.4515 | 0.4329 |
| hotpotqa/e5-large-hotpotqa | 0.4354 | 0.5205 | 0.5009 |
| hotpotqa/e5basev2-hotpotqa | 0.4074 | 0.4887 | 0.4707 |
| hotpotqa/norag-hotpotqa | 0.1994 | 0.2797 | 0.2740 |
| hotpotqa/qwen0.6b-hotpotqa | 0.3808 | 0.4615 | 0.4435 |
| hotpotqa/qwen4b-hotpotqa | 0.4189 | 0.5034 | 0.4844 |
| nq/bge-large-nq | 0.3159 | 0.4583 | 0.5261 |
| nq/bge-m3-nq | 0.2925 | 0.4252 | 0.4909 |
| nq/bge-nq | 0.3109 | 0.4495 | 0.5165 |
| nq/diver0.6b-nq | 0.2648 | 0.3908 | 0.4457 |
| nq/e5-large-nq | 0.3354 | 0.4804 | 0.5559 |
| nq/e5basev2-nq | 0.3271 | 0.4701 | 0.5443 |
| nq/norag-nq | 0.0831 | 0.1786 | 0.2541 |
| nq/qwen0.6b-nq | 0.2836 | 0.4148 | 0.4783 |
| nq/qwen4b-nq | 0.3126 | 0.4538 | 0.5224 |
| triviaqa/bge-large-tqa | 0.5626 | 0.6693 | 0.6904 |
| triviaqa/bge-m3-tqa | 0.5415 | 0.6471 | 0.6685 |
| triviaqa/bge-tqa | 0.5493 | 0.6549 | 0.6771 |
| triviaqa/diver0.6b-tqa | 0.5471 | 0.6514 | 0.6729 |
| triviaqa/e5-large-tqa | 0.5935 | 0.7009 | 0.7240 |
| triviaqa/e5basev2-tqa | 0.5766 | 0.6835 | 0.7060 |
| triviaqa/norag-tqa | 0.3544 | 0.4589 | 0.5044 |
| triviaqa/qwen0.6b-tqa | 0.5479 | 0.6537 | 0.6753 |
| triviaqa/qwen4b-tqa | 0.5865 | 0.6937 | 0.7160 |

### 5.4 `examples/quick_start/`

| 实验 (dir) | EM | F1 | Acc |
|------|----|----|-----|
| output/nq_2026_02_18_00_14_experiment | 0.0588 | 0.0588 | 0.0588 |

> 注：`quick_start` 为冒烟测试（极小样本），指标仅供流程验证，无实验意义。
