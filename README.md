# Semantic Kernel Code Execution Example

This repository contains examples of using Semantic Kernel to execute Python code either locally or in a sandboxed environment. The examples demonstrate how to set up and use `ChatCompletionAgent` to process user input, generate Python code, and execute it safely.

## Features

- **Azure OpenAI Integration**: Uses Azure OpenAI services for code generation.
- **Safe Code Execution**: Executes Python code in a restricted environment to ensure safety.
- **Logging**: Provides detailed logging for debugging and monitoring.
- **Environment Configuration**: Uses environment variables for configuration.
- **Flexible Execution**: Can be executed locally or in the [Azure Container Apps Dynamic Sessions Code Interpreter](https://learn.microsoft.com/en-us/azure/container-apps/sessions-code-interpreter).
- **Agent Group Chat**: Demonstrates how to create a group chat with multiple agents working together.

## Getting Started

### Prerequisites

- Python 3.12
- Azure OpenAI account

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/john-carroll-sw/semantic-kernel-agent-code-execution.git
    cd semantic-kernel-agent-code-execution
    ```

2. Create and activate a virtual environment:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up your environment variables in a `.env` file. You can use the provided [`.env.sample`](.env.sample) as a template:
    ```dotenv
    AZURE_OPENAI_ENDPOINT=https://your-openai-endpoint.openai.azure.com/
    AZURE_OPENAI_API_KEY="your-api-key"
    AZURE_OPENAI_API_VERSION=2024-08-01-preview
    AZURE_OPENAI_DEPLOYMENT=your-deployment-name
    AZURE_CODE_INTERPRETER_POOL_ENDPOINT=your-pool-endpoint
    ```

    - `AZURE_OPENAI_ENDPOINT`: The endpoint for your Azure OpenAI service.
    - `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key.
    - `AZURE_OPENAI_API_VERSION`: The API version to use for Azure OpenAI.
    - `AZURE_OPENAI_DEPLOYMENT`: The deployment name for your Azure OpenAI service.
    - `AZURE_CODE_INTERPRETER_POOL_ENDPOINT`: The endpoint for managing the [Azure Container Apps Dynamic Sessions Code Interpreter](https://learn.microsoft.com/en-us/azure/container-apps/sessions-code-interpreter). **Only add this if you plan on using the ACA Dynamic Sessions Code Interpreter which uses the `SessionsPythonTool`.**

### Usage

By default, the generated code is set to run locally. If you want to run the code in a sandboxed environment, make sure to configure the `AZURE_CODE_INTERPRETER_POOL_ENDPOINT` and set `USE_CODE_INTERPRETER_SESSIONS_TOOL` to `True` in the respective scripts.

#### Code Execution Example

Run the script:
```sh
python code_execution_example.py
```

Enter your message when prompted, and the agent will process it, generate Python code, and execute it. This example demonstrates how to execute code either locally or in a sandboxed environment.

#### Agent Group Code Execution Example

Run the script:
```sh
python agent_group_code_execution.py
```

Enter your message when prompted, and the agents will work together to generate and execute Python code. This example also supports executing code either locally or in a sandboxed environment.

#### Agent Group Writing Example

Run the script:
```sh
python agent_group_writing_example.py
```

Enter your message when prompted, and the agents will work together to review and rewrite the content.

### Example Questions for Code Interpreter

For examples of good questions or prompts to use with a code interpreter, refer to the [code_interpreter_questions.md](code_interpreter_questions.md) file.

### License

This project is licensed under the MIT License.