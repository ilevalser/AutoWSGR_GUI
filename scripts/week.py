from autowsgr.fight.normal_fight import NormalFightPlan
from autowsgr.scripts.main import start_script
from constants import SETTINGS_FILE

timer = start_script(SETTINGS_FILE)

def week(start=1, start_times=0, fleet_id=4, change=True):
    # 完成周常任务
    changes = [None, -1, -1, -1, -1, None, None, None, None, -1]
    last_point = [None, 'B', 'F', 'G', 'L', 'I', 'J', 'M', 'L', 'O']
    result = [None] + ['S'] * 9
    if change:
        changes[start] = -1
    for i in range(start, 10):
        plan = NormalFightPlan(
            timer,
            timer.plan_tree['week'][f'{i}'],
            fleet_id,
            changes[i],
        )
        if i == start:
            plan.run_for_times_condition(5 - start_times, last_point[i], result[i])
        else:
            plan.run_for_times_condition(5, last_point[i], result[i])