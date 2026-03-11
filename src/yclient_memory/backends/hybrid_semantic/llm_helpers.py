def llm_json(runtime, prompt_key: str, variables: dict, config: dict | None = None):
    return runtime.llm_json(prompt_key, variables, config)


def llm_text(runtime, prompt_key: str, variables: dict, config: dict | None = None):
    return runtime.llm_text(prompt_key, variables, config)
