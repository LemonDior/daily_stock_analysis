# 数据库 Migration 说明

本文说明本项目当前的数据库演进方式。  
结论先说：现在按 Flyway 的思路处理数据库变更，**新增表、加字段、改索引，都要写显式 migration**，不再依赖启动时根据 ORM metadata 自动补库。

## 1. 当前机制

项目启动时会执行数据库 migration 检查，入口在：

- [src/storage.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/storage.py)
- [main.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/main.py)
- [api/app.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/api/app.py)

迁移框架代码在：

- [src/db_migrations/runner.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/runner.py)

迁移脚本目录在：

- [src/db_migrations/sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql)

迁移历史表：

- `schema_migrations`

启动时行为：

1. 确保 `schema_migrations` 表存在
2. 扫描 `src/db_migrations/sql/V*.sql`
3. 校验已执行 migration 的 checksum
4. 按版本顺序执行未执行 migration
5. 把执行结果写入 `schema_migrations`

## 2. migration 文件命名规则

文件名格式：

```text
V0001__baseline_schema.sql
V0002__add_portfolio_tags.sql
V0003__create_alert_rules_table.sql
V0003__create_alert_rules_table.mysql.sql
V0003__create_alert_rules_table.sqlite.sql
```

规则：

- 必须以 `V` 开头
- 后面是递增版本号，建议固定宽度，如 `0001`、`0002`
- 版本号后面必须跟 `__`
- 描述部分用下划线分隔

不要做的事：

- 不要复用旧版本号
- 不要修改已执行 migration 的文件内容
- 不要跳着写混乱版本号

## 3. migration 文件怎么写

每个 migration 文件是 SQL 文件，不是 Python 文件。

支持两种形式：

1. 通用 SQL：

```text
V0003__create_alert_rules_table.sql
```

2. 方言专用 SQL：

```text
V0003__create_alert_rules_table.mysql.sql
V0003__create_alert_rules_table.sqlite.sql
```

如果同一个版本同时存在通用和方言专用文件，runner 会优先使用当前数据库方言对应的 SQL 文件。

适合用方言专用脚本的场景：

- MySQL `COMMENT`
- SQLite 不支持的 DDL 能力
- 不同数据库的索引 / 约束语法差异

## 4. 新建表怎么做

标准流程：

1. 先在 [src/storage.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/storage.py) 里加 ORM 模型
2. 再新增一个 migration SQL 文件
3. 在 SQL 文件里显式建表
4. 补业务读写逻辑和测试

推荐写法：

```sql
CREATE TABLE example_table (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(64) NOT NULL
);

CREATE INDEX ix_example_table_name ON example_table (name);
```

说明：

- 不要指望“模型加了，启动就自动建表”
- 现在建表的正式入口是 migration，不是 metadata 自动同步

## 5. 新增字段怎么做

标准流程：

1. 先改 ORM 模型，加上新 `Column`
2. 再新增 migration SQL 文件
3. 在 SQL 文件里显式执行 `ALTER TABLE ... ADD COLUMN ...`
4. 如果需要，顺带做数据回填
5. 补测试

示例：

```sql
ALTER TABLE analysis_history ADD COLUMN extra_tag VARCHAR(32);
```

注意：

- migration 必须自己负责把库结构改到位
- 现在不会再自动为旧表补齐缺列

## 6. 推荐原则

以后做数据库变更，默认遵循下面这套规则：

1. 改 ORM 模型只是“声明目标结构”
2. 改数据库结构必须通过 migration 落地
3. MySQL 路径下，新表和新字段默认要补齐中文注释
4. 已执行 migration 文件只追加，不修改
5. 高风险变更必须拆阶段，不要一步到位

## 7. 哪些变更必须显式 migration

现在实际上是：

- 新建表：必须写 migration
- 新增字段：必须写 migration
- 新增索引：必须写 migration
- 新增表注释 / 字段注释：必须写 migration
- 改字段类型：必须写 migration
- 删除字段：必须写 migration
- 改字段名：必须写 migration
- 改唯一约束 / 主键 / 外键：必须写 migration
- 历史数据修复 / 回填：必须写 migration 或单独脚本

## 8. 推荐变更策略

