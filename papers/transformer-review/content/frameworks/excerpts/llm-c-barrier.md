**源码摘录：损失读取完成后才允许覆盖 logits。** 仓库 `llm.c`，固定提交 `f1e2ace651495b74ae22d45d1723443fd00ecd3a`；文件 `llmc/fused_classifier.cuh`，第 82–92 行，符号 `fused_classifier_kernel5`。[对应源码](https://github.com/karpathy/llm.c/blob/f1e2ace651495b74ae22d45d1723443fd00ecd3a/llmc/fused_classifier.cuh#L82-L92)。

```cuda
    // calculate the probability needed for the loss and update (single-threaded)
    if(threadIdx.x == 0) {
        float prob = expf((float)logits[idx * P + ix] - sp.Offset) * sp.Scale;
        losses[idx] -= logf(prob);
    }

    // without this synchronization point we have a race condition:
    // the logits used above to compute the loss are concurrently (race) modified to carry backward pass grads.
    // since the "logits" are overwritten to be in the [-1, 1] range and sp.Offset is sometimes smaller than -90
    // we errouneously end up computing exp^(90+) which gives us infinities in the loss! this is the fix.
    __syncthreads();
```
