# 本地 SQLite 数据库

GitHub 不保存生成后的数据库文件。数据库体积较大，而且可以通过仓库中的原始 CSV、建表定义和统一脚本完整重建。

## 文件位置

- 原始数据：`data/raw/`
- 建表定义：`database/schema.sql`
- 构建脚本：`src/data_processing/build_sqlite_database.py`
- 构建结果：`database/brazil_ecommerce.db`

## Windows 构建步骤

先在终端中进入项目根目录，再执行：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\data_processing\build_sqlite_database.py
```

脚本会读取 `data/raw/` 中的 9 个 CSV，校验各表行数，并在全部导入成功后生成 `database/brazil_ecommerce.db`。每次重新运行都会重建数据库，因此不要直接在原始表中手工修改需要长期保留的数据。

## 在 DBeaver 中打开

1. 新建 SQLite 连接。
2. 选择 `database/brazil_ecommerce.db`。
3. 连接后刷新 **Tables**。
4. 确认可以看到 9 张表。
