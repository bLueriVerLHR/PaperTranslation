### 第四部分 数据库 {#interview-database}

数据库部分以 MySQL 为主线：先讲 SQL 与数据建模，再进入存储引擎、索引与访问路径，随后是事务、隔离级别与锁，以及日志、复制与恢复，然后讨论执行计划、容量设计和并发写入。PostgreSQL 与 SQLite 作为对照放在后面，用来说明版本管理方式与并发边界的差异。Redis 与缓存作为辅助部分放在最后，先讲数据模型和底层编码，再讲持久化、复制与集群，最后回到缓存失效、一致性和分布式锁这类业务问题。

{{include:database-sql.md}}

{{include:database-index.md}}

{{include:database-transactions.md}}

{{include:database-logs.md}}

{{include:database-tuning.md}}

{{include:database-others.md}}

{{include:database-cache.md}}

{{include:redis-model.md}}

{{include:redis-internals.md}}

{{include:redis-cluster.md}}
