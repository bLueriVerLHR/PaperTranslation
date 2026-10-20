#### 对象模型：类、继承与多态 {#interview-cpp-object}

<article class="qa-item" id="qa-struct-class-access" data-level="basic" markdown="1">
<p class="qa-question">Q11 · struct 与 class 有什么区别？public、protected、private 怎样作用？</p>
<div class="qa-answer" markdown="1">

在 C++ 中，两者都可以有构造函数、成员函数、继承和虚函数，主要差别是默认访问权限和默认继承权限：struct 为 public，class 为 private。不是“struct 只能存数据，class 才能有行为”。public 提供公开接口，private 限制外部直接访问实现，protected 给派生实现有限的访问入口；友元还能获得被授予的访问权限。[200]

继承权限影响基类成员在派生接口中的可访问性及相应转换，不让派生类直接访问基类 private 成员。protected 也不是允许派生类通过任意基类对象操作其受保护状态。封装的价值是让所有修改经过维持不变量的入口，例如余额不能绕过检查随意赋值；访问控制是编译期语言规则，不是内存加密或对抗任意内存破坏的安全边界。

</div>
</article>

<article class="qa-item" id="qa-polymorphism-vtable" data-level="basic" markdown="1">
<p class="qa-question">Q12 · 封装、继承、多态怎样区分？虚函数表是每个对象一份吗？</p>
<div class="qa-answer" markdown="1">

封装把状态及其合法操作组织成接口；继承建立基类与派生类关系；多态允许同一接口对应不同实现。C++ 的静态多态可用模板、重载等组织，动态多态通常通过虚函数按对象动态类型选择最终覆盖函数。限定调用如 `p->Base::f()` 会抑制对应的虚分派。虚分派并不要求调用方使用 typeid 或运行时检查式 dynamic_cast，不能把虚函数机制与 RTTI 查询接口混为一谈。[51]

常见 ABI 在对象或基类子对象中保存 vptr，并让同一最派生类的对象共享相应表集合，不是每创建一个对象就复制整张表。以 Itanium C++ ABI 为例，分派入口可以是虚成员函数，也可以是先调整对象指针再转入该函数的入口；表中还可能有基类偏移和类型信息，表的地址点不必位于表开头。[199] 多继承、虚继承和构造阶段可能涉及多张表及其他元数据，语言不规定“一类一表、每个对象固定一个指针”。

空间成本要分开看共享表和每对象的指针、布局与对齐开销，不能套用固定的“每个对象增加四字节”或按基类数量直接乘四。虚调用可能需要间接寻址，也可能被去虚化；成本还与缓存、分支预测和可否内联相关，不能给出单继承必然等速或多继承必然更慢的通用结论。取得一个实现内部地址不等于获得可写权限；改写虚表不是标准 C++ 支持的扩展接口，是否能写、怎样分派及可能触发的保护均依赖实现，不能作为可移植的业务设计。

</div>
</article>

<article class="qa-item" id="qa-overload-override-final" data-level="basic" markdown="1">
<p class="qa-question">Q13 · 重载、重写、隐藏、override 和 final 有什么区别？</p>
<div class="qa-answer" markdown="1">

重载是在名字查找与重载决议中选择不同参数接口；重写是派生成员成为基类虚函数的覆盖实现；隐藏则是派生类的同名声明使基类名字不再按原方式可见，它不要求参数相同或基类函数是虚函数。需要继续暴露基类重载时，可以使用合适的 `using Base::f`。[51]

override 让编译器检查“这个成员确实重写了基类虚函数”，有助于发现 const、参数或引用限定不匹配。返回类型一般一致，满足规则的类指针或引用可以协变，不能概括成完全相同。final 可以禁止继续重写一个虚函数，也可以禁止继承一个类；设计不能继承的类时直接定义 `class C final {};`，比通过构造权限绕行更直接。私有虚函数也可被覆盖，访问控制不参与判断是否重写。[51,138]

</div>
</article>

<article class="qa-item" id="qa-object-slicing" data-level="principle" markdown="1">
<p class="qa-question">Q14 · 对象切片在什么时候发生？为什么基类值参数会丢掉派生部分？</p>
<div class="qa-answer" markdown="1">

按值复制多态对象时只会复制静态类型所对应的子对象：`void f(Base b)` 接收 `Derived` 实参、`Base b = derived;` 或把派生对象放进 `std::vector<Base>`，都只保留基类部分。复制构造与赋值按静态类型在编译期选择，不经过虚分派，因此派生类新增的成员被丢掉，容器里保存的基类对象调用虚函数也不会分派到派生实现。[288]

这不是未定义行为，而是静默的信息丢失：代码能编译、能运行，只是多态行为消失；如果基类析构函数非虚，再通过基类指针销毁该对象还会进入另一条未定义行为路径（见 [虚析构函数](#qa-virtual-destruction)）。

避免方式是多态对象用引用或指针语义：参数用 `const Base&`／`Base*`，容器保存指针、智能指针或 `std::reference_wrapper`。反向的做法是让类型本身不支持被切片：多态类的公开拷贝／移动应被抑制或改为受保护，接口文档明确“按值传递即失去派生部分”（Core Guidelines 的 C.67 规则正是这个意思）。判断标准很简单：打算依赖覆盖行为的类型不要按值复制，按值复制的类型不要指望派生行为。

</div>
</article>

<article class="qa-item" id="qa-pure-inline-static" data-level="principle" markdown="1">
<p class="qa-question">Q15 · 纯虚函数必须没有实现吗？构造、静态和 inline 函数能是虚函数吗？</p>
<div class="qa-answer" markdown="1">

纯虚函数用 `= 0` 表达抽象接口，但可以在类外提供定义。是否可实例化，要看类是否仍有最终覆盖函数为纯虚的成员；派生类可以继续保持抽象，不是每个派生类都必须立刻补全实现。纯虚析构函数仍需要定义，因为销毁派生对象会调用基类析构。[56]

构造函数不能声明为虚函数，静态成员函数也不能，因为虚调用需要对应对象。inline 与 virtual 则可以共存，是否展开是另一个优化问题。[51, 53]

构造或析构函数中可以调用非纯虚成员；对当前正在构造或销毁的对象进行虚调用时，选择正在执行构造或析构的那一层的最终覆盖函数，不分派到更深的派生层。例如 Base 构造期间不会调用 Derived 的覆盖函数，并非一概“调用父类版本”或“禁止调用虚函数”。[202] 对当前对象虚调用纯虚函数仍属于未定义行为，不能把“纯虚函数另有函数体”当成安全分派保证；显式限定调用和正常虚调用还要区分。[56]

</div>
</article>

<article class="qa-item" id="qa-construction-order" data-level="principle" markdown="1">
<p class="qa-question">Q16 · 默认、委托、拷贝和移动构造如何区分？构造析构顺序由谁决定？</p>
<div class="qa-answer" markdown="1">

默认构造函数的参数可以全有默认实参，也可以没有参数，所以 `C(int n = 0)` 也可以是默认构造函数。“默认构造”不等于“由编译器默认生成”：`C() = default` 是要求按语言规则默认定义，仍可能因成员或基类无法初始化而被定义为删除，不能据此保证对象一定能创建。[201]

参数化构造根据实参建立对象；拷贝构造从既有对象建立新对象，移动构造提供消耗相应源状态的接口；委托构造把同类初始化交给一个目标构造函数，目标完成后再执行委托者的函数体。移动是否真的便宜，仍由成员及实现决定。[13, 55]

非委托构造由最派生类按继承图深度优先、从左至右的顺序初始化虚基类，再按基类声明顺序初始化直接基类，然后按成员声明顺序初始化成员，最后执行函数体；不是按初始化列表的书写顺序。销毁对象先执行析构函数体，再逆序销毁成员和基类。[55,137] 因此成员 b 依赖 a 时，应让 a 在声明中先出现。构造抛异常会清理已完成的子对象，但不会调用尚未完成对象本身的析构；引用和 const 成员也不能靠函数体中的普通赋值代替必需初始化。[55]

</div>
</article>

<article class="qa-item" id="qa-virtual-inheritance" data-level="principle" markdown="1">
<p class="qa-question">Q17 · 菱形继承有什么问题？虚继承是不是单纯为了节省内存？</p>
<div class="qa-answer" markdown="1">

如果 B、C 都普通继承 A，D 再继承 B 和 C，D 中包含两个不同的 A 基类子对象，成员访问和向 A 的转换可能产生歧义。让相应路径虚继承 A，可以让最派生对象共享这一个虚基类子对象；核心是对象身份与接口语义，不只是减少几字节。[203]

虚基类由最派生类负责初始化，中间类的虚基类初始化在作为子对象构造时不会生效。[55] 共享 A 也不自动解决所有成员歧义：B 和 C 都覆盖同一个虚成员时，D 可能需要提供唯一最终覆盖函数，否则类定义不合法。[51] 实现可能增加偏移查找、布局和指针调整成本；组合关系足够表达设计时，并不需要为复用几段代码引入复杂继承。

</div>
</article>

<article class="qa-item" id="qa-this-storage-restriction" data-level="principle" markdown="1">
<p class="qa-question">Q18 · this 是什么？空指针能调用成员吗？怎样限制类的创建位置？</p>
<div class="qa-answer" markdown="1">

在普通非静态成员函数中，this 是指向当前对象的指针；静态成员函数没有 this。通过空指针调用需要对象的非静态成员，即使函数体看起来不使用字段，也不能当成合法接口。“public”只表示访问权限，不建立一个有效对象。静态成员则应通过类名调用，避免把它和对象调用混在一起。

禁止类内 `operator new` 可以限制常规类分配表达式，但不能严格保证“只在栈上”：静态对象、作为别的对象成员、显式全局分配或适当的定位构造，都需要分别分析。[136] 私有析构配合工厂和自定义删除器，可以限制外部创建自动对象并控制销毁；约束来自访问与所有权协议，不是编译器对所有存储区域的绝对分类。[137]

下面的原创 C++11 示例让普通调用方通过工厂获得 RAII 句柄，由嵌套删除器访问私有析构。它约束公开接口，而不是证明类内或友元永远无法构造其他存储期对象；未编译或运行此示例。

```cpp
#include <memory>

class ManagedObject final {
public:
    struct Dispose {
        void operator()(ManagedObject* object) const { delete object; }
    };
    using Handle = std::unique_ptr<ManagedObject, Dispose>;
    static Handle make() { return Handle(new ManagedObject); }
private:
    ManagedObject() = default;
    ~ManagedObject() = default;
    ManagedObject(const ManagedObject&) = delete;
    ManagedObject& operator=(const ManagedObject&) = delete;
};
```

将类内普通 `operator new(std::size_t)` 声明为 deleted 可以阻止相应的 `new T`，数组分配还要考虑 `operator new[]`，显式 `::new` 又会使用全局查找。[136] 因此公开设计宜表达禁止复制、受控创建或受控拥有等真正要求，而不把“堆／栈”口诀当成完整语言约束。

</div>
</article>

<article class="qa-item" id="qa-static-polymorphism" data-level="principle" markdown="1">
<p class="qa-question">Q19 · 编译期多态（模板、CRTP）与运行期多态各付什么代价？</p>
<div class="qa-answer" markdown="1">

运行期多态靠虚分派：调用点只知道基类接口，实际目标在运行期确定，常见实现是间接跳转，通常难以内联；[338] 换来的是统一接口、可按运行期条件选择实现、可把不同派生对象放进同一容器，以及在 ABI 兼容前提下的插件式替换。

编译期多态把选择移到编译期：模板与重载让调用点看到具体类型，实例化后的调用可以内联、没有间接跳转。[325] 常见惯用法是 CRTP——派生类把自己的类型作为模板实参传给基类，使基类能在没有虚函数的情况下复用实现并静态分派。代价是每个实参组合生成一份代码（二进制体积与指令缓存压力、编译时间增长）、无法在运行期按配置切换实现、错误信息随实例化层级变长，以及不同类型不能直接放进同一个容器。

判断依据是“替换发生在什么时候”：需要运行期可替换就用虚函数，需要零间接开销且类型编译期已知就用模板；类型擦除（`std::function`、`std::any`、自写虚接口）是折中——对外是统一的编译期接口，内部保留一次间接调用。模板实例化本身不保证更快：只有调用点可内联、且内联后的优化确有价值时才可能更快，反之虚调用在可预测的调用点上也不一定昂贵，因此要用测量而不是类型学下结论。

</div>
</article>

<article class="qa-item" id="qa-singleton-global" data-level="scenario" markdown="1">
<p class="qa-question">Q20 · 怎样写线程安全的单例？多个全局对象相互依赖时怎么办？</p>
<div class="qa-answer" markdown="1">

常见做法是用函数局部 static 保存实例，C++11 起相应动态初始化具有并发初始化保护；同时禁止不希望发生的复制和移动，才能维护实例约束。这个保护只覆盖初始化，不保护实例上的所有业务调用。递归地再次进入尚在初始化的局部 static 属于未定义行为；初始化抛异常后，下次进入会再次尝试。[135]

下面是原创 C++11 教学示例，不是题库原文或实测代码。私有构造和析构将创建与销毁接在类内访问点，删除复制接口也抑制相应隐式移动生成；可变业务状态仍需另外同步。

```cpp
class ServiceRegistry final {
public:
    static ServiceRegistry& instance() {
        static ServiceRegistry registry;
        return registry;
    }
private:
    ServiceRegistry() {}
    ~ServiceRegistry() = default;
    ServiceRegistry(const ServiceRegistry&) = delete;
    ServiceRegistry& operator=(const ServiceRegistry&) = delete;
};
```

裸指针懒初始化若没有同步，多个线程可以同时观察空值并创建对象，读写共享指针本身也可能数据竞争；它不是线程安全单例。按需初始化不消除退出时的使用者依赖。

跨翻译单元的全局动态初始化有复杂顺序规则，不能假设所有依赖对象都已完成。几十或几百个对象最好建立显式依赖关系和拥有者，让成员声明、构造及逆序销毁表达顺序；也可按需初始化局部对象。真正的循环依赖不能靠换成单例自动消失。生命周期还要覆盖后台线程：在全局资源开始析构前结束使用者，否则“初始化一次”并不能避免退出时访问失效对象。

</div>
</article>
