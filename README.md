## はじめに

OpenAIのFunction Callingを使うとAIモデルに特定の関数を呼び出す能力を与えられます。ただこの機能を使用するためには、関数の詳細な情報（名前、説明、パラメータなど）をJSON形式で提供する必要があります。この設定ファイルを皆さんどうやって作ってるのでしょうか。

恐らくベストプラクティスがあるのでしょうがちょっと調べて見当たらなかったので、自分用にクラスから生成するコードを作成してみました。他に良い方法があったら是非シェアして欲しい。

## ToolsInspctorの概要

ToolsInspctorは、Pythonの`inspect`モジュールを活用して、クラスのメソッド情報を詳細に解析し、構造化されたデータとして出力します。主な機能は以下の通りです：

1. クラスのメソッド情報の抽出
2. パラメータの型情報の取得
3. ドキュメント文字列（docstring）からの説明の抽出
4. 関数情報のJSON形式への変換
5. 分類データの生成と出力の整理

それでは、ToolsInspctorの各機能について詳しく見ていきましょう。

## コードの詳細解説

### クラスの初期化

```python
class ToolsInspctor():
    def __init__(self) -> None:
        pass
```

ToolsInspctorクラスの初期化メソッドです。現在は特別な初期化処理は行っていませんが、将来的に設定オプションなどを追加する可能性を考慮して定義しています。

### パラメータの型情報の取得

```python
def get_param_type(self, param):
    if param.annotation != inspect.Parameter.empty:
        if isinstance(param.annotation, type):
            return param.annotation.__name__
        elif hasattr(param.annotation, '__origin__'):
            origin = param.annotation.__origin__.__name__
            args = ', '.join([arg.__name__ for arg in param.annotation.__args__])
            return f"{origin}[{args}]"
        else:
            return str(param.annotation)
    else:
        return "any"
```

このメソッドは、関数パラメータの型情報を取得します。以下のような処理を行っています：

1. パラメータに型アノテーションがある場合：
   - 通常の型（int, str など）の場合は、その型名を返します。
   - ジェネリック型（List[int] など）の場合は、型名と引数を組み合わせた文字列を返します。
   - その他の型の場合は、文字列に変換して返します。
2. 型アノテーションがない場合は、"any"を返します。

この処理により、様々な型のパラメータに対応することができます。

### 関数情報の取得

```python
def get_function_info(self, func):
    name = func.__name__
    docstring = inspect.getdoc(func)
    description = docstring.split('Args:')[0].strip() if docstring else ""
    
    args_section = docstring.split('Args:')[1].split('Returns:')[0] if 'Args:' in docstring else ""
    args_dict = {}
    if args_section:
        for line in args_section.strip().split('\n'):
            parts = line.split(':', 1)
            if len(parts) == 2:
                arg_name = parts[0].strip()
                arg_desc = parts[1].strip()
                args_dict[arg_name] = arg_desc

    signature = inspect.signature(func)
    parameters = signature.parameters

    param_info = {}
    required_params = []
    for param_name, param in parameters.items():
        if param_name != 'self':
            param_type = self.get_param_type(param)
            param_info[param_name] = {
                "type": param_type
            }
            if param_name in args_dict:
                param_info[param_name]["description"] = args_dict[param_name]
            if param.default == inspect.Parameter.empty:
                required_params.append(param_name)

    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": param_info,
            "required": required_params,
            "additionalProperties": False
        }
    }
```

このメソッドは、関数の詳細情報を取得します。主な処理は以下の通りです：

1. 関数名とドキュメント文字列を取得します。
2. ドキュメント文字列から関数の説明部分を抽出します。
3. ドキュメント文字列の"Args:"セクションからパラメータの説明を抽出します。
4. 関数のシグネチャを解析し、パラメータ情報を取得します。
5. 各パラメータについて、型情報、説明、必須かどうかの情報を収集します。
6. 収集した情報を構造化されたディクショナリとして返します。

この処理により、関数の詳細な情報をOpenAIのFunction Calling用のフォーマットに近い形で取得することができます。

### クラスのメソッド情報の取得

```python
def get_class_methods_info(self, cls):
    methods_info = {}
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('__'):
            methods_info[name] = {
                "type": "function",
                "function": self.get_function_info(method)
            }
    return methods_info
```

このメソッドは、クラス内のすべての公開メソッド（マジックメソッドを除く）の情報を取得します。各メソッドに対して`get_function_info`を呼び出し、結果を辞書形式で格納します。

### ツールスキーマの生成

```python
def generate_tools_schema(self, classes: list[type], name: str | None = None) -> dict[str, any]:
    json_output = {}
    for cls in classes:
        class_info = self.get_class_methods_info(cls)
        json_output[cls.__name__] = class_info

    if name is None:
        name = "classes_info.json"
    if not name.endswith('.json'):
        name += '.json'

    with open(name, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=4)
    print(f"JSONファイルが生成されました: {name}")
    return json_output
```

このメソッドは、複数のクラスの情報を解析し、JSON形式で出力します。主な処理は以下の通りです：

1. 各クラスに対して`get_class_methods_info`を呼び出し、メソッド情報を取得します。
2. クラス名をキーとして、メソッド情報を辞書に格納します。
3. 指定されたファイル名（デフォルトは"classes_info.json"）でJSONファイルを生成します。
4. 生成したJSONデータを返します。

### 分類データの生成

```python
def generate_classification_data(self, schema: dict[str, any]) -> dict[str, dict[str, bool]]:
    classification_data = {}
    for class_name, class_info in schema.items():
        classification_data[class_name] = {
            func_name: True for func_name in class_info.keys() if not func_name.startswith('__')}
    return classification_data
```

このメソッドは、生成されたスキーマを元に分類用のデータを生成します。各クラスのメソッドに対して、デフォルトで`True`を設定します。この分類データは後で特定のメソッドを選択的に含めたり除外したりするのに使用できます。

### スキーマの整理

```python
def organize_schema(self, schema: dict[str, any], classification_data: dict[str, dict[str, bool]]) -> list[dict[str, any]]:
    organized_data = []
    for class_name, class_info in schema.items():
        if class_name in classification_data:
            for func_name, func_info in class_info.items():
                if classification_data[class_name].get(func_name, False):
                    organized_data.append(func_info['function'])
    return organized_data
```

このメソッドは、生成されたスキーマと分類データを使用して、最終的な出力形式に整理します。分類データで`True`に設定されているメソッドのみを含む、フラットなリスト形式で出力します。

## 使用方法と結果

ToolsInspctorの使用方法を具体的に見ていきましょう。以下は`example_class.py`に定義された`ExampleClass`を使用した例です。

```python
class ExampleClass:
    def method1(self, a: int, b: int = 10):
        """
        This is method1.
        
        Args:
            a: The first parameter
            b: The second parameter (default: 10)
        
        Returns:
            The sum of a and b
        """
        return a + b
    
    def method2(self, x: str) -> int:
        """
        This is method2.
        
        Args:
            x: A parameter
        
        Returns:
            The square of x
        """
        return x
```

このクラスを使用して、ToolsInspctorの各機能を試してみます。

```python
if __name__ == "__main__":
    tools = ToolsInspctor()
    
    # ツールスキーマの生成
    print(tools.generate_tools_schema([ExampleClass]))
    
    # 生成されたスキーマの取得
    tools_schema = tools.generate_tools_schema([ExampleClass])
    
    # 分類データの生成
    classification_data = tools.generate_classification_data(tools_schema)
    print(classification_data)
    
    # スキーマの整理
    organized_data = tools.organize_schema(tools_schema, classification_data)
    print(organized_data)
```

### 結果

1. ツールスキーマの生成:

```json
{
    "ExampleClass": {
        "method1": {
            "type": "function",
            "function": {
                "name": "method1",
                "description": "This is method1.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "int",
                            "description": "The first parameter"
                        },
                        "b": {
                            "type": "int",
                            "description": "The second parameter (default: 10)"
                        }
                    },
                    "required": ["a"],
                    "additionalProperties": false
                }
            }
        },
        "method2": {
            "type": "function",
            "function": {
                "name": "method2",
                "description": "This is method2.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "str",
                            "description": "A parameter"
                        }
                    },
                    "required": ["x"],
                    "additionalProperties": false
                }
            }
        }
    }
}
```

2. 分類データの生成:

```python
{
    "ExampleClass": {
        "method1": True,
        "method2": True
    }
}
```

3. スキーマの整理:

```python
[
    {
        "name": "method1",
        "description": "This is method1.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {
                    "type": "int",
                    "description": "The first parameter"
                },
                "b": {
                    "type": "int",
                    "description": "The second parameter (default: 10)"
                }
            },
            "required": ["a"],
            "additionalProperties": false
        }
    },
    {
        "name": "method2",
        "description": "This is method2.",
        "parameters": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "str",
                    "description": "A parameter"
                }
            },
            "required": ["x"],
            "additionalProperties": false
        }
    }
]
```

これらの結果から、ToolsInspctorが以下のことを実現していることがわかります：

1. クラスのメソッド情報を正確に抽出し、構造化されたJSON形式で出力しています。
2. メソッドの名前、説明、パラメータ情報（型、説明、必須かどうか）を適切に取得しています。
3. 分類データを生成し、後で特定のメソッドを選択的に含めたり除外したりできるようにしています。
4. 最終的に、OpenAIのFunction Callingで使用可能な形式にデータを整理しています。

## まとめ

ToolsInspctorは、Pythonクラスから関数情報を自動生成し、OpenAIのFunction Calling用に最適化された形式で出力するツールです。このツールを使用することで、以下のような利点があります：

1. 既存のPythonクラスからFunction Calling用の関数情報を簡単に生成できます。
2. ドキュメント文字列（docstring）を活用して、関数の説明やパラメータの詳細を自動的に取得します。
3. 型アノテーションを解析して、パラメータの型情報を正確に取得します。
4. 複数のクラスを一度に処理し、JSONファイルとして出力できます。
5. 分類データを使用して、特定のメソッドを選択的に含めたり除外したりできます。
