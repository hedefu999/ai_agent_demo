from pydantic.v2 import BaseModel, Field
from typing import List, Optional, Dict, Any, Generic

# 定义智能体要执行的动作
class Action(BaseModel):
    name: str = Field(description="Tool name")
    args: Optional[Dict[str, Any]] = Field(description="Tool input arguments, containing arguments names and values")

    def __str__(self):
        ret = f"Action(name={self.name}"
        if self.args:
            for k, v in self.args.items():
                ret += f", {k}={v}"
        ret += ")"
        return ret
