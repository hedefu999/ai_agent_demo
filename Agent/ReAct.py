import re
from typing import List, Tuple

from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain.schema.output_parser import StrOutputParser
from langchain.tools.base import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import  render_text_description
from pydantic import ValidationError
from langchain_core.prompts import HumanMessagePromptTemplate

from Agent.Action import Action
from Utils.CallbackHandlers import *


class ReActAgent:
    """AutoGPT：基于Langchain实现"""

    @staticmethod
    def __format_thought_observation(thought: str, action: Action, observation: str) -> str:
        # 将全部JSON代码块替换为空
        ret = re.sub(r'```json(.*?)```', '', thought, flags=re.DOTALL)
        ret += "\n" + str(action) + "\n返回结果:\n" + observation
        return ret

    @staticmethod
    def __extract_json_action(text: str) -> str | None:
        # 匹配最后出现的JSON代码块，这个正则表达是说匹配markdown中的json代码块，通常是获取 ```json xxx ``` 这个符号里包含的内容
        # re.DOTALL 是说 . 这个通配符也能匹配换行符，这样pretty的json报文就能全部捕获了
        json_pattern = re.compile(r'```json(.*?)```', re.DOTALL)
        matches = json_pattern.findall(text)
        if matches:
            last_json_str = matches[-1]
            return last_json_str
        return None

    def __init__(
            self,
            llm: BaseChatModel,
            tools: List[BaseTool],
            work_dir: str,
            main_prompt_file: str,
            max_thought_steps: int = 10,
    ):
        self.llm = llm
        self.tools = tools
        self.work_dir = work_dir
        self.max_thought_steps = max_thought_steps

        # PydanticOutputParser告诉LangChain使用哪个BaseModel定义的字段输出格式化信息
        # - 这些格式说明会被添加到提示模板中
        self.output_parser = PydanticOutputParser(pydantic_object=Action)
        # OutputFixingParser： 如果输出格式不正确，尝试修复
        self.robust_parser = OutputFixingParser.from_llm(
            parser=self.output_parser,
            llm=llm
        )
        # 提示词放到文件 /prompts/main/main.txt 中
        self.main_prompt_file = main_prompt_file
        # 从提示词文件中加载到 HumanMessagePromptTemplate
        self.__init_prompt_templates()
        # 创建一个chain
        self.__init_chains()

        self.verbose_handler = ColoredPrintHandler(color=THOUGHT_COLOR)

    def __init_prompt_templates(self):
        with open(self.main_prompt_file, 'r', encoding='utf-8') as f:
            self.prompt = ChatPromptTemplate.from_messages(
                [
                    MessagesPlaceholder(variable_name="chat_history"),
                    HumanMessagePromptTemplate.from_template(f.read()),
                ]
            ).partial( # partial方法提供prompt模板中的占位符参数的值
                work_dir=self.work_dir,
                # render_text_description格式化tool（BaseTool）信息：{tool.name} - {tool.description}
                tools=render_text_description(self.tools),
                tool_names=','.join([tool.name for tool in self.tools]),
                # get_format_instructions() 得到的内容在Action中进行了演示
                # 功能就是生成一个大模型提示词模板，而且是源码里写死的，英文版的
                format_instructions=self.output_parser.get_format_instructions(),
            )

    def __init_chains(self):
        # 主流程的chain
        self.main_chain = (self.prompt | self.llm | StrOutputParser())

    def __find_tool(self, tool_name: str) -> Optional[BaseTool]:
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    def __step(self, task, short_term_memory, chat_history,
                verbose=False) -> Tuple[Action, str]:

        """执行一步思考"""

        inputs = {
            "input": task,
            "agent_scratchpad": "\n".join(short_term_memory),
            "chat_history": chat_history.messages,
        }

        config = {
            "callbacks": [self.verbose_handler]
            if verbose else []
        }
        response = ""
        for s in self.main_chain.stream(inputs, config=config):
            response += s
        # 提取JSON代码块
        json_action = self.__extract_json_action(response)
        # 带容错的解析，大模型提供了灵活的格式纠正
        action = self.robust_parser.parse(
            json_action if json_action else response
        )
        return action, response

    def __exec_action(self, action: Action) -> str:
        # 查找工具
        tool = self.__find_tool(action.name)
        if tool is None:
            observation = (
                f"Error: 找不到工具或指令 '{action.name}'. "
                f"请从提供的工具/指令列表中选择，请确保按对顶格式输出。"
            )
        else:
            try:
                # 执行工具
                observation = tool.run("" if action.args is None else action.args) 
            except ValidationError as e:
                # 工具的入参异常
                observation = (
                    f"Validation Error in args: {str(e)}, args: {action.args}"
                )
            except Exception as e:
                # 工具执行异常
                observation = f"Error: {str(e)}, {type(e).__name__}, args: {action.args}"

        return observation

    def run(self, task: str, chat_history: ChatMessageHistory,
            verbose=False ) -> str:
        """
        运行智能体
        :param task: 用户任务
        :param chat_history: 对话上下文（长时记忆）
        :param verbose: 是否显示详细信息
        """
        # 初始化短时记忆: 记录推理过程
        short_term_memory:list[str] = []

        # 思考步数
        thought_step_count = 0

        reply = ""

        # 开始逐步思考
        while thought_step_count < self.max_thought_steps:
            if verbose:
                self.verbose_handler.on_thought_start(thought_step_count)

            # 执行一步思考
            action, response = self.__step(
                task=task,
                short_term_memory=short_term_memory,
                chat_history=chat_history,
                verbose=verbose,
            )

            # 如果是结束指令，执行最后一步
            if action.name == "FINISH":
                reply = self.__exec_action(action)
                break

            # 执行动作
            observation = self.__exec_action(action)

            if verbose:
                self.verbose_handler.on_tool_end(observation)

            # 更新短时记忆
            short_term_memory.append(
                self.__format_thought_observation(
                    response, action, observation
                )
            )

            thought_step_count += 1

        if thought_step_count >= self.max_thought_steps:
            # 如果思考步数达到上限，返回错误信息
            reply = "抱歉，我没能完成您的任务。"

        # 更新长时记忆
        chat_history.add_user_message(task)
        chat_history.add_ai_message(reply)
        return reply
