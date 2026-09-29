"""训练与评估入口（多股票面板场景，模块二跨股票注意力）。

用法示例:
    python train_panel.py                          # 目录下全部股票 + 注意力（完整模型）
    python train_panel.py --no-attention           # 关掉模块二（消融对照）
    python train_panel.py --vol-weight             # 叠加模块三波动自适应损失
    python train_panel.py --codes 600036.SH 601288.SH 601328.SH 601988.SH  # 股票子集

输出:
    1. 终端打印面板统计与测试集指标（整体 + 逐股 MSE / MAE / R² / 方向准确率）
    2. results/ 下自动保存（答辩展示素材）:
       - panel_{tag}_h{horizon}_loss.png  训练损失与验证 MSE 收敛曲线
       - panel_{tag}_h{horizon}_attn.png  测试集平均注意力权重热力图（开题图 3-4 素材，
                                          仅注意力开启时生成）
"""

import argparse
import glob
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

from data import FEATURE_NAMES, load_panel_dataset
from models import PanelBiMamba, VolatilityAdaptiveLoss


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--dir', type=str, default='docs/csv', help='股票 CSV 所在目录')
    p.add_argument('--codes', type=str, nargs='+', default=None,
                   help='只用这些股票代码（如 600036.SH），默认目录下全部')
    p.add_argument('--horizon', type=int, default=1, help='预测期限：1=次日，5=未来5日')
    p.add_argument('--window', type=int, default=60, help='滑动窗口长度（交易日）')
    p.add_argument('--sample-start', type=str, default='2019-01-01', help='样本起始日')
    p.add_argument('--hidden', type=int, default=32, help='Mamba 模型维度 d_model')
    p.add_argument('--layer', type=int, default=2, help='Mamba 层数')
    p.add_argument('--epochs', type=int, default=100, help='最大训练轮数')
    p.add_argument('--bs', type=int, default=32, help='批量大小（按交易日批切）')
    p.add_argument('--lr', type=float, default=1e-3, help='学习率')
    p.add_argument('--wd', type=float, default=1e-4, help='L2 权重衰减')
    p.add_argument('--patience', type=int, default=15, help='早停耐心（验证 MSE 多少轮不降则停）')
    p.add_argument('--seed', type=int, default=1, help='随机种子（保证可复现）')
    p.add_argument('--no-attention', action='store_true',
                   help='关闭跨股票注意力（模块二消融对照，退化为逐股独立双向预测）')
    p.add_argument('--vol-weight', action='store_true', help='启用波动自适应损失加权（模块三）')
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
def predict(model: nn.Module, X: np.ndarray, device: torch.device, bs: int = 128,
            need_attn: bool = False):
    """批量推理。need_attn=True 时同时返回各批注意力权重拼接后的 (D, N, N) 数组。"""
    model.eval()
    preds, attns = [], []
    for i in range(0, len(X), bs):
        xb = torch.from_numpy(X[i:i + bs]).to(device)
        if need_attn:
            out, attn_w = model(xb, return_attn=True)
            attns.append(attn_w.cpu().numpy())
        else:
            out = model(xb)
        preds.append(out.cpu().numpy())
    pred = np.concatenate(preds)
    return (pred, np.concatenate(attns)) if need_attn else pred


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
    use_attn = not args.no_attention
    # 输出文件标签：区分 注意力开/关 × 预测期限，避免不同实验互相覆盖
    tag = f"{'attn' if use_attn else 'noattn'}_h{args.horizon}"

    # ---------- 数据 ----------
    csv_paths = sorted(glob.glob(os.path.join(args.dir, '*.csv')))
    if args.codes:
        wanted = set(args.codes)
        csv_paths = [p for p in csv_paths
                     if os.path.basename(p).replace('.csv', '') in wanted]
    if not csv_paths:
        raise FileNotFoundError(f'{args.dir} 下没有找到匹配的 CSV')
    ds = load_panel_dataset(csv_paths, window=args.window, horizon=args.horizon,
                            sample_start=args.sample_start)
    s = ds.stats
    print('=' * 66)
    print(f"面板: {s['n_stocks']} 只股票 {ds.codes} | 窗口 {args.window} 日 | "
          f"预测未来 {args.horizon} 日收益率 | 设备 {device}")
    print(f"共同交易日: {s['n_days']} = 训练 {s['n_train']} + 验证 {s['n_val']} + 测试 {s['n_test']}")
    print(f"训练段 {s['train_range'][0]} ~ {s['train_range'][1]} | "
          f"验证段 {s['val_range'][0]} ~ {s['val_range'][1]} | "
          f"测试段 {s['test_range'][0]} ~ {s['test_range'][1]}")
    print(f"模块二注意力: {'开' if use_attn else '关（消融对照）'} | "
          f"模块三波动加权: {'开' if args.vol_weight else '关'}")
    print('=' * 66)

    to_tensor = lambda a: torch.from_numpy(a)  # noqa: E731
    # 沿交易日维度批切：一个 batch = B 个交易日 × 全部 N 只股票
    train_loader = DataLoader(
        TensorDataset(to_tensor(ds.X_train), to_tensor(ds.y_train), to_tensor(ds.w_train)),
        batch_size=args.bs, shuffle=True,  # 仅训练集打乱；验证/测试保持时序
        generator=torch.Generator().manual_seed(args.seed),
    )

    # ---------- 模型 ----------
    model = PanelBiMamba(n_features=len(FEATURE_NAMES), d_model=args.hidden,
                         n_layers=args.layer, use_attention=use_attn).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f'模型: PanelBiMamba (attention={use_attn}) | 参数量: {n_params:,}')

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
            pred = model(xb)                        # (B_days, N)
            if args.vol_weight:
                loss = vol_loss(pred, yb, wb)       # 【模块三】高波动样本更高学习优先级
            else:
                loss = mse(pred, yb).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            n_batch = yb.numel()                    # 按"交易日×股票"计样本数
            epoch_loss += loss.item() * n_batch
            n_seen += n_batch
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

    # ---------- 测试（整体 + 逐股指标；注意力开启时顺便收集权重） ----------
    test_pred, test_attn = predict(model, ds.X_test, device, need_attn=use_attn)
    m = regression_metrics(ds.y_test.ravel(), test_pred.ravel())
    print('-' * 66)
    print(f'最优验证 MSE: {best_val:.6f}（模型选择只依据验证集，不用测试集调参）')
    print(f"测试集整体指标（{ds.y_test.size} 个样本 = {s['n_test']} 日 × {s['n_stocks']} 股）:")
    print(f"  MSE  {m['MSE']:.6f}")
    print(f"  RMSE {m['RMSE']:.6f}")
    print(f"  MAE  {m['MAE']:.6f}")
    print(f"  R2   {m['R2']:.4f}")
    print(f"  DA   {m['DA']:.4f}  (方向准确率)")

    # 逐股指标（模块二消融对比的证据粒度：哪些股票从注意力中受益）
    print('逐股测试指标:')
    print(f"  {'代码':<10} {'MSE':>10} {'R2':>8} {'DA':>8}")
    for i, code in enumerate(ds.codes):
        mi = regression_metrics(ds.y_test[:, i], test_pred[:, i])
        print(f"  {code:<10} {mi['MSE']:>10.6f} {mi['R2']:>8.4f} {mi['DA']:>8.4f}")
    print(f'训练耗时 {time.time() - t0:.1f}s')

    # ---------- 出图 1：训练收敛曲线 ----------
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(train_losses, label='Train loss')
    ax.plot(val_mses, label='Val MSE')
    ax.set_title(f'Panel training curve (attention={use_attn}, horizon={args.horizon})')
    ax.set_xlabel('Epoch')
    ax.set_yscale('log')
    ax.legend()
    fig.tight_layout()
    p1 = os.path.join(args.outdir, f'panel_{tag}_loss.png')
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    print(f'图片已保存: {p1}')

    # ---------- 出图 2：跨股票注意力权重热力图（开题图 3-4 素材） ----------
    # 测试集全部交易日的注意力权重取平均：行=查询股票，列=被关注股票
    if use_attn:
        attn_mean = test_attn.mean(axis=0)          # (N, N)
        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(attn_mean, cmap='viridis')
        ax.set_xticks(range(len(ds.codes)), ds.codes, rotation=45, ha='right')
        ax.set_yticks(range(len(ds.codes)), ds.codes)
        ax.set_xlabel('Key stock (attended to)')
        ax.set_ylabel('Query stock')
        ax.set_title(f'Cross-stock attention weights (test-set mean, horizon={args.horizon})')
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        # 每格标注数值，答辩时一目了然
        for i in range(len(ds.codes)):
            for j in range(len(ds.codes)):
                ax.text(j, i, f'{attn_mean[i, j]:.2f}', ha='center', va='center',
                        fontsize=7, color='w' if attn_mean[i, j] < attn_mean.max() * 0.7 else 'k')
        fig.tight_layout()
        p2 = os.path.join(args.outdir, f'panel_{tag}_attn.png')
        fig.savefig(p2, dpi=150)
        plt.close(fig)
        print(f'图片已保存: {p2}')


if __name__ == '__main__':
    main()
