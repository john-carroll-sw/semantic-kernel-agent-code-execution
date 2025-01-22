# Semantic Kernel Code Execution Example

This repository contains examples of using Semantic Kernel to execute Python code in a sandboxed environment. The examples demonstrate how to set up and use `ChatCompletionAgent` to process user input, generate Python code, and execute it safely.

## Features

- **Azure OpenAI Integration**: Uses Azure OpenAI services for code generation.
- **Safe Code Execution**: Executes Python code in a restricted environment to ensure safety.
- **Logging**: Provides detailed logging for debugging and monitoring.
- **Environment Configuration**: Uses environment variables for configuration.
- **Flexible Execution**: Can be executed locally or in the Azure Container Apps Dynamic Sessions Code Interpreter Pool.
- **Agent Group Chat**: Demonstrates how to create a group chat with multiple agents working together.

## Getting Started

### Prerequisites

- Python 3.12
- Azure OpenAI account

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/semantic-kernel-code-execution-example.git
    cd semantic-kernel-code-execution-example
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
    POOL_MANAGEMENT_ENDPOINT=your-pool-endpoint
    ```

### Usage

#### Code Execution Example

Run the script:
```sh
python code_execution_example.py
```

Enter your message when prompted, and the agent will process it, generate Python code, and execute it.

#### Agent Group Code Execution Example

Run the script:
```sh
python agent_group_code_execution.py
```

Enter your message when prompted, and the agents will work together to generate and execute Python code.

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