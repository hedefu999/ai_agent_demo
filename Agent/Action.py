from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Generic
import json

# 定义智能体要执行的动作
class Action(BaseModel):
    name: str = Field(description="Tool name")
    args: Optional[Dict[str, Any]] = Field(description="Tool input arguments, containing arguments names and values")

    def __str__(self):
        ret = f"Action(name={self.name}"
        if self.args:
            for k, v in self.args.items():
                ret += f", {k}: {v}"
        ret += ")"
        return ret
    
if '__main__'==__name__:
    action = Action(name='list_files_in_directory', args={'path': '.'})
    schema = dict(action.model_json_schema().items())
    reduced_schema = schema
    if "title" in reduced_schema:
        del reduced_schema["title"]
    if "type" in reduced_schema:
        del reduced_schema["type"]
    schema_str = json.dumps(reduced_schema, ensure_ascii=False)
    _PYDANTIC_FORMAT_INSTRUCTIONS = """The output should be formatted as a JSON instance that conforms to the JSON schema below.

    As an example, for the schema {{"properties": {{"foo": {{"title": "Foo", "description": "a list of strings", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["foo"]}}
    the object {{"foo": ["bar", "baz"]}} is a well-formatted instance of the schema. The object {{"properties": {{"foo": ["bar", "baz"]}}}} is not well-formatted.

    Here is the output schema:
    ```
    {schema}
    ```"""
    result = _PYDANTIC_FORMAT_INSTRUCTIONS.format(schema=schema_str)
    print(f'Action: {result}')
    """
    As an example, for the schema {"properties": {"foo": {"title": "Foo", "description": "a list of strings", "type": "array", "items": {"type": "string"}}}, "required": ["foo"]}
    the object {"foo": ["bar", "baz"]} is a well-formatted instance of the schema. The object {"properties": {"foo": ["bar", "baz"]}} is not well-formatted.

    Here is the output schema:
    ```
{
  "properties": {
    "name": {
      "description": "Tool name",
      "title": "Name",
      "type": "string"
    },
    "args": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "description": "Tool input arguments, containing arguments names and values",
      "title": "Args"
    }
  },
  "required": [
    "name",
    "args"
  ]
}    ```
    """
