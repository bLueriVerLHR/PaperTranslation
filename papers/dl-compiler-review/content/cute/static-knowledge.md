## 静态知识与被放弃的检查 {#cute-static-knowledge}

上一节的整除条件是这套代数成立的前提，而它在实现里被有选择地执行。`include/cute/int_tuple.hpp` 的除法函数把两种强度的检查并列写在一起，两种都没有生效或只在特定条件下生效：

```cpp
// 编者定位：repos/cutlass · 0b55a2f691d6 · include/cute/int_tuple.hpp:403-412
    // Strong divisibility condition
    //static_assert((IntTupleA::value % IntTupleB::value == 0) or (IntTupleB::value % IntTupleA::value == 0), "Divisibility Condition");

    // Weak divisibility condition
    if constexpr (is_static<IntTupleA>::value and is_static<IntTupleB>::value) {
      static_assert(((IntTupleA::value % IntTupleB::value) == 0) or ((IntTupleB::value % IntTupleA::value) == 0), "Divisibility Condition");
    } else {
      // DEBUG assert can cause extra registers and inappropriate compile-time/run-time failure
      //assert((((a % b) == 0) or ((a % b) == 0)) && "Divisibility Condition");
    }

    return (a + b - Int<1>{}) / b;
```

三段按条件生效：被注释掉的第一行是强条件，对任何输入都成立；接下来的静态断言只在两个操作数都是编译期常量时检查；其余情况落到 `else`，里面的运行时断言同样被注释掉，原因写在旁边——调试断言会增加寄存器用量，并可能造成不恰当的编译期或运行时失败。最后一行照常做向上取整除法。被注释的运行时断言里两个比较式写成了同一个表达式，这也说明这行文本没有被编译过。

结果是一条清楚的分界：**形状在编译期已知时，条件由编译器强制；形状未知时，条件由使用者自己保证**。违反前提不会在这里被拦下，而会在后续某处表现为偏移算错或实例化失败。这类取舍在布局库里是结构性的，因为检查本身要占用寄存器与编译时间，而布局库的调用场景对此很敏感。

同一目录的 `config.hpp:155-156` 给出了这对断言的惯用写法：`CUTE_STATIC_ASSERT` 与 `CUTE_STATIC_ASSERT_V`，后者要求参数本身带 `value` 成员，因此只能接受编译期常量。库内其他检查都用这套宏表达，例如张量切片时的维数一致性检查（`int_tuple.hpp:309`、`:330`、`:390` 等处的 `"Mismatched ranks"`）。

对使用者来说，这条分界决定了调试方式：把形状、步长、分块尺寸写成常量，错误会停在编译期并把条件说清楚；把它们留成运行期变量，同样的错误会推迟到结果里。`python/pycute/layout.py` 的存在也服务于这件事——它把代数以可读形式重写一遍，可以在不触发模板展开的情况下验证一条恒等式是否成立。
