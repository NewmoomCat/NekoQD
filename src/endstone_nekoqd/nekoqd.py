from datetime import date
from pathlib import Path
from typing import Any

from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.event import PlayerJoinEvent, event_handler
from endstone.plugin import Plugin


class NekoQD(Plugin):
    """每日签到插件。

    兼容 UMoney 和 JsonMoney 两种经济插件，并继续使用
    ``data/<player_uuid>_<YYYY-MM-DD>.json`` 作为签到记录格式。
    """

    api_version = "0.11"
    version = "0.3.1"
    authors = ["XinYueNeko"]
    description = "Daily sign-in plugin for Endstone"

    # Endstone 文档中使用 usages（复数）。
    commands = {
        "sign": {
            "description": "Daily sign-in command.",
            "usages": ["/sign"],
            "permissions": ["xinyue.neko.qd.cmd.sign"],
        }
    }

    permissions = {
        "xinyue.neko.qd.cmd.sign": {
            "description": "Allow players to sign in.",
            "default": True,
        }
    }

    # 这是可选依赖：两个插件至少存在一个即可运行。
    soft_depend = ["umoney", "ye111566_jsonmoney"]

    _PREFIX_COLOR = ColorFormat.AQUA
    _PREFIX_RESET = ColorFormat.RESET

    def __init__(self) -> None:
        super().__init__()
        self._auto_sign = False
        self._reward = 0
        self._plugin_title = "NekoQD"
        self._economy_plugin: Any | None = None
        self._economy_name: str | None = None

    def on_enable(self) -> None:
        self.save_default_config()
        self._load_config()
        self._select_economy_plugin()

        if self._economy_plugin is None:
            self.logger.error(
                "No enabled economy plugin found. Expected UMoney "
                "or ye111566_jsonmoney; NekoQD will be disabled."
            )
            self.server.plugin_manager.disable_plugin(self)
            return

        # Python 事件处理器需要显式注册。
        self.register_events(self)
        self.logger.info(
            f"{ColorFormat.AQUA}NekoQD enabled "
            f"(economy: {self._economy_name}, reward: {self._reward})"
        )

    def on_disable(self) -> None:
        self.logger.info(f"{ColorFormat.AQUA}NekoQD disabled")

    def _load_config(self) -> None:
        """读取配置，并对用户配置做类型和范围校验。

        同时兼容旧代码使用的 ``config.auto-sign`` 风格和常见嵌套 TOML：
        ``[config] auto-sign = true``。
        """
        config = self.config
        self._auto_sign = self._as_bool(
            self._config_value(config, "auto-sign", False), default=False
        )
        self._reward = self._as_non_negative_int(
            self._config_value(config, "money", 0), default=0
        )
        title = self._config_value(config, "plugin-title", "NekoQD")
        self._plugin_title = str(title).strip() or "NekoQD"

    @staticmethod
    def _config_value(config: dict[str, Any], key: str, default: Any) -> Any:
        """从扁平键或嵌套 config 表中读取配置。"""
        if key in config:
            return config[key]
        section = config.get("config")
        if isinstance(section, dict) and key in section:
            return section[key]
        return default

    @staticmethod
    def _as_bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "on", "1"}:
                return True
            if normalized in {"false", "no", "off", "0"}:
                return False
        return default

    @staticmethod
    def _as_non_negative_int(value: Any, default: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return default
        return max(0, number)

    def _select_economy_plugin(self) -> None:
        manager = self.server.plugin_manager
        candidates = (
            ("umoney", "umoney"),
            ("ye111566_jsonmoney", "jsonmoney"),
        )

        for plugin_id, display_name in candidates:
            plugin = manager.get_plugin(plugin_id)
            if plugin is None:
                continue
            if hasattr(plugin, "is_enabled") and not plugin.is_enabled:
                continue
            self._economy_plugin = plugin
            self._economy_name = display_name
            return

    def _add_money(self, player: Player) -> bool:
        """调用已检测到的经济插件，返回是否成功。"""
        if self._economy_plugin is None:
            return False

        try:
            if self._economy_name == "umoney":
                result = self._economy_plugin.api_change_player_money(
                    player.name, self._reward
                )
            else:
                result = self._economy_plugin.change(player.name, self._reward)
        except Exception:
            self.logger.error(
                f"Failed to add {self._reward} money to {player.name}."
            )
            return False

        # 大多数旧经济插件没有返回值；只有明确返回 False 时视为失败。
        return result is not False

    def _record_path(self, player: Player, sign_date: date | None = None) -> Path:
        day = sign_date or date.today()
        record_dir = self.data_folder / "data"
        record_dir.mkdir(parents=True, exist_ok=True)
        return record_dir / f"{player.unique_id}_{day.isoformat()}.json"

    def _message(self, text: str) -> str:
        return (
            f"{self._PREFIX_COLOR}[{self._plugin_title}]"
            f"{self._PREFIX_RESET}{text}"
        )

    def _do_sign(self, player: Player) -> bool:
        """执行一次签到；使用独占创建避免重复发奖。"""
        record_file = self._record_path(player)

        try:
            # ``x`` 模式是原子独占创建：并发触发时只有一个请求能成功。
            with record_file.open("x", encoding="utf-8") as file:
                file.write('{"signed": true}\n')
        except FileExistsError:
            player.send_message(self._message("你今天已经签到过了哟～！"))
            return False
        except OSError:
            self.logger.error(f"Failed to create sign-in record for {player.name}.")
            player.send_message(self._message("签到失败，请稍后再试。"))
            return False

        if not self._add_money(player):
            # 发奖失败时删除记录，允许玩家稍后重试，避免“未拿到钱但无法签到”。
            try:
                record_file.unlink(missing_ok=True)
            except OSError:
                self.logger.exception(
                    f"Failed to roll back sign-in record for {player.name}."
                )
            player.send_message(self._message("签到失败，经济插件暂时不可用。"))
            return False

        player.send_message(self._message(f"签到成功！您已获得 {self._reward} 块钱！"))
        return True

    def on_command(
        self, sender: CommandSender, command: Command, args: list[str]
    ) -> bool:
        if command.name != "sign":
            return False
        if not isinstance(sender, Player):
            sender.send_error_message("This command can only be used by players.")
            return True
        if args:
            sender.send_message("用法：/sign")
            return True

        self._do_sign(sender)
        return True

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        if not self._auto_sign:
            return

        player = event.player
        if self._do_sign(player):
            player.send_message(self._message("自动签到已开启。"))