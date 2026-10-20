## 降低与代码生成：查表分派与主机／设备分离 {#tvm-lowering}

张量层表示走向目标代码的过程分为两段。仓库架构文档把它画成一张流程图：先跑 TIR 管线把 `PrimFunc` 降低（展平缓冲、展开内建等），再用 `split_host_device_mods()` 把函数按所在设备分开，然后对主机与设备模块分别调用 `codegen_build()`，最后把设备模块 `import_module()` 回主机模块（`docs/arch/codegen.rst:39-68`）。整段过程由 `tirx.build()` 完成，而它本身由 `relax.build()` 调用——图级编译的主流程负责把两部分结果拼到一起。

按新的张量 IR 看，这一步的管线短得出奇：

```cpp
// 编者定位：repos/tvm · 2bb1a553be19 · src/tirx/transform/lower_tirx.cc:36-43
Pass LowerTIRx() {
  std::vector<tvm::transform::Pass> passes = {TilePrimitiveDispatch()};
  if (std::getenv("TVM_PRINT_AFTER_TIRX_DISPATCH_OPS")) {
    passes.push_back(tvm::transform::PrintIR());
  }
  passes.push_back(LowerTIRxCleanup());
  return tvm::transform::Sequential(passes, "tirx.LowerTIRx");
}
```

两件事：把 tile 原语调用分派成具体实现，然后清理。`TilePrimitiveDispatch` 的职责写在文件头注释里——通过已注册的分派器降低 `TilePrimitiveCall` 结点，同时解析作用域声明并给出启动参数（`src/tirx/transform/tile_primitive_dispatch.cc:20-23`）。把“块级搬运与计算”提到原语层再统一分派，意味着后端只需注册自己支持的实现；调度的重活在别处——同一目录下还有向量化、展开、线程轴重映射、存储重写等逐个 pass（`src/tirx/transform/`）。

最后一跳是一次名字查表：

```cpp
// 编者定位：repos/tvm · 2bb1a553be19 · src/target/codegen.cc:49-59
ffi::Module Build(IRModule mod, Target target) {
  if (transform::PassContext::Current()->GetConfig<bool>("tirx.disable_assert", false).value()) {
    mod = tirx::transform::SkipAssert()(mod);
  }

  // the build function.
  std::string build_f_name = "target.build." + target->kind->name;
  const auto bf = tvm::ffi::Function::GetGlobal(build_f_name);
  TVM_FFI_ICHECK(bf.has_value()) << build_f_name << " is not enabled";
  return (*bf)(mod, target).cast<ffi::Module>();
}
```

代码生成因此是一个注册式接口：每种目标把自己的模块构建函数注册到全局函数表里，名为 `target.build.<kind>`，入口按目标名查出对应实现；查不到时给出的信息是“该目标的构建函数未启用”，调用方由此知道问题在目标支持上，而不必在生成器内部找。入口顺带处理了一件事：配置 `tirx.disable_assert` 打开时先跑一遍 `SkipAssert()`，把断言从生成的代码里去掉。

TVM 对这条链的下界有明确取舍。架构文档写道，许多低层优化可以交给目标阶段已有的 LLVM、CUDA C 与其他目标编译器处理，因此寄存器分配一类工作留给下游编译器，TVM 只做下游不覆盖的优化（`docs/arch/index.rst:97-100`）。这句话解释了整章的分工：调度负责决定数据怎么移动、线程怎么映射，寄存器分配与指令选择交给成熟的编译器后端，两边交界处的产物就是上面那个 `ffi::Module`。
