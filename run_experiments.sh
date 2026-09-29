#!/bin/bash
# 实验批跑脚本：单股票场景对照实验矩阵
# 用法: bash run_experiments.sh   （结果追加到 results/experiment_log.txt，可中断重跑）
# 每组实验独立，中断后重跑只会重复当前组，不影响已落盘的结果
PY=.venv/Scripts/python.exe
LOG=results/experiment_log.txt
mkdir -p results

run() { # $1=股票代码 $2=模型 $3=horizon $4=hidden $5=lr $6=wd
  local tag="$1 $2 horizon=$3 hidden=$4 lr=$5 wd=$6 seed=1"
  # 断点续跑：该配置在日志中已有完整结果（含 DA 行）则跳过，中断后重跑不重复劳动
  if grep -A8 "^=== $tag " $LOG 2>/dev/null | grep -q "DA"; then
    echo "--- 跳过（已有结果）: $tag" | tee -a $LOG
    return
  fi
  echo "=== $tag $(date '+%H:%M') ===" | tee -a $LOG
  $PY train.py --csv docs/csv/$1.csv --model $2 --horizon $3 --hidden $4 --lr $5 --wd $6 \
      --epochs 150 --patience 30 --seed 1 2>&1 \
    | grep -E "早停于|最优验证|^  (MSE|RMSE|MAE|R2|DA)" | tee -a $LOG
}

# A. 双向加强正则诊断：验证"双向落败是正则不足"假说（600036, h16, wd 3e-4）
run 600036.SH bimamba 1 16 1e-3 3e-4

# B. 大容量对照：验证"双向需要更大容量"假说（4股, h32, horizon=1）
for code in 600036.SH 601288.SH 601328.SH 601988.SH; do
  run $code baseline 1 32 1e-3 1e-4
  run $code bimamba 1 32 1e-3 1e-4
done

# C. 5日预测全面对照（4股, h16, horizon=5）
for code in 600036.SH 601288.SH 601328.SH 601988.SH; do
  run $code baseline 5 16 1e-3 1e-4
  run $code bimamba 5 16 1e-3 1e-4
done

echo "ALL DONE $(date '+%H:%M')" | tee -a $LOG
