from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SCRIPT_DIR = BASE_DIR / 'scripts/'
ICONS_DIR = BASE_DIR / 'resources/icons/'
MAP_PICS_DIR = BASE_DIR / 'resources/pics/map'
SHIP_NAME_FILE = BASE_DIR / 'resources/ship_name.yaml'
SHIPS_FILE = BASE_DIR / 'resources/all_ships.yaml'
LOGO_FILE = BASE_DIR / 'resources/pics/logo/logo.png'
SETTINGS_FILE = BASE_DIR / 'user_settings.yaml'
UI_CONFIGS_FILE = BASE_DIR / 'ui_configs.yaml'
STYLE_FILE = BASE_DIR / 'style.qss'
NORMAL_MAP_CONFIGS_FILE = BASE_DIR / 'resources/normal_map_configs.yaml'
EVENT_MAP_CONFIGS_FILE = BASE_DIR / 'resources/event_map_configs.yaml'
ENEMY_SHIP_TYPES = {
    'BB': '战列',
    'BC': '战巡',
    'CL': '轻巡',
    'CV': '航母',
    'CA': '重巡',
    'CVL': '轻母',
    'NAP': '常规补给',
    'DD': '驱逐',
    'SS': '潜艇',
    'CLT': '雷巡',
    'KP': '导巡',
    'BM': '重炮',
    'AV': '装母',
    'AADG': '防驱',
    'ASDG': '导驱',
    'BG': '导战',
    'CBG': '大巡',
    'BBV': '航战',
    'CAV': '航巡',
    'SC': '炮潜',
    'SAP': '胖次补给'
}
SYMBOLS = {
    ">=": "≥",
    "<=": "≤", 
    ">": ">",
    "<": "<",
    "==": "=",
    "!=": "≠"
}
QUANTITIES = set(["0", "1", "2", "3", "4", "5", "6"])
LOGIC_OPS = {
    "and": "并且",
    "or": "或者", 
    "+": "+"
}
PARENS = set(["(", ")"])
ACTION_ITEMS = {
    "retreat": "撤退",
    "detour": "迂回",
    "1": "单纵阵(1)",
    "2": "复纵阵(2)",
    "3": "轮形阵(3)",
    "4": "梯形阵(4)",
    "5": "单横阵(5)"
}
FORMATION_ITEMS = {
    "单纵": "单纵阵",
    "复纵": "复纵阵", 
    "轮形": "轮形阵",
    "梯形": "梯形阵",
    "单横": "单横阵"
}
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
BATTLE_TYPES = ["普通驱逐", "普通巡洋", "普通战列", "普通航母", "普通潜艇",
                "困难驱逐", "困难巡洋", "困难战列", "困难航母", "困难潜艇"]
LOG_LEVEL = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
EMULATOR_TYPE_ITEMS = ["雷电", "蓝叠", "MuMu", "云手机", "其他"]
VISIBLE_PARAMS_MAP = {
    'normal_fight': {
        'long_missile_support', 'detour', 'enemy_rules', 'enemy_formation_rules',
        'SL_when_spot_enemy_fails', 'SL_when_detour_fails', 'SL_when_enter_fight',
        'formation', 'formation_when_spot_enemy_fails', 'night', 'proceed', 'proceed_stop'
    },
    'week': {
        'long_missile_support', 'detour', 'enemy_rules', 'enemy_formation_rules',
        'SL_when_spot_enemy_fails', 'SL_when_detour_fails', 'SL_when_enter_fight',
        'formation', 'formation_when_spot_enemy_fails', 'night', 'proceed', 'proceed_stop'
    },
    'special_ap_task': {
        'long_missile_support', 'detour', 'enemy_rules', 'enemy_formation_rules',
        'SL_when_spot_enemy_fails', 'SL_when_detour_fails', 'SL_when_enter_fight',
        'formation', 'formation_when_spot_enemy_fails', 'night', 'proceed', 'proceed_stop'
    },
    'event': {
        'long_missile_support', 'detour', 'enemy_rules', 'enemy_formation_rules',
        'SL_when_spot_enemy_fails', 'SL_when_detour_fails', 'SL_when_enter_fight',
        'formation', 'formation_when_spot_enemy_fails', 'night', 'proceed', 'proceed_stop'
    },
    'exercise': {'enemy_rules', 'formation', 'night'},
    'battle': {'formation', 'night'}
}
KEY_ORDER_MAP = {
    'normal_fight': ['chapter', 'map', 'repair_mode', 'fight_condition', 'fleet_id', 'fleet', 'selected_nodes', 'node_defaults', 'node_args'],
    'week': ['chapter', 'map', 'repair_mode', 'fight_condition', 'fleet_id', 'fleet', 'selected_nodes', 'node_defaults', 'node_args'],
    'special_ap_task': ['chapter', 'map', 'repair_mode', 'fight_condition', 'fleet_id', 'fleet', 'selected_nodes', 'node_defaults', 'node_args'],
    'battle': ['map', 'repair_mode', 'node_args'],
    'event': ['chapter', 'map', 'repair_mode', 'fleet_id', 'from_alpha', 'fleet', 'selected_nodes', 'node_defaults', 'node_args'],
    'exercise': ['exercise_times', 'robot', 'fleet_id', 'max_refresh_times', 'node_defaults', 'node_args']
}
PARAM_DEFAULTS = {
    'long_missile_support': False,
    'detour': False,
    'SL_when_spot_enemy_fails': False,
    'SL_when_detour_fails': True,
    'SL_when_enter_fight': False,
    'formation': 2,
    'formation_when_spot_enemy_fails': 0,
    'night': False,
    'proceed': True,
    'proceed_stop': 2,
}
REPAIR_ITEMS = ["逐位自定义", "中破修", "大破修"]
PROCEED_ITEMS = ["逐位自定义", "中破停", "大破停"]
FIGHT_CONDITION_ITEMS = ["无战况", "左上", "中间", "右上", "左下", "右下"]
SPOT_FAILS_FORMATION_ITEMS = ["不设置", "单纵阵", "复纵阵", "轮形阵", "梯形阵", "单横阵"]