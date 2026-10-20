#### 身份、TLS 与 HTTPS {#interview-network-security}

<article class="qa-item" id="qa-https" data-level="basic" markdown="1">
<p class="qa-question">Q149 · HTTPS 建立连接时，DNS、TCP 与 TLS 分别承担什么职责？</p>
<div class="qa-answer" markdown="1">

DNS 将服务名称关联到地址等信息；在常见 HTTP/1.1 或 HTTP/2 的 HTTPS 路径中，TCP 建立有序字节流，TLS 协商加密参数并认证相应对端，随后 HTTP 在保护的通道内组织请求和响应。缓存、连接复用、代理和不同协议版本会改变实际步骤，不必每次请求都重新执行完整过程。[25–27]

TLS 1.3 的目标包括认证、机密性与完整性，握手建立密钥材料，记录层保护后续流量。常见证书握手需要检查信任链、有效性与目标名称等匹配；“有证书”或“报文加密”单独都不能证明连接到了预期服务。TLS 1.3 不能照搬旧版静态 RSA 密钥交换流程。[27]（§1、§1.2）

HTTPS 不保证应用返回的内容真实，也不隐藏全部通信长度和端点信息。TLS 终止在网关时，网关到后端是另一段信任与传输边界；用户身份、访问权限和业务幂等仍由上层协议处理。

</div>
</article>

<article class="qa-item" id="qa-tls-cryptography" data-level="principle" markdown="1">
<p class="qa-question">Q150 · 加密、摘要、数字签名和证书各承担什么？TLS 1.3 怎样建立可信的会话密钥？</p>
<div class="qa-answer" markdown="1">

加密保护明文不被无授权者读出，摘要将内容映射到固定长度值，但单独摘要不证明发送者身份；MAC 使用共享秘密保护完整性与来源，数字签名由私钥生成、以相应公钥验证。证书把公钥与某种身份声明关联，并由签发者签名；信任仍依赖证书链、名称、有效性及验证策略。

常见 TLS 1.3 证书握手中，双方交换临时密钥协商材料，派生会话密钥；服务端通过证书及 CertificateVerify 等证明相应身份，Finished 认证握手上下文，随后记录层用派生的对称密钥保护数据。PSK、恢复会话和客户端认证存在不同路径，不能把每条连接都画成同一证书交换流程。[27]

“服务端用私钥加密，客户端用公钥解密全部响应”不是现代 TLS 的工作方式，也混淆签名和加密。临时密钥交换有助于前向保密，但恢复和 0-RTT 等模式有自己的边界；TLS 1.3 的早期数据存在重放风险，不能直接承载没有额外防护的非幂等业务操作。通道认证也不等于登录用户已获得全部业务权限。[27]

</div>
</article>

<article class="qa-item" id="qa-cookie-session-token" data-level="principle" markdown="1">
<p class="qa-question">Q151 · Cookie、Session 和 JWT 有什么区别？浏览器关闭或令牌签名是否足以保证登录安全？</p>
<div class="qa-answer" markdown="1">

Cookie 是浏览器保存并按范围附带的 HTTP 状态数据；Session 是应用维护的会话状态，常通过 Cookie 中的随机会话标识关联；JWT 是表达声明的一种令牌格式，可以放在 Cookie 或其他传输位置。三者不是相互排斥的登录方案。[86–87]

Cookie 的 Domain、Path 和有效期控制发送范围与保存行为；Secure 限制安全通道发送，HttpOnly 限制相应脚本 API 读取。它们不让被窃取的会话标识自动失效，也不替代请求权限验证。未指定持久期的 Cookie 依赖浏览器对“会话结束”的定义，浏览器恢复功能等使“关闭窗口必然退出登录”不成立；服务端 Session 的有效期又是另一套规则。[86]

签名或 MAC 保护的 JWT 可以被读取，除非另行加密；Base64URL 编码不是秘密保护。验证除了签名，还要按应用策略约束算法、密钥、发行者、受众和过期等声明。JWT 中的 `exp` 若存在，规定其可接受时间上限；格式并不强制每个应用自动设置或正确验证所有安全条件。[87] 自包含令牌减少逐请求读取会话状态的需要，却增加撤销、权限变更和密钥轮换的协调成本。注销、刷新与被盗后的控制必须形成完整协议，不能只说“无状态所以更安全”。

</div>
</article>
