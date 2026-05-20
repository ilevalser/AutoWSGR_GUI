@echo off
setlocal enabledelayedexpansion

:: =================================================================
:: AutoWSGR GUI Updater
:: =================================================================
:: This script automatically updates AutoWSGR GUI to the latest version.
:: Supports two modes:
::   1. Git clone users - uses git pull
::   2. ZIP users       - downloads ZIP from GitHub and extracts
:: =================================================================

title AutoWSGR GUI Updater

:: =================================================================
:: Configuration
:: =================================================================
set "REPO_OWNER=ilevalser"
set "REPO_NAME=AutoWSGR_GUI"
set "BRANCH=main"
set "GITHUB_API=https://api.github.com"
set "GITHUB_RAW=https://github.com/%REPO_OWNER%/%REPO_NAME%/archive/refs/heads/%BRANCH%.zip"

:: Protected user files (will NOT be overwritten)
set "PROTECTED_FILES=user_settings.yaml ui_configs.yaml resources\ship_name.yaml %~nx0"
set "PROTECTED_DIRS=plans"

:: =================================================================
:: Welcome Message
:: =================================================================
echo.
echo ==========================================================
echo ==                AutoWSGR GUI Updater                  ==
echo ==========================================================
echo.
echo This script will update AutoWSGR GUI 1.0 to the latest version.
echo.
echo           Make 1.0 Great Again !
echo.
echo.
echo.
echo Repository: https://github.com/%REPO_OWNER%/%REPO_NAME%
echo Branch: %BRANCH%
echo.
echo The following user files are protected and will NOT be overwritten:
echo   - %~nx0 (Updater itself)
echo   - user_settings.yaml
echo   - ui_configs.yaml
echo   - resources\ship_name.yaml
echo   - plans\ (all files under this directory)
echo.

:: Ask user for confirmation
set /p CONFIRM="Continue with update? (Y/N): "
if /i not "!CONFIRM!"=="Y" (
    echo.
    echo Update cancelled.
    goto :end
)

echo.
echo =================================================================
echo ==  Step 1: Check local repository status                   ==
echo =================================================================
echo.

:: Check if git is available
where git >nul 2>nul
set "GIT_AVAILABLE=%errorlevel%"

:: Check if .git directory exists
if not exist ".git" (
    echo [INFO] No Git repository detected, using ZIP download method.
    goto :zip_update
)

echo [INFO] Git repository detected (.git directory exists).
if %GIT_AVAILABLE% EQU 0 (
    echo [INFO] git command available, using git pull for update.
    goto :git_update
) else (
    echo [WARN] .git directory found but git command not available.
    echo [INFO] Falling back to ZIP download method.
    goto :zip_update
)


:: =================================================================
:: Method A: Git Pull Update
:: =================================================================
:git_update
echo.
echo =================================================================
echo ==  Step 2: Executing git pull                             ==
echo =================================================================
echo.

:: 将 stash、pull 和 pop 整个流程全部打包进内存块
(
    echo [INFO] Stashing local changes...
    git stash --include-untracked
    set STASH_STATUS=!errorlevel!

    if !STASH_STATUS! EQU 0 (
        echo [INFO] Local changes stashed.
    ) else (
        :: 注意这里的括号必须用 ^ 转义，否则会破坏内存块结构
        echo [WARN] Failed to stash local changes ^(none to stash, continuing^).
    )

    echo.
    echo [INFO] Fetching latest code from remote...
    echo.

    :: 备份当前脚本，强制防止它被更新
    copy /y "%~f0" "%TEMP%\updater_backup.bat" >nul

    git pull origin %BRANCH%
    set PULL_STATUS=!errorlevel!

    if !PULL_STATUS! EQU 0 (
        echo.
        echo [INFO] Git pull succeeded.
        
        echo [INFO] Restoring local changes...
        git stash pop
        set POP_STATUS=!errorlevel!
        
        if !POP_STATUS! EQU 0 (
            echo [INFO] Local changes restored.
        ) else (
            echo [INFO] No local changes to restore.
        )
        
        :: 无论 Git 怎么操作，最后都用刚才的备份把脚本强行盖回来
        copy /y "%TEMP%\updater_backup.bat" "%~f0" >nul
        goto :update_success
        
    ) else (
        echo.
        echo [ERROR] Git pull failed!
        echo.
        echo Possible causes:
        echo   1. Network connection issue
        echo   2. Conflicting local changes
        echo.
        echo Try manual steps:
        echo   git status        # Check current status
        echo   git stash         # Stash local changes
        echo   git pull          # Fetch from remote
        echo   git stash pop     # Restore local changes
        
        :: 失败也要把脚本还原
        copy /y "%TEMP%\updater_backup.bat" "%~f0" >nul
        goto :end
    )
)

