from autowsgr.scripts.daily_api import DailyOperation
from autowsgr.scripts.main import start_script
from constants import SETTINGS_FILE

timer = start_script(SETTINGS_FILE)

operation = DailyOperation(timer)
operation.run()
      