from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

NORMAL_PLANS_DIR = BASE_DIR / 'plans/normal_fight/'
EVENT_PLANS_DIR = BASE_DIR / 'plans/event/'
SCRIPT_DIR = BASE_DIR / 'scripts/'
ICONS_DIR = BASE_DIR / 'resources/icons/'
SHIP_NAME_FILE = BASE_DIR / 'resources/ship_name.yaml'

LOGO_FILE = BASE_DIR / 'resources/pics/logo/logo.png'
SETTINGS_FILE = BASE_DIR / 'user_settings.yaml'
UI_CONFIGS_FILE = BASE_DIR / 'user_configs.yaml'
STYLE_FILE = BASE_DIR / 'style.qss'

SHIP_DISPLAY_ORDER = ["航母", "轻母", "装母", "战列", "航战", 
                      "战巡", "重巡", "航巡", "雷巡", "轻巡",
                      "重炮", "驱逐", "导潜", "潜艇", "炮潜",
                      "补给", "导驱", "防驱", "导巡", "防巡",
                      "大巡", "导战", "其他"]

CATEGORY_DISPLAY_ORDER = ["大型", "中型", "小型", "主力", "护卫"]

SHIP_TYPE_CATEGORIES_LOGIC = {
    "大型": ["航母", "装母", "战列", "航战", "战巡", "大巡", "导战"],
    "中型": ["轻母", "重巡", "航巡", "雷巡", "轻巡", "导巡", "防巡"],
    "小型": ["重炮", "驱逐", "导潜", "潜艇", "炮潜", "补给", "导驱", "防驱"],
    "主力": ["航母", "装母", "战列", "航战", "战巡", "导潜", "导驱", "导巡", "大巡", "导战"],
    "护卫": ["轻母", "重巡", "航巡", "雷巡", "轻巡", "重炮", "驱逐", "潜艇", "炮潜", "补给", "防驱", "防巡"],
    "全部": SHIP_DISPLAY_ORDER }

BATTLE_TYPES = ["普通驱逐", "困难驱逐", "普通巡洋", "困难巡洋", "普通战列",
                "困难战列","普通航母", "困难航母", "普通潜艇", "困难潜艇"]

LOG_LEVEL = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

ALL_SS_NAME = {
    "C国": ["潜甲", "潜乙", "422", "303", "351"],
    "E国": ["K1", "支持者", "激流", "M1", "M2", "X1"],
    "F国": ["絮库夫"],
    "G国": ["U-47", "U-505", "U-552", "U-81", "U-96", "U-2540", "U-156", "U-1206", "U-1405", "莉安夕", "U-35", "U-2511", "U-459", "U-556", "U-441", "IIIA", "U-4501"],
    "I国": ["莱昂纳多·达·芬奇"],
    "J国": ["吕-34", "伊-25", "伊-201"],
    "S国": ["S-56", "K-21", "M-296"],
    "U国": ["大青花鱼", "射水鱼","刺尾鱼", "鹦鹉螺", "鲃鱼", "鳞鲀"],
    "其他": ["U-14", "鹰"],
}