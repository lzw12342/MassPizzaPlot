import numpy as np
import matplotlib.pyplot as plt
import pathlib
from datetime import datetime
from pizza_plot_core import generate_pizza_plot, generate_colorbar


class PizzaPlotLogic:
    def __init__(self):
        self.plot_items = {}
        self.global_data_min = 0
        self.global_data_max = 1
        self._refresh_hook = None
        self._rebuild_ui_hook = None

    # ---------- 钩子 ----------
    def set_refresh_hook(self, func):
        self._refresh_hook = func

    def set_rebuild_ui_hook(self, func):
        self._rebuild_ui_hook = func

    # ---------- 配置解析 ----------
    def parse_config(self, m_str, n_str, tick_str, custom_layer, layer_str,
                     cb_font_str, enable_custom_ticks, cb_tick_str):
        try:
            m = int(m_str)
            n = int(n_str)
            tick_count = int(tick_str)
            if m < 2 or n < 2:
                raise ValueError("层数/块数必须≥2！")
            if tick_count < 3:
                raise ValueError("刻度数量必须≥3！")

            layer_points = []
            if custom_layer:
                if not layer_str.strip():
                    raise ValueError("已启用自定义层区域，请输入值！")
                layer_points = [float(x) for x in layer_str.split(',')]
                if len(layer_points) != m - 1:
                    raise ValueError(f"需输入{m - 1}个层区域值！")
            else:
                layer_points = [i / m for i in range(1, m)]

            cb_font = int(cb_font_str.strip())
            cb_ticks = []
            if enable_custom_ticks and cb_tick_str.strip():
                cb_ticks = [float(x) for x in cb_tick_str.split(',')]

            return {
                "m_layers": m, "n_blocks": n, "layer_points": layer_points,
                "tick_count": tick_count, "cb_font_size": cb_font,
                "cb_custom_ticks": cb_ticks
            }
        except ValueError as e:
            raise ValueError(f"配置解析失败：{str(e)}")

    # ---------- 绘图项管理 ----------
    def create_plot_item(self, config):
        max_num = max((int(k.split('_')[1]) for k in self.plot_items), default=0)
        plot_id = f"plot_{max_num + 1}"
        m = config["m_layers"]
        n = config["n_blocks"]
        self.plot_items[plot_id] = {
            "config": config,
            "data": np.zeros((m, n)),
            "fig": None
        }
        self.update_global_min_max()
        return plot_id

    def delete_plot_item(self, plot_id):
        if plot_id not in self.plot_items:
            raise ValueError(f"绘图项{plot_id}不存在！")
        item = self.plot_items[plot_id]
        if item["fig"]:
            plt.close(item["fig"])

        del_num = int(plot_id.split('_')[1])
        del self.plot_items[plot_id]
        self.update_global_min_max()

        old_keys = sorted(self.plot_items, key=lambda k: int(k.split('_')[1]))
        for old_id in old_keys:
            cur_num = int(old_id.split('_')[1])
            if cur_num > del_num:
                new_id = f"plot_{cur_num - 1}"
                self.plot_items[new_id] = self.plot_items.pop(old_id)

        self.regenerate_all_plots()
        if self._refresh_hook:
            self._refresh_hook()
        if self._rebuild_ui_hook:
            self._rebuild_ui_hook()

    def delete_all_plots(self):
        for item in self.plot_items.values():
            if item["fig"]:
                plt.close(item["fig"])
        self.plot_items.clear()
        if self._refresh_hook:
            self._refresh_hook()
        if self._rebuild_ui_hook:
            self._rebuild_ui_hook()

    def update_plot_data(self, plot_id, new_data_str):
        if plot_id not in self.plot_items:
            raise ValueError(f"绘图项{plot_id}不存在！")
        item = self.plot_items[plot_id]
        m = item["config"]["m_layers"]
        n = item["config"]["n_blocks"]

        lines = new_data_str.strip().split('\n')
        data_rows = []
        for line_idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                raise ValueError(f"第{line_idx}行不能为空！")
            nums = [float(x.strip()) for x in line.split(',')]
            if len(nums) != n:
                raise ValueError(f"第{line_idx}行需输入{n}个值！")
            data_rows.append(nums)
        if len(data_rows) != m:
            raise ValueError(f"需输入{m}行数据！")

        item["data"] = np.array(data_rows)
        self.update_global_min_max()
        self.regenerate_all_plots()
        if self._refresh_hook:
            self._refresh_hook()

    # ---------- 绘图 ----------
    def generate_plot_fig(self, plot_id, cb_custom_ticks=[], is_preview=True):
        if plot_id not in self.plot_items:
            raise ValueError(f"绘图项{plot_id}不存在！")
        item = self.plot_items[plot_id]
        config = item["config"]
        raw_data = item["data"]  # 原始数据（不修改）
        
        # 步骤1：获取vmin/vmax（取消时回落全局数据范围）
        plot_vmin, plot_vmax = self._get_vmin_vmax_from_ticks(cb_custom_ticks)
        
        # 步骤2：仅启用自定义刻度时才钳位数据，取消时直接用原始数据
        if cb_custom_ticks:
            data_to_plot = self._clamp_data_to_range(raw_data, plot_vmin, plot_vmax)
        else:
            data_to_plot = raw_data  # 取消时用原始数据，不做任何钳位
        
        # 步骤3：传递数据给core层绘制
        fig, ax = generate_pizza_plot(
            m_layers=config["m_layers"],
            n_blocks=config["n_blocks"],
            layer_points=config["layer_points"],
            data=data_to_plot,  # 取消时为原始数据，启用时为钳位后数据
            vmin=plot_vmin,
            vmax=plot_vmax,
            tick_count=config["tick_count"],
            figsize=(2, 2) if is_preview else (7, 7),
            dpi=80 if is_preview else 100,
        )
        item["fig"] = fig
        return fig

    # 修正前：def regenerate_all_plots(self): （无参数）
    # 修正后：添加cb_custom_ticks参数，与UI层调用匹配
    def regenerate_all_plots(self, cb_custom_ticks=[]):
        """重绘所有图（接收自定义刻度参数，传递给generate_plot_fig）"""
        for plot_id in list(self.plot_items.keys()):
            self.generate_plot_fig(
                plot_id,
                cb_custom_ticks=cb_custom_ticks,  # 传递自定义刻度
                is_preview=True,
            )

    def generate_colorbar_fig(self, cb_font_size, cb_custom_ticks):
        fig, ax = generate_colorbar(
            vmin=self.global_data_min,
            vmax=self.global_data_max,
            cb_font_size=cb_font_size,
            cb_custom_ticks=cb_custom_ticks
        )
        return fig

    # ---------- 辅助 ----------
    def update_global_min_max(self):
        all_data = []
        for plot_id in self.plot_items:
            all_data.append(self.plot_items[plot_id]["data"].flatten())
        if all_data:
            combined_data = np.concatenate(all_data)
            self.global_data_min = combined_data.min()
            self.global_data_max = combined_data.max()
            if self.global_data_min == self.global_data_max:
                self.global_data_min = 0
                self.global_data_max = 1
        else:
            self.global_data_min = 0
            self.global_data_max = 1

    def get_plot_item(self, plot_id):
        if plot_id not in self.plot_items:
            raise ValueError(f"绘图项{plot_id}不存在！")
        return self.plot_items[plot_id].copy()

    def get_all_plot_ids(self):
        return list(self.plot_items.keys())

    def get_global_min_max(self):
        return self.global_data_min, self.global_data_max

    def get_plot_data_str(self, plot_id):
        if plot_id not in self.plot_items:
            raise ValueError(f"绘图项{plot_id}不存在！")
        data = self.plot_items[plot_id]["data"]
        return "\n".join([",".join(map(str, row)) for row in data])
    
    def _get_vmin_vmax_from_ticks(self, cb_custom_ticks):
        if cb_custom_ticks:
            unique_ticks = sorted(list(set(cb_custom_ticks)))
            vmin = unique_ticks[0]
            vmax = unique_ticks[-1]
        else:
            vmin = self.global_data_min
            vmax = self.global_data_max
        
        if vmin == vmax:
            vmin = 0
            vmax = 1
        
        return vmin, vmax

    def _clamp_data_to_range(self, data, vmin, vmax):
        return np.clip(data, vmin, vmax)
    
    def _get_export_dir(self):
        """生成当前目录下的时间戳导出目录（如：export_20240520_153045）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = pathlib.Path.cwd() / f"export_{timestamp}"
        export_dir.mkdir(parents=True, exist_ok=True)  # 自动创建目录，不存在则创建
        return export_dir

    def export_single_plot(self, plot_id, cb_custom_ticks=[]):
        """导出单张图到时间戳目录，文件名格式：plot{编号}_{时间戳}.png"""
        if plot_id not in self.plot_items:
            raise ValueError(f"绘图项{plot_id}不存在！")
        
        export_dir = self._get_export_dir()
        plot_num = plot_id.split('_')[1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        main_filename = f"plot{plot_num}_{timestamp}.png"
        main_path = export_dir / main_filename

        # 生成主图并保存
        fig = self.generate_plot_fig(
            plot_id, 
            cb_custom_ticks=cb_custom_ticks,
            is_preview=False, 
        )
        fig.savefig(
            main_path,
            dpi=300,
            bbox_inches='tight',
            pad_inches=0.1,
            transparent=True,  # 透明背景核心参数
            facecolor='none',  # 画布背景设为无
        )
        plt.close(fig)

        return main_path

    def export_all_plots(self, export_cb=False, cb_font_size=18, cb_custom_ticks=[]):
        """批量导出所有图到同一个时间戳目录"""
        if not self.plot_items:
            raise ValueError("没有可导出的绘图项！")
        
        export_dir = self._get_export_dir()
        export_paths = []

        # 导出所有图
        for plot_id in self.plot_items:
            plot_num = plot_id.split('_')[1]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            main_filename = f"plot{plot_num}_{timestamp}.png"
            main_path = export_dir / main_filename

            fig = self.generate_plot_fig(
                plot_id,
                cb_custom_ticks=cb_custom_ticks,
                is_preview=False,
            )
            fig.savefig(
                main_path,
                dpi=300,
                bbox_inches='tight',
                pad_inches=0.1,
                transparent=True,  # 透明背景核心参数
                facecolor='none',  # 画布背景设为无
            )
            plt.close(fig)
            export_paths.append(main_path)

            # 导出对应Colorbar
            if export_cb:
                cb_filename = f"colorbar_plot{plot_num}_{timestamp}.png"
                cb_path = export_dir / cb_filename
                self.export_colorbar(
                    cb_path,
                    cb_font_size=cb_font_size,
                    cb_custom_ticks=cb_custom_ticks
                )
                export_paths.append(cb_path)
        return export_paths, export_dir

    def export_colorbar(self, save_path, cb_font_size=18, cb_custom_ticks=[]):
        """保存Colorbar到指定路径（由_logic层自动生成路径，不再依赖UI选择）"""
        cb_vmin, cb_vmax = self._get_vmin_vmax_from_ticks(cb_custom_ticks)
        fig, ax = generate_colorbar(
            vmin=cb_vmin,
            vmax=cb_vmax,
            cb_font_size=cb_font_size,
            cb_custom_ticks=cb_custom_ticks
        )
        fig.savefig(
            save_path,
            dpi=300,
            bbox_inches='tight',
            pad_inches=0.1,
            facecolor='none',
            edgecolor='none'
        )
        plt.close(fig)
        return save_path
        