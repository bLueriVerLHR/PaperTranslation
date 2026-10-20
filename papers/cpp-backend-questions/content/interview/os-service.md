#### 服务运行与隔离 {#interview-os-service}

<article class="qa-item" id="qa-daemon-service" data-level="scenario" markdown="1">
<p class="qa-question">Q115 · 守护进程为什么会双重 fork？现代服务仍应照搬这一流程吗？</p>
<div class="qa-answer" markdown="1">

传统守护化先 fork，使子进程能调用 setsid 建立新会话并脱离原控制终端，再次 fork 让最终进程不是会话首进程，避免按相应规则重新取得控制终端；还需处理目录、描述符和标准输入输出。后台运行与服务可管理是两回事，不是末尾加一个 & 就建立完整守护协议。

现代服务管理器常期望服务前台运行，由它管理启动、日志、资源和停止，自行双重 fork 反而可能破坏监督。umask 应按最小权限选择，不宜机械设 0；关闭描述符须保留约定的监听、日志或激活通道，不是无差别关闭所有句柄。可靠关闭还需停止准入、等待或取消任务并完成资源依赖清理；这些步骤属于服务协议，不能靠脱离终端自动获得。[66]

</div>
</article>

<article class="qa-item" id="qa-virtual-machine-container" data-level="scenario" markdown="1">
<p class="qa-question">Q116 · 虚拟机和容器隔离了什么？namespace 和 cgroup 有什么区别？</p>
<div class="qa-answer" markdown="1">

虚拟机通过相应 CPU、内存与 I/O 虚拟化提供来宾运行环境，来宾通常运行自己的内核；容器通常共享宿主内核，用 namespace 等隔离资源视图，用 cgroup 等限制和统计资源。namespace 改变“看到哪些进程、路径或网络对象”，cgroup 控制“可用多少 CPU、内存等”，不能交换两者职责。

隔离强度还受权限、设备、挂载、能力和内核接口影响，容器不是天然等于独立机器。CPU 虚拟化有执行及退出路径，内存虚拟化可能增加地址转换层，I/O 可以模拟、半虚拟化或直通，各自以兼容性、成本和安全边界换取不同效果。容器内的线程栈、地址空间和语言数据竞争仍按对应协议工作；内存限额、PID 限额或 CPU 节流也可能在宿主总体余量足够时触发，容量分析必须在正确资源范围内进行。

</div>
</article>

<article class="qa-item" id="qa-nginx-event-service" data-level="scenario" markdown="1">
<p class="qa-question">Q117 · NGINX 怎样以 worker 处理很多连接？配置 reload 是不是直接替换所有旧请求？</p>
<div class="qa-answer" markdown="1">

官方入门资料描述 master 负责读取配置、维护 worker，worker 实际处理请求，并采用事件模型及操作系统机制分配处理工作。[75] 一个 worker 可以在等待多个连接期间交错推进工作，但不意味着一个核心同时执行全部请求；CPU 计算、阻塞模块和输出背压仍影响响应。静态服务、反向代理和负载均衡分别涉及文件、上游及选择策略。

成功 reload 会启动新 worker 并让旧 worker 停止接收新连接、继续完成在途请求，不是把全部旧连接瞬间变成新配置；配置验证或应用失败时保留旧配置。[75] 已建立连接、worker 退出时间及上游副作用仍有边界，不能据此推出任意模块或程序状态都可无损热更新。此处依据官方行为说明建立概念，不宣称已编译、部署或逐行审读 NGINX 实现。

</div>
</article>
