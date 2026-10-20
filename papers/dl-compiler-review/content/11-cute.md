# CuTe：布局代数与模板实例化 {#cute}

CuTe 走的是另一条路。它没有独立的编译器进程，也没有 pass 管线：布局被表示成可以做代数运算的类型，分块、线程映射与指令选择都在模板实例化与 MLIR 降低这两处完成。正确性靠编译期断言约束，代价压在编译期。本章先讲这套代数在算什么，再讲指令知识如何按架构组织，最后看它把哪些责任交回给写代码的人。

{{include:cute/layout-algebra.md}}

{{include:cute/atoms.md}}

{{include:cute/static-knowledge.md}}

{{include:cute/dsl.md}}
