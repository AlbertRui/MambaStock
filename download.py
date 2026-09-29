"""沪深300成分股数据批量下载脚本（Tushare Pro）。

用途：Tushare Token 申请下来之后，批量下载成分股日频行情 + 每日指标，
输出与项目现有 CSV 完全同构的文件，train.py 无需任何改动即可切换新数据。

用法:
    # Token 三选一：命令行 --token / 环境变量 TUSHARE_TOKEN / 项目根目录 .env 文件
    python download.py --token 你的token --outdir data/csi300
    python download.py --codes 600036.SH 601288.SH        # 只下指定股票（先小测）
    python download.py --skip-existing                    # 断点续下（默认开启）

注意:
    - 下载区间默认 2018-06-01 ~ 2025-12-31：多出的半年用于技术指标预热，
      实际样本区间由 train.py 的 --sample-start 2019-01-01 裁剪
    - index_weight 接口需要一定积分权限；若权限不足，先用 --codes 手动指定名单
    - 接口限流：每次调用间隔 sleep，300 只约需十几分钟
"""

import argparse
import os
import time

import pandas as pd

# 输出 CSV 的列与顺序，和项目现有 4 个 CSV 保持一致（train.py/data.py 直接兼容）
OUT_COLUMNS = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close',
               'change', 'pct_chg', 'vol', 'amount',
               'turnover_rate', 'volume_ratio', 'pe', 'pb', 'ps',
               'total_share', 'float_share', 'free_share', 'total_mv', 'circ_mv']


def get_token(args) -> str:
    """Token 优先级：命令行 > 环境变量 > .env 文件。"""
    if args.token:
        return args.token
    if os.environ.get('TUSHARE_TOKEN'):
        return os.environ['TUSHARE_TOKEN']
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        for line in open(env_path, encoding='utf-8'):
            if line.strip().startswith('TUSHARE_TOKEN='):
                return line.strip().split('=', 1)[1]
    raise SystemExit('未找到 Tushare Token：请用 --token 传入，或写入 .env 的 TUSHARE_TOKEN=...')


def get_constituents(pro, args) -> list:
    """获取沪深300成分股名单。积分不足时提示改用 --codes 手动指定。"""
    if args.codes:
        return args.codes
    try:
        # 取最近一个交易日的成分权重表作为当前名单
        df = pro.index_weight(index_code='399300.SZ', start_date=args.end, end_date=args.end)
        if df.empty:  # 末日非交易日时往前多取几天
            df = pro.index_weight(index_code='399300.SZ')
        latest = df['trade_date'].max()
        codes = sorted(df[df['trade_date'] == latest]['con_code'].unique().tolist())
        print(f'沪深300成分股名单（{latest}）: {len(codes)} 只')
        return codes
    except Exception as e:  # 权限/积分不足时给出明确指引，而不是报栈
        raise SystemExit(f'获取成分股名单失败: {e}\n'
                         f'若因积分不足，可用 --codes 600036.SH 601288.SH ... 手动指定股票下载')


_basic_warned = False   # 降级提示只打印一次，避免批量下载时刷屏
_basic_interval = 0     # 触发限流后记住的调用间隔（低积分档 daily_basic 约 1 次/分钟）


def _fetch_daily_basic(pro, ts_code: str, start: str, end: str) -> pd.DataFrame:
    """带限流重试的 daily_basic 调用。

    低积分档限流约 1 次/分钟：触发频率限制后等待 65 秒重试（最多 3 次），
    并记住该间隔，后续调用前 preemptively 等待，避免反复撞限流。
    """
    global _basic_interval
    fields = ('ts_code,trade_date,turnover_rate,volume_ratio,pe,pb,ps,'
              'total_share,float_share,free_share,total_mv,circ_mv')
    for _ in range(3):
        if _basic_interval:
            time.sleep(_basic_interval)
        try:
            return pro.daily_basic(ts_code=ts_code, start_date=start, end_date=end, fields=fields)
        except Exception as e:
            if '频率' in str(e) or '频次' in str(e):
                _basic_interval = 65
                continue
            raise  # 非限流错误（如权限不足）直接抛给上层降级逻辑
    raise RuntimeError(f'{ts_code} daily_basic 多次限流重试仍失败')


def download_one(pro, ts_code: str, start: str, end: str, outdir: str) -> str:
    """下载单只股票的日行情 + 每日指标，合并存为 CSV。返回保存路径。

    daily 接口需 120 积分；daily_basic 需 2000 积分，权限不足时自动降级：
    相应列填 NaN 但保持 CSV 列结构一致 —— 本项目特征（data.py）只用 OHLCV，
    降级不影响训练。
    """
    global _basic_warned
    daily = pro.daily(ts_code=ts_code, start_date=start, end_date=end)
    time.sleep(args_sleep)  # 限流
    df = daily
    try:
        basic = _fetch_daily_basic(pro, ts_code, start, end)
        df = pd.merge(daily, basic.drop(columns=['ts_code']), on='trade_date', how='left')
    except Exception as e:
        # 降级：daily_basic 的列全部置 NaN（列名保留，保持 CSV 结构一致）
        for col in OUT_COLUMNS:
            if col not in df.columns:
                df[col] = float('nan')
        if not _basic_warned:
            print(f'  提示: daily_basic 不可用（{e}），相关列置空，不影响训练（后续股票同）')
            _basic_warned = True
    df = df.sort_values('trade_date')  # 升序，与现有 CSV 一致
    out_path = os.path.join(outdir, f'{ts_code}.csv')
    df[OUT_COLUMNS].to_csv(out_path, index=False)
    return out_path


args_sleep = 0.4  # 接口调用间隔（秒），Tushare 限流保护


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token', type=str, default=None, help='Tushare Pro Token')
    ap.add_argument('--outdir', type=str, default='docs/csv', help='CSV 输出目录')
    ap.add_argument('--start', type=str, default='20180601', help='下载起始日（含指标预热段）')
    ap.add_argument('--end', type=str, default='20251231', help='下载截止日')
    ap.add_argument('--codes', type=str, nargs='+', default=None, help='手动指定股票代码列表')
    ap.add_argument('--skip-existing', action='store_true', default=True, help='跳过已存在文件（断点续下）')
    ap.add_argument('--force', action='store_false', dest='skip_existing', help='强制覆盖重下已存在的文件')
    args = ap.parse_args()

    import tushare as ts  # 延迟导入：没装 tushare 时不影响项目其他部分
    pro = ts.pro_api(get_token(args))
    os.makedirs(args.outdir, exist_ok=True)

    codes = get_constituents(pro, args)
    print(f'计划下载 {len(codes)} 只 -> {args.outdir}/')

    n_ok, n_fail = 0, 0
    for i, code in enumerate(codes, 1):
        out_path = os.path.join(args.outdir, f'{code}.csv')
        if args.skip_existing and os.path.exists(out_path):
            print(f'[{i}/{len(codes)}] {code} 已存在，跳过')
            n_ok += 1
            continue
        try:
            download_one(pro, code, args.start, args.end, args.outdir)
            n_ok += 1
            print(f'[{i}/{len(codes)}] {code} 完成')
        except Exception as e:
            n_fail += 1
            print(f'[{i}/{len(codes)}] {code} 失败: {e}')  # 单只失败不中断整体
        time.sleep(args_sleep)

    print(f'下载结束：成功 {n_ok}，失败 {n_fail}。失败的重跑一次本脚本即可（自动跳过已完成）。')


if __name__ == '__main__':
    main()