### 场景 A：字段改名

推荐两阶段：

1. 新增新字段 + migration
2. 代码兼容读写新旧字段
3. 数据回填
4. 下一版再删旧字段

### 场景 B：字段改非空

推荐两阶段：

1. 先保持可空，migration 只加列
2. 回填历史数据
3. 下一版再收紧约束

### 场景 C：字段类型变化

推荐三阶段：

1. 新增新类型列
2. 回填旧数据
3. 切换代码读写
4. 最后清理旧列

## 9. baseline 是什么

当前仓库已经有：

- [V0001__baseline_schema.mysql.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0001__baseline_schema.mysql.sql)
- [V0001__baseline_schema.sqlite.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0001__baseline_schema.sqlite.sql)

这个 baseline migration 用于初始化当前全部 ORM 表结构。

它的职责是：

- 新库首次启动时，把现有业务表建出来
- 老库切入这套 migration 体系时，登记 baseline 版本

## 10. 如何新增一个 migration

以后你要加 migration，直接照这个模板：

```sql
ALTER TABLE your_table ADD COLUMN your_column VARCHAR(64);
```

如果是建表：

```sql
CREATE TABLE your_table (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(64) NOT NULL
);
```

本仓库现在有一个实际示例：

- 模型：[src/storage.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/storage.py) 中的 `MigrationDemoRecord`
- migration：
  - [V0002__create_migration_demo_records.mysql.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0002__create_migration_demo_records.mysql.sql)
  - [V0002__create_migration_demo_records.sqlite.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0002__create_migration_demo_records.sqlite.sql)

这个例子的作用只是演示“新增表”应该怎样走完整流程：

1. 先加 ORM 模型
2. 再加 `V0002` migration
3. 启动时由 runner 记录到 `schema_migrations`

另一个更贴近真实维护的例子：

- [V0003__add_chinese_table_comments.mysql.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0003__add_chinese_table_comments.mysql.sql)
- [V0003__add_chinese_table_comments.sqlite.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0003__add_chinese_table_comments.sqlite.sql)

这个例子演示了：

1. MySQL 通过 `ALTER TABLE ... COMMENT='中文说明'` 给现有表补注释
2. SQLite 因为不支持表注释，所以对应 migration 做 no-op

再往下一步的完整示例：

- [V0004__add_chinese_column_comments.mysql.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0004__add_chinese_column_comments.mysql.sql)
- [V0004__add_chinese_column_comments.sqlite.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0004__add_chinese_column_comments.sqlite.sql)

这个例子演示了：

1. 通过 migration 给现有字段补中文注释
2. 用 `information_schema.columns` 保留 MySQL 当前字段定义，避免为了加注释把类型和空值约束改坏
3. SQLite 路径继续保持 no-op

新增表示例：

- [V0005__create_cn_stock_master.mysql.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0005__create_cn_stock_master.mysql.sql)
- [V0005__create_cn_stock_master.sqlite.sql](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/db_migrations/sql/V0005__create_cn_stock_master.sqlite.sql)

这个例子演示了：

1. 新表在 MySQL 路径下同时补表注释和字段注释
2. SQLite 路径提供等价建表语句，保证本地测试和轻量运行可用
3. ORM 模型与 migration 一起落地，保证 `Base.metadata` 和真实数据库一致

## 11. 开发时怎么验证

最低建议：

1. 用空库启动一次，确认 migration 能跑完
2. 用已有库启动一次，确认 `schema_migrations` 版本记录正确
3. 跑对应存储层测试

当前参考测试：

- [tests/test_storage.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/tests/test_storage.py)

建议至少补这类测试：

- migration 历史记录是否写入
- baseline 是否创建全量表
- 新 migration 是否按版本执行
- 已执行 migration checksum 被改动时是否报错

## 12. 一句话总结

以后数据库变更不要再想“改模型自动补库”。  
正确流程是：

1. 改 [src/storage.py](/Users/lemon/workSpace/pythonWorkSpace/daily_stock_analysis/src/storage.py) 的 ORM 模型
2. 新增一个 `src/db_migrations/sql/Vxxxx__*.sql`
3. 在 SQL 文件里显式改库
4. 启动服务执行 migration
