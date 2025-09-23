import os
from typing import List
from dotenv import load_dotenv, find_dotenv
# 全面使用智谱大模型GLM
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.embeddings import ZhipuAIEmbeddings

_ = load_dotenv(find_dotenv())


class ChatModelFactory:
    model_params = {
        "temperature": 0,
        "model_kwargs": {"seed": 42},
    }

    @classmethod
    def get_default_model(cls):
        return ChatZhipuAI(
                model = "glm-4.5",
                api_key = os.environ["ZHIPU_API_KEY"],
                **cls.model_params
            )


class EmbeddingModelFactory:

    @classmethod
    def get_default_model(cls):
        return ZhipuAIEmbeddings(
            api_key=os.environ["ZHIPU_API_KEY"],
            model="embedding-3",
            dimensions=1024,
        )
    

