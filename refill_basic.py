"""daily_basic 列补全工具（限流友好版）。

背景：低积分档 daily_basic 限流苛刻（约 1 次/分钟且窗口不稳定），
批量下载时容易触发降级导致整列置空。本脚本以"每只间隔 75 秒、
多轮循环、超时自动退出"的耐心策略，逐只补齐 docs/csv 中
turnover_rate 列为空的 CSV。可随时中断重跑（已补齐的自动跳过）。

用法: python refill_basic.py
"""

import glob
import os
import time
from argparse import Namespace

import pandas as pd

from download import get_token  # 复用 download.py 的 Token 读取逻辑

CSV_DIR = 'docs/csv'
INTERVAL = 75        # 两次尝试之间的间隔（秒），避开限流窗口
MAX_MINUTES = 45     # 最长运行时间，到点退出，可再次运行继续


def incomplete_files() -> list:
    """返回 turnover_rate 列全空的 CSV 路径列表。"""
    files = []
    for path in sorted(glob.glob(os.path.join(CSV_DIR, '*.csv'))):
        df = pd.read_csv(path, usecols=['turnover_rate'])
        if df['turnover_rate'].isna().all():
            files.append(path)
    return files


def refill_one(pro, path: str):
    """为单个 CSV 补齐 daily_basic 列（原地更新，保持原列顺序）。"""
    code = os.path.basename(path).replace('.csv', '')
    basic = pro.daily_basic(ts_code=code, start_date='20180601', end_date='20251231',
                            fields='ts_code,trade_date,turnover_rate,volume_ratio,pe,pb,ps,'
                                   'total_share,float_share,free_share,total_mv,circ_mv')
    df = pd.read_csv(path, dtype={'trade_date': str})
    orig_cols = df.columns.tolist()
    # 先丢掉旧的空列再合并，避免产生 _x/_y 后缀列
    df = df.drop(columns=[c for c in basic.columns if c in df.columns and c != 'trade_date'])
    df = df.merge(basic.drop(columns=['ts_code']), on='trade_date', how='left')
    df = df.reindex(columns=orig_cols)
    df.to_csv(path, index=False)


def main():
    import tushare as ts  # 延迟导入，不影响项目其他部分
    pro = ts.pro_api(get_token(Namespace(token=None)))
    deadline = time.time() + MAX_MINUTES * 60

    round_no = 0
    while time.time() < deadline:
        todo = incomplete_files()
        if not todo:
            print('全部 CSV 的 daily_basic 列已补齐。')
            return
        round_no += 1
        print(f'第 {round_no} 轮：待补 {len(todo)} 只 -> {[os.path.basename(p) for p in todo]}')
        for path in todo:
            if time.time() > deadline:
                break
            try:
                refill_one(pro, path)
                print(f'  {os.path.basename(path)} 补齐成功')
            except Exception as e:
                print(f'  {os.path.basename(path)} 本轮失败: {e}')
            time.sleep(INTERVAL)

    print('达到时间上限，可再次运行本脚本继续（已补齐的不会重复下载）。')


if __name__ == '__main__':
    main()
