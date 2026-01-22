import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
from pizza_plot_logic import PizzaPlotLogic


class PizzaPlotUI:
    def __init__(self, root):
        self.root = root
        self.root.title("披萨云图绘制工具")
        self.root.geometry("1200x700")

        self.logic = PizzaPlotLogic()
        self.plot_item_frames = {}
        self._preview_canvas = {}
        self.export_cb_with_plot = tk.BooleanVar(value=False)

        

        self.logic.set_refresh_hook(self._rebuild_ui_list)
        self.logic.set_rebuild_ui_hook(self._rebuild_ui_list)

        # 仅初始化勾选框状态变量（无输入框变量）
        self.enable_custom_ticks_var = tk.BooleanVar(value=False)
        # 跟踪上次有效刻度配置
        self.last_valid_tick_config = (False, [])

        self.last_valid_layer_config = [] 

        self._init_layout()

        self._update_default_layer_config()
        self._update_layer_display()  # 同时更新显示标签

        self.root.protocol("WM_DELETE_WINDOW", self._on_app_close)

    # -------------------- 布局 --------------------
    def _init_layout(self):
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill='x', side='top')

        tab_frame = ttk.Frame(top_frame)
        tab_frame.pack(side='left', fill='both', expand=True)
        notebook = ttk.Notebook(tab_frame)
        notebook.pack(fill='x', expand=True)
        self.cloud_tab = ttk.Frame(notebook, padding="10")
        self.cb_tab = ttk.Frame(notebook, padding="10")
        notebook.add(self.cloud_tab, text="云图设置")
        notebook.add(self.cb_tab, text="Colorbar设置")
        self._init_cloud_tab_layout()
        self._init_cb_tab_layout()

        log_frame = ttk.LabelFrame(top_frame, text="日志")
        log_frame.pack(side='right', fill='both', expand=True, padx=10, pady=5)
        self.log_text = tk.Text(log_frame, width=40, height=10, state='disabled', wrap='word')
        self.log_text.pack(fill='both', expand=True)

        # 操作按钮行：grid 一行
        op_row = ttk.Frame(self.root, padding="10")
        op_row.pack(fill='x', side='top')

        self.export_cb_check = ttk.Checkbutton(op_row, text="同时导出Colorbar",
                                               variable=self.export_cb_with_plot)
        self.export_cb_check.grid(row=0, column=0, sticky='w', padx=(0, 10))

        col = 1
        ttk.Button(op_row, text="创建云图项",
                   command=self._on_create_plot_click).grid(row=0, column=col, padx=2); col += 1
        ttk.Button(op_row, text="预览Colorbar",
                   command=self._on_preview_cb_click).grid(row=0, column=col, padx=2); col += 1
        ttk.Button(op_row, text="导出Colorbar",
                   command=self._on_export_cb_click).grid(row=0, column=col, padx=2); col += 1
        self.delete_all_btn = ttk.Button(op_row, text="删除所有",
                                         command=self._on_delete_all_click)
        self.delete_all_btn.grid(row=0, column=col, padx=2); col += 1
        self.export_all_btn = ttk.Button(op_row, text="导出所有",
                                         command=self._on_export_all_click)
        self.export_all_btn.grid(row=0, column=col, padx=2); col += 1

        op_row.grid_columnconfigure(0, weight=0)
        op_row.grid_columnconfigure(col, weight=1)

        self._update_btn_states()

        list_frame = ttk.LabelFrame(self.root, text="绘制列表", padding="10")
        list_frame.pack(fill='both', expand=True, pady=5)

        self.list_canvas = tk.Canvas(list_frame)
        self.list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=self.list_scrollbar.set)
        self.list_scrollbar.pack(side='right', fill='y')
        self.list_canvas.pack(side='left', fill='both', expand=True)

        self.list_content_frame = ttk.Frame(self.list_canvas)
        self.list_canvas.create_window((0, 0), window=self.list_content_frame, anchor="nw")
        self.list_content_frame.bind("<Configure>",
                                     lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))

    def _init_cloud_tab_layout(self):
        row = 0
        # 层数、块数相关布局（保持不变）
        ttk.Label(self.cloud_tab, text="层数(m)：").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.current_m = tk.StringVar(value="3")
        self.m_label = ttk.Label(self.cloud_tab, textvariable=self.current_m)
        self.m_label.grid(row=row, column=1, padx=5, pady=5)
        self.modify_m_btn = ttk.Button(self.cloud_tab, text="修改", command=self._on_modify_m_click)
        self.modify_m_btn.grid(row=row, column=2, padx=5, pady=5)
        ttk.Label(self.cloud_tab, text="块数(n)：").grid(row=row, column=3, sticky='w', padx=5, pady=5)
        self.current_n = tk.StringVar(value="6")
        self.n_label = ttk.Label(self.cloud_tab, textvariable=self.current_n)
        self.n_label.grid(row=row, column=4, padx=5, pady=5)
        self.modify_n_btn = ttk.Button(self.cloud_tab, text="修改", command=self._on_modify_n_click)
        self.modify_n_btn.grid(row=row, column=5, padx=5, pady=5)
        
        row += 1
        # 启用自定义层区域勾选框
        self.custom_layer_var = tk.BooleanVar(value=False)
        self.custom_layer_check = ttk.Checkbutton(
            self.cloud_tab, text="启用自定义层区域", variable=self.custom_layer_var,
            command=self._toggle_layer_entry
        )
        self.custom_layer_check.grid(row=row, column=0, sticky='w', padx=5, pady=5)
        # 修改按钮
        self.modify_layer_btn = ttk.Button(self.cloud_tab, text="修改", command=self._on_modify_layer_click,state='disabled')
        self.modify_layer_btn.grid(row=row, column=1, padx=5, pady=5)
        
        # 👇 新增：层区域显示Label（和自定义刻度显示逻辑完全一致）
        self.layer_display_label = ttk.Label(
            self.cloud_tab,
            font=("微软雅黑", 9),
            relief="sunken",  # 和刻度显示框保持相同样式（凹陷）
            width=20
        )
        self.layer_display_label.grid(row=row, column=2, padx=10, pady=5, sticky='w')
        
        row += 1
        # 刻度数量相关布局（保持不变）
        ttk.Label(self.cloud_tab, text="刻度数量：").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.tick_entry = ttk.Entry(self.cloud_tab, width=10)
        self.tick_entry.insert(0, "9")
        self.tick_entry.grid(row=row, column=1, padx=5, pady=5)

    def _init_cb_tab_layout(self):
        """初始化Colorbar标签页布局（完全匹配需求：勾选框+刻度显示+修改按钮同一行）"""
        # 核心：用一个Frame包裹同一行的所有组件，强制同行
        main_frame = ttk.Frame(self.cb_tab)
        main_frame.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        # Frame内所有组件都用 row=0，不同column，实现同一行排列
        col = 0  # Frame内的列号
        
        # 1. 启用自定义刻度勾选框（column=0）
        self.enable_custom_ticks_check = ttk.Checkbutton(
            main_frame, 
            text="启用自定义刻度", 
            variable=self.enable_custom_ticks_var,
            command=self._on_tick_change
        )
        self.enable_custom_ticks_check.grid(row=0, column=col, sticky='w', padx=0, pady=0)
        col += 1
        
        # 2. 当前自定义刻度：标签 + 显示框（column=1）
        ttk.Label(main_frame, text="当前自定义刻度：", font=("微软雅黑", 9)).grid(
            row=0, column=col, sticky='w', padx=10, pady=0
        )
        col += 1
        self.current_ticks_label = ttk.Label(
            main_frame,
            font=("微软雅黑", 9),
            width=15,
            state='readonly'
        )
        # 初始化显示内容（直接设置text，无需state切换）
        self.current_ticks_label.grid(row=0, column=col, sticky='w', padx=5, pady=0)
        col += 1
        
        # 3. 修改自定义刻度按钮（column=2）
        self.tick_modify_btn = ttk.Button(
            main_frame, 
            text="修改自定义刻度", 
            command=self._on_tick_modify_click, 
            state='disabled'
        )
        self.tick_modify_btn.grid(row=0, column=col, sticky='w', padx=10, pady=0)
        col += 1

        # 下一行：Colorbar字体大小（row=1）
        row = 1
        ttk.Label(self.cb_tab, text="Colorbar字体大小：").grid(row=row, column=0, sticky='w', padx=5, pady=5)
        self.cb_font_entry = ttk.Entry(self.cb_tab, width=10)
        self.cb_font_entry.insert(0, "10")
        self.cb_font_entry.grid(row=row, column=1, padx=5, pady=5)

    # -------------------- 事件 --------------------
    def _on_create_plot_click(self):
        try:
            # 获取自定义刻度字符串（从上次有效配置中获取）
            cb_tick_str = ""
            if self.enable_custom_ticks_var.get():
                cb_ticks = self.last_valid_tick_config[1]
                cb_tick_str = ",".join(map(str, cb_ticks)) if cb_ticks else ""

            layer_str = ""
            if self.custom_layer_var.get():
                layer_str = ",".join(map(str, self.last_valid_layer_config))
            else:
                # 未启用时也传递均分值（确保新图初始状态正确）
                m = int(self.current_m.get())
                default_layers = [i / m for i in range(1, m)]
                layer_str = ",".join(map(str, default_layers))
            
            config = self.logic.parse_config(
                m_str=self.current_m.get(),
                n_str=self.current_n.get(),
                tick_str=self.tick_entry.get().strip(),
                custom_layer=self.custom_layer_var.get(),
                layer_str=layer_str,
                cb_font_str=self.cb_font_entry.get().strip(),
                enable_custom_ticks=self.enable_custom_ticks_var.get(),
                cb_tick_str=cb_tick_str  # 使用上面生成的刻度字符串
            )
            plot_id = self.logic.create_plot_item(config)
            plot_num = plot_id.split('_')[1]
            item = self.logic.get_plot_item(plot_id)
            self._log(f"添加图{plot_num}（{item['config']['m_layers']}层×{item['config']['n_blocks']}块）")
            self._rebuild_ui_list()
            self._update_btn_states()
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self._log(f"创建失败：{str(e)}")

    def _on_modify_m_click(self):
        def confirm():
            try:
                old_m = int(self.current_m.get())
                new_m = int(entry.get().strip())
                if new_m < 2:
                    raise ValueError("层数需≥2")
                
                if new_m != old_m:
                    self.current_m.set(str(new_m))
                    self._log(f"层数修改为{new_m}")
                    
                    # ✅ 自动生成新的默认配置（不删除用户历史配置）
                    self._update_default_layer_config()
                    
                    # 如果当前启用了自定义，提示用户配置已更新
                    if self.custom_layer_var.get():
                        self._log(f"自定义层区域已自动更新：{self.last_valid_layer_config}")
                    
                    self.logic.delete_all_plots()
                    self._rebuild_ui_list()
                    self._update_layer_display()
                win.destroy()
            except ValueError as e:
                if "层数需≥2" in str(e):
                    messagebox.showerror("错误", str(e))
                else:
                    messagebox.showerror("错误", "请输入有效整数（≥2）")
        
        win = tk.Toplevel(self.root)
        win.title("修改层数")
        win.geometry("200x125")
        win.resizable(False, False)
        ttk.Label(win, text="请输入层数（≥2）：").pack(pady=10)
        entry = ttk.Entry(win, width=10)
        entry.insert(0, self.current_m.get())
        entry.pack(pady=5)
        ttk.Button(win, text="确认", command=confirm).pack(pady=5)

    def _on_modify_n_click(self):
        def confirm():
            try:
                # 1. 获取修改前的旧块数（关键：用于对比）
                old_n = int(self.current_n.get())
                # 2. 获取新输入的块数并校验
                new_n = int(entry.get().strip())
                if new_n < 3:
                    raise ValueError("块数需≥3")
                
                # 3. 仅当数值真正变化时，才更新并清空自定义层显示
                if new_n != old_n:
                    self.current_n.set(str(new_n))
                    self._log(f"块数修改为{new_n}")
                    self.logic.delete_all_plots()
                    self._rebuild_ui_list()
                    # 👇 仅数值变化时清空
                win.destroy()
            except ValueError as e:
                if "块数需≥3" in str(e):
                    messagebox.showerror("错误", str(e))
                else:
                    messagebox.showerror("错误", "请输入有效整数（≥3）")
        
        win = tk.Toplevel(self.root)
        win.title("修改块数")
        win.geometry("200x125")
        win.resizable(False, False)
        ttk.Label(win, text="请输入块数（≥3）：").pack(pady=10)
        entry = ttk.Entry(win, width=10)
        entry.insert(0, self.current_n.get())
        entry.pack(pady=5)
        ttk.Button(win, text="确认", command=confirm).pack(pady=5)

    def _clear_all_plot_items_ui(self):
        for frame in self.plot_item_frames.values():
            frame.destroy()
        self.plot_item_frames.clear()
        self._preview_canvas.clear()

    def _on_modify_layer_click(self):
        """修改层区域（层数≥2都允许）"""
        m = int(self.current_m.get())
        win = tk.Toplevel(self.root)
        win.title("修改层区域")
        # ✅ 根据层数动态调整窗口大小
        win.geometry("350x140" if m > 3 else "300x125")
        win.resizable(False, False)
        
        # ✅ 动态提示文本
        ttk.Label(win, text=f"请输入{m-1}个0~1之间的分界点（英文逗号分隔）：").pack(pady=10)
        
        ent = ttk.Entry(win, width=30)
        # ✅ 始终填充当前配置（默认或上次输入）
        ent.insert(0, ",".join([f"{x:.3f}" for x in self.last_valid_layer_config]))
        ent.pack(pady=5)
        
        def confirm():
            try:
                vals = [float(x.strip()) for x in ent.get().split(',')]
                if len(vals) != m - 1:
                    raise ValueError(f"数量错误")
                
                # 验证范围
                if not all(0 <= v <= 1 for v in vals):
                    raise ValueError("范围错误")
                
                # 验证单调递增
                if not all(vals[i] < vals[i+1] for i in range(len(vals)-1)):
                    raise ValueError("非递增")
                
                # ✅ 保存新配置
                self.last_valid_layer_config = vals
                self._log(f"层区域更新：{vals}")
                
                # 如果当前启用了自定义，立即应用
                if self.custom_layer_var.get():
                    for pid in list(self.logic.plot_items.keys()):
                        self.logic.plot_items[pid]['config']['layer_points'] = vals
                    self.logic.regenerate_all_plots()
                    self._rebuild_ui_list()
                
                self._update_layer_display()
                win.destroy()
                
            except ValueError as e:
                if "数量错误" in str(e):
                    messagebox.showerror("错误", f"需要输入{m-1}个数字！")
                elif "范围错误" in str(e):
                    messagebox.showerror("错误", "所有数值必须在0~1之间！")
                elif "非递增" in str(e):
                    messagebox.showerror("错误", "数值必须严格递增！")
                else:
                    messagebox.showerror("错误", "请输入有效的数字！")
        
        ttk.Button(win, text="确认", command=confirm).pack(pady=5)

    def _on_set_data_click(self, plot_id):
        try:
            item = self.logic.get_plot_item(plot_id)
            m = item["config"]["m_layers"]
            n = item["config"]["n_blocks"]
            plot_num = plot_id.split('_')[1]
            current_data_str = self.logic.get_plot_data_str(plot_id)

            data_win = tk.Toplevel(self.root)
            data_win.title(f"设置图{plot_num}数据")
            data_win.geometry("600x500")
            data_win.transient(self.root)

            btn_bar = ttk.Frame(data_win)
            btn_bar.pack(fill='x', pady=5)
            ttk.Button(btn_bar, text="按列输入",
                       command=lambda: self._open_column_matrix_input(data_win, m, n, target_text)).pack(side='left', padx=5)
            ttk.Label(btn_bar, text=f"输入{m}行，每行{n}个数值（逗号分隔）：").pack(side='left', padx=5)

            target_text = tk.Text(data_win, width=70, height=15)
            target_text.pack(pady=5, fill='both', expand=True, padx=10)
            target_text.insert('end', current_data_str)

            def confirm():
                try:
                    self.logic.update_plot_data(plot_id, target_text.get('1.0', 'end'))
                    self._rebuild_ui_list()
                    self._log(f"图{plot_num}数据已更新")
                    data_win.destroy()
                except ValueError as e:
                    messagebox.showerror("错误", str(e))
                    self._log(f"设置数据失败：{str(e)}")

            ttk.Button(data_win, text="确认", command=confirm).pack(side='left', padx=10, pady=10)
            ttk.Button(data_win, text="取消", command=data_win.destroy).pack(side='left', padx=10, pady=10)
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self._log(f"打开数据窗口失败：{str(e)}")

    def _open_column_matrix_input(self, parent, m, n, target_text):
        total = m * n
        col_win = tk.Toplevel(parent)
        col_win.title("按列输入 - 矩阵生成器")
        col_win.geometry("350x500")
        col_win.transient(parent)

        ttk.Label(col_win,
                  text=f"连续输入 {total} 行（每行一个数）→ 按 {n} 行切成 {m} 段",
                  font=("微软雅黑", 9)).pack(pady=5, anchor='w')

        text_frame = ttk.Frame(col_win)
        text_frame.pack(fill='both', expand=True, padx=10, pady=5)
        scroll = ttk.Scrollbar(text_frame, orient='vertical')
        text = tk.Text(text_frame, width=25, height=18, yscrollcommand=scroll.set, font=("微软雅黑", 9))
        scroll.config(command=text.yview)
        scroll.pack(side='right', fill='y')
        text.pack(side='left', fill='both', expand=True)

        btn_frame = ttk.Frame(col_win)
        btn_frame.pack(side='bottom', fill='x', pady=5)
        ttk.Button(btn_frame, text="生成并编辑矩阵",
                   command=lambda: self._generate_matrix_from_text(text, m, n, target_text, col_win))\
            .pack(side='left', padx=10)
        ttk.Button(btn_frame, text="取消", command=col_win.destroy).pack(side='left', padx=10)

    def _generate_matrix_from_text(self, text, m, n, target_text, col_win):
        lines = text.get('1.0', 'end').strip().splitlines()
        total = m * n
        if len(lines) != total:
            messagebox.showerror("错误", f"需要输入{total}行！")
            return
        try:
            nums = [float(x.strip()) for x in lines]
        except ValueError:
            messagebox.showerror("错误", "请输入合法数字！")
            return

        mat = np.array(nums).reshape(m, n)
        data_str = '\n'.join([','.join(map(str, row)) for row in mat])
        target_text.delete('1.0', 'end')
        target_text.insert('1.0', data_str)
        col_win.destroy()

    def _open_matrix_editor(self, parent, mat, target_text):
        m, n = mat.shape
        edit_win = tk.Toplevel(parent)
        edit_win.title("矩阵编辑器")
        edit_win.geometry("500x400")
        edit_win.transient(parent)

        entries = []
        frm = ttk.Frame(edit_win)
        frm.pack(pady=10)
        for i in range(m):
            row = []
            for j in range(n):
                e = ttk.Entry(frm, width=8)
                e.grid(row=i, column=j, padx=2, pady=2)
                e.insert(0, str(mat[i, j]))
                row.append(e)
            entries.append(row)

        def apply():
            try:
                new_mat = np.zeros((m, n))
                for i in range(m):
                    for j in range(n):
                        new_mat[i, j] = float(entries[i][j].get())
                data_str = '\n'.join([','.join(map(str, row)) for row in new_mat])
                target_text.delete('1.0', 'end')
                target_text.insert('1.0', data_str)
                edit_win.destroy()
                parent.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入合法数字！")

        ttk.Button(edit_win, text="应用", command=apply).pack(pady=5)
        ttk.Button(edit_win, text="取消", command=edit_win.destroy).pack(pady=5)

    def _on_preview_cb_click(self):
        try:
            cb_font = int(self.cb_font_entry.get().strip())
            cb_ticks = self.last_valid_tick_config[1] if self.enable_custom_ticks_var.get() else []
            fig = self.logic.generate_colorbar_fig(cb_font, cb_ticks)
            
            cb_win = tk.Toplevel(self.root)
            cb_win.title("Colorbar预览")
            cb_win.geometry("500x500")
            cb_win.transient(self.root)
            
            canvas = FigureCanvasTkAgg(fig, master=cb_win)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill='both', expand=True)

            def close_win():
                try:
                    # ✅ 正确的清理顺序：
                    canvas_widget.destroy()
                    canvas.figure = None
                    plt.close(fig)
                    cb_win.destroy()
                except Exception as e:
                    print(f"关闭Colorbar窗口时出错: {e}")
                    cb_win.destroy()
            
            ttk.Button(cb_win, text="关闭", command=close_win).pack(pady=10)
            cb_win.protocol("WM_DELETE_WINDOW", close_win)
            
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self._log(f"预览Colorbar失败：{str(e)}")

    # ✅ 补回：预览按钮 → 弹窗大图
    def _on_preview_click(self, plot_id):
        try:
            cb_ticks = self.last_valid_tick_config[1] if self.enable_custom_ticks_var.get() else []
            fig = self.logic.generate_plot_fig(plot_id, cb_custom_ticks=cb_ticks, is_preview=False)
            
            preview_win = tk.Toplevel(self.root)
            preview_win.title(f"图{plot_id.split('_')[1]} 预览")
            preview_win.geometry("600x600")
            preview_win.transient(self.root)

            canvas = FigureCanvasTkAgg(fig, master=preview_win)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill='both', expand=True)

            def close_win():
                try:
                    # ✅ 正确的清理顺序：
                    # 1. 先销毁 Tkinter Canvas 组件
                    canvas_widget.destroy()
                    
                    # 2. 断开 canvas 与 figure 的引用（这应在 plt.close 之前或之后都可以，但必须在 canvas 销毁后）
                    canvas.figure = None
                    
                    # 3. 关闭 matplotlib figure（触发关闭事件）
                    plt.close(fig)
                    
                    # 4. 最后关闭窗口
                    preview_win.destroy()
                except Exception as e:
                    print(f"关闭窗口时出错: {e}")
                    preview_win.destroy()
            
            ttk.Button(preview_win, text="关闭", command=close_win).pack(pady=10)
            preview_win.protocol("WM_DELETE_WINDOW", close_win)
            
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self._log(f"预览失败：{str(e)}")

    def _on_export_single_click(self, plot_id):
        try:
            # 从last_valid_tick_config获取刻度
            cb_ticks = self.last_valid_tick_config[1] if self.enable_custom_ticks_var.get() else []
            main_path = self.logic.export_single_plot(plot_id, cb_ticks)
            self._log(f"导出至：{main_path}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self._log(f"导出失败：{str(e)}")

    def _on_export_all_click(self):
        try:
            cb_font = int(self.cb_font_entry.get().strip())
            # 从last_valid_tick_config获取刻度
            cb_ticks = self.last_valid_tick_config[1] if self.enable_custom_ticks_var.get() else []
            export_paths, export_dir = self.logic.export_all_plots(self.export_cb_with_plot.get(),
                                                                cb_font, cb_ticks)
            self._log(f"批量导出完成，共导出{len(export_paths)}个文件，位于：\n{export_dir.absolute()}")
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self._log(f"批量导出失败：{str(e)}")

    def _on_export_cb_click(self):
        """导出Colorbar到时间戳目录，文件名：colorbar_时间戳.png"""
        try:
            enable_custom = self.enable_custom_ticks_var.get()
            cb_ticks = self.last_valid_tick_config[1] if enable_custom else []
            cb_font = int(self.cb_font_entry.get().strip() or 18)
            
            # 生成时间戳文件名和路径（无需用户选择）
            export_dir = self.logic._get_export_dir()  # 获取自动生成的目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cb_filename = f"colorbar_{timestamp}.png"
            save_path = export_dir / cb_filename

            # 调用logic层导出
            self.logic.export_colorbar(
                save_path,
                cb_font_size=cb_font,
                cb_custom_ticks=cb_ticks
            )
            messagebox.showinfo("成功", f"Colorbar已导出到：\n{save_path}")
            self._log(f"导出Colorbar成功：{save_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"导出Colorbar出错：{str(e)}")
            self._log(f"导出Colorbar失败：{str(e)}")

    def _on_delete_all_click(self):
        if not self.logic.plot_items:
            return
        ans = messagebox.askyesno("确认", "确定删除所有图项？")
        if ans:
            self.logic.delete_all_plots()
            self._rebuild_ui_list()
            self._log("已删除所有图项")
            self._update_btn_states()

    def _toggle_layer_entry(self):
        """勾选/取消自定义层区域（不清空配置，只切换使用状态）"""
        is_enabled = self.custom_layer_var.get()
        self.modify_layer_btn.config(state='normal' if is_enabled else 'disabled')
        
        # 如果没有图项，只更新显示
        if not self.logic.plot_items:
            self._update_layer_display()
            return
        
        # 获取当前层数，用于计算默认均分值
        m = int(self.current_m.get())
        default_layers = [i / m for i in range(1, m)]
        
        # 根据启用/禁用状态确定目标层配置
        target_layers = self.last_valid_layer_config if is_enabled else default_layers
        
        # ✅ 检查是否真的需要更新配置（避免不必要的重绘）
        needs_update = False
        for pid in list(self.logic.plot_items.keys()):
            current_config = self.logic.plot_items[pid]['config']['layer_points']
            if current_config != target_layers:
                needs_update = True
                self.logic.plot_items[pid]['config']['layer_points'] = target_layers
        
        # ✅ 只有当配置有实际变化时才执行重绘和UI更新
        if needs_update:
            status_msg = "恢复均分状态" if not is_enabled else f"应用自定义：{self.last_valid_layer_config}"
            self._log(f"自定义层区域{'取消' if not is_enabled else '启用'}，{status_msg}")
            
            # 重绘所有图
            self.logic.regenerate_all_plots(
                cb_custom_ticks=self.last_valid_tick_config[1] if self.enable_custom_ticks_var.get() else []
            )
            self._rebuild_ui_list()
            self._update_layer_display()
        else:
            # 配置没有变化，只记录日志
            self._log(f"自定义层区域{'取消' if not is_enabled else '启用'}（配置已是{'均分' if not is_enabled else '自定义'}）")

    def _toggle_ticks_entry(self):
        if self.enable_custom_ticks_var.get():
            self.cb_tick_entry.config(state='normal')
        else:
            self.cb_tick_entry.config(state='disabled')

    # -------------------- 统一重建：任何变化 → 全新列表 --------------------
    def _add_plot_item_ui(self, plot_id, config):
        row_frame = ttk.Frame(self.list_content_frame)
        row_frame.pack(fill='x', pady=4)

        preview_frame = ttk.Frame(row_frame, width=120, height=120)
        preview_frame.pack(side='left', padx=(0, 8))
        preview_frame.pack_propagate(False)

        # 获取当前生效的自定义刻度
        cb_ticks = self.last_valid_tick_config[1] if self.enable_custom_ticks_var.get() else []
        # 传递cb_custom_ticks参数
        fig = self.logic.generate_plot_fig(
            plot_id, 
            cb_custom_ticks=cb_ticks,  # 新增：传递自定义刻度
            is_preview=True, 
        )
        canvas = FigureCanvasTkAgg(fig, master=preview_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self._preview_canvas[plot_id] = canvas

        right_frame = ttk.Frame(row_frame)
        right_frame.pack(side='left', fill='y')

        ttk.Label(right_frame, text=f"图{plot_id.split('_')[1]}", font=("微软雅黑", 10, "bold")).pack(anchor='w')
        btn_bar = ttk.Frame(right_frame)
        btn_bar.pack(pady=2)
        ttk.Button(btn_bar, text="设置数据", command=lambda: self._on_set_data_click(plot_id)).pack(side='left', padx=2)
        ttk.Button(btn_bar, text="预览", command=lambda: self._on_preview_click(plot_id)).pack(side='left', padx=2)
        ttk.Button(btn_bar, text="导出", command=lambda: self._on_export_single_click(plot_id)).pack(side='left', padx=2)
        ttk.Button(btn_bar, text="删除", command=lambda: self._on_delete_single_click(plot_id)).pack(side='left', padx=2)

        self.plot_item_frames[plot_id] = row_frame

    def _on_delete_single_click(self, plot_id):
        try:
            self.logic.delete_plot_item(plot_id)
        except ValueError:
            pass
        self._rebuild_ui_list()

    def _refresh_plot_preview(self, plot_id):
        fig = self.logic.generate_plot_fig(plot_id, is_preview=True, show_colorbar=False)
        self._preview_canvas[plot_id].figure.clear()
        self._preview_canvas[plot_id].figure = fig
        self._preview_canvas[plot_id].draw()

    # 统一入口：任何数据变化 → 重建列表
    def _rebuild_ui_list(self):
        for w in self.list_content_frame.winfo_children():
            w.destroy()
        self.plot_item_frames.clear()
        self._preview_canvas.clear()
        for plot_id, config in self.logic.plot_items.items():
            self._add_plot_item_ui(plot_id, config)
        self._update_btn_states()

    def _update_btn_states(self):
        has_items = bool(self.logic.plot_items)
        self.delete_all_btn.config(state='normal' if has_items else 'disabled')
        self.export_all_btn.config(state='normal' if has_items else 'disabled')

    def _log(self, msg):
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"{datetime.now():%H:%M:%S}  {msg}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def _on_tick_modify_click(self):
        """点击“修改自定义刻度”弹出独立窗口输入，无界面输入框"""
        # 创建弹窗（模态窗口，禁止点击主界面）
        tick_dialog = tk.Toplevel(self.root)
        tick_dialog.title("修改自定义刻度")
        tick_dialog.geometry("400x180")
        tick_dialog.resizable(False, False)
        # 弹窗居中（基于主窗口）
        tick_dialog.transient(self.root)
        tick_dialog.grab_set()
        x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 180) // 2
        tick_dialog.geometry(f"+{x}+{y}")
        # 弹窗内控件（仅弹窗里有输入框）
        ttk.Label(
            tick_dialog, 
            text="请输入自定义刻度值（英文逗号分隔，如：0,0.8）："
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=15, sticky='w')
        
        # 弹窗输入框（默认填充上次有效刻度）
        tick_entry = ttk.Entry(tick_dialog, width=35)
        last_ticks = self.last_valid_tick_config[1]
        if last_ticks:
            tick_entry.insert(0, ",".join(map(str, last_ticks)))
        tick_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky='we')
        # 确认按钮逻辑
        def confirm_ticks():
            try:
                tick_str = tick_entry.get().strip()
                if not tick_str:
                    raise ValueError("刻度值不能为空，请输入至少2个数字（如0,0.8）")
                
                # 解析并校验刻度
                cb_ticks = [float(x.strip()) for x in tick_str.split(',')]
                if len(cb_ticks) < 2:
                    raise ValueError("至少需要输入2个刻度值（如0,0.8）")
                if not all(cb_ticks[i] < cb_ticks[i+1] for i in range(len(cb_ticks)-1)):
                    raise ValueError("刻度值必须按升序排列（如0,0.4,0.8）")
                
                # 更新配置并重绘
                self.last_valid_tick_config = (True, cb_ticks)
                self.logic.regenerate_all_plots(cb_custom_ticks=cb_ticks)
                self._rebuild_ui_list()
                
                # -------------------------- 新增：刷新刻度显示 --------------------------
                self.current_ticks_label.config(text=",".join(map(str, cb_ticks)))
                # --------------------------------------------------------------------------
                
                tick_dialog.grab_release()  # ✅ 释放抓取
                tick_dialog.destroy()
                self._log(f"自定义刻度修改成功：{cb_ticks}")
            except ValueError as e:
                messagebox.showerror("输入错误", str(e))
        # 取消按钮逻辑
        def cancel_ticks():
            tick_dialog.grab_release()  # ✅ 释放抓取
            tick_dialog.destroy()
        # 弹窗按钮布局
        btn_frame = ttk.Frame(tick_dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=15)
        ttk.Button(btn_frame, text="确认", command=confirm_ticks).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="取消", command=cancel_ticks).pack(side='left', padx=5)

    def _on_tick_change(self):
        """仅控制“修改自定义刻度”按钮的启用/禁用（无输入框相关逻辑）"""
        enable_custom = self.enable_custom_ticks_var.get()
        # 勾选启用 → 按钮激活；取消 → 按钮禁用
        self.tick_modify_btn.config(state='normal' if enable_custom else 'disabled')
        
        # 取消启用时，重置刻度配置并重绘（恢复原始数据范围）
        if not enable_custom:
            self.last_valid_tick_config = (False, [])
            self.logic.regenerate_all_plots(cb_custom_ticks=[])
            self._rebuild_ui_list()
            self._log("取消自定义刻度，已恢复原始数据范围重绘")

    def _on_app_close(self):
        """应用程序关闭时清理所有资源"""
        import gc
        
        # 关闭所有matplotlib图形
        for item in self.logic.plot_items.values():
            if item["fig"]:
                plt.close(item["fig"])
                item["fig"] = None
        
        # 清空预览Canvas
        for canvas in self._preview_canvas.values():
            if canvas:
                canvas.figure = None
                try:
                    canvas.get_tk_widget().destroy()
                except:
                    pass
        
        # 强制垃圾回收
        gc.collect()
        
        # 退出主循环
        self.root.quit()
        self.root.destroy()

    def _update_layer_display(self):
        """更新层区域显示标签（区分默认/自定义/禁用状态）"""
        m = int(self.current_m.get())
        default_layers = [i / m for i in range(1, m)]
        
        if self.custom_layer_var.get():
            # 启用自定义
            layer_str = ", ".join([f"{x:.3f}" for x in self.last_valid_layer_config])
            self.layer_display_label.config(text=f"✨ 自定义: {layer_str}")
        else:
            # 禁用状态，显示默认均分
            layer_str = ", ".join([f"{x:.3f}" for x in default_layers])
            self.layer_display_label.config(text=f"📐 默认: {layer_str}")

    def _update_default_layer_config(self):
        """根据当前层数生成并保存默认均分配置"""
        m = int(self.current_m.get())
        # 如果层数=2，生成 [0.5]；层数=3，生成 [0.33, 0.67]
        self.last_valid_layer_config = [i / m for i in range(1, m)]


# -------------------- 启动 --------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PizzaPlotUI(root)
    root.mainloop()