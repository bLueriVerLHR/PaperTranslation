**源码摘录：将逻辑批拆为可容纳的物理批并返回处理上下文。** 仓库 `llama.cpp`，固定提交 `cb7934c52ca8710994b2ecc19775ebefcfdb8d01`；文件 `src/llama-memory.h`，第 85–91 行，符号 `llama_memory_i::init_batch`。[对应源码](https://github.com/ggml-org/llama.cpp/blob/cb7934c52ca8710994b2ecc19775ebefcfdb8d01/src/llama-memory.h#L85-L91)。

```cpp
    // split the input batch into a set of ubatches and verify that they can fit into the cache
    // return a context object containing the ubatches and memory state required to process them
    // check the llama_memory_context_i::get_status() for the result
    virtual llama_memory_context_ptr init_batch(
            llama_batch_allocr & balloc,
            uint32_t n_ubatch,
            bool embd_all) = 0;
```
