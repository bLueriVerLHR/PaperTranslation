## 16. DCQCN：反馈、减速与恢复 {#dcqcn-mechanism}

DCQCN（Datacenter QCN）针对 2015 年论文中的三个实际约束：在三层可路由 RoCEv2 网络工作、以 NIC 实现保持低 CPU 开销，以及无拥塞时让短传输快速启动。QCN 的二层反馈不能直接跨 IP 路由，DCTCP 的逐 ACK 反馈又不等于 RoCE 的 CNP 机制。因此 DCQCN 组合了交换机 ECN、接收端反馈压缩与发送端速率控制，而不是把两套算法的参数照搬相加。[3]（§§2–3）

{{include:dcqcn/control.md}}

{{include:dcqcn/model-evidence.md}}
