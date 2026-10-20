**源码摘录：沿祖先链更新引用与可驱逐容量。** 仓库 `mini-sglang`，固定提交 `9a91cfafe754aa85daee49998176275667eb58f2`；文件 `python/minisgl/kvcache/radix_cache.py`，第 113–130 行，符号 `RadixPrefixCache.lock_handle`。[对应源码](https://github.com/sgl-project/mini-sglang/blob/9a91cfafe754aa85daee49998176275667eb58f2/python/minisgl/kvcache/radix_cache.py#L113-L130)。

```python
    def lock_handle(self, handle: BaseCacheHandle, unlock: bool = False) -> None:
        assert isinstance(handle, RadixCacheHandle)
        node = handle.node
        if unlock:
            while not node.is_root():
                node.ref_count -= 1
                assert node.ref_count >= 0
                if node.ref_count == 0:
                    self.evictable_size += node.length
                    self.protected_size -= node.length
                node = node.parent
        else:
            while not node.is_root():
                if node.ref_count == 0:
                    self.evictable_size -= node.length
                    self.protected_size += node.length
                node.ref_count += 1
                node = node.parent
```
