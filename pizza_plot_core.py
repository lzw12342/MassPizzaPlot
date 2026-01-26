import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

def generate_pizza_plot(
        m_layers, n_blocks, layer_points, data,
        vmin, vmax, tick_count=9,figsize=(2, 2), dpi=64):
    if m_layers < 2 or n_blocks < 2:
        raise ValueError("层数和块数必须≥2")
    if data.shape != (m_layers, n_blocks):
        raise ValueError(f"数据维度需为{m_layers}×{n_blocks}，当前{data.shape}")

    layer_points = np.clip(np.array(layer_points), 0.01, 0.99).tolist()
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi, facecolor='white')
    ax.set_aspect('equal')
    ax.tick_params(
        axis='both', labelsize=8, direction='in', length=4,
        top=True, right=True, bottom=True, left=True,
        labelbottom=False, labelleft=False, labeltop=False, labelright=False
    )

    fig.canvas.draw()
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    plot_width = bbox.width * fig.dpi if bbox.width > 0 else figsize[0] * dpi
    plot_height = bbox.height * fig.dpi if bbox.height > 0 else figsize[1] * dpi
    r_max = min(plot_width, plot_height) * 0.45 / dpi

    all_points = np.array([0] + layer_points + [1.0]) * r_max
    r_inner = all_points[:-1]
    r_outer = all_points[1:]
    theta = np.linspace(0, 2 * np.pi, n_blocks + 1)[::-1]
    norm = plt.Normalize(vmin, vmax)
    patches = []

    for i in range(m_layers):
        for j in range(n_blocks):
            t = np.linspace(theta[j], theta[j + 1], 20)
            x_outer = r_outer[i] * np.cos(t)
            y_outer = r_outer[i] * np.sin(t)
            x_inner = r_inner[i] * np.cos(np.flip(t))
            y_inner = r_inner[i] * np.sin(np.flip(t))
            x = np.concatenate([x_outer, x_inner, [x_outer[0]]])
            y = np.concatenate([y_outer, y_inner, [y_outer[0]]])
            verts = np.column_stack([x, y])

            poly = Polygon(verts, facecolor=plt.cm.jet(norm(data[i, j])),
                           edgecolor='none', linewidth=0)
            ax.add_patch(poly)
            patches.append(poly)

    ax.set_xlim(-r_max, r_max)
    ax.set_ylim(-r_max, r_max)
    edge = np.linspace(-r_max, r_max, tick_count+2)
    tick_vals = edge[1:-1]
    ax.set_xticks(tick_vals)
    ax.set_yticks(tick_vals)

    def on_resize(event):
        nonlocal r_max
        fig.canvas.draw()
        bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        plot_width = bbox.width * fig.dpi if bbox.width > 0 else figsize[0] * dpi
        plot_height = bbox.height * fig.dpi if bbox.height > 0 else figsize[1] * dpi
        r_max = min(plot_width, plot_height) * 0.45 / dpi
        all_points = np.array([0] + layer_points + [1.0]) * r_max
        r_inner = all_points[:-1]
        r_outer = all_points[1:]
        for idx, p in enumerate(patches):
            i = idx // n_blocks
            j = idx % n_blocks
            t = np.linspace(theta[j], theta[j + 1], 20)
            x_outer = r_outer[i] * np.cos(t)
            y_outer = r_outer[i] * np.sin(t)
            x_inner = r_inner[i] * np.cos(np.flip(t))
            y_inner = r_inner[i] * np.sin(np.flip(t))
            x = np.concatenate([x_outer, x_inner, [x_outer[0]]])
            y = np.concatenate([y_outer, y_inner, [y_outer[0]]])
            p.set_xy(np.column_stack([x, y]))
        ax.set_xlim(-r_max, r_max)
        ax.set_ylim(-r_max, r_max)
        fig.canvas.draw()

    fig.canvas.mpl_connect('resize_event', on_resize)
    return fig, ax


def generate_colorbar(vmin, vmax, cb_font_size=10, cb_custom_ticks=[],
                      figsize=(5, 5),  # 预览界面常用尺寸
                      dpi=100):
    # 1. 创建居中布局的画布+轴
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi, facecolor='none')
    fig.patch.set_visible(False)
    ax.set_facecolor('none')
    # 强制轴居中（覆盖默认的边缘布局）
    ax.set_position([0.4, 0.1, 0.2, 0.8])  # [左, 下, 宽, 高]：让轴在画布中间

    norm = plt.Normalize(vmin, vmax)
    sm = plt.cm.ScalarMappable(cmap='jet', norm=norm)
    sm.set_array([])

    # 2. 色条居中显示（锚定在轴的中心）
    cb = fig.colorbar(
        sm, ax=ax, orientation='vertical',
        shrink=0.9,  # 色条占轴高度的90%（避免顶边/底边溢出）
        aspect=20,   # 调整色条长宽比（更修长，适配居中）
        pad=0.05,    # 色条与轴的边距（避免贴边）
        anchor=(0.5, 0.5)  # 色条锚定在轴的中心→整体居中
    )

    # 3. label对齐+防错位
    dynamic_pad = cb_font_size * 0.5  # 适配字体的label间距
    cb.ax.tick_params(
        labelsize=cb_font_size,
        direction='in',
        labelright=True,   # label显示在色条右侧
        labelleft=False,
        left=True,
        right=True,
        pad=dynamic_pad,   # label与色条的距离
        length=6,
        width=1.0
    )

    # 4. 强制自定义刻度+label精准对齐
    if cb_custom_ticks:
        cb.set_ticks(cb_custom_ticks)
        cb.ax.set_ylim(min(cb_custom_ticks), max(cb_custom_ticks))
        # label紧贴色条右侧，且与刻度线对齐
        cb.ax.set_yticklabels(
            [f'{tick:.2f}' for tick in cb_custom_ticks],
            ha='left',    # 让label的左侧贴紧色条右侧（避免错位）
            va='center',
            fontsize=cb_font_size,
            ma='left'
        )
        plt.setp(cb.ax.get_yticklabels(), rotation=0)

    # 隐藏冗余元素
    ax.axis('off')
    cb.outline.set_visible(False)
    cb.dividers.set_visible(False)

    # 强制居中布局
    fig.tight_layout(pad=0.5)  # 画布留边，避免内容溢出
    fig.canvas.draw()
    fig.canvas.flush_events()

    return fig, ax