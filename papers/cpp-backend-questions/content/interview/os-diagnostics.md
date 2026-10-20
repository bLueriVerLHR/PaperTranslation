#### 系统观测与容量 {#interview-linux-service}

<article class="qa-item" id="qa-linux-load-diagnosis" data-level="scenario" markdown="1">
<p class="qa-question">Q118 · Linux 负载高应该怎样定位？load average 等于 CPU 使用率吗？</p>
<div class="qa-answer" markdown="1">

不等于。Linux load average 综合可运行任务和相应不可中断等待任务的数量，展示不同时间窗口的平均；CPU 百分比则描述采样期间处理器时间去向。[70] 因此高负载但 CPU 不忙可能与等待有关，高 CPU 也要区分用户计算、内核工作、虚拟化偷取时间及可用核心预算。

可以先用 uptime、top／ps 对齐时间、进程和线程，再用 vmstat、pidstat、iostat、ss 等把假设分到运行队列、内存回收、存储等待及连接状态。例如高运行队列且用户态 CPU 饱和，才进一步查热点栈和计算路径；大量 D 状态则需检查具体等待对象，不能自动认定磁盘坏了。容器 CPU 限额也会使“宿主机空闲”与“进程被限速”同时成立。单次截屏是线索，采样窗口、基线和请求时延关联才支持更强判断；这里介绍诊断路径，不对任何实际服务器宣布根因。

</div>
</article>

<article class="qa-item" id="qa-memory-metrics" data-level="scenario" markdown="1">
<p class="qa-question">Q119 · VIRT、RSS、PSS、free、available 和 swap 应怎样理解？</p>
<div class="qa-answer" markdown="1">

VIRT 描述虚拟地址范围等统计，不等于实际 RAM 占用；RSS 统计驻留页面，共享页可能在多个进程各自出现；PSS 按共享关系分摊相应页面，适合解释共享映射的归属，但也不是应用活对象大小。[71] free 的 free 是未用内存，available 则估计不新增交换即可提供给新应用的内存，包含部分可回收缓存，具体列的计算还要看工具版本。[72]

因此 buff/cache 大不必然是泄漏，swap 已有占用也不证明此刻正在频繁交换，要观察换入换出速率和压力。对象已释放但分配器保留存储时，RSS 可能不降；RDB 等写时复制场景还会使共享页逐渐转为私有。定位增长可以对齐 smaps、分配统计、对象生命周期和时间序列，不能把 RSS、PSS、系统 used 直接相加成精确的业务容量。[34, 71–72]

</div>
</article>

<article class="qa-item" id="qa-disk-df-du" data-level="scenario" markdown="1">
<p class="qa-question">Q120 · df 和 du 为什么可能对不上？SSD 一定更耐用、写入一定更快吗？</p>
<div class="qa-answer" markdown="1">

df 查看文件系统层的容量与可用量，du 沿目录统计相应文件占用，两者范围和口径不同。已解除路径链接但仍被进程打开的文件可能继续占空间，du 沿原目录找不到它；稀疏文件、硬链接、快照、保留块及挂载边界也会影响解释。[73–74] 删除日志名字不自动让写入者关闭原描述符，可靠轮转要有重新打开协议。

机械盘有寻道和旋转成本，闪存 SSD 没有相同机械运动，随机访问常受益；SSD 又有擦写、垃圾回收、磨损与写放大，不能笼统说支持无限更多次写入。容量、设备队列、请求尺寸、缓存及持久化要求共同决定表现。iostat 中较高利用率是观测指标，不保证能据一个百分比推算现代多队列设备已达到绝对吞吐上限；故障和数据安全还需备份及恢复设计。

</div>
</article>

<article class="qa-item" id="qa-shell-text-files" data-level="scenario" markdown="1">
<p class="qa-question">Q121 · 文件查看、搜索、归档与 Shell 管道怎样组合？为什么文件名边界重要？</p>
<div class="qa-answer" markdown="1">

pwd、ls、stat 用于定位与属性，head、tail、less 用于查看文本，grep 按内容条件筛选，find 按路径和属性找对象，sort、uniq、wc、awk 等组织文本；tar 与 gzip 负责归档和压缩，不自动证明备份可恢复。/etc 常存配置，/var 常存可变状态，/proc 和/sys 是内核接口，/tmp 是临时空间，部署仍要按具体发行版和挂载约定理解。

管道连接标准输出与下一程序的标准输入，标准错误、返回码和重定向另有规则，不能仅因最后一段成功就认定全部成功。带空格、换行或前导短横线的文件名会破坏按空格拆分的简单脚本；相应场景可用正确引用、`--`、NUL 分隔的 find／xargs 协议。读取还要区分文本与二进制，编码错误不应靠静默替换掩盖。rm、覆盖重定向和解包路径会修改数据，操作例子的语义不能代替对真实目标的授权与校验。

</div>
</article>

<article class="qa-item" id="qa-fd-core-capacity" data-level="scenario" markdown="1">
<p class="qa-question">Q122 · /proc 文件描述符、ulimit 与系统上限怎样影响服务？一个数字就是连接容量吗？</p>
<div class="qa-answer" markdown="1">

文件描述符是进程中的句柄索引，不只代表普通磁盘文件，也可指 socket、管道及其他内核对象。Linux 的 `/proc/<pid>/fd` 有助于查看现有打开引用，信息仍受进程寿命、权限和命名空间影响；诊断过程自己打开目录也会影响瞬时观察。

进程资源限制分软硬上限，继承关系与服务管理配置决定实际值；系统文件句柄预算又是另一层限制。端口、内存、监听队列、业务连接池和处理能力同时构成容量条件，不能把描述符上限或某个 `/proc` 数值直接换算成可稳定服务的连接数。[88–89]

Core 的资源限制只控制相应转储的一部分行为，不证明已有完整文件，也不保证磁盘预算、安全策略和收集配置允许转储。描述符泄漏需要联系打开、转移和关闭的拥有关系；盲目增大上限可能延后暴露问题而增加资源压力。

</div>
</article>
