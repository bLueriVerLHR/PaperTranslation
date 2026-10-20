### 第三部分 网络 {#interview-network}

网络部分按协议栈自下而上组织：先建立分层和地址的概念，再进入传输层的连接建立、可靠传输与拥塞控制，然后讨论 HTTP 与应用消息边界、身份与传输安全，最后用全链路串讲和线上排查把这些层次连起来。判断网络结论时，层次、连接状态和观测点分别说明；一次 `curl` 成功不能代替对端口和服务的判断。

{{include:network-layers.md}}

{{include:network-transport.md}}

{{include:network-lifecycle.md}}

{{include:network-http.md}}

{{include:network-security.md}}

{{include:network-diagnostics.md}}
