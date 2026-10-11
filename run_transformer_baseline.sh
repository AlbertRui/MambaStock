#!/bin/bash
# Transformer 基线批跑脚本：与 run_experiments_v2.sh 完全相同的数据区间/超参数/种子，
# 仅替换编码器架构，保证对照实验的唯一变量是序列建模器（导师评审意见：补充 Transformer 基线）。
# 用法: bash run_transformer_baseline.sh   （结果追加到 results/experiment_log_v2.txt，可中断重跑）
# PY 可用环境变量覆盖：本地默认 .venv，远端 GPU 服务器用 PY=python3 bash run_transformer_baseline.sh
PY=${PY:-.venv/Scripts/python.exe}
LOG=results/experiment_log_v2.txt
mkdir -p results

# ---------- 单股票：4 只银行股 × Transformer 基线（vol-weight 是本文模块，基线不开） ----------
run() { # $1=股票代码
  local tag="$1 transformer volw=off horizon=1 hidden=32 lr=1e-3 wd=1e-4 seed=1"
  # 断点续跑：该配置在日志中已有完整结果（含 DA 行）则跳过
  if grep -A10 "^=== $tag " $LOG 2>/dev/null | grep -q "DA"; then
    echo "--- 跳过（已有结果）: $tag" | tee -a $LOG
    return
  fi
  echo "=== $tag $(date '+%H:%M') ===" | tee -a $LOG
  $PY train.py --csv docs/csv/$1.csv --model transformer --horizon 1 --hidden 32 \
      --lr 1e-3 --wd 1e-4 --epochs 150 --patience 30 --seed 1 2>&1 \
    | grep -E "早停于|最优验证|^  (MSE|RMSE|MAE|R2|DA)" | tee -a $LOG
}

# ---------- 面板：8 只银行股 × Transformer 基线（逐股独立编码，无跨股票注意力） ----------
run_panel() {
  local tag="PANEL8 arch=transformer horizon=1 hidden=32 lr=1e-3 wd=1e-4 seed=1"
  if grep -A14 "^=== $tag " $LOG 2>/dev/null | grep -q "DA"; then
    echo "--- 跳过（已有结果）: $tag" | tee -a $LOG
    return
  fi
  echo "=== $tag $(date '+%H:%M') ===" | tee -a $LOG
  $PY train_panel.py --arch transformer --horizon 1 --hidden 32 --lr 1e-3 --wd 1e-4 \
      --epochs 150 --patience 30 --seed 1 2>&1 \
    | grep -E "早停于|最优验证|^  (MSE|RMSE|MAE|R2|DA)|^  [0-9]{6}" | tee -a $LOG
}

for code in 600036.SH 601288.SH 601328.SH 601988.SH; do
  run $code
done
run_panel

echo "ALL DONE $(date '+%H:%M')" | tee -a $LOG
