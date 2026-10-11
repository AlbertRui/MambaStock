#!/bin/bash
# v3 调参网格：hidden {32,64} × lr {1e-3,5e-4}，wd=1e-4/seed=1/150轮/早停30 与 v2 正式实验一致
# 选择规则（预先固定）：每个模型配置取验证集 MSE 最小的超参组合，再报告测试集 —— 标准模型选择流程
# 所有模型（含基线与 Transformer）走完全相同流程，保证公平
# 用法: PY=python3 bash run_tuning_v3.sh   （日志 results/experiment_log_v3_tuning.txt，可中断重跑）
PY=${PY:-.venv/Scripts/python.exe}
LOG=results/experiment_log_v3_tuning.txt
mkdir -p results

run() { # $1=code $2=model $3=vw(on/off) $4=hidden $5=lr
  local tag="$1 $2 volw=$3 horizon=1 hidden=$4 lr=$5 wd=1e-4 seed=1"
  if grep -A10 "^=== $tag " $LOG 2>/dev/null | grep -q "DA"; then
    echo "--- 跳过: $tag" | tee -a $LOG; return
  fi
  local extra=""
  [ "$3" = "on" ] && extra="--vol-weight"
  echo "=== $tag $(date '+%H:%M') ===" | tee -a $LOG
  $PY train.py --csv docs/csv/$1.csv --model $2 --horizon 1 --hidden $4 \
      --lr $5 --wd 1e-4 --epochs 150 --patience 30 --seed 1 $extra 2>&1 \
    | grep -E "早停于|最优验证|^  (MSE|RMSE|MAE|R2|DA)" | tee -a $LOG
}

run_panel() { # $1=attn(on/off) $2=vw(on/off) $3=hidden $4=lr ；$1=tf 表示 Transformer 基线
  local tag="PANEL8 arch=$1 volw=$2 horizon=1 hidden=$3 lr=$4 wd=1e-4 seed=1"
  if grep -A14 "^=== $tag " $LOG 2>/dev/null | grep -q "DA"; then
    echo "--- 跳过: $tag" | tee -a $LOG; return
  fi
  local extra=""
  if [ "$1" = "tf" ]; then
    extra="--arch transformer"
  else
    [ "$1" = "off" ] && extra="--no-attention"
    [ "$1" = "on" ] && extra="--attn-nowd"   # 报告口径：注意力分支免权重衰减
  fi
  [ "$2" = "on" ] && extra="$extra --vol-weight"
  echo "=== $tag $(date '+%H:%M') ===" | tee -a $LOG
  $PY train_panel.py --horizon 1 --hidden $3 --lr $4 --wd 1e-4 \
      --epochs 150 --patience 30 --seed 1 $extra 2>&1 \
    | grep -E "早停于|最优验证|^  (MSE|RMSE|MAE|R2|DA)|^  [0-9]{6}" | tee -a $LOG
}

# A. 单股票：4股 × {baseline, bimamba} × {off,on} + transformer off = 5配置 × 4超参 = 80组
for code in 600036.SH 601288.SH 601328.SH 601988.SH; do
  for hidden in 32 64; do
    for lr in 1e-3 5e-4; do
      run $code baseline off $hidden $lr
      run $code bimamba  off $hidden $lr
      run $code baseline on  $hidden $lr
      run $code bimamba  on  $hidden $lr
      run $code transformer off $hidden $lr
    done
  done
done

# B. 面板：{noattn, attn(nowd), noattn+vw, attn+vw(nowd), transformer} × 4超参 = 20组
for hidden in 32 64; do
  for lr in 1e-3 5e-4; do
    run_panel off off $hidden $lr
    run_panel on  off $hidden $lr
    run_panel off on  $hidden $lr
    run_panel on  on  $hidden $lr
    run_panel tf  off $hidden $lr
  done
done

echo "ALL DONE $(date '+%H:%M')" | tee -a $LOG
