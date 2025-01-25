import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import aiohttp
import asyncio
from openai import AsyncOpenAI
import json
from datetime import datetime
import os

#Remember to fill in the API key!!!

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Chat")
        self.root.geometry("600x500")
        
        # 初始化处理状态
        self.is_processing = False
        
        # 设置样式
        self.bg_color = "#f0f0f0"
        self.user_color = "#d1e7ff"
        self.assistant_color = "#ffffff"
        self.system_color = "#ffebee"  # 浅红色背景
        self.font = ("微软雅黑", 14)
        self.system_font = ("微软雅黑", 12, "italic")  # 斜体小一号字体
        
        # 初始化异步OpenAI客户端
        self.client = AsyncOpenAI(api_key="<api key>", base_url="https://api.deepseek.com")
        self.messages = [{"role": "system", "content": "你是一个ai助手，请回答一切用户所问的问题"}]
        
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
        
        self.send_button = tk.Button(
            input_frame,
            text="Send",
            command=self.send_message,
            bg="#4CAF50",
            fg="white",
            font=self.font,
            relief=tk.FLAT,
            padx=15,
            state=tk.NORMAL
        )
        self.send_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 自动加载历史记录
        self.load_auto_save()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    async def send_message_async(self, user_input):
        try:
            # 显示加载状态
            self.chat_history.config(state='normal')
            self.chat_history.insert(tk.END, "[Assistant]: 正在处理中...\n", "Assistant")
            self.chat_history.config(state='disabled')
            self.chat_history.see(tk.END)
            
            # 异步API调用
            response = await self.client.chat.completions.create(
                model="deepseek-reasoner",
                messages=self.messages,
                stream=True
            )
            
            # 初始化助手回复
            assistant_reply = ""
            self.chat_history.config(state='normal')
            self.chat_history.delete("end-2l", "end-1l")  # 删除"正在处理中"提示
            
            # 实时显示流式响应
            async for chunk in response:
                if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    assistant_reply += content
                    # 使用after方法更新UI
                    self.root.after(0, lambda c=content: self.update_chat(c))
            
            # 添加助手回复到对话历史
            self.messages.append({"role": "assistant", "content": assistant_reply})
            # 完成时添加换行
            self.root.after(0, self.finish_chat)
            
        except Exception as e:
            self.root.after(0, lambda: self.display_message("System", f"错误信息: {str(e)}"))
        finally:
            self.root.after(0, self.enable_send_button)
            # 每5条消息自动保存一次
            if len(self.messages) % 5 == 0:
                self.save_auto()
    
    def send_message(self, event=None):
        if self.is_processing:
            self.display_message("System", "请等待上一条消息处理完成后再发送新消息")
            return
            
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
            
        # 检查上一条消息角色
        if len(self.messages) > 0 and self.messages[-1]['role'] == 'user':
            self.display_message("System", "请等待上一条消息处理完成后再发送新消息")
            return
            
        # 添加用户消息到对话历史
        self.messages.append({"role": "user", "content": user_input})
        
        # 禁用发送按钮
        self.is_processing = True
        self.send_button.config(state=tk.DISABLED, bg="#cccccc")
        
        # 启动异步任务
        asyncio.create_task(self.send_message_async(user_input))
        
    def update_chat(self, content):
        """更新聊天内容"""
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, content)
        self.chat_history.see(tk.END)
        self.chat_history.config(state='disabled')
        
    def enable_send_button(self):
        """启用发送按钮"""
        self.is_processing = False
        self.send_button.config(state=tk.NORMAL, bg="#4CAF50")
        
    def finish_chat(self):
        """完成聊天更新"""
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, "\n\n")
        self.chat_history.config(state='disabled')
        
    def display_message(self, sender, message):
        self.chat_history.config(state='normal')
        
        # 获取当前时间
        timestamp = datetime.now().strftime("%H:%M")
        
        # 设置消息样式
        if sender == "You":
            bg_color = self.user_color
            font = self.font
        elif sender == "Assistant":
            bg_color = self.assistant_color
            font = self.font
        else:  # System messages
            bg_color = self.system_color
            font = self.system_font
            
        self.chat_history.tag_config(sender, 
                                   background=bg_color,
                                   font=font,
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
                    saved_messages = json.load(f)
                
                # 重置消息历史，只保留系统消息
                self.messages = [self.messages[0]]
                
                # 只加载有效的用户和助手消息对
                for msg in saved_messages:
                    if msg['role'] == 'user':
                        self.messages.append(msg)
                        self.display_message("You", msg['content'])
                    elif msg['role'] == 'assistant' and len(self.messages) > 0 and self.messages[-1]['role'] == 'user':
                        self.messages.append(msg)
                        self.display_message("Assistant", msg['content'])
                
                self.chat_history.config(state='normal')
                self.chat_history.delete(1.0, tk.END)
                
            except Exception as e:
                print(f"加载历史记录失败: {str(e)}")
                
    def save_auto(self):
        save_path = "chat_auto_save.json"
        try:
            # 只保存有效的用户和助手消息对
            valid_messages = [self.messages[0]]  # 保留系统消息
            for i in range(1, len(self.messages)):
                if (self.messages[i]['role'] == 'user' and 
                    (i == 1 or self.messages[i-1]['role'] == 'assistant')) or \
                   (self.messages[i]['role'] == 'assistant' and 
                    self.messages[i-1]['role'] == 'user'):
                    valid_messages.append(self.messages[i])
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(valid_messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"自动保存失败: {str(e)}")
            
    def new_chat(self):
        # 重置对话历史
        self.messages = [{"role": "system", "content": "你是一个ai助手，请回答一切用户所问的问题"}]
        self.chat_history.config(state='normal')
        self.chat_history.delete(1.0, tk.END)
        self.chat_history.config(state='disabled')
        
    def on_closing(self):
        # 自动保存
        self.save_auto()
        self.root.destroy()

async def main():
    root = tk.Tk()
    app = ChatApp(root)
    
    # 启动Tkinter主循环
    while True:
        root.update()
        await asyncio.sleep(0.01)

if __name__ == "__main__":
    asyncio.run(main())
