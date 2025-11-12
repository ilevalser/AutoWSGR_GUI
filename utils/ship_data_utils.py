import yaml
from collections import defaultdict
from PySide6.QtWidgets import QMessageBox
from constants import SHIPS_FILE

def load_ship_data(file_path=SHIPS_FILE, target_types=None, group_by_type=False):
    """
    加载并解析舰船数据YAML文件，支持按舰种筛选和自定义返回结构。

    Args:
        file_path (str): 'all_ships.yaml' 文件的路径。
        target_types (list, optional): 
            一个包含舰种字符串的列表 (例如 ['BB', 'BC'])。
            如果为 None 或 ['all']，则加载所有舰种。默认为 None。
        group_by_type (bool, optional): 
            决定返回字典的结构。
            - False (默认): 返回按国籍分组的扁平字典。
              {'C国': ['船A', '船B'], 'E国': ['船C']}
            - True: 返回按国籍和舰种分组的嵌套字典。
              {'C国': {'BB': ['船A'], 'BC': ['船B']}, 'E国': ...}

    Returns:
        dict: 根据参数构建的舰船数据字典。出错时返回空字典。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            full_ship_data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        QMessageBox.warning(None, "数据文件缺失", f"未找到 '{file_path}'。")
        return {}
    except Exception as e:
        QMessageBox.critical(None, "数据文件错误", f"加载 '{file_path}' 时出错: {e}")
        return {}

    if not isinstance(full_ship_data, dict):
        QMessageBox.critical(None, "数据格式错误", f"'{file_path}' 内容非有效字典。")
        return {}

    # 初始化返回结果的结构
    if group_by_type:
        # defaultdict 的 lambda 写法可以创建嵌套的 defaultdict
        result_data = defaultdict(lambda: defaultdict(set))
    else:
        result_data = defaultdict(set)
    
    # 确定是否需要筛选
    should_filter = isinstance(target_types, list) and 'all' not in target_types

    for ship_type, nations in full_ship_data.items():
        if should_filter and ship_type not in target_types:
            continue  # 如果需要筛选且当前类型不匹配，则跳过
        
        if not isinstance(nations, dict): continue
        for nation, ships in nations.items():
            if not isinstance(ships, list): continue
            
            # 根据 group_by_type 参数填充数据
            if group_by_type:
                result_data[nation][ship_type].update(ships)
            else:
                result_data[nation].update(ships)

    # 将最终结果中的 set 转换为排序后的 list
    if group_by_type:
        return {
            nation: {stype: sorted(list(slist)) for stype, slist in sdict.items()}
            for nation, sdict in result_data.items()
        }
    else:
        return {nation: sorted(list(slist)) for nation, slist in result_data.items()}