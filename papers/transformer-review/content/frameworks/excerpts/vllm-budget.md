**源码摘录：把请求进度差额约束到本轮预算。** 仓库 `vllm`，固定提交 `b0e21b308352587a6fd02f72722a2e815bfd62f0`；文件 `vllm/v1/core/sched/scheduler.py`，第 683–692 行，符号 `Scheduler.schedule`。[对应源码](https://github.com/vllm-project/vllm/blob/b0e21b308352587a6fd02f72722a2e815bfd62f0/vllm/v1/core/sched/scheduler.py#L683-L692)。

```python
            num_new_tokens = (
                request.num_tokens_with_spec
                + request.num_output_placeholders
                - request.num_computed_tokens
            )
            if 0 < long_prefill_token_threshold < num_new_tokens:
                num_new_tokens = long_prefill_token_threshold
            num_new_tokens = min(
                num_new_tokens, token_budget, input_budget - draft_slots
            )
```
