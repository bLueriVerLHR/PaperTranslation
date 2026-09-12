## 2.1 样例小节

这是一段用于验证排版的中文正文，包含行内公式 <math><mi>d</mi><mo>=</mo><mn>128</mn></math>
以及英文术语 cross-layer reuse（跨层复用）。段落应当两端对齐，并在窄屏上自然换行。

### 2.1.1 更深一层

嵌套标题用于验证目录的层级结构。

<div class="equation" id="eq-sample">
<math display="block">
  <mrow>
    <mi>r</mi><mo>(</mo><mi>&#x2113;</mi><mo>,</mo><mi>b</mi><mo>)</mo>
    <mo>=</mo><mo>&#x2212;</mo><mi>min</mi>
    <mo>(</mo>
    <msub><mi>C</mi><mtext>max</mtext></msub>
    <mo>,</mo>
    <mi>k</mi><mo>(</mo><mi>b</mi><mo>)</mo>
    <mfrac>
      <mi>&#x2113;</mi>
      <msub><mi>L</mi><mtext>norm</mtext></msub>
    </mfrac>
    <mo>)</mo>
  </mrow>
</math>
<span class="eqno">(11)</span>
</div>

<figure>
<img src="assets/figures/figure-03.png" alt="样例图">
<figcaption>图 3 | 样例图注，用于验证图片与图注的排版。</figcaption>
</figure>

<table>
<caption>表 1 | 样例表格。</caption>
<thead>
<tr><th>项目</th><th>数值</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td>全局 KV</td><td>890</td><td>字节/词元</td></tr>
<tr><td>持久化 KV</td><td>1/8</td><td>相对基线</td></tr>
</tbody>
</table>

<pre class="algorithm"><code><span class="alg-keyword">Require:</span> 权重 <span class="alg-op">W</span>, 梯度 <span class="alg-op">G</span>
<span class="alg-number">1:</span> <span class="alg-fn">M</span> ← 动量更新        <span class="alg-comment">⊳ 注记</span>
<span class="alg-number">2:</span> <span class="alg-keyword">for</span> k = 1, …, K <span class="alg-keyword">do</span>
<span class="alg-number">3:</span>     逐步归一化
<span class="alg-number">4:</span> <span class="alg-keyword">end for</span></code></pre>

这一段带脚注[^note]，用于验证脚注渲染。

[^note]: 样例脚注内容。
