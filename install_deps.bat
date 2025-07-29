@echo off
setlocal enabledelayedexpansion

:: ���ô��ڱ���
title AutoWSGR Dependencies Installer

:: =================================================================
:: ��ӭ��Ϣ
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
:: �����߼���������ȷ�� Python ����
:: =================================================================
set "TARGET_PYTHON="

echo.
echo --- Phase 1: Searching for Python environments using 'py.exe'...
for /f "tokens=*" %%a in ('py -0p 2^>nul') do (
    set "PYTHON_EXE="
    :: ����ڲ�ѭ����Ϊ�˻�ȡÿ�����һ���ʣ���Python·��
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
:: δ�ҵ������Ĵ���
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
:: �ҵ�������ִ�а�װ
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
:: �ű�����
:: =================================================================
:end
echo.
echo Press any key to exit.
pause >nul
endlocal