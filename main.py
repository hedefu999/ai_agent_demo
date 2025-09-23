import sys,os
print(f'system current dir: {os.getcwd()}')
sys.path.append(os.getcwd())
# 不知道为啥main.py跑起来StructuredTools中导入的Tool会找不到，非要在FileQATool前加个点才能从父目录下自动找到
# 但这样直接调试PythonTool等单元测试会找不到，这里直接将Tools这个path加进来就可以了
sys.path.append(os.getcwd()+'/Tools')

# 加载环境变量
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())

from Agent.ReAct import ReActAgent
from Models.Factory import ChatModelFactory
from Tools import *
from Tools.PythonTool import ExcelAnalyser
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
import os


def launch_agent(agent: ReActAgent):
    human_icon = "\U0001F468"
    ai_icon = "\U0001F916"
    chat_history = ChatMessageHistory()

    while True:
        task = input(f"{ai_icon}：有什么可以帮您？\n{human_icon}：")
        if task.strip().lower() == "quit":
            break
        reply = agent.run(task, chat_history, verbose=True)
        print(f"{ai_icon}：{reply}\n")


def main():

    # 语言模型
    llm = ChatModelFactory.get_default_model()

    # 自定义工具集
    tools = [
        document_qa_tool,
        document_generation_tool,
        email_tool,
        excel_inspection_tool,
        directory_inspection_tool,
        finish_placeholder,
        ExcelAnalyser(
            llm=llm,
            prompt_file="./prompts/tools/excel_analyser.txt",
            verbose=True
        ).as_tool()
    ]

    # 定义智能体
    agent = ReActAgent(
        llm=llm,
        tools=tools,
        work_dir="./data",
        main_prompt_file="./prompts/main/main.txt",
        max_thought_steps=20,
    )

    # 运行智能体
    launch_agent(agent)


if __name__ == "__main__":
    main()
