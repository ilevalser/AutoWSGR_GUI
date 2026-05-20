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
set "PROTECTED_FILES=user_settings.yaml ui_configs.yaml resources\ship_name.yaml"
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

:: Stash local changes to avoid conflicts
echo [INFO] Stashing local changes...
git stash --include-untracked

if %errorlevel% EQU 0 (
    echo [INFO] Local changes stashed.
) else (
    echo [WARN] Failed to stash local changes (none to stash, continuing).
)

echo.
echo [INFO] Fetching latest code from remote...
echo.

git pull origin %BRANCH%

:: 检查 git pull 的结果
if %errorlevel% EQU 0 goto :git_pull_success

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
goto :end

:git_pull_success
echo.
echo [INFO] Git pull succeeded.

:: Restore stashed changes (if any)
echo [INFO] Restoring local changes...
git stash pop
if %errorlevel% EQU 0 (
    echo [INFO] Local changes restored.
) else (
    echo [INFO] No local changes to restore.
)

goto :update_success


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

:: Use PowerShell to download, extract, and overwrite files
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
$ErrorActionPreference = 'Stop'; ^
try { ^
    $repoOwner = '%REPO_OWNER%'; ^
    $repoName = '%REPO_NAME%'; ^
    $branch = '%BRANCH%'; ^
    $tempZip = [System.IO.Path]::GetTempFileName() + '.zip'; ^
    $tempDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), [System.IO.Guid]::NewGuid().ToString()); ^
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
    $srcRoot = Get-ChildItem -Path $tempDir -Directory | Select-Object -First 1; ^
    if (-not $srcRoot) { throw 'No directory found after extraction'; } ^
    $srcPath = $srcRoot.FullName; ^
    ^
    Write-Host '[INFO] Copying files...'; ^
    $protectedFiles = @('user_settings.yaml', 'ui_configs.yaml', 'resources\ship_name.yaml'); ^
    $protectedDirs = @('plans'); ^
    ^
    Get-ChildItem -Path $srcPath -Recurse | ForEach-Object { ^
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
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue; ^
    Remove-Item -Force $tempZip -ErrorAction SilentlyContinue; ^
    exit 0; ^
} catch { ^
    Write-Host ''; ^
    Write-Host '[ERROR] Update failed: ' $_.Exception.Message; ^
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue; ^
    Remove-Item -Force $tempZip -ErrorAction SilentlyContinue; ^
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