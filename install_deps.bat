@echo off
setlocal enabledelayedexpansion

:: 设置窗口标题
title AutoWSGR Dependencies Installer

:: =================================================================
:: 欢迎信息
:: =================================================================
echo.
echo ===============================================================
echo ==        AutoWSGR Python Dependencies Installer           ==
echo ===============================================================
echo.
echo This script will install the following required libraries:
echo   - PySide6
echo   - ruamel.yaml
echo   - ansi2html
echo.
echo It will automatically detect the Python environment where
echo 'autowsgr' is installed and use the Tsinghua University
echo mirror for faster downloads.
echo.
echo Press any key to start the process...
pause >nul

:: =================================================================
:: 核心逻辑：查找正确的 Python 环境
:: =================================================================
set "TARGET_PYTHON="

echo.
echo --- Phase 1: Searching for Python environments using 'py.exe'...
for /f "tokens=*" %%a in ('py -0p 2^>nul') do (
    set "PYTHON_EXE="
    :: 这个内部循环是为了获取每行最后一个词，即Python路径
    for %%b in (%%a) do set "PYTHON_EXE=%%b"
    
    if defined PYTHON_EXE (
        echo Checking: !PYTHON_EXE!
        "!PYTHON_EXE!" -c "import autowsgr" >nul 2>nul
        if !errorlevel! equ 0 (
            echo   ^> Found 'autowsgr' in this environment!
            set "TARGET_PYTHON=!PYTHON_EXE!"
            goto :found_python
        )
    )
)

echo.
echo --- Phase 2: 'py.exe' did not find a suitable environment.
echo ---          Searching in your system PATH using 'where'...
for /f "delims=" %%i in ('where python 2^>nul') do (
    echo Checking: %%i
    "%%i" -c "import autowsgr" >nul 2>nul
    if !errorlevel! equ 0 (
        echo   ^> Found 'autowsgr' in this environment!
        set "TARGET_PYTHON=%%i"
        goto :found_python
    )
)

:: =================================================================
:: 未找到环境的处理
:: =================================================================
:not_found
echo.
echo =================================== ERROR ===================================
echo.
echo Could not find a Python environment with the 'autowsgr' library installed.
echo.
echo Please ensure you have installed 'autowsgr' in at least one Python
echo environment accessible via 'py.exe' or your system's PATH.
echo.
echo =============================================================================
goto :end

:: =================================================================
:: 找到环境后，执行安装
:: =================================================================
:found_python
if not defined TARGET_PYTHON goto :not_found

echo.
echo =============================================================================
echo.
echo Target Python environment found:
echo %TARGET_PYTHON%
echo.
echo Starting installation...
echo.

"%TARGET_PYTHON%" -m pip install PySide6 ruamel.yaml ansi2html -i https://pypi.tuna.tsinghua.edu.cn/simple

if %errorlevel% equ 0 (
    echo.
    echo =============================================================================
    echo.
    echo All libraries have been successfully installed or are already up-to-date.
    echo.
    echo =============================================================================
) else (
    echo.
    echo =================================== ERROR ===================================
    echo.
    echo An error occurred during installation. Please check the messages above.
    echo You may need to run this script as an Administrator.
    echo.
    echo =============================================================================
)

:: =================================================================
:: 脚本结束
:: =================================================================
:end
echo.
echo Press any key to exit.
pause >nul
endlocal