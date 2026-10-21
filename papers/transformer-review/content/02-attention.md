## 2. 注意力机制：共享、压缩、递推与选择

第 1 章把注意力写成一次打分、一次按行归一化和一次加权汇聚，那是标准多头注意力（Multi-head Attention，MHA）的形式。把它按自回归解码的方式用起来，代价集中在两处：每个历史位置要为每一层留下键与值，位置个数随上下文线性增长；每生成一个 token，又要按层把这些键值整体读回来。后续工作绕不开这两处代价，改动分别落在三条轴上：每个历史位置存什么，键值在多少个头之间共享、每个位置留多宽都属于这一条；历史怎样被压进一个可递推的状态；当前查询允许读到哪些位置。

这三种改动各有自己的公式、状态口径和失效条件，混在别处只能讲成一句“更省缓存”。本章按引用与改进关系把它们排开，每项机制都要说清继承自谁、改了哪一步，收益与代价也落在同一组单位上。来源以最初定义该机制的那篇论文为准，后续论文转述时的措辞差异不作为定义。

数字的读法需要事先统一。序列长度记为 N，查询头数 Hq，键值头数 Hkv，每头键维 d_k、值维 d_v，每层每个 token 的缓存元素数记为 E。容量由 E 决定，解码带宽由每步实际读取的元素数决定，算力由每 token 的乘加决定，递推类机制另有状态矩阵的大小决定它能存多少条互不干扰的关联。四项不能互相替代，参数量也不在其中。不同论文的硬件、批量、训练数据和评测协议各不相同，报告值只在口径相同的地方并列，不拼成一张排名。

{{include:attention/overview.md}}

{{include:attention/head-sharing.md}}

{{include:attention/mla.md}}

{{include:attention/linear-attention.md}}

{{include:attention/retention.md}}

{{include:attention/delta-rule.md}}

{{include:attention/gdn.md}}

{{include:attention/kda.md}}

{{include:attention/ssm-rwkv.md}}

{{include:attention/sliding-window.md}}

{{include:attention/nsa.md}}

{{include:attention/dsa.md}}

{{include:attention/msa.md}}

{{include:attention/ledger.md}}
