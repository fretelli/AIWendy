@echo off
echo ========================================
echo KeelTrader Phase 2 初始化脚本
echo ========================================
echo.

REM 检查Python环境
echo [1/3] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 运行数据库迁移
echo [2/3] 运行数据库迁移...
cd /d C:\KeelTrader\aiwendy
alembic upgrade head
if %errorlevel% neq 0 (
    echo 错误: 数据库迁移失败
    pause
    exit /b 1
)

echo.
echo [3/3] 初始化教练数据...
cd /d C:\KeelTrader\aiwendy\apps\api
python scripts\init_coaches.py
if %errorlevel% neq 0 (
    echo 错误: 初始化教练数据失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo Phase 2 初始化完成！
echo.
echo 已完成：
echo - 多教练系统数据库表创建
echo - 5个不同风格的AI教练初始化
echo - 教练市场前端页面
echo - 教练选择器组件
echo.
echo 现在可以访问以下新功能：
echo - /coaches - 教练市场页面
echo - /coaches/[id] - 教练详情页面
echo ========================================
pause