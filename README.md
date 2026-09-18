# NekoQD 签到插件

**Usage:**

配置文件 (config.toml)
```toml
[config]
auto-sign = false # 自动签到开关
money = 50 # 签到钱数，可调整
plugin-title = "签到插件" # 插件log前缀
```

本插件支持jsonmoney和Umoney经济API
请根据你的服务器所使用的插件进行选择

**Build:**

Run this (如果你有UV)

```bash
uv tool run --from build pyproject-build
```

or

```bash
pip install pipx # install pipx
pipx run build wheel
```