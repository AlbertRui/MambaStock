"""模型定义：基线与 Bi-Mamba-Stock 三大创新模块。

本文件结构与开题报告"2.3 主要研究内容"一一对应：

  ┌─────────────────────────────────────────────────────────────┐
  │ MambaBaseline            单向 Mamba 基线（MambaStock 修正版）│
  ├─────────────────────────────────────────────────────────────┤
  │ 【模块一】BidirectionalMamba      双向选择性扫描 + 门控融合  │
  │          对应开题 2.3(1)：双向选择性扫描机制的股价序列编码   │
  ├─────────────────────────────────────────────────────────────┤
  │ 【模块二】CrossStockAttention     轻量化跨股票注意力         │
  │          对应开题 2.3(2)：市场隐含关联的轻量动态建模         │
  ├─────────────────────────────────────────────────────    │
  │          对应开题 2.3(3)：波动自适应训练策略                 │
  │          （EWMA 波动率与分档在 data.py 中完成，此处为损失）  │
  ├─────────────────────────────────────────────────────────────┤
  │ BiMambaStock             模块一组装的单股票核心模型          │
  └─────────────────────────────────────────────────────────────┘

设计原则：三个模块独立可插拔 —— 消融实验 = 逐个移除再对比（开题第 6 个────────┤
  │ 【模块三】VolatilityAdaptiveLoss  波动率分档加权损失     月计划）。
"""

import torch
import torch.nn as nn

from mamba import Mamba, MambaConfig


class MambaBaseline(nn.Module):
    """单向 Mamba 股价预测基线（窗口化修正版 MambaStock）。

    模型结构与 MambaStock 一致，仅修正了训练方式（滑窗 + 标签 shift + 标准化）。
    输入: (B, L, F)，B=批量，L=窗口长度（60），F=特征维数（10）
    输出: (B,)，未来 horizon 日对数收益率的预测值
    """

    def __init__(self, n_features: int, d_model: int = 16, n_layers: int = 2):
        super().__init__()
        self.in_proj = nn.Linear(n_features, d_model)      # 特征维 -> 模型维
        self.encoder = Mamba(MambaConfig(d_model=d_model, n_layers=n_layers))
        self.head = nn.Linear(d_model, 1)                  # 最后时刻隐态 -> 标量预测

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.encoder(self.in_proj(x))          # (B, L, D)
        # Mamba 因果扫描：最后时刻隐态只聚合 t 日及之前的信息，符合预测因果性
        return self.head(h[:, -1]).squeeze(-1)     # (B,)


# ---------------------------------------------------------------------------
# 【模块一】双向选择性扫描 + 可学习门控融合（开题 2.3(1)、3.1.2(1)）
# ---------------------------------------------------------------------------
class BidirectionalMamba(nn.Module):
    """双向选择性状态空间编码器。

    结构（对应开题图 3-2）：
      - forward_mamba:  沿时间正序扫描，捕捉历史趋势与惯性
      - backward_mamba: 沿时间逆序扫描，捕捉窗口内的回溯上下文
      - gate:           门控权重由当前输入特征经线性变换 + Sigmoid 生成，
                        对双路隐态做自适应加权融合（开题原文机制）

    时序严谨性说明（答辩高频问题）：
      后向路径的扫描范围仍是 [t-L+1, t] 的历史窗口内部，
      不涉及 t 日之后的任何数据 —— 双向 ≠ 穿越，与 Bi-Mamba+ 处理方式一致。

    计算量：双向仅比单向多一倍扫描，整体仍保持近线性复杂度（开题 3.1.2(1)）。

    输入: (B, L, D)    输出: (B, L, D)
    """

    def __init__(self, d_model: int, n_layers: int = 2):
        super().__init__()
        self.forward_mamba = Mamba(MambaConfig(d_model=d_model, n_layers=n_layers))
        self.backward_mamba = Mamba(MambaConfig(d_model=d_model, n_layers=n_layers))
        self.gate = nn.Linear(d_model, d_model)  # 门控：当前输入特征 -> [0,1] 权重

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h_f = self.forward_mamba(x)                        # (B, L, D) 前向
        h_b = self.backward_mamba(x.flip(1)).flip(1)       # (B, L, D) 后向（时间维翻转进出）
        g = torch.sigmoid(self.gate(x))                    # (B, L, D) 逐位置门控权重
        return g * h_f + (1 - g) * h_b                     # 自适应加权融合


