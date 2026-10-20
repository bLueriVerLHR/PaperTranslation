**源码摘录：先验证准入，再建立序列状态与设备批元数据。** 仓库 `deepspeed`，固定提交 `8fb2c9a256c00df488793ac4a103f688992dcfe4`；文件 `deepspeed/inference/v2/engine_v2.py`，第 122–139 行，符号 `InferenceEngineV2.put`。[对应源码](https://github.com/microsoft/DeepSpeed/blob/8fb2c9a256c00df488793ac4a103f688992dcfe4/deepspeed/inference/v2/engine_v2.py#L122-L139)。

```python
        if do_checks:
            token_lens = [len(tokens) for tokens in batch_tokens]
            schedule_check = self.can_schedule(batch_uids, token_lens)
            if schedule_check != SchedulingResult.Success:
                raise SchedulingError(schedule_check)

        self._batch.clear()
        for uid, tokens in zip(batch_uids, batch_tokens):

            host_seq_desc = self._state_manager.get_or_create_sequence(uid)
            self._model.maybe_allocate_kv(host_seq_desc, tokens.numel())
            host_seq_desc.pre_forward(tokens.numel())

            # We can disable checks since we already validated schedulability.
            self._batch.insert_sequence(host_seq_desc, tokens, do_checks=do_checks)

        # Send all metadata to the device
        self._batch.finalize()
```
