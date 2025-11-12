import sys
from autowsgr.fight import DecisiveBattle
from autowsgr.port.task_runner import TaskRunner
from autowsgr.scripts.main import start_script
from constants import SETTINGS_FILE

run_times = int(sys.argv[1])
timer = start_script(SETTINGS_FILE)

if '--use-task-runner' in sys.argv:
    runner = TaskRunner(timer)
    runner.add_decisive_task(run_times)
    runner.run()
else:
    decisive_battle = DecisiveBattle(timer)
    decisive_battle.run_for_times(run_times)