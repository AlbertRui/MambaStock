#!/bin/bash
# v2 实验批跑脚本：新数据（20180601-20251231 全区间）+ pre_close 修正标签口径
# 与 v1 的区别：数据区间 2019-2025（v1 只有 2019-2022）、标签除息修正、独立日志文件
# 用法: bash run_experiments_v2.sh   （结果追加到 results/experiment_log_v2.txt，可中断重跑）
# PY 可用环境变量覆盖：本地默认 .venv，远端 GPU 服务器用 PY=python3 bash run_experiments_v2.sh
PY=${PY:-.venv/Scripts/python.exe}
LOG=results/experiment_log_v2.txt
mkdir -p results

# ---------- 单股票实验：模块一（双向）与模块三（波动加权）的消融矩阵 ----------
run() { # $1=股票代码 $2=模型 $3=volweight(on/off)
  local tag="$1 $2 volw=$3 horizon=1 hidden=32 lr=1e-3 wd=1e-4 seed=1"
  # 断点续跑：该配置在日志中已有完整结果（含 DA 行）则跳过
  if grep -A10 "^=== $tag " $LOG 2>/dev/null | grep -q "DA"; then
    echo "--- 跳过（已有结果）: $tag" | tee -a $LOG
    return
  fi
  local extra=""
  [ "$3" = "on" ] && extra="--vol-weight"
  echo "=== $tag $(date '+%H:%M') ===" | tee -a $LOG
  $PY train.py --csv docs/csv/$1.csv --model $2 --horizon 1 --hidden 32 \
      --lr 1e-3 --wd 1e-4 --epochs 150 --patience 30 --seed 1 $extra 2>&1 \
    | grep -E "早停于|最优验证|^  (MSE|RMSE|MAE|R2|DA)" | tee -a $LOG
}

# ---------- 面板实验：模块二（跨股票注意力）消融 + 完整模型 ----------
run_panel() { # $1=attn(on/off) $2=volweight(on/off)
  local tag="PANEL8 attn=$1 volw=$2 horizon=1 hidden=32 lr=1e-3 wd=1e-4 seed=1"
  if grep -A10 "^=== $tag " $LOG 2>/dev/null | grep -q "DA"; then
    echo "--- 跳过（已有结果）: $tag" | tee -a $LOG
    return
  fi
  local extra=""
  [ "$1" = "off" ] && extra="--no-attention"
  [ "$2" = "on" ] && extra="$extra --vol-weight"
  echo "=== $tag $(date '+%H:%M') ===" | tee -a $LOG
  $PY train_panel.py --horizon 1 --hidden 32 --lr 1e-3 --wd 1e-4 \
      --epochs 150 --patience 30 --seed 1 $extra 2>&1 \
    | grep -E "早停于|最优验证|^  (MSE|RMSE|MAE|R2|DA)|^  [0-9]{6}" | tee -a $LOG
}

# A. 单股票消融矩阵：4股 × {baseline, bimamba} × {无加权, 波动加权} = 16 组
#    （与 v1 相同的 4 只银行，保证 v1/v2 可对比；h32 沿用 v1 结论的最佳配置）
for code in 600036.SH 601288.SH 601328.SH 601988.SH; do
  run $code baseline off
  run $code bimamba  off
  run $code baseline on
  run $code bimamba  on
done

# B. 面板消融矩阵：{无注意力, 注意力} × {无加权, 波动加权} = 4 组
#    attn off→on 验证模块二贡献；volw off→on 验证模块三在完整模型上的贡献
run_panel off off
run_panel on  off
run_panel off on
run_panel on  on

echo "ALL DONE $(date '+%H:%M')" | tee -a $LOG
