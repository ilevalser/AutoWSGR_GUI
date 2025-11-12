from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

def update_config_value(config_data: dict, path: str, value):
    """
    更新配置字典中指定路径的值。

    Args:
        config_data (dict): 要更新的配置字典。
        path (str): 以点分隔的键路径，例如 'daily_automation.auto_expedition'。
        value: 要设置的新值。
    """
    keys = path.split('.')
    d = config_data
    for key in keys[:-1]:
        # 如果路径中的某个键不存在，则创建它
        d = d.setdefault(key, CommentedMap())
    d[keys[-1]] = value


def save_config(yaml_manager: YAML, config_data: dict, file_path, key_order: list = None):
    """
    使用指定的YAML管理器将配置数据保存到文件，并可选择按指定顺序排序键。

    Args:
        yaml_manager (YAML): ruamel.yaml 的实例。
        config_data (dict): 要保存的配置数据。
        file_path: 目标文件的路径 (Path 对象)。
        key_order (list, optional): 一个包含键字符串的列表。如果提供，
                                    函数会按照此列表的顺序排列config_data中的键，
                                    然后再保存。默认为 None，即按原顺序保存。

    Raises:
        Exception: 当文件写入失败时抛出异常。
    """
    data_to_save = config_data

    # 如果提供了键顺序列表，则根据它重建字典
    if key_order:
        ordered_data = CommentedMap()
        # 按照预设顺序拷贝键
        for key in key_order:
            if key in config_data:
                ordered_data[key] = config_data[key]
        # 拷贝不在预设顺序中的其他键，防止数据丢失
        for key, value in config_data.items():
            if key not in ordered_data:
                ordered_data[key] = value
        data_to_save = ordered_data

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml_manager.dump(data_to_save, f)
    except Exception as e:
        raise Exception(f"保存配置文件 {file_path.name} 失败: {e}")

def numeric_conversion(text, target_type=int, default_on_error=0, validation_func=None):
    """
    安全地将文本转换为指定数值类型，并进行可选的验证。

    :param text: 输入的字符串。
    :param target_type: 目标数值类型，如 int 或 float。
    :param default_on_error: 当转换或验证失败时返回的默认值。
    :param validation_func: 一个可选的函数，用于验证转换后的值。
                              该函数应接收一个数值并返回 True (有效) 或 False (无效)。
                              例如: lambda x: x >= 0 用于检查非负数。
    :return: 转换和验证后的数值，或默认值。
    """
    # 如果输入文本为空或仅包含空白，直接返回默认值
    if not text or text.isspace():
        return default_on_error

    try:
        # 尝试将字符串转换为目标数值类型
        value = target_type(text)
        
        # 如果提供了验证函数，则执行验证
        if validation_func and not validation_func(value):
            # 验证失败，返回默认值
            return default_on_error
        
        # 转换和验证都成功，返回转换后的值
        return value
    except (ValueError, TypeError):
        # 如果字符串无法转换为目标类型，捕获异常并返回默认值
        return default_on_error

def validate_and_save_line_edit(
    line_edit, config_path, settings_data, settings_path, yaml_manager,
    default_value, target_type=int, clamp_range=None, log_signal=None
):
    """
    通用函数，用于验证 QLineEdit 的数值输入，修正范围，更新UI，并保存到配置。

    :param line_edit: QLineEdit 控件实例。
    :param config_path: 要更新的配置路径。
    :param settings_data: 整个配置字典。
    :param settings_path: 配置文件的路径。
    :param yaml_manager: YAML 管理器实例。
    :param default_value: 当输入为空或无效时的默认值。
    :param target_type: 目标数值类型，如 int 或 float。
    :param clamp_range: 一个元组 (min, max)，用于限制值的范围。
    :param log_signal: 用于发送日志消息的信号 (可选)。
    """
    initial_text = line_edit.text()
    value = numeric_conversion(initial_text, target_type=target_type, default_on_error=default_value)

    if clamp_range:
        min_val, max_val = clamp_range
        value = max(min_val, min(value, max_val))

    if str(value) != initial_text:
        line_edit.setText(str(value))

    try:
        update_config_value(settings_data, config_path, value)
        save_config(yaml_manager, settings_data, settings_path)
    except Exception as e:
        if log_signal:
            log_signal.emit(str(e))

def validate_and_save_text_input(
    line_edit, config_path, settings_data, settings_path, yaml_manager,
    validation_func, log_signal=None
):
    """
    通用函数，用于验证 QLineEdit 的文本输入，提供UI反馈，并保存到配置。

    :param line_edit: QLineEdit 控件实例。
    :param config_path: 要更新的配置路径。
    :param settings_data: 整个配置字典。
    :param settings_path: 配置文件的路径。
    :param yaml_manager: YAML 管理器实例。
    :param validation_func: 一个接收文本并返回 True (有效) 或 False (无效) 的函数。
    :param log_signal: 用于发送日志消息的信号 (可选)。
    """
    text = line_edit.text()
    is_valid = validation_func(text)

    if is_valid:
        line_edit.setProperty("state", "valid")
        try:
            update_config_value(settings_data, config_path, text)
            save_config(yaml_manager, settings_data, settings_path)
        except Exception as e:
            if log_signal:
                log_signal.emit(f"保存配置失败: {e}")
    else:
        line_edit.setProperty("state", "invalid")

    line_edit.style().unpolish(line_edit)
    line_edit.style().polish(line_edit)