# Retrieval comparison (40 labelled queries, KB-A + KB-B)

| Mode | Precision@5 | Recall@10 | MRR | nDCG@10 | ms/query |
| --- | --- | --- | --- | --- | --- |
| keyword | 0.405 | 0.672 | 0.743 | 0.505 | 68 |
| vector | 0.585 | 0.852 | 0.926 | 0.687 | 961 |
| hybrid | 0.505 | 0.823 | 0.856 | 0.645 | 513 |
| hybrid+rerank | 0.570 | 0.858 | 0.975 | 0.702 | 3276 |

Models: sentence-transformers/all-MiniLM-L6-v2 (vectors), cross-encoder/ms-marco-MiniLM-L-6-v2 (reranker).
Generated 2026-11-26 02:06 by scripts/eval_retrieval.py.
