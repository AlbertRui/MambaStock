#!/bin/bash
# v3 调参网格·并行版：按子集分工，4 进程同卡并行（模型仅约4.6万参数，GPU 远未占满）
# 用法: PY=python3 LOG=results/log_v3_x.txt bash run_tuning_v3_par.sh <a|b|c|d>
#   a=601288  b=601328  c=601988  d=面板8股
# 断点续跑：某配置在 $LOG 中已有完整结果块（含 DA 行）则跳过
SUBSET=$1
PY=${PY:-.venv/Scripts/python.exe}
LOG=${LOG:-results/experiment_log_v3_tuning.txt}
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

run_panel() { # $1=attn(on/off/tf) $2=vw(on/off) $3=hidden $4=lr
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

run_stock() { # $1=code：5配置 × 4超参 = 20组
  for hidden in 32 64; do
    for lr in 1e-3 5e-4; do
      run $1 baseline off $hidden $lr
      run $1 bimamba  off $hidden $lr
      run $1 baseline on  $hidden $lr
      run $1 bimamba  on  $hidden $lr
      run $1 transformer off $hidden $lr
    done
  done
}

case $SUBSET in
  a) run_stock 601288.SH ;;
  b) run_stock 601328.SH ;;
  c) run_stock 601988.SH ;;
  d) for hidden in 32 64; do
       for lr in 1e-3 5e-4; do
         run_panel off off $hidden $lr
         run_panel on  off $hidden $lr
         run_panel off on  $hidden $lr
         run_panel on  on  $hidden $lr
         run_panel tf  off $hidden $lr
       done
     done ;;
  *) echo "unknown subset: $SUBSET"; exit 1 ;;
esac

echo "ALL DONE $SUBSET $(date '+%H:%M')" | tee -a $LOG
