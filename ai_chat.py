# self.messages上下文共两条，都要添加提示词，以及记得添加apikey
#并且本程序运行效率有问题，最好API调用改为异步线程处理，并优化UI更新频率

import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from openai import OpenAI
import json
from datetime import datetime
import os

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Chat")
        self.root.geometry("600x500")
        
        # 设置样式
        self.bg_color = "#f0f0f0"
        self.user_color = "#d1e7ff"
        self.assistant_color = "#ffffff"
        self.font = ("微软雅黑", 14)
        
        # 初始化OpenAI客户端
        self.client = OpenAI(api_key="<api key>", base_url="https://api.deepseek.com") # 请在这里输入API密钥
        self.messages = [{"role": "system", "content": "<输入提示词>"}]# 请在这里输入提示词
        
        # 配置主窗口背景
        self.root.configure(bg=self.bg_color)
        
        # 创建侧边栏
        sidebar = tk.Frame(root, width=100, bg="#e0e0e0")
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 添加新建聊天按钮
        new_chat_btn = tk.Button(
            sidebar,
            text="新建聊天",
            command=self.new_chat,
            bg="#2196F3",
            fg="white",
            font=("微软雅黑", 12),
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        new_chat_btn.pack(pady=10)
        
        # 创建聊天记录显示区域
        self.chat_history = scrolledtext.ScrolledText(
            root,
            state='disabled',
            wrap=tk.WORD,
            bg=self.bg_color,
            font=self.font,
            padx=10,
            pady=10
        )
        self.chat_history.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 创建输入框和发送按钮
        input_frame = tk.Frame(root, bg=self.bg_color)
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # 配置输入框样式
        self.input_entry = tk.Entry(
            input_frame,
            font=self.font,
            relief=tk.FLAT,
            bd=2
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_entry.bind("<Return>", self.send_message)
        
        send_button = tk.Button(
            input_frame,
            text="Send",
            command=self.send_message,
            bg="#4CAF50",
            fg="white",
            font=self.font,
            relief=tk.FLAT,
            padx=15
        )
        send_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 自动加载历史记录
        self.load_auto_save()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def send_message(self, event=None):
        user_input = self.input_entry.get()
        if not user_input:
            return
            
        # 清空输入框
        self.input_entry.delete(0, tk.END)
        
        # 显示用户消息
        self.display_message("You", user_input)
        
        # 确保系统提示词始终在对话历史中
        if len(self.messages) > 20:  # 防止对话历史过长
            self.messages = [self.messages[0]] + self.messages[-19:]
            
        # 添加用户消息到对话历史
        self.messages.append({"role": "user", "content": user_input})
        
        # 调用API（流式传输）
        try:
            response = self.client.chat.completions.create(
                model="deepseek-reasoner",
                messages=self.messages,
                stream=True
            )
            
            # 初始化助手回复
            assistant_reply = ""
            self.chat_history.config(state='normal')
            self.chat_history.insert(tk.END, "[Assistant]:\n", "Assistant")
            
            # 实时显示流式响应
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    assistant_reply += content
                    self.chat_history.insert(tk.END, content)
                    self.chat_history.see(tk.END)
                    self.chat_history.update()
            
            # 添加换行并禁用编辑
            self.chat_history.insert(tk.END, "\n\n")
            self.chat_history.config(state='disabled')
            
            # 添加助手回复到对话历史
            self.messages.append({"role": "assistant", "content": assistant_reply})
            
            # 每5条消息自动保存一次
            if len(self.messages) % 5 == 0:
                self.save_auto()
                
        except Exception as e:
            self.display_message("System", f"错误信息: {str(e)}")
        
    def display_message(self, sender, message):
        self.chat_history.config(state='normal')
        
        # 获取当前时间
        timestamp = datetime.now().strftime("%H:%M")
        
        # 设置消息样式
        bg_color = self.user_color if sender == "You" else self.assistant_color
        self.chat_history.tag_config(sender, 
                                   background=bg_color,
                                   font=self.font,
                                   spacing1=5,
                                   spacing3=5)
        
        # 插入带时间戳的消息
        self.chat_history.insert(tk.END, f"[{timestamp}] {sender}:\n", sender)
        self.chat_history.insert(tk.END, f"{message}\n\n")
        
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)
        
    def load_auto_save(self):
        save_path = "chat_auto_save.json"
        if os.path.exists(save_path):
            try:
                with open(save_path, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
                self.chat_history.config(state='normal')
                self.chat_history.delete(1.0, tk.END)
                for msg in self.messages:
                    if msg['role'] in ['user', 'assistant']:
                        self.display_message(
                            "You" if msg['role'] == 'user' else "Assistant",
                            msg['content']
                        )
            except Exception as e:
                print(f"加载历史记录失败: {str(e)}")
                
    def save_auto(self):
        save_path = "chat_auto_save.json"
        try:
            # 保存完整的对话历史，包括系统提示词
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"自动保存失败: {str(e)}")
            
    def new_chat(self):
        # 重置对话历史
        self.messages = [{"role": "system", "content": "<输入提示词>"}]# 请在这里输入提示词,最好和上面一样
        self.chat_history.config(state='normal')
        self.chat_history.delete(1.0, tk.END)
        self.chat_history.config(state='disabled')
        
    def on_closing(self):
        # 自动保存
        self.save_auto()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
