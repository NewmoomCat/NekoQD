import datetime

from endstone.command import Command, CommandSender
from endstone.event import event_handler, PlayerJoinEvent
from endstone.plugin import Plugin
from endstone import ColorFormat, Player
"""
CatSign -> NekoQD

0.3.0 彻底重构

@author XinYueNeko (NewmoomCat)
"""
class NekoQD(Plugin):
    api_version = "0.11"
    authors = ["XinYueNeko"]

    commands = {
        'sign': {
            "description": "Daily sign in command",
            "usage": ["/sign"],
            "permissions": ["xinyue.neko.qd.cmd.sign"]
        }
    }

    permissions = {
        "xinyue.neko.qd.cmd.sign": {
            "description": "Allow players to sign in",
            "default": True
        }
    }

    def __init__(self):
        super().__init__()
        self.auto = None
        self.money_num = None
        self.plugin_title = None
        self.umoney = None
        self.jsonmoney = None

    def on_load(self) -> None:
        self.save_default_config()

    def get_money_plugin(self) -> None:
        self.umoney = self.server.plugin_manager.get_plugin("umoney")
        self.jsonmoney = self.server.plugin_manager.get_plugin("ye111566_jsonmoney")
        if self.umoney or self.jsonmoney:
            self.logger.info(f"{ColorFormat.AQUA}NekoQD Enabled")
        else:
            self.logger.error(f"{ColorFormat.RED}No {ColorFormat.YELLOW}JsonMoney/UMoney {ColorFormat.RED}economy plugin detected.")
            self.server.plugin_manager.disable_plugin(self)

    def on_enable(self) -> None:
        self.auto = self.config.get("config.auto-sign")
        self.money_num = self.config.get("config.money")
        self.plugin_title = self.config.get("config.plugin-title")
        self.get_money_plugin()

    def on_disable(self) -> None:
        self.logger.info(f"{ColorFormat.AQUA}NekoQD disabled")

    def _change_money(self, player_name: str, number: int) -> None:
        if self.umoney:
            self.umoney.api_change_player_money(player_name, number)
        elif self.jsonmoney:
            self.jsonmoney.change(player_name, number)

    def _do_sige(self, player: Player) -> bool:
        today = datetime.date.today().isoformat()
        record_dir = self.data_folder / "data"
        record_dir.mkdir(exist_ok=True)
        record_file = record_dir / f"{player.unique_id}_{today}.json"

        if record_file.exists():
            player.send_message(f"{ColorFormat.AQUA}[{self.plugin_title}]{ColorFormat.RESET}你今天已经签到过了哟～！")
            return False

        record_file.write_text('{ "signed": true }', encoding="utf-8")
        self._change_money(player.name, int(self.money_num))
        player.send_message(f"{ColorFormat.AQUA}[{self.plugin_title}]{ColorFormat.RESET}签到成功! 您已获得{self.money_num}块钱！")
        return True

    def on_command(self,sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_error_message("This command can only be used by players.")
            return True
        """ 分割线 """
        if command is None or not command.name:
            return False

        if command.name == "sign":
            self._do_sige(sender)

        # Emm...
        return True

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        player: Player = event.player
        if self.auto:
            self._do_sige(player)
            player.send_message(f"{ColorFormat.AQUA}[{self.plugin_title}]{ColorFormat.GRAY}自动签到已开启")