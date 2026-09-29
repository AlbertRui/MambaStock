"""数据管道：指标计算、平稳化特征、滑动窗口样本、时序切分、波动率分档。

对应开题报告 3.1.1 的技术约定，并保证严格的时序严谨性（答辩重点）：
1. 标签为未来 horizon 日累计对数收益率（基于 pre_close 逐日修正，除权除息日不产生假收益），
   输入窗口只包含 t 日及之前的特征 —— 从根本上避免"用今天预测今天"的标签穿越；
2. Z-score 标准化的均值/方差只在训练段上拟合，再应用到验证/测试段；
3. 样本严格按时间顺序切分 train/val/test，不打乱；
4. 技术指标在完整历史序列上计算（利用 2019 年之前的数据做预热），
   样本起点由 sample_start 控制，保证第一个样本的指标已经"熟透"。

数据替换说明：本文件只依赖 Tushare daily 格式的 CSV（与项目现有 4 个 CSV 同构），
后续 Tushare 新数据下载后（download.py 输出同格式），直接把路径换成新 CSV 即可。
"""

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

# 10 维特征（开题报告：OHLCV 5 维 + MA5/MA20 2 维 + RSI 1 维 + MACD 2 维）
FEATURE_NAMES = [
    'r_open', 'r_high', 'r_low', 'r_close', 'r_vol',   # 量价比值类 5 维
    'ma5_dev', 'ma20_dev', 'rsi14', 'dif', 'dea',       # 技术指标 5 维
]

# 波动率分档 -> 损失权重（开题报告 3.1.2(3)：低/中/高三档 -> 0.5 / 1.0 / 2.0）
VOL_WEIGHTS = (0.5, 1.0, 2.0)


def load_daily(csv_path: str) -> pd.DataFrame:
    """读取 Tushare daily 格式的 CSV，按交易日升序排列。"""
    df = pd.read_csv(csv_path, dtype={'trade_date': str})
    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    return df.sort_values('trade_date').reset_index(drop=True)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """构造平稳化特征。

    原始 OHLCV 是随价格水平漂移的非平稳序列，直接喂给模型容易过拟合。
    这里全部转换为"比值/差分"类平稳量：价格相对前收盘的对数变化、
    均线偏离度、RSI（天然有界）、MACD 除以价格消除量纲。
    """
    close, open_, high, low, vol = df['close'], df['open'], df['high'], df['low'], df['vol']
    prev_close = df['pre_close'].where(df['pre_close'] > 0, close.shift(1))  # 除权除息修正的昨收价（Tushare pre_close 列）
    prev_vol = vol.shift(1).replace(0, np.nan)  # 防停牌日成交量为 0 导致除零

    # 均线（注意：在完整历史上计算，早期行会有 NaN，后续统一剔除）
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()

    # RSI-14（Wilder 平滑，alpha=1/14 等价于 Wilder 定义）
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi14 = 100 - 100 / (1 + gain / loss)  # loss=0 -> RSI=100；两者皆 0 -> NaN -> 填 50（中性）
    rsi14 = rsi14.fillna(50.0)

    # MACD：DIF = EMA12 - EMA26，DEA = DIF 的 9 日 EMA；除以价格消除量纲
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()

    feats = pd.DataFrame({
        'r_open': np.log(open_ / prev_close),      # 今开相对昨收（隔夜跳空）
        'r_high': np.log(high / prev_close),       # 盘中最高相对昨收
        'r_low': np.log(low / prev_close),         # 盘中最低相对昨收
        'r_close': np.log(close / prev_close),     # 日对数收益率（核心量）
        'r_vol': np.log(vol / prev_vol),           # 成交量对数变化
        'ma5_dev': close / ma5 - 1,                # 相对 5 日均线偏离度
        'ma20_dev': close / ma20 - 1,              # 相对 20 日均线偏离度
        'rsi14': rsi14 / 100.0,                    # 归一化到 [0,1]
        'dif': dif / close,
        'dea': dea / close,
    }, index=df.index)
    return feats.replace([np.inf, -np.inf], np.nan)


def ewma_volatility(log_ret: pd.Series, span: int = 20) -> pd.Series:
    """EWMA 波动率：指数加权移动标准差（RiskMetrics 思路）。

    相比简单滚动标准差，近期样本权重更高，缓解波动率估计滞后（开题报告 3.3(4)）。
    """
    return log_ret.ewm(span=span, adjust=False).std()


@dataclass
class StockDataset:
    """单股票数据集容器：numpy 数组形式的窗口样本 + 元信息。"""
    X_train: np.ndarray  # (N_train, window, F) 标准化后的特征窗口
    y_train: np.ndarray  # (N_train,) 未来 horizon 日对数收益率
    w_train: np.ndarray  # (N_train,) 波动档位损失权重
    X_val: np.ndarray
    y_val: np.ndarray
    w_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    w_test: np.ndarray
    dates_test: np.ndarray   # 测试样本锚点日期（窗口最后一天），画图用
    close_test: np.ndarray   # 测试样本锚点日真实收盘价，用于价格还原展示
    stats: dict              # 数据集统计信息（中期报告素材）


def load_stock_dataset(csv_path: str, window: int = 60, horizon: int = 1,
                       sample_start: str = '2019-01-01',
                       train_ratio: float = 0.7, val_ratio: float = 0.15,
                       vol_span: int = 20) -> StockDataset:
    """从单个 CSV 构建无泄露的窗口数据集。

    参数:
        csv_path:     Tushare daily 格式 CSV 路径
        window:       滑动窗口长度（开题报告取 60 个交易日）
        horizon:      预测期限（1 = 次日收益率，5 = 未来 5 日累计收益率）
        sample_start: 样本起始日（此前历史仅用于指标预热，不构成样本）
    """
    df = load_daily(csv_path)
    feats = build_features(df)
    # 逐日对数收益率统一用 pre_close 口径（除权除息修正）：
    # 波动率估计与标签都基于它，避免除息假暴跌污染波动分档（模块三）
    prev_close_adj = df['pre_close'].where(df['pre_close'] > 0, df['close'].shift(1))
    log_ret = np.log(df['close'] / prev_close_adj)
    vol = ewma_volatility(log_ret, span=vol_span)

    # 剔除指标预热期的 NaN 行（ma20 需 20 天、EMA26 需约 26 天稳定等）
    valid = feats.notna().all(axis=1) & vol.notna()
    fv = feats[valid].to_numpy(np.float32)
    cv = df['close'][valid].to_numpy(np.float64)
    dv = df['trade_date'][valid].to_numpy()
    vv = vol[valid].to_numpy(np.float64)

    # 逐日修正收益率的累计和：标签 = 区间 (a, a+horizon] 内逐日收益率之和，
    # 这样 horizon>1 时落在窗口内部的除息日也被精确处理
    pv = df['pre_close'][valid].to_numpy(np.float64)
    pv = np.where(pv > 0, pv, np.r_[np.nan, cv[:-1]])  # 防御：缺失时回退原始前收盘
    lr = np.nan_to_num(np.log(cv / pv))  # 首行无前收（属预热段），置 0 防 cumsum 被污染
    lr_cum = np.concatenate(([0.0], np.cumsum(lr)))

    n = len(fv)
    # 锚点 a：窗口覆盖 [a-window+1, a]，标签覆盖 (a, a+horizon]
    # 因此 a 最大为 n-1-horizon，保证标签日也在历史内（特征与标签不重叠）
    anchors = np.arange(window - 1, n - horizon)
    if len(anchors) == 0:
        raise ValueError(f'{csv_path}: 有效历史 {n} 天不足以构成 window={window}, horizon={horizon} 的样本')

    X = np.stack([fv[a - window + 1:a + 1] for a in anchors])
    y = (lr_cum[anchors + horizon + 1] - lr_cum[anchors + 1]).astype(np.float32)
    anchor_dates = dv[anchors]
    anchor_close = cv[anchors]
    vol_anchor = vv[anchors]

    # 裁剪到样本区间（预热段只参与指标计算，不进入样本）
    keep = anchor_dates >= np.datetime64(sample_start)
    X = X[keep]
    y, anchor_dates = y[keep], anchor_dates[keep]
    anchor_close, vol_anchor = anchor_close[keep], vol_anchor[keep]

    # ---- 严格时序切分：前 70% 训练、中间 15% 验证、最后 15% 测试 ----
    n_all = len(X)
    n_train = int(n_all * train_ratio)
    n_val = int(n_all * val_ratio)
    tr = slice(0, n_train)
    va = slice(n_train, n_train + n_val)
    te = slice(n_train + n_val, n_all)

    # Z-score 标准化：均值/方差只在训练段拟合（防止验证/测试分布信息泄露到预处理）
    mu = X[tr].reshape(-1, X.shape[-1]).mean(axis=0)
    sd = X[tr].reshape(-1, X.shape[-1]).std(axis=0)
    sd[sd == 0] = 1.0  # 防除零
    X = ((X - mu) / sd).astype(np.float32)

    # 波动率分档：阈值取训练段波动率的 1/3、2/3 分位数（同理只用训练段定档）
    q1, q2 = np.quantile(vol_anchor[tr], [1 / 3, 2 / 3])
    bucket = np.digitize(vol_anchor, [q1, q2])  # 0=低波动 1=中波动 2=高波动
    w = np.array(VOL_WEIGHTS, dtype=np.float32)[bucket]

    # 数据集统计（写中期报告"已完成工作"直接用）
    stats = {
        'n_samples': n_all,
        'n_train': n_train, 'n_val': n_val, 'n_test': n_all - n_train - n_val,
        'train_range': (str(anchor_dates[tr][0])[:10], str(anchor_dates[tr][-1])[:10]),
        'val_range': (str(anchor_dates[va][0])[:10], str(anchor_dates[va][-1])[:10]),
        'test_range': (str(anchor_dates[te][0])[:10], str(anchor_dates[te][-1])[:10]),
        'up_ratio_train': float((y[tr] > 0).mean()),       # 训练段上涨样本占比
        'vol_quantiles': (float(q1), float(q2)),           # 低/中/高分档阈值
        'vol_bucket_dist': [int((bucket == i).sum()) for i in range(3)],
    }

    return StockDataset(
        X_train=X[tr], y_train=y[tr], w_train=w[tr],
        X_val=X[va], y_val=y[va], w_val=w[va],
        X_test=X[te], y_test=y[te], w_test=w[te],
        dates_test=anchor_dates[te],
        close_test=anchor_close[te],
        stats=stats,
    )


# ---------------------------------------------------------------------------
# 多股票面板数据（模块二：跨股票注意力的输入形态）
# ---------------------------------------------------------------------------

@dataclass
class PanelDataset:
    """多股票面板数据集：同一交易日多只股票的窗口样本对齐。

    X 形状 (D, N, L, F)：D=交易日数，N=股票数，L=窗口长度，F=特征维数。
    一个样本 = 一个交易日 × 全部 N 只股票的窗口切片；y/w 形状 (D, N)。
    """
    X_train: np.ndarray
    y_train: np.ndarray  # (D, N) 各股票未来 horizon 日累计对数收益率
    w_train: np.ndarray  # (D, N) 各股票波动档位权重
    X_val: np.ndarray
    y_val: np.ndarray
    w_val: np.ndarray
    X_test: np.ndarray
    y_test: np.ndarray
    w_test: np.ndarray
    dates_test: np.ndarray
    codes: list          # 股票代码（顺序与 N 维一致）
    stats: dict


def load_panel_dataset(csv_paths: list, window: int = 60, horizon: int = 1,
                       sample_start: str = '2019-01-01',
                       train_ratio: float = 0.7, val_ratio: float = 0.15,
                       vol_span: int = 20) -> PanelDataset:
    """构建多股票面板数据集。

    与单股票管线（load_stock_dataset）完全同一口径：pre_close 修正标签、
    时序切分、Z-score 与波动分档阈值均只用各股票自己的训练段拟合。

    差异：先对每只股票独立构建窗口样本，再按交易日取交集对齐 ——
    只有全部股票都有数据的交易日才进入面板（停牌缺口自然剔除）。
    """
    per_stock = []
    for path in csv_paths:
        df = load_daily(path)
        feats = build_features(df)
        prev_close_adj = df['pre_close'].where(df['pre_close'] > 0, df['close'].shift(1))
        log_ret = np.log(df['close'] / prev_close_adj)
        vol = ewma_volatility(log_ret, span=vol_span)
        valid = feats.notna().all(axis=1) & vol.notna()
        fv = feats[valid].to_numpy(np.float32)
        cv = df['close'][valid].to_numpy(np.float64)
        dv = df['trade_date'][valid].to_numpy()
        vv = vol[valid].to_numpy(np.float64)
        # 逐日修正收益率累计和 -> 标签（与单股票版同一公式）
        pv = df['pre_close'][valid].to_numpy(np.float64)
        pv = np.where(pv > 0, pv, np.r_[np.nan, cv[:-1]])
        lr = np.nan_to_num(np.log(cv / pv))
        lr_cum = np.concatenate(([0.0], np.cumsum(lr)))
        n = len(fv)
        anchors = np.arange(window - 1, n - horizon)
        X = np.stack([fv[a - window + 1:a + 1] for a in anchors])
        y = (lr_cum[anchors + horizon + 1] - lr_cum[anchors + 1]).astype(np.float32)
        per_stock.append({'dates': dv[anchors], 'X': X, 'y': y, 'vol': vv[anchors]})

    # 交易日对齐：所有股票锚点日期的交集，再裁剪到样本区间
    common = per_stock[0]['dates']
    for s in per_stock[1:]:
        common = np.intersect1d(common, s['dates'])
    common = common[common >= np.datetime64(sample_start)]
    if len(common) == 0:
        raise ValueError('面板对齐后无共同交易日，请检查各股票数据区间')

    # 收集成面板数组
    N = len(per_stock)
    Xs, ys, vs = [], [], []
    for s in per_stock:
        idx = {d: i for i, d in enumerate(s['dates'])}
        rows = [idx[d] for d in common]
        Xs.append(s['X'][rows])   # (D, L, F)
        ys.append(s['y'][rows])   # (D,)
        vs.append(s['vol'][rows])
    X = np.stack(Xs, axis=1)      # (D, N, L, F)
    y = np.stack(ys, axis=1)      # (D, N)
    vol = np.stack(vs, axis=1)    # (D, N)

    # 时序切分（按交易日，所有股票共享同一切分点）
    D = len(common)
    n_train, n_val = int(D * train_ratio), int(D * val_ratio)
    tr = slice(0, n_train)
    va = slice(n_train, n_train + n_val)
    te = slice(n_train + n_val, D)

    # 每股独立 Z-score（只用训练段统计量，防泄露）
    mu = X[tr].mean(axis=(0, 2), keepdims=True)          # (1, N, 1, F)
    sd = X[tr].std(axis=(0, 2), keepdims=True)
    sd[sd == 0] = 1.0
    X = ((X - mu) / sd).astype(np.float32)

    # 每股独立波动分档（阈值用各自训练段分位数，防泄露）
    w = np.empty_like(y)
    for i in range(N):
        q1, q2 = np.quantile(vol[tr, i], [1 / 3, 2 / 3])
        w[:, i] = np.array(VOL_WEIGHTS, dtype=np.float32)[np.digitize(vol[:, i], [q1, q2])]

    codes = [os.path.basename(p).replace('.csv', '') for p in csv_paths]
    stats = {
        'n_stocks': N, 'n_days': D,
        'n_train': n_train, 'n_val': n_val, 'n_test': D - n_train - n_val,
        'train_range': (str(common[tr][0])[:10], str(common[tr][-1])[:10]),
        'val_range': (str(common[va][0])[:10], str(common[va][-1])[:10]),
        'test_range': (str(common[te][0])[:10], str(common[te][-1])[:10]),
    }
    return PanelDataset(X[tr], y[tr], w[tr], X[va], y[va], w[va],
                        X[te], y[te], w[te], common[te], codes, stats)
