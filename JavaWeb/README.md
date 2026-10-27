# 期末：网络新闻热度预测 Web

## 运行

依赖 JDK 21、Maven、Docker 和 Conda 环境 `news_popularity`。IDEA 直接打开 `pom.xml`；代码只有启动类、控制器和 MyBatis Mapper，前端为一个 HTML 文件。

1. Docker 中启动已有 MySQL 8 实例，映射 `127.0.0.1:3306`。用 Navicat 连接后执行 `init.sql`，只创建本项目的 `news_popularity` 数据库。
2. 在本文件夹新建 `local.ps1`，设置本地参数。它已被 Git 忽略，不上传账号密码：

```powershell
$env:DB_USER='root'
$env:DB_PASSWORD=Read-Host '请输入本地 MySQL 密码'
$env:NEWS_PYTHON='D:\ProgramData\conda\envs\news_popularity\python.exe'
```

3. 新电脑先在附带的 `python` 文件夹执行 `conda env create -f environment.yml`。交付包已附模型和数据，公开仓库缺少模型时运行 `python train.py` 生成。
4. 在本文件夹执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`。脚本启动项目 Redis，必要时构建 JAR，再运行 Java。
5. 浏览器访问 http://127.0.0.1:8088 。选择模型，填写特征或填入数据集示例，执行预测并查询记录。

启动脚本保存为 UTF-8 编码标记格式，以兼容 Windows PowerShell 中文路径。手工启动时也可设置 `NEWS_ANALYSIS` 为包含 `predict.py`、`models`、`results` 的目录，执行 `mvn package -DskipTests` 和 `java -jar target/news-popularity-1.0.0.jar`。

停止 Java：启动窗口按 Ctrl+C。停止项目 Redis：`docker compose stop` 或执行 `stop.ps1`，保留数据卷。MySQL 为现有共用服务，不由本项目停止或重建。需要重新拉取 Redis 时执行 `docker compose pull`。

## 数据与功能

- Spring Boot 3.5.6、Spring MVC、MyBatis Starter 3.0.4；内嵌 Tomcat，无需另外部署。
- 左侧导航进入新闻预测、数据分析和预测记录。分析页通过图表标签切换，避免将所有图表纵向堆叠。
- MySQL 连接会话使用东八区，记录时间按北京时间展示；不修改共用 MySQL 的全局时区。
- Python 文件及模型与期中一致，保留相同十项输入和分类阈值；Java 经标准输入 JSON 调用 Python，不拼接命令。
- MySQL 表 `prediction_record` 保存模型、输入、类别、概率和时间；页面显示最近 100 条，可查看输入和删除。
- Redis 使用 `news:metrics:v1` 键缓存两模型指标，有效期 600 秒；页面提示是否命中。
- `GET /api/schema`、`/api/sample`、`/api/quality`、`/api/metrics`、`/api/figure/{name}` 提供字段、示例、数据与图表。
- `POST /api/predict` 接受 `{"model":"random_forest","features":{...}}`；返回保存记录及编号。
- `GET /api/records` 查询，`DELETE /api/records/{id}` 删除；无效参数返回 400，依赖不可用返回 503。

默认只绑定本机地址，用于本地课程演示。无登录功能，不直接部署到公网。Redis 只映射本机 6379，数据通过命名卷保留。

本机默认临时目录曾出现 Java NIO 内部连接错误；`start.ps1` 为当前进程指定项目内 `.runtime-temp` 目录并已验证启动。若在 IDEA 直接运行，可把 VM options 设置为 `-Djdk.net.unixdomain.tmpdir=项目绝对路径/.runtime-temp`，先创建该目录。

数据来源、许可证与字段解释见 `python/data/数据来源与字段.md`；分析结果和逐图解读见 `python/results/图表解读.md`。所有评估均复用期中实验，不重新编造网页端模型成绩。
