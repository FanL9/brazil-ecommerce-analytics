# 本地 SQLite 数据库

GitHub 不保存生成后的数据库文件。数据库可以由仓库中的 9 个原始 CSV、`schema.sql` 和统一构建脚本完整重建。原始 CSV 不会被脚本修改。

## 文件位置

- 原始数据：`data/raw/`
- 建表及索引定义：`database/schema.sql`
- 构建脚本：`src/data_processing/build_sqlite_database.py`
- 构建结果：`database/brazil_ecommerce.db`

`.gitignore` 会忽略生成的 `.db` 以及 SQLite 的 `-journal`、`-wal` 和 `-shm` 临时文件；`schema.sql`、构建脚本、文档和项目现有的原始 CSV 仍由 Git 正常管理。

## 构建步骤

先在终端中进入项目根目录，再安装依赖并运行脚本：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\data_processing\build_sqlite_database.py
```

也可以从其他工作目录使用脚本的绝对路径运行；数据、schema 和输出路径都根据脚本所在的项目目录解析，不依赖当前工作目录。

脚本会严格检查 9 个 CSV 的文件名、UTF-8 编码、列名、列顺序和预期行数，并按外键依赖顺序导入。每次运行先构建 `database/brazil_ecommerce.tmp.db`，只有在行数、主键、外键、表、索引、`integrity_check` 和 JOIN 冒烟查询全部通过后，才会原子替换正式数据库。构建失败时，已有的正式数据库不会被删除或替换。

## 表关系与键

- `customers(customer_id)` → `orders(customer_id)`
- `orders(order_id)` → `order_items(order_id)`
- `orders(order_id)` → `order_payments(order_id)`
- `orders(order_id)` → `order_reviews(order_id)`
- `products(product_id)` → `order_items(product_id)`
- `sellers(seller_id)` → `order_items(seller_id)`

上述 6 个关系在当前原始 CSV 中没有孤立记录，因此由 SQLite 外键强制执行。连接建立后脚本会启用并检查 `PRAGMA foreign_keys = ON`。

各表主键如下：

- 单列自然主键：`customers(customer_id)`、`orders(order_id)`、`products(product_id)`、`sellers(seller_id)`、`product_category_name_translation(product_category_name)`
- 联合主键：`order_items(order_id, order_item_id)`、`order_payments(order_id, payment_sequential)`、`order_reviews(review_id, order_id)`
- 内部主键：`geolocation(geolocation_id)`；CSV 的 5 个原始字段通过列名显式导入，ID 由 SQLite 自动生成

当前 CSV 中 `review_id` 和 `order_id` 单独都不是唯一值，但 `(review_id, order_id)` 唯一，因此评论表使用联合主键。`geolocation_zip_code_prefix` 对应多行，不能设为主键或唯一键。

商品数据有 13 行、2 个非空品类值在翻译表中没有匹配项，所以 `products.product_category_name` 与翻译表之间保留可选 JOIN，不建立会拒绝原始数据的外键。地理表也不能作为客户和卖家邮编的外键目标：邮编不唯一，而且分别有 278 个客户记录和 7 个卖家记录的邮编未被地理表覆盖。所有邮编字段均以 `TEXT` 存储并建立适量索引。

订单的审批/配送时间、评论标题/正文和部分商品属性在原始数据中允许缺失。构建器会把 pandas 的缺失值写成 SQL `NULL`，不会写成字符串 `"nan"` 或 `"NaT"`。

## 在 DBeaver 中打开

1. 完成上述构建并确认终端显示验证成功。
2. 在 DBeaver 中选择 **新建数据库连接**，搜索并选择 **SQLite**。
3. 在数据库文件位置选择项目内的 `database/brazil_ecommerce.db`。
4. 测试并完成连接，然后刷新 **Tables**，应看到 9 张业务表。
5. 若要重新运行构建脚本，请先断开 DBeaver 对该文件的连接，避免 Windows 文件锁阻止原子替换。
