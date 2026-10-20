**源码摘录：仅在本轮计划覆盖预填充尾部时转入运行队列。** 仓库 `nano-vllm`，固定提交 `bb823b3e06983d71485a8e1f23715ebd87d98ef8`；文件 `nanovllm/engine/scheduler.py`，第 46–52 行，符号 `Scheduler.schedule`。[对应源码](https://github.com/GeeeekExplorer/nano-vllm/blob/bb823b3e06983d71485a8e1f23715ebd87d98ef8/nanovllm/engine/scheduler.py#L46-L52)。

```python
            seq.num_scheduled_tokens = min(num_tokens, remaining)
            num_batched_tokens += seq.num_scheduled_tokens
            if seq.num_cached_tokens + seq.num_scheduled_tokens == seq.num_tokens:
                seq.status = SequenceStatus.RUNNING
                self.waiting.popleft()
                self.running.append(seq)
            scheduled_seqs.append(seq)
```
