# Docker registry and network troubleshooting

<a id="zh-cn"></a>
[中文](#zh-cn) | [English](#en)

KeelTrader 默认使用 Docker Hub、PyPI 和 npm 官方源，以保证公开构建定义可移植、可审计。若所在网络访问官方源不稳定，请仅在本地未跟踪的 `.env` 中覆盖：

```dotenv
PIP_INDEX_URL=https://your-pypi-mirror.example/simple/
NPM_CONFIG_REGISTRY=https://your-npm-mirror.example/
```

Docker Hub 镜像加速应配置在 Docker Engine/Desktop 层，而不是把某个地区的镜像代理硬编码进仓库。修改后使用以下命令验证：

```bash
docker compose -f docker-compose.selfhost.yml config
docker compose -f docker-compose.selfhost.yml build
```

不要提交代理凭据、公司 CA、镜像仓库密码或本地 `.env`。

---

<a id="en"></a>
## English

KeelTrader defaults to the official Docker Hub, PyPI, and npm registries so public build definitions remain portable and auditable. If those registries are unreliable on your network, override them only in an untracked local `.env`:

```dotenv
PIP_INDEX_URL=https://your-pypi-mirror.example/simple/
NPM_CONFIG_REGISTRY=https://your-npm-mirror.example/
```

Configure Docker Hub acceleration at the Docker Engine/Desktop layer instead of hard-coding a regional proxy in the repository. Validate changes with:

```bash
docker compose -f docker-compose.selfhost.yml config
docker compose -f docker-compose.selfhost.yml build
```

Never commit proxy credentials, corporate CAs, registry passwords, or local `.env` files.
