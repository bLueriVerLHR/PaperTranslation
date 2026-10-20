**源码摘录：在寄存器中计算输出与输出梯度的行内点积。** 仓库 `flash-attention`，固定提交 `e9515d5dee6ade134a33d6020d38d01ef0596996`；文件 `flash_attn/cute/flash_bwd_preprocess.py`，第 409–412 行，符号 `FlashAttentionBackwardPreprocess.kernel（无 O 残差分支）`。[对应源码](https://github.com/dao-ailab/flash-attention/blob/e9515d5dee6ade134a33d6020d38d01ef0596996/flash_attn/cute/flash_bwd_preprocess.py#L409-L412)。

```python
                # Sum across the "k" dimension
                pdpsum = (tOrO.load().to(Float32) * tOrdO.load().to(Float32)).reduce(
                    cute.ReductionOp.ADD, init_val=0.0, reduction_profile=(0, None, 1)
                )
```
