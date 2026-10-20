**源码摘录：先应用物理页边界，再查找逻辑前缀。** 仓库 `sglang`，固定提交 `00bcc25f6c857dc7cfb9e624ee38269d4c3735f6`；文件 `python/sglang/srt/mem_cache/radix_cache.py`，第 392–407 行，符号 `RadixCache.match_prefix`。[对应源码](https://github.com/sgl-project/sglang/blob/00bcc25f6c857dc7cfb9e624ee38269d4c3735f6/python/sglang/srt/mem_cache/radix_cache.py#L392-L407)。

```python
        key = params.key
        key, _ = key.maybe_to_bigram_view(self.is_eagle)

        if self.disable or len(key) == 0:
            return self._empty_match_result

        key = key.page_aligned(self.page_size)

        if len(key) == 0:
            return self._empty_match_result

        value, last_node = self._match_prefix_helper(self.root_node, key)
        if value:
            value = torch.cat(value)
        else:
            value = self._empty_match_result.device_indices
```
