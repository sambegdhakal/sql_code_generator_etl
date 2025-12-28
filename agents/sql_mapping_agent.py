from langchain.agents import create_agent

def sqL_script_agent(llm, tools):
    system_prompt = (
        "Forget previous data or conversation. "
        "You will receive a list of dictionaries as input. Only use that input." \
        "For each row, generate a SQL expression. Do the following steps:\n"
        "- Understand transformation logic for each row separately.\n"
        "- Do not mix it up.\n"
        "- After understanding it generate sql logic.\n"
        "- Use source_sub_column if source is an array of structs.\n"
        "- Wrap in ARRAY() if target_data_type is array.\n"
        "- Handle any new conditions that are not mentioned in a best way possible."
        "- If source_column is missing, map NULL to target_column.\n"
        "RETURN **ONLY** a JSON array of dictionaries. Not as a python script. "
        "Do not include:" \
        "- Any Python code" \
        "- Explanations or extra text" \
        "- Markdown formatting (no ```python)" \
        "The JSON must be valid and parseable by json.loads().\n\n"
        "Each dictionary must have these keys:\n"
        "source_table, source_column, source_sub_column, transformation_logic, "
        "target_table, target_column, target_sub_column, sql_expression.\n\n"
        "EXAMPLE OUTPUT (JSON only, no code):\n"
        "[\n"
        "  {\n"
        "    \"source_table\": \"orders_src\",\n"
        "    \"source_column\": \"first_name\",\n"
        "    \"source_sub_column\": null,\n"
        "    \"transformation_logic\": \"concat(first_name, ' ', last_name)\",\n"
        "    \"target_table\": \"orders_tgt\",\n"
        "    \"target_column\": \"audit_items\",\n"
        "    \"target_sub_column\": \"first_name\",\n"
        "    \"sql_expression\": \"concat(first_name, ' ', last_name)\"\n"
        "  }\n"
        "]"
        "Above is just an example. Each row will have thier own transformation."
        "**Highly important: Do not create your own tables and columns.**"
    )

    agent = create_agent(llm, tools, system_prompt=system_prompt)
    return agent
