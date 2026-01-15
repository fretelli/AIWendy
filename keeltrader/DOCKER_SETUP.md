# Docker 拉取失败与镜像加速（常见问题）

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

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

---

<a id="en"></a>
## English

If you hit network issues when pulling base images (e.g. Docker Hub timeouts), troubleshoot in the order below.

### 1) Use the built-in mirror config first

This project’s `docker-compose.yml` defaults to using the `docker.1ms.run` mirror (useful for networks in mainland China).

If you want to replace it with your own mirror:

- Edit `apps/api/Dockerfile` and `apps/web/Dockerfile`
- Replace `docker.1ms.run/library/` with your own mirror prefix

### 2) Configure Docker Desktop proxy (corporate networks)

Windows/macOS (Docker Desktop):

1. Open Docker Desktop settings
2. Resources → Proxies
3. Enable Manual proxy configuration
4. Fill HTTP/HTTPS proxy
5. Apply & Restart

Linux (systemd): follow Docker’s docs to set `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`.

### 3) Start and debug

For running and troubleshooting, follow the self-hosting doc: `docs/SELF_HOSTING.md`

Common commands:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f
```

