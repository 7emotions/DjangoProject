**项目名称**
- **OCR 服务工具（DjangoPaddleOCR）**: 基于 Django 的图片上传与布局解析小服务，上传图片后调用布局解析接口并保存解析结果与生成的 Markdown 文档。

**项目概述**
- **说明**: 该项目提供前端上传界面与后台记录管理，处理上传图片并调用布局解析 API（可替换为本地/远程解析服务），把解析结果以 Markdown 与图片形式保存到 `media/` 目录，并将记录持久化到数据库。

**快速开始**
- **前提**: 已安装 Python（建议 3.8+）与 `pip`。
- **安装依赖**:

```powershell
pip install -r requirements.txt
```

- **数据库迁移**:

```powershell
python manage.py migrate
```

- **运行开发服务器**:

```powershell
python manage.py runserver
```

访问 `http://127.0.0.1:8000/` 进行图片上传与解析测试；管理后台在 `http://127.0.0.1:8000/admin/`。

**主要文件与位置**
- **入口与配置**: `manage.py`, `DjangoPaddleOCR/settings.py`, `DjangoPaddleOCR/urls.py`。
- **应用代码**: `parser_app/` — 包含视图 `parser_app/views.py`、模型 `parser_app/models.py`、路由 `parser_app/urls.py`、管理后台 `parser_app/admin.py`、模板过滤器 `parser_app/templatetags/custom_filters.py`。
- **模板**: `templates/` 下的 `index.html`, `result.html`, `detail.html`, `conversion_history.html`, `record_detail.html`。
- **媒体文件**: `media/` （上传的图片、生成的 Markdown 与导出文件）。
- **依赖**: `requirements.txt`。

**路由与关键端点概览**
- **GET /**: 上传首页（由 `parser_app.views.index` 提供）。
- **POST /upload/**: 上传并触发解析（`parser_app.views.upload_image`）。
- **GET /history/**: 转换记录列表（`parser_app.views.conversion_history`）。
- **GET /history/<id>/**: 单条记录详情（`parser_app.views.record_detail`）。
- **POST /history/<id>/delete/**: 删除记录（`parser_app.views.delete_record`）。
- **POST /history/bulk-delete/**: 批量删除（`parser_app.views.bulk_delete_records`）。
- **GET /history/export/**: 导出 CSV（`parser_app.views.export_records`）。
- **GET /history/statistics/**: 统计数据接口（`parser_app.views.statistics_data`）。
- **GET /result/<image_id>/<result_index>/**: 结果详情（`parser_app.views.result_detail`）。
- **POST /api/parse/**: AJAX/API 解析接口（`parser_app.views.api_parse`）。

**媒体与静态文件**
- **配置**: `MEDIA_ROOT` 与 `MEDIA_URL` 在 `DjangoPaddleOCR/settings.py` 中配置为 `media/` 与 `/media/`（请确认）。
- **保存位置**: 生成的 Markdown 与关联图片通常在 `media/markdown_<image_id>_<result_index>/` 目录下。

**开发与调试提示**
- **更换解析 API**: 修改 `parser_app.views` 内的 API地址或逻辑以对接本地/远程解析服务。
- **文件大小限制**: 项目默认对上传大小有校验（参见 `parser_app.views.upload_image`），必要时在 `settings.py` 调整。
- **日志**: 使用项目内的 `logging` 进行调试与排错。

**常用命令**

```powershell
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 创建超级用户（用于访问 admin）
python manage.py createsuperuser

# 运行开发服务器
python manage.py runserver
```

**Docker 部署**

项目提供了完整的 Docker 部署配置，包含 Gunicorn + Nginx。

**前提**: 已安装 [Docker](https://www.docker.com/) 与 [Docker Compose](https://docs.docker.com/compose/)。

**快速启动**:

```bash
docker-compose up -d
```

访问 `http://localhost` 即可。

**关键文件说明**:
- `Dockerfile`: 构建 Django 应用镜像（Python 3.9 + Gunicorn + 依赖）。
- `docker-compose.yml`: 定义两个服务：
  - `web`: Django 应用容器，暴露 8000 端口。
  - `nginx`: Nginx 反向代理容器，暴露 80 端口，负责静态文件、媒体文件与请求转发。
- `nginx.conf`: Nginx 配置文件，配置代理规则与缓存策略。
- `.dockerignore`: Docker 构建时忽略的文件列表。

**常见操作**:

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f web

# 停止服务
docker-compose down

# 重建镜像
docker-compose build --no-cache

# 进入 web 容器
docker exec -it django_paddle_ocr bash

# 在容器内创建超级用户
docker exec -it django_paddle_ocr python manage.py createsuperuser
```

**生产部署建议**:
1. 修改 `DjangoPaddleOCR/settings.py` 中的 `DEBUG=False`、`ALLOWED_HOSTS` 与 `SECRET_KEY`。
2. 使用环境变量管理敏感信息（可参考 `docker-compose.yml` 中的 `environment` 部分）。
3. 数据库推荐替换为 PostgreSQL（修改 `docker-compose.yml` 添加 PostgreSQL 服务）。
4. 配置 HTTPS（通过 Nginx 与 Let's Encrypt 证书）。
5. 使用卷持久化数据库与媒体文件。

**贡献与注意事项**
- **贡献流程**: 提交 PR 或 issue 前请本地验证上传、解析、记录查看、删除与导出功能。
- **媒体目录**: `media/` 一般应被忽略（位于 `.gitignore`），避免将用户上传内容提交到仓库。

**许可证**
- 若仓库内有 `LICENSE` 文件，请参照该文件。否则请在添加开源许可证前与项目所有者确认授权策略。

**下一步建议**
- **可选项**: 添加 `Dockerfile` 与 `docker-compose.yml` 以便更方便部署（可将 Gunicorn + Nginx 与 SQLite/其他数据库结合）。
- **文档**: 为 API（`/api/parse/` 等）添加更详尽的示例请求/响应文档。

---

文件位置: `README.md`（项目根）

如需我可以：添加 Docker 示例、将 README 翻译为英文或扩展为更详细的部署指南。
