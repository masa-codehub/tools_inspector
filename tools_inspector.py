import inspect
import json


class ToolsInspctor():
    def __init__(self) -> None:
        pass

    def get_param_type(self, param):
        """
        パラメータの型を取得する
        Args:
            param: パラメータ
        """
        # パラメータにアノテーションがある場合はその型を返す
        if param.annotation != inspect.Parameter.empty:
            if isinstance(param.annotation, type):
                # アノテーションがクラスの場合はクラス名を返す
                return param.annotation.__name__
            elif hasattr(param.annotation, '__origin__'):
                # アノテーションがジェネリック型の場合は、ジェネリック型名と引数を返す
                # Generic types like List[int]
                origin = param.annotation.__origin__.__name__
                args = ', '.join(
                    [arg.__name__ for arg in param.annotation.__args__])
                return f"{origin}[{args}]"
            else:
                # その他の型の場合はそのまま文字列にして返す
                return str(param.annotation)
        else:
            # 型アノテーションがない場合はデフォルトで"any"を返す
            return "any"

    def get_function_info(self, func):
        """
        関数の情報を取得
        Args:
            func: 関数
        """
        # 関数名とドキュメント文字列を取得
        name = func.__name__
        docstring = inspect.getdoc(func)

        # Argsセクション以前の部分を取得
        description = docstring.split('Args:')[0].strip() if docstring else ""

        # Argsセクションを解析
        args_section = docstring.split('Args:')[1].split(
            'Returns:')[0] if 'Args:' in docstring else ""
        args_dict = {}
        if args_section:
            # Argsセクションを行ごとに分割し、パラメータ名と説明を取得
            for line in args_section.strip().split('\n'):
                parts = line.split(':', 1)
                # パラメータ名と説明がある行のみ処理
                if len(parts) == 2:
                    # パラメータ名と説明を取得
                    arg_name = parts[0].strip()
                    arg_desc = parts[1].strip()
                    args_dict[arg_name] = arg_desc

        # 関数の引数情報を取得
        signature = inspect.signature(func)
        parameters = signature.parameters

        # 引数情報を整形
        param_info = {}
        required_params = []
        # 引数ごとに情報を取得
        for param_name, param in parameters.items():
            # self以外の引数の情報を取得
            if param_name != 'self':
                # 引数の型を取得
                param_type = self.get_param_type(param)
                # 引数の情報を追加
                param_info[param_name] = {
                    "type": param_type
                }
                # 引数の説明がある場合は追加
                if param_name in args_dict:
                    param_info[param_name]["description"] = args_dict[param_name]

                # 初期値が設定されていない場合のみrequiredに追加
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

    def get_class_methods_info(self, cls):
        """
        クラスのメソッド情報を取得
        Args:
            cls: クラス
        """
        # クラスのメソッド情報を格納する辞書
        methods_info = {}
        # クラスのメソッドを取得
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # メソッド名が__で始まる場合はマジックメソッドなので除外
            if not name.startswith('__'):
                methods_info[name] = {
                    "type": "function",
                    "function": self.get_function_info(method)
                }
        return methods_info

    def generate_tools_schema(self, classes: list[type], name: str | None = None) -> dict[str, any]:
        """
        複数のクラスのツール構造をJSON形式で出力

        Args:
            classes: 解析するクラスのリスト
            name: 出力ファイル名
        """
        json_output = {}

        for cls in classes:
            # クラスのメソッド情報を取得
            class_info = self.get_class_methods_info(cls)
            # クラス名をキーとして、クラス情報を追加
            json_output[cls.__name__] = class_info

        # ファイル名が指定されていない場合はデフォルトのファイル名を使用
        if name is None:
            name = "classes_info.json"
        if not name.endswith('.json'):
            name += '.json'

        # JSONファイルに書き込み
        with open(name, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, ensure_ascii=False, indent=4)

        print(f"JSONファイルが生成されました: {name}")
        return json_output

    def generate_classification_data(self, schema: dict[str, any], name: str | None = None) -> dict[str, dict[str, bool]]:
        """
        generate_tools_schemaの結果を元に分類用の辞書データを生成する

        Args:
            schema: generate_tools_schemaの出力結果

        Returns:
            分類用の辞書データ
        """
        # 分類用の辞書データを初期化
        classification_data = {}
        # クラスごとに関数名を取得し、分類用の辞書データに追加
        for class_name, class_info in schema.items():
            # マジックメソッド以外の関数名を取得
            classification_data[class_name] = {
                func_name: True for func_name in class_info.keys() if not func_name.startswith('__')}

        if name is None:
            name = "classification_data.json"
        if not name.endswith('.json'):
            name += '.json'

        # 分類用の辞書データをJSON形式に変換して保存
        classification_data_json = json.dumps(
            classification_data, ensure_ascii=False, indent=4)
        with open("classification_data.json", "w", encoding="utf-8") as f:
            f.write(classification_data_json)

        # 分類用の辞書データを返す
        return classification_data

    def organize_schema(self, schema: dict[str, any], classification_data: dict[str, dict[str, bool]] | str) -> list[dict[str, any]]:
        """
        分類データを元に出力を整理する

        Args:
            schema: generate_tools_schemaの出力
            classification_data: 分類用の辞書データ

        Returns:
            整理された出力（すべての関数を1つのリストにまとめたもの）
        """
        if isinstance(classification_data, str):
            # 分類用の辞書データがファイル名の場合は読み込む
            if classification_data.endswith('.json'):
                with open(classification_data, "r", encoding="utf-8") as f:
                    classification_data = json.load(f)
            else:
                return []

        # 整理されたデータを格納するリスト
        organized_data = []
        # クラスごとに関数情報を取得し、分類用の辞書データに含まれる関数のみ追加
        for class_name, class_info in schema.items():
            # 分類用の辞書データにクラス名が含まれている場合のみ処理
            if class_name in classification_data:
                # クラスの関数情報を取得
                for func_name, func_info in class_info.items():
                    # 分類用の辞書データに関数名が含まれている場合のみ追加
                    if classification_data[class_name].get(func_name, False):
                        # 関数情報を追加
                        organized_data.append({
                            "type": "function",
                            "function": func_info
                        })

        # 整理されたデータを返す
        return organized_data


if __name__ == "__main__":

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

    tools = ToolsInspctor()
    print(tools.generate_tools_schema([ExampleClass]))

    tools_schema = tools.generate_tools_schema([ExampleClass])
    classification_data = tools.generate_classification_data(tools_schema)

    print(classification_data)

    organized_data = tools.organize_schema(tools_schema, classification_data)

    print(organized_data)