# ---------------------------------------------------------------------------
# 【模块二】轻量化跨股票缩放点积注意力（开题 2.3(2)、3.1.2(2)）
# ---------------------------------------------------------------------------
class CrossStockAttention(nn.Module):
    """跨股票注意力模块（对应开题图 3-3）。

    将每只股票的隐态视为 Q/K/V，通过缩放点积动态计算股票间相似度权重，
    对 Value 加权聚合 —— 不依赖预定义图结构，替代 SAMBA 等工作的图卷积。

    轻量化手段（开题 3.1.2(2)）：默认单头注意力，参数量仅 3 个 D×D 投影矩阵，
    计算为一次 N×N 矩阵乘（N=板块内股票数，小规模验证场景下开销可忽略）。

    输入: (B, N, D)，N=股票数
    输出: (聚合特征 (B, N, D), 注意力权重 (B, N, N))
          —— 注意力权重单独返回，用于绘制开题图 3-4 的权重热力图（答辩展示素材）
    """

    def __init__(self, d_model: int):
        super().__init__()
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)

    def forward(self, h: torch.Tensor):
        q, k, v = self.q_proj(h), self.k_proj(h), self.v_proj(h)
        d_k = q.size(-1)
        # 缩放点积：softmax(QK^T / sqrt(d_k)) V
        attn = torch.softmax(q @ k.transpose(-2, -1) / d_k ** 0.5, dim=-1)  # (B, N, N)
        return attn @ v, attn


# ---------------------------------------------------------------------------
# 【模块三】波动自适应损失（开题 2.3(3)、3.1.2(3)）
# ---------------------------------------------------------------------------
class VolatilityAdaptiveLoss(nn.Module):
    """波动率分档加权损失：L = Σ_i w_i · l_i / Σ_i w_i。

    样本权重 w_i ∈ {0.5, 1.0, 2.0}（低/中/高波动档），
    由 data.py 基于 EWMA 波动率 + 训练段分位数预先计算（防泄露），
    高波动样本获得更高学习优先级（开题公式 3.x 的实现）。
    """

    def forward(self, pred: torch.Tensor, target: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
        per_sample = (pred - target) ** 2          # 逐样本 MSE，可无缝换成 MAE（开题原文）
        return (weight * per_sample).sum() / weight.sum()


# ---------------------------------------------------------------------------
# 组装：Bi-Mamba-Stock 单股票核心模型（模块一）
# ---------------------------------------------------------------------------
class BiMambaStock(nn.Module):
    """Bi-Mamba-Stock（单股票场景）：特征投影 -> 双向编码 -> 最后时刻隐态 -> 预测头。

    与 MambaBaseline 的唯一区别是编码器换成【模块一】BidirectionalMamba，
    保证"单向 vs 双向"对比实验的控制变量纯净（消融实验的对照设计）。
    多股票场景（模块二接入）在单股票实验完成后扩展。

    输入: (B, L, F)    输出: (B,)
    """

    def __init__(self, n_features: int, d_model: int = 16, n_layers: int = 2):
        super().__init__()
        self.in_proj = nn.Linear(n_features, d_model)
        self.encoder = BidirectionalMamba(d_model=d_model, n_layers=n_layers)
        self.head = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.encoder(self.in_proj(x))          # (B, L, D)
        return self.head(h[:, -1]).squeeze(-1)     # (B,)


# ---------------------------------------------------------------------------
# 组装：多股票联合预测模型（模块一 + 模块二 + 门控融合，开题 3.1.3）
# ---------------------------------------------------------------------------
class PanelBiMamba(nn.Module):
    """Bi-Mamba-Stock 多股票联合预测模型。

    前向流程（对应开题图 3-1 的特征融合与预测输出层）：
      1) 每只股票独立经【模块一】双向 Mamba 编码，取最后时刻隐态 (B, N, D)
      2) 【模块二】跨股票注意力聚合板块联动信息 -> (B, N, D)
      3) 可学习门控对时序特征与关联特征自适应加权融合（开题 3.1.3 原文机制）
      4) 共享预测头逐股输出 -> (B, N)

    use_attention=False 时跳过模块二，退化为逐股独立双向预测（消融对照用）。

    输入: (B, N, L, F)  输出: (B, N)
    return_attn=True 时附带返回注意力权重 (B, N, N)
    —— 即开题图 3-4 跨股票注意力权重热力图的数据来源。
    """

    def __init__(self, n_features: int, d_model: int = 32, n_layers: int = 2,
                 use_attention: bool = True):
        super().__init__()
        self.use_attention = use_attention
        self.in_proj = nn.Linear(n_features, d_model)
        self.encoder = BidirectionalMamba(d_model=d_model, n_layers=n_layers)
        self.attn = CrossStockAttention(d_model)
        self.fuse_gate = nn.Linear(d_model, d_model)  # 开题 3.1.3 门控融合
        self.head = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor, return_attn: bool = False):
        B, N, L, F = x.shape
        # 批次维与股票维合并，逐股独立编码
        h = self.in_proj(x.reshape(B * N, L, F))
        h = self.encoder(h)[:, -1].reshape(B, N, -1)   # (B, N, D)
        attn_w = None
        if self.use_attention:
            a, attn_w = self.attn(h)                    # (B, N, D), (B, N, N)
            g = torch.sigmoid(self.fuse_gate(h))        # 门控权重
            h = g * h + (1 - g) * a                     # 时序/关联特征自适应融合
        out = self.head(h).squeeze(-1)                  # (B, N)
        return (out, attn_w) if return_attn else out