:: =================================================================
:: Method B: ZIP Download and Extract
:: =================================================================
:zip_update
echo.
echo =================================================================
echo ==  Step 2: Downloading latest version from GitHub          ==
echo =================================================================
echo.
echo [INFO] Fetching %REPO_NAME% latest version...
echo [INFO] Download URL: %GITHUB_RAW%
echo.
echo Download may take a while, please be patient...
echo.

:: 使用向下兼容的 PowerShell 核心块，不再包含任何管道符(|)及高版本.NET组件
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
$ErrorActionPreference = 'Stop'; ^
$tempDir = $null; ^
try { ^
    $repoOwner = '%REPO_OWNER%'; ^
    $repoName = '%REPO_NAME%'; ^
    $branch = '%BRANCH%'; ^
    $tempZip = [System.IO.Path]::GetTempFileName() + '.zip'; ^
    $randNum = Get-Random -Minimum 100000 -Maximum 999999; ^
    $tempDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'AutoWSGR_' + $randNum); ^
    $scriptDir = '%CD%'; ^
    ^
    Write-Host '[INFO] Downloading ZIP package...'; ^
    $url = 'https://github.com/' + $repoOwner + '/' + $repoName + '/archive/refs/heads/' + $branch + '.zip'; ^
    Invoke-WebRequest -Uri $url -OutFile $tempZip -UseBasicParsing -TimeoutSec 120; ^
    ^
    Write-Host '[INFO] Download complete, extracting...'; ^
    [void](New-Item -ItemType Directory -Force -Path $tempDir); ^
    Expand-Archive -Path $tempZip -DestinationPath $tempDir; ^
    ^
    $dirs = Get-ChildItem -Path $tempDir -Directory; ^
    if ($dirs.Count -eq 0) { throw 'No directory found after extraction'; } ^
    $srcPath = $dirs[0].FullName; ^
    ^
    Write-Host '[INFO] Copying files...'; ^
    $thisScript = '%~nx0'; ^
    $protectedFiles = @('user_settings.yaml', 'ui_configs.yaml', 'resources\ship_name.yaml', $thisScript); ^
    $protectedDirs = @('plans'); ^
    ^
    $allFiles = Get-ChildItem -Path $srcPath -Recurse; ^
    foreach ($_ in $allFiles) { ^
        $relative = $_.FullName.Substring($srcPath.Length + 1); ^
        $skip = $false; ^
        ^
        foreach ($pf in $protectedFiles) { ^
            if ($relative -eq $pf) { $skip = $true; break } ^
        } ^
        if (-not $skip) { ^
            foreach ($pd in $protectedDirs) { ^
                if ($relative -eq $pd -or $relative -like ($pd + '\*')) { $skip = $true; break } ^
            } ^
        } ^
        ^
        if (-not $skip) { ^
            $dest = Join-Path $scriptDir $relative; ^
            if ($_.PSIsContainer) { ^
                if (-not (Test-Path $dest)) { [void](New-Item -ItemType Directory -Force -Path $dest) } ^
            } else { ^
                $parent = Split-Path $dest -Parent; ^
                if (-not (Test-Path $parent)) { [void](New-Item -ItemType Directory -Force -Path $parent) } ^
                Copy-Item -Force -Path $_.FullName -Destination $dest; ^
            } ^
        } ^
    }; ^
    ^
    Write-Host ''; ^
    Write-Host '[INFO] File copy complete.'; ^
    ^
    if ($tempDir -and (Test-Path $tempDir)) { Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue }; ^
    if (Test-Path $tempZip) { Remove-Item -Force $tempZip -ErrorAction SilentlyContinue }; ^
    exit 0; ^
} catch { ^
    Write-Host ''; ^
    Write-Host '[ERROR] Update failed: ' $_.Exception.Message; ^
    if ($tempDir -and (Test-Path $tempDir)) { Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue }; ^
    if (Test-Path $tempZip) { Remove-Item -Force $tempZip -ErrorAction SilentlyContinue }; ^
    exit 1; ^
}

:: Check PowerShell execution result
if %errorlevel% EQU 0 goto :update_success

echo.
echo =================================== ERROR ===================================
echo.
echo An error occurred during the update. Please check:
echo   1. Network connectivity
echo   2. GitHub accessibility
echo   3. Available disk space
echo.
echo Your configuration files are unaffected. You can continue using the current version.
echo.
echo =============================================================================
goto :end


:: =================================================================
:: Update Successful
:: =================================================================
:update_success
echo.
echo =================================================================
echo ==           Update Successful!                              ==
echo =================================================================
echo.
echo AutoWSGR GUI has been successfully updated to the latest version.
echo.
echo Please close this window and restart AutoWSGR GUI to apply the update.
echo.
echo Note: If you encounter any issues, try running install_deps.bat
echo       to ensure all dependencies are up to date.
echo.
echo =================================================================
goto :end


:: =================================================================
:: Script End
:: =================================================================
:end
echo.
echo ================================================================
echo  Update finished at: %DATE% %TIME%
echo ================================================================
echo.
pause
exit /b 0