## 布局是映射，代数是对映射做运算 {#cute-layout-algebra}

CuTe 里的布局由一个形状与一个步长组成，作用是把逻辑坐标映射成线性偏移。仓库提供了一份可读的 Python 实现 `python/pycute/layout.py`，它的构造说明了默认步长从哪里来：

```python
# 编者定位：repos/cutlass · 0b55a2f691d6 · python/pycute/layout.py:52-57
class Layout(LayoutBase):
  def __init__(self, _shape, _stride=None):
    self.shape  = _shape
    if _stride is None:
      self.stride = prefix_product(self.shape)
    else:
      self.stride = _stride
```

不给步长时按行优先的累积乘积生成，也就是最后一维连续。这段代码上方还有一句注释，说明这份 Python 实现刻意与 C++ 的 `Layout::operator(Coord const&)` 保持一致（`:77`），因此读它可以当作读 C++ 模板的入口。

映射的域与值域要分开计数。`size` 是逻辑元素的个数，`cosize` 是布局实际触及的偏移范围：

```python
# 编者定位：repos/cutlass · 0b55a2f691d6 · python/pycute/layout.py:99-104
  def size(self):
    return product(self.shape)

  # cosize(layout)   Size of the codomain
  def cosize(self):
    return self(self.size() - 1) + 1
```

`cosize` 取最后一个逻辑元素映射到的偏移再加一。两者相同时布局是紧的；`cosize` 大于 `size` 时布局在存储里留了空洞，申请空间的算法必须按较大的那个数来算。分块拍平、线程划分、共享内存摆放都会改变这两个量，这也是布局运算值得单独成体系的原因。

有了 (shape, stride) 这种表示，分块就能写成映射之间的运算。`composition(A, B)` 是把 A 的作用施加在 B 的取值上，实现里有一个必须满足的前提：

```python
# 编者定位：repos/cutlass · 0b55a2f691d6 · python/pycute/layout.py:205-214
  else:
    result_shape  = []
    result_stride = []
    rest_shape    = layoutB.shape
    rest_stride   = layoutB.stride
    flat_A = coalesce(layoutA)
    for (curr_shape, curr_stride) in zip(flatten(flat_A.shape)[:-1], flatten(flat_A.stride)[:-1]):
      assert curr_shape % rest_stride == 0 or rest_stride % curr_shape == 0
      new_shape = min(max(1, curr_shape // rest_stride), rest_shape)
```

循环第一句断言的是整除关系：参与复合的两维要么整除以对方，要么被对方整除。这条断言给出的是复合运算在该表示下成立的条件：步长与形状不能任意配对。`coalesce(layoutA)` 先做一步化简，把可以合并的相邻维合并掉，减少要检查的维数。

同文件里其余运算按同一思路展开：`complement`（`:232`）求出让组合覆盖连续区间所需的补布局，`logical_divide`（`:297`）与 `zipped_divide`（`:343`）把布局按分块切开并给出“块内”与“块间”两级坐标，`tiled_divide`（`:348`）保留分块结果的维结构，`slice_and_offset`（`:364`）取切片并回传偏移。写 GEMM 时用到的那种“按 tile 载入、按 tile 计算”的概念，在实现里就是这几个函数的组合。

一个具体例子能把 `size` 与 `cosize` 的差别算清楚。取布局 `(4,2):(2,1)`：逻辑坐标 `(i,j)` 映射到 `2i + j`，域大小是 8，最后一个元素 `(3,1)` 落在偏移 7，于是 `cosize` 也是 8，布局是紧的。换成 `(4,2):(2,4)`：映射为 `2i + 4j`，域大小仍是 8，`i` 取 0～3、`j` 取 0～1，8 个逻辑元素落在 6 个不同的偏移 `{0, 2, 4, 6, 8, 10}` 上，最大偏移 10，因此 `cosize` 等于 11。区间 `[0, 10]` 里有 5 个偏移没有任何元素占用，`cosize - size` 则是 3——两个数不相等，因为重复落点的元素把差别抵消了。按这套布局下标的存储确实占到第 10 号位置，于是共享内存里一个 tile 要占多少字节由 `cosize` 决定，而 `size` 只说明有多少个元素要算。
