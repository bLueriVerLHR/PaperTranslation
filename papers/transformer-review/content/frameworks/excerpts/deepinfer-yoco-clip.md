**源码摘录：有界重放的截断量被夹在保留区间与最后 1 个 token 之间。** 仓库 `deepinfer`，固定提交 `774ce244b87cc0eb8d4b94ab9f5de2ab22049f01`；文件 `csrc/engine/input_metadata/prepare_tensor_input_v4.cpp`，第 219–232 行，符号 `fill_yoco_truncation_metadata`。[对应源码](https://github.com/deepseek-ai/DeepInfer/blob/774ce244b87cc0eb8d4b94ab9f5de2ab22049f01/csrc/engine/input_metadata/prepare_tensor_input_v4.cpp#L219-L232)。

```cpp
        int32_t q_len = p_seq->seqlen_q;
        int32_t q_start = p_seq->seqlen_k - q_len;
        int32_t data_len = p_seq->seq_data->get_len();
        // 逻辑保留区间 = [max(0, data_len - keep_tokens), data_len) ∩ [q_start, q_end)。clip_prefix 即 chunk 开头被截断
        // 的 token 数；上界 q_len - 1 即 整个 chunk 在保留区间之前时仍保留 chunk 最后 1 个 token 占位。
        // mask 模式不截行，clip_prefix 恒为 0（全部 token 照常计算，只是矩形之外的可见域为空）。
        int32_t clip_prefix = compact ? std::clamp(data_len - keep_tokens - q_start, 0, q_len - 1) : 0;
        clip_prefixes[i_seq] = clip_prefix;
        full_bases[i_seq] = full_base;
        int32_t keep_len = q_len - clip_prefix;
        p_cu_c[i_seq + 1] = p_cu_c[i_seq] + keep_len;
        full_base += q_len;
    }
    const int32_t total_q_c = p_cu_c[n_seq];
```
