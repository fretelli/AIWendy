# Docker 拉取失败与镜像加速（常见问题）

如果你在拉取基础镜像时遇到网络问题（例如 Docker Hub 连接失败/超时），优先按下列顺序排查。

## 1) 先用项目自带的镜像源配置

本项目的 `docker-compose.yml` 已默认使用镜像源 `docker.1ms.run`（适用于中国网络环境）。

如果你需要替换为自己的镜像源：

- 编辑 `apps/api/Dockerfile`、`apps/web/Dockerfile`
- 将 `docker.1ms.run/library/` 替换为你的镜像源前缀

## 2) 配置 Docker Desktop 代理（公司网络/需要代理时）

Windows/macOS（Docker Desktop）：

1. 打开 Docker Desktop 设置
2. Resources → Proxies
3. 启用 Manual proxy configuration
4. 填入 HTTP/HTTPS proxy
5. Apply & Restart

Linux（systemd）可参考官方文档配置 `HTTP_PROXY/HTTPS_PROXY/NO_PROXY`。

## 3) 启动与排错

运行与排错请以自托管文档为准：`docs/SELF_HOSTING.md`

常用命令：

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

