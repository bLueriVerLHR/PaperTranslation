**源码摘录：用 remap 表区分新行与上一步延续行。** 仓库 `deepinfer`，固定提交 `774ce244b87cc0eb8d4b94ab9f5de2ab22049f01`；文件 `csrc/engine/zos.cpp`，第 147–176 行，符号 `prepare_zos_inputs`。[对应源码](https://github.com/deepseek-ai/DeepInfer/blob/774ce244b87cc0eb8d4b94ab9f5de2ab22049f01/csrc/engine/zos.cpp#L147-L176)。

```cpp
    std::vector<int32_t> remap_indices(seq_metadata_list.size(), -1);
    bool same_order = seq_metadata_list.size() == prev_seq_metadata_list.size();
    if (same_order) {
        for (int32_t i = 0; i < static_cast<int32_t>(seq_metadata_list.size()); ++i) {
            if (prev_seq_metadata_list[i]->is_placeholder || seq_metadata_list[i]->seq_id != prev_seq_metadata_list[i]->seq_id) {
                same_order = false;
                break;
            }
            remap_indices[i] = i;
        }
    }

    bool has_overlap = same_order && !seq_metadata_list.empty();
    if (!same_order) {
        std::unordered_map<int64_t, int32_t> prev_indices;
        prev_indices.reserve(prev_seq_metadata_list.size());
        for (int32_t i = 0; i < static_cast<int32_t>(prev_seq_metadata_list.size()); ++i) {
            if (!prev_seq_metadata_list[i]->is_placeholder) {
                prev_indices.insert_or_assign(prev_seq_metadata_list[i]->seq_id, i);
            }
        }
        for (int32_t i = 0; i < static_cast<int32_t>(seq_metadata_list.size()); ++i) {
            auto prev = prev_indices.find(seq_metadata_list[i]->seq_id);
            remap_indices[i] = prev == prev_indices.end() ? -1 : prev->second;
            has_overlap |= remap_indices[i] >= 0;
        }
    }
    if (!has_overlap) {
        return {std::nullopt, std::nullopt, std::nullopt, false};
    }
```
