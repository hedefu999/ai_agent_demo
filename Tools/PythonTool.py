import sys,os
# 将当前workdir（项目根目录）添加到系统路径，这样可以访问各模块
sys.path.append(os.getcwd())

import re
from typing import Union

from langchain.tools import StructuredTool
from langchain_core.language_models import BaseChatModel, BaseLanguageModel
from langchain_core.output_parsers import BaseOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate

from Utils.CallbackHandlers import ColoredPrintHandler
from Models.Factory import ChatModelFactory
from Utils.PrintUtils import CODE_COLOR
# from langchain_openai import ChatOpenAI
from Tools.ExcelTool import get_first_n_rows, get_column_names
from langchain_experimental.utilities.python import PythonREPL
# from langchain_community.utilities import PythonREPL


class PythonCodeParser(BaseOutputParser):

    """从大模型返回的文本中提取Python代码，Markdown格式"""
    @staticmethod
    def __remove_marked_lines(input_str: str) -> str:
        lines = input_str.strip().split('\n')
        if lines and lines[0].strip().startswith('```'):
            del lines[0]
        if lines and lines[-1].strip().startswith('```'):
            del lines[-1]

        ans = '\n'.join(lines)
        return ans

    def parse(self, text: str) -> str:
        # 使用正则表达式找到所有的Python代码块
        python_code_blocks = re.findall(r'```python\n(.*?)\n```', text, re.DOTALL)
        # 从re返回结果提取出Python代码文本
        python_code = ""
        if len(python_code_blocks) > 0:
            python_code = python_code_blocks[0]
            python_code = self.__remove_marked_lines(python_code)
        return python_code


class ExcelAnalyser:
    """
    通过程序脚本分析一个结构化文件（例如excel文件）的内容。
    输人中必须包含文件的完整路径和具体分析方式和分析依据，阈值常量等。
    """
    def __init__(
            self,
            llm: Union[BaseLanguageModel, BaseChatModel],
            prompt_file="./prompts/tools/excel_analyser.txt",
            verbose=False
    ):
        self.llm = llm
        self.prompt = PromptTemplate.from_file(prompt_file)
        self.verbose = verbose
        self.verbose_handler = ColoredPrintHandler(CODE_COLOR)

    def analyse(self, query, filename):

        """分析一个结构化文件（例如excel文件）的内容。"""

        # columns = get_column_names(filename)
        inspections = get_first_n_rows(filename, 3)
        print(f'提取前三行数据：{inspections}')
        code_parser = PythonCodeParser()
        chain = self.prompt | self.llm | StrOutputParser()

        response = ""

        for c in chain.stream({
            "query": query,
            "filename": filename,
            "inspections": inspections
        }, config={
            "callbacks": [
                self.verbose_handler
            ] if self.verbose else []
        }):
            response += c
            # if c: print(c, end="") 上面指定的callback就带有了流式打印功能，以后别再手写了
        code = code_parser.parse(response)

        if code:
            # 动态执行python代码，大模型输出的pyhton代码字符串如何执行
            print(f'Warning! 准备执行Python代码：\n')
            invoke_result = PythonREPL().run(code)
            ans = query + " <-这个问题的处理结果是：\n" + invoke_result
            return ans
        else:
            return "没有找到可执行的Python代码"

    def as_tool(self):
        return StructuredTool.from_function(
            func=self.analyse,
            name="AnalyseExcel",
            # __class__获取当前实例的类对象，__doc__获取该类的文档字符串docstring，就是上面的注释
            # __class__.__name__将获取类名称 ExcelAnalyser
            description=self.__class__.__doc__.replace("\n", ""),
        )


if __name__ == "__main__":
    analyser = ExcelAnalyser(
        ChatModelFactory.get_default_model(),
    )
    result = analyser.analyse(
        query="9月销售额",
        # 文件路径根据 os.getcwd() 确定workdir再决定路径
        filename="data/2023年8月-9月销售记录.xlsx"
    )
    print(result)
    """打印结果
    Python REPL can execute arbitrary code. Use with caution.
    8月销售额
    2023年8月总销售额为：2605636元

    看看大模型的回复：
    ```python
    import pandas as pd

    # 读取Excel文件
    file_path = 'data/2023年8月-9月销售记录.xlsx'
    df = pd.read_excel(file_path, sheet_name='2023年8月-9月销售记录')

    # 转换销售日期为datetime类型
    df['销售日期'] = pd.to_datetime(df['销售日期'])

    # 筛选8月份的数据（2023年8月）
    august_data = df[df['销售日期'].dt.month == 8]

    # 计算销售额（单价 * 销售量）
    august_data['销售额'] = august_data['单价(元)'] * august_data['销售量']

    # 计算8月总销售额
    total_sales = august_data['销售额'].sum()

    # 输出结果
    print(f"2023年8月总销售额为: {total_sales} 元")
    ```

    强大地一腿
    """
