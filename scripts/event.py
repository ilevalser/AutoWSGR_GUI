import sys
import importlib
from autowsgr.scripts.main import start_script
from autowsgr.game.game_operation import set_support
from autowsgr.game.get_game_info import get_loot_and_ship
from constants import SETTINGS_FILE

event_identifier = sys.argv[1] 
plan_path = str(sys.argv[2])
fleet_id = int(sys.argv[3])
battle_count = int(sys.argv[4])
reuse_daily_settings = sys.argv[5] == 'True'
bonus_check_interval = int(sys.argv[6])

timer = start_script(SETTINGS_FILE)

try:
    module_name = f"autowsgr.fight.event.event_{event_identifier}"
    class_name = f"EventFightPlan{event_identifier.replace('_', '')}"
    event_module = importlib.import_module(module_name)
    timer.logger.info(f"使用活动: {class_name}")
    EventFightPlanClass = getattr(event_module, class_name)

except (ImportError, AttributeError) as e:
    timer.logger.error(f"无法加载指定的活动模块或类: {module_name}.{class_name}")
    sys.exit()

if reuse_daily_settings:
    if timer.config.daily_automation.stop_max_loot:
        get_loot_and_ship(timer)
        
        if timer.got_ship_num == 500:
            timer.logger.info("已达出征上限，无法继续出征")
            sys.exit()
        elif timer.got_ship_num + battle_count >= 500:
            battle_count = 500 - timer.got_ship_num
            timer.logger.info(f"调整出征次数为 {battle_count} 次")

    if timer.config.daily_automation.auto_set_support:    
        set_support(timer, True)

plan = EventFightPlanClass(
    timer,
    plan_path=plan_path,
    fleet_id=fleet_id,
)

plan.run_for_times(battle_count,gap=bonus_check_interval)