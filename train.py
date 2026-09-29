"""训练与评估入口（单股票场景）。

用法示例:
    python train.py --csv 600036.SH.csv                     # 基线（单向 Mamba）
    python train.py --csv 600036.SH.csv --vol-weight        # 开启波动自适应损失
    python train.py --csv 600036.SH.csv --horizon 5         # 预测未来 5 日收益率

输出:
    1. 终端打印数据集统计与测试集指标（MSE / RMSE / MAE / R² / 方向准确率）
    2. results/ 下自动保存两张图（答辩展示素材）:
       - {股票}_price.png  测试段真实次日收盘价 vs 模型一步预测价格
       - {stock}_loss.png   训练损失与验证 MSE 收敛曲线
"""

import argparse
import os
import time

import matplotlib
matplotlib.use('Agg')  # 无界面环境下也能出图（服务器/AutoDL 适用）
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch.utils.data import DataLoader, TensorDataset

from data import FEATURE_NAMES, load_stock_dataset
from models import BiMambaStock, MambaBaseline, VolatilityAdaptiveLoss

# 可选模型注册表：baseline=单向基线，bimamba=模块一双向模型（后续扩展多股票）
MODELS = {'baseline': MambaBaseline, 'bimamba': BiMambaStock}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', type=str, default='docs/csv/600036.SH.csv', help='股票数据 CSV 路径')
    p.add_argument('--horizon', type=int, default=1, help='预测期限：1=次日，5=未来5日')
    p.add_argument('--window', type=int, default=60, help='滑动窗口长度（交易日）')
    p.add_argument('--sample-start', type=str, default='2019-01-01', help='样本起始日')
    p.add_argument('--model', type=str, default='baseline', choices=list(MODELS),
                   help='模型：baseline=单向Mamba基线，bimamba=模块一双向模型')
    p.add_argument('--hidden', type=int, default=16, help='Mamba 模型维度 d_model')
    p.add_argument('--layer', type=int, default=2, help='Mamba 层数')
    p.add_argument('--epochs', type=int, default=100, help='最大训练轮数')
    p.add_argument('--bs', type=int, default=32, help='批量大小')
    p.add_argument('--lr', type=float, default=1e-3, help='学习率')
    p.add_argument('--wd', type=float, default=1e-5, help='L2 权重衰减')
    p.add_argument('--patience', type=int, default=15, help='早停耐心（验证 MSE 多少轮不降则停）')
    p.add_argument('--seed', type=int, default=1, help='随机种子（保证可复现）')
    p.add_argument('--vol-weight', action='store_true', help='启用波动自适应损失加权')
    p.add_argument('--outdir', type=str, default='results', help='结果图片输出目录')
    return p.parse_args()


def set_seed(seed: int):
    """固定全部随机源，保证同参数下结果可复现（论文实验的基本要求）。"""
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """方向准确率：预测涨跌方向与实际一致的比例（金融预测的关键指标）。"""
    return float((np.sign(y_true) == np.sign(y_pred)).mean())


@torch.no_grad()
def predict(model: nn.Module, X: np.ndarray, device: torch.device, bs: int = 256) -> np.ndarray:
    """批量推理，返回 numpy 预测序列。"""
    model.eval()
    preds = []
    for i in range(0, len(X), bs):
        xb = torch.from_numpy(X[i:i + bs]).to(device)
        preds.append(model(xb).cpu().numpy())
    return np.concatenate(preds)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """回归指标全集：MSE / RMSE / MAE / R² / 方向准确率。"""
    mse = mean_squared_error(y_true, y_pred)
    return {
        'MSE': mse,
        'RMSE': float(np.sqrt(mse)),
        'MAE': mean_absolute_error(y_true, y_pred),
        'R2': r2_score(y_true, y_pred),
        'DA': directional_accuracy(y_true, y_pred),
    }


def main():
    args = parse_args()
    set_seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    os.makedirs(args.outdir, exist_ok=True)
    stock = os.path.basename(args.csv).split('.')[0]  # 股票代码，用于命名输出文件

    # ---------- 数据 ----------
    ds = load_stock_dataset(args.csv, window=args.window, horizon=args.horizon,
                            sample_start=args.sample_start)
    s = ds.stats
    print('=' * 60)
    print(f'股票 {stock} | 窗口 {args.window} 日 | 预测未来 {args.horizon} 日收益率 | 设备 {device}')
    print(f"样本: 总 {s['n_samples']} = 训练 {s['n_train']} + 验证 {s['n_val']} + 测试 {s['n_test']}")
    print(f"训练段 {s['train_range'][0]} ~ {s['train_range'][1]} | "
          f"验证段 {s['val_range'][0]} ~ {s['val_range'][1]} | "
          f"测试段 {s['test_range'][0]} ~ {s['test_range'][1]}")
    print(f"训练段上涨样本占比 {s['up_ratio_train']:.3f} | "
          f"波动分档阈值 {s['vol_quantiles'][0]:.5f}/{s['vol_quantiles'][1]:.5f} | "
          f"低/中/高样本数 {s['vol_bucket_dist']}")
    print('=' * 60)

    to_tensor = lambda a: torch.from_numpy(a)  # noqa: E731
    train_loader = DataLoader(
        TensorDataset(to_tensor(ds.X_train), to_tensor(ds.y_train), to_tensor(ds.w_train)),
        batch_size=args.bs, shuffle=True,  # 仅训练集打乱；验证/测试保持时序
        generator=torch.Generator().manual_seed(args.seed),
    )

    # ---------- 模型 ----------
    model = MODELS[args.model](n_features=len(FEATURE_NAMES),
                               d_model=args.hidden, n_layers=args.layer).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f'模型: {args.model} | 参数量: {n_params:,}')

    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.wd)
    mse = nn.MSELoss(reduction='none')  # 逐样本损失，便于做波动加权
    vol_loss = VolatilityAdaptiveLoss()  # 【模块三】波动自适应损失

    # ---------- 训练（验证集早停 + 最优权重回滚） ----------
    best_val = float('inf')
    best_state = None
    bad_epochs = 0
    train_losses, val_mses = [], []
    t0 = time.time()

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss, n_seen = 0.0, 0
        for xb, yb, wb in train_loader:
            xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
            pred = model(xb)
            per_sample = mse(pred, yb)
            if args.vol_weight:
                loss = vol_loss(pred, yb, wb)  # 【模块三】高波动样本获得更高学习优先级
            else:
                loss = per_sample.mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            epoch_loss += loss.item() * len(xb)
            n_seen += len(xb)
        train_losses.append(epoch_loss / n_seen)

        # 验证集 MSE（始终不加权，作为统一的早停标准）
        val_pred = predict(model, ds.X_val, device)
        val_mse = mean_squared_error(ds.y_val, val_pred)
        val_mses.append(val_mse)

        if val_mse < best_val - 1e-8:
            best_val = val_mse
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= args.patience:
                print(f'早停于第 {epoch} 轮（验证 MSE 连续 {args.patience} 轮未改善）')
                break

        if epoch % 10 == 0:
            print(f'Epoch {epoch:3d} | train loss {train_losses[-1]:.6f} | val MSE {val_mse:.6f}')

    # 回滚到验证集表现最好的权重（早停的标准做法，防止后期过拟合污染评估）
    if best_state is not None:
        model.load_state_dict(best_state)

    # ---------- 测试 ----------
    test_pred = predict(model, ds.X_test, device)
    m = regression_metrics(ds.y_test, test_pred)
    print('-' * 60)
    print(f'最优验证 MSE: {best_val:.6f}（模型选择只依据验证集，不用测试集调参）')
    print(f'测试集指标（{len(ds.y_test)} 个样本）:')
    print(f"  MSE  {m['MSE']:.6f}")
    print(f"  RMSE {m['RMSE']:.6f}")
    print(f"  MAE  {m['MAE']:.6f}")
    print(f"  R2   {m['R2']:.4f}")
    print(f"  DA   {m['DA']:.4f}  (方向准确率)")
    print(f'训练耗时 {time.time() - t0:.1f}s')

    # ---------- 出图 1：价格还原对比（最直观的答辩展示图） ----------
    # 用锚点日真实收盘价 * exp(预测/真实对数收益率) 还原"次日收盘价"，
    # 一步预测语义，不使用递归外推，方法上站得住
    true_price = ds.close_test * np.exp(ds.y_test)
    pred_price = ds.close_test * np.exp(test_pred)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ds.dates_test, true_price, label='True close (t+1)', linewidth=1.2)
    ax.plot(ds.dates_test, pred_price, label='Predicted close (t+1)', linewidth=1.2, alpha=0.85)
    ax.set_title(f'{stock} next-day close prediction (horizon={args.horizon})')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.legend()
    fig.tight_layout()
    p1 = os.path.join(args.outdir, f'{stock}_price.png')
    fig.savefig(p1, dpi=150)
    plt.close(fig)

    # ---------- 出图 2：训练收敛曲线 ----------
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(train_losses, label='Train loss')
    ax.plot(val_mses, label='Val MSE')
    ax.set_title(f'{stock} training curve')
    ax.set_xlabel('Epoch')
    ax.set_yscale('log')
    ax.legend()
    fig.tight_layout()
    p2 = os.path.join(args.outdir, f'{stock}_loss.png')
    fig.savefig(p2, dpi=150)
    plt.close(fig)

    print(f'图片已保存: {p1} , {p2}')


if __name__ == '__main__':
    main()
