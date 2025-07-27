import sys
from autowsgr.fight import DecisiveBattle
from autowsgr.scripts.main import start_script
from constants import SETTINGS_FILE

run_times = int(sys.argv[1])
timer = start_script(SETTINGS_FILE)

decisive_battle = DecisiveBattle(timer)
decisive_battle.run_for_times(run_times)