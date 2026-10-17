## 中文章节 {#stable-heading}

行内表达式 $x_i + \frac{a}{b}$ 保留原生数学结构。[^condition]

::: {.equation #eq-example}
$$
\begin{aligned}
y &= \sum_{i=1}^n x_i \\
z &= \frac{1}{2}
\end{aligned}
$$
[(1)]{.eqno}
:::

![图 1：合成流程图，图注由渲染器生成。](assets/figures/figure-03.png){#fig-flow}

::: {.note}
**限定条件**：此处仅验证文档结构，不表示数学或实验结论已经审校。
:::

| 输入 | 输出 |
| --- | --- |
| Markdown | 原生 HTML |

```python
    def probe(x):
        return x < 2
```

[^condition]: 完整的条件说明保留在离线页中。

## Acknowledgements {#author-ack}

原作者的致谢属于正文，不按标题关键词搬移。
