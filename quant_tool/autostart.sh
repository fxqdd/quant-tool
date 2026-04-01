#!/bin/bash
# A股量化分析系统 - 开机自启动脚本
# ================================
# 
# 功能：
# 1. 每日收盘后(15:30)自动收集数据并预测
# 2. 生成每日预测记录
# 3. 每5个交易日后生成统计报告
#
# 安装方法：
#   chmod +x setup_autostart.sh
#   ./setup_autostart.sh
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PREDICTOR_SCRIPT="$SCRIPT_DIR/auto_predictor.py"
PYTHON_BIN=$(which python3)

# 日志目录
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/autopredict_$(date +%Y%m%d).log"

# ================== 任务配置 ==================

# 任务1: 每日收盘后运行预测 (工作日 15:35 执行)
DAILY_PREDICT_JOB="35 15 * * 1-5"

# 任务2: 每5个交易日后生成报告 (每周五 16:00 执行)
WEEKLY_REPORT_JOB="0 16 * * 5"

# ================== 任务脚本 ==================

run_daily_predict() {
    echo "[$(date)] 开始每日预测..." >> "$LOG_FILE"
    cd "$SCRIPT_DIR"
    $PYTHON_BIN $PREDICTOR_SCRIPT >> "$LOG_FILE" 2>&1
    echo "[$(date)] 每日预测完成" >> "$LOG_FILE"
}

run_weekly_report() {
    echo "[$(date)] 开始生成周报..." >> "$LOG_FILE"
    cd "$SCRIPT_DIR"
    $PYTHON_BIN $PREDICTOR_SCRIPT --report >> "$LOG_FILE" 2>&1
    echo "[$(date)] 周报生成完成" >> "$LOG_FILE"
}

# ================== 自动安装 ==================

install_cron() {
    echo "正在安装定时任务..."
    
    # 移除旧任务
    crontab -l 2>/dev/null | grep -v "auto_predictor.py" > /tmp/current_cron
    crontab /tmp/current_cron
    
    # 添加新任务
    (crontab -l 2>/dev/null; echo "# A股量化分析系统 - 每日预测") | crontab -
    (crontab -l 2>/dev/null; echo "$DAILY_PREDICT_JOB cd $SCRIPT_DIR && $PYTHON_BIN $PREDICTOR_SCRIPT >> $LOG_FILE 2>&1") | crontab -
    
    # 添加周报任务
    (crontab -l 2>/dev/null; echo "# A股量化分析系统 - 周报") | crontab -
    (crontab -l 2>/dev/null; echo "$WEEKLY_REPORT_JOB cd $SCRIPT_DIR && $PYTHON_BIN $PREDICTOR_SCRIPT --report >> $LOG_FILE 2>&1") | crontab -
    
    echo "定时任务安装完成！"
    echo ""
    echo "当前定时任务："
    crontab -l | grep -E "auto_predictor|# A股"
}

uninstall_cron() {
    echo "正在卸载定时任务..."
    crontab -l 2>/dev/null | grep -v "auto_predictor.py" > /tmp/current_cron
    crontab /tmp/current_cron
    echo "定时任务已卸载"
}

show_status() {
    echo "=== A股量化分析系统 定时任务状态 ==="
    echo ""
    echo "脚本位置: $PREDICTOR_SCRIPT"
    echo "日志目录: $LOG_DIR"
    echo ""
    echo "当前定时任务："
    crontab -l 2>/dev/null | grep -E "auto_predictor|# A股" || echo "  (无)"
    echo ""
    echo "最近日志："
    ls -la "$LOG_DIR"/autopredict_*.log 2>/dev/null | tail -3 || echo "  (无日志)"
}

# ================== 主程序 ==================

case "$1" in
    install)
        install_cron
        ;;
    uninstall)
        uninstall_cron
        ;;
    status)
        show_status
        ;;
    daily)
        run_daily_predict
        ;;
    report)
        run_weekly_report
        ;;
    *)
        echo "Usage: $0 {install|uninstall|status|daily|report}"
        echo ""
        echo "  install   - 安装定时任务 (开机自启)"
        echo "  uninstall - 卸载定时任务"
        echo "  status    - 查看状态"
        echo "  daily     - 立即运行每日预测"
        echo "  report    - 立即生成报告"
        exit 1
        ;;
esac
