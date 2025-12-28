from langchain.tools import tool

@tool
def sql_expression_tool(rows: list[dict]) -> list[dict]:
    print("=== Debug: sql_expression_tool input ===")
    print(f"Type of input: {type(rows)}")
    if isinstance(rows, list):
        print(f"Number of rows: {len(rows)}")
        for i, row in enumerate(rows, 1):
            print(f"Row {i}: {row}")
    else:
        print("Input is not a list! Printing raw input:")
        print(rows)
    return rows