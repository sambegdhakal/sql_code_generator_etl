import pandas as pd
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import re

# ----------------------------
# CONFIG
# ----------------------------
INPUT_FILE = "transformation_files/Transformation_logic.xlsx"
OUTPUT_FILE = "output_with_sql.xlsx"

llm = ChatOllama(
    model="gemma3:4b",
    temperature=0
)

# ----------------------------
# PROMPT TEMPLATE
# ----------------------------
def build_prompt(row, multiple_fields=None, exploded_alias=None):
    """
    exploded_alias: str or None. If source array exploded but target is scalar.
    multiple_fields: list of dict rows for struct/array combination
    """
    if multiple_fields:
        source_cols = ", ".join(f"{r['source_column']}" for r in multiple_fields)
        sub_cols = ", ".join(f"{r['source_sub_column'] or r['source_column']}" for r in multiple_fields)
        transformation_logic = "; ".join(
            f"{r['transformation_logic']} AS {r['target_sub_column']}" if pd.notna(r['transformation_logic']) and str(r['transformation_logic']).strip() != "" 
            else f"{r['source_column']} AS {r['target_sub_column']}"
            for r in multiple_fields
        )

        prompt_text = f"""
You are a senior data engineer.
Generate ONLY the SQL expression (not a full query) for the following array target.

Combine the following source columns into a single array/struct:
- source columns: {source_cols}
- sub-columns: {sub_cols}
- transformation logic: {transformation_logic}

Rules:
- Use only Apache Spark SQL / Databricks SQL functions
- Use struct() to combine multiple sub-columns
- If target data type is array, wrap the struct() in ARRAY(...), e.g. ARRAY(STRUCT(...))
- If the target data type and source data type are both scalar, strictly do NOT wrap the expression in STRUCT() or ARRAY(). Just generate the transformation logic and alias it as the target column
- Direct mapping from source column or source sub column to target if transformation is empty
- Use CASE WHEN only if conditional logic exists
- If any source column is an array, use the exploded alias {exploded_alias} in the expression
- DO NOT use SELECT, FROM, EXPLODE(), ARRAY_ELEMENT_AT(), or any other non-Spark SQL functions
- Alias output as the target column only using AS
- Return EXACTLY the expression, nothing else, no extra text, and strictly no SQL clause like SELECT or FROM table name
- Strictly no SQL clause like SELECT or FROM table name or any other SQL clause inside ARRAY(....)
"""
    else:
        source_column_ref = row['source_column']
        # Use exploded_alias if source array → scalar target
        if exploded_alias:
            source_column_ref = f"{exploded_alias}.{row['source_sub_column'] or row['source_column']}"

        # If transformation_logic is empty, directly map source → target
        if pd.isna(row['transformation_logic']) or str(row['transformation_logic']).strip() == "":
            return f"{source_column_ref} AS {row['target_sub_column'] or row['target_column']}"

        prompt_text = f"""
You are a senior data engineer.
Generate ONLY the SQL expression (not a full query) for this field.

Source:
- column: {source_column_ref}
- sub column: {row['source_sub_column']}
- data type: {row['source_data_type']}
- sub data type: {row['source_sub_data_type']}

Transformation logic:
{row['transformation_logic']}

Target:
- column: {row['target_column']}
- sub column: {row['target_sub_column']}
- data type: {row['target_data_type']}
- sub data type: {row['target_sub_data_type']}

Rules:
- Use only Apache Spark SQL / Databricks SQL functions
- Use struct() if combining multiple sub-columns
- If target data type is array, wrap the struct() in ARRAY(...), e.g. ARRAY(STRUCT(...))
- If the target data type and source data type are both scalar, strictly do NOT wrap the expression in STRUCT() or ARRAY(). Just generate the transformation logic and alias it as the target column
- Direct mapping from source column or source sub column to target if transformation is empty
- Use CASE WHEN only if conditional logic exists
- Use exploded alias {exploded_alias} if source is array but target is scalar
- DO NOT use SELECT, FROM, EXPLODE(), ARRAY_ELEMENT_AT(), or any other non-Spark SQL functions
- Alias output only with AS
- Return EXACTLY the expression, nothing else, no extra text, and strictly no SQL clause like SELECT or FROM table name
- Strictly no SQL clause like SELECT or FROM table name or any other SQL clause inside ARRAY(....)
"""
    return prompt_text

# ----------------------------
# MAIN
# ----------------------------
df = pd.read_excel(INPUT_FILE)

# only copy
df = df.copy()

# 2. Prepare output columns
df['generated_sql_expression'] = ""
df['lateral_exploded_alias'] = ""  # store exploded alias if source array → scalar target

# 3. Group by target_table + target_column for array aggregation
grouped = df.groupby(['target_table', 'target_column'])

for (_, _), group in grouped:
    # Case 1: target is array and multiple sub-columns → combine into struct/array
    if group['target_data_type'].iloc[0] == 'array' and len(group) > 1:
        prompt = build_prompt(None, multiple_fields=group.to_dict('records'))
        response = llm.invoke([HumanMessage(content=prompt)])
        expr = response.content.replace("```", "").replace("sql", "").replace("`","").strip()
        df.loc[group.index[0], 'generated_sql_expression'] = expr
        continue

    # Case 2: single row or scalar target
    for idx, row in group.iterrows():
        if pd.isna(row['target_column']):
            continue

        # Check if source is array but target is NOT array
        exploded_alias_name = None
        if row['source_data_type'] == 'array' and row['target_data_type'] != 'array':
            source_col = str(row['source_column'])
            exploded_alias_name = f"{source_col[:3]}_{source_col[-3:]}_expl"
            df.at[idx, 'lateral_exploded_alias'] = f"LATERAL VIEW EXPLODE({source_col}) AS {exploded_alias_name}"

        # Determine correct alias for SQL
        if row['target_data_type'] == 'array':
            alias_name = row['target_sub_column'] or row['target_column']
        else:
            alias_name = row['target_column']

        # Direct mapping if transformation logic is empty
        if pd.isna(row['transformation_logic']) or str(row['transformation_logic']).strip() == "":
            source_ref = exploded_alias_name + "." + (row['source_sub_column'] or row['source_column']) if exploded_alias_name else row['source_column']
            df.at[idx, 'generated_sql_expression'] = f"{source_ref} AS {alias_name}"
            continue

        # Build prompt for LLM
        prompt = build_prompt(row, exploded_alias=exploded_alias_name)
        response = llm.invoke([HumanMessage(content=prompt)])
        expr = response.content.replace("```", "").replace("sql", "").replace("`","").strip()
        df.at[idx, 'generated_sql_expression'] = expr

# 4. Save output
df.to_excel(OUTPUT_FILE, index=False)
print(f"SQL expressions written to {OUTPUT_FILE}")
