import os
import dotenv
import datetime
import logging
import tempfile

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential
from functools import reduce
from semantic_kernel import Kernel
from semantic_kernel.agents.chat_completion.chat_completion_agent import (
    ChatCompletionAgent,
)
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import (
    AzureChatCompletion,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.core_plugins.sessions_python_tool.sessions_python_plugin import (
    SessionsPythonTool,
)
from semantic_kernel.exceptions.function_exceptions import FunctionExecutionException
from logging_utils import log_message, log_flow, log_separator

# Config
dotenv.load_dotenv()
streaming = False
USE_CODE_INTERPRETER_SESSIONS_TOOL = False  # Set to False to use CodeExecutionPlugin
pool_management_endpoint = os.getenv("POOL_MANAGEMENT_ENDPOINT")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def auth_callback_factory(scope):
    auth_token = None

    async def auth_callback() -> str:
        """Auth callback for the SessionsPythonTool.
        This is a sample auth callback that shows how to use Azure's DefaultAzureCredential
        to get an access token.
        """
        nonlocal auth_token
        current_utc_timestamp = int(
            datetime.datetime.now(datetime.timezone.utc).timestamp()
        )

        if not auth_token or auth_token.expires_on < current_utc_timestamp:
            credential = DefaultAzureCredential()

            try:
                auth_token = credential.get_token(scope)
            except ClientAuthenticationError as cae:
                err_messages = getattr(cae, "messages", [])
                raise FunctionExecutionException(
                    f"Failed to retrieve the client auth token with messages: {' '.join(err_messages)}"
                ) from cae

        return auth_token.token

    return auth_callback


async def invoke_agent(
    agent: ChatCompletionAgent, to_agent: str, input: str, history: ChatHistory
):
    """Invoke the agent with the user input."""
    history.add_user_message(input)

    if streaming:
        contents = []
        content_name = ""
        async for content in agent.invoke_stream(history):
            content_name = content.name
            contents.append(content)
        streaming_chat_message = reduce(lambda first, second: first + second, contents)
        log_flow(content_name, to_agent)
        print(f"\033[94m{streaming_chat_message}'\n")
        history.add_message(content)
    else:
        async for content in agent.invoke(history):
            log_flow(content.name, to_agent)
            print(f"\033[94m{content.content}'\n")
            history.add_message(content)

    if history.messages:
        last_message = history.messages[-1]
    return last_message


class CodeExecutionPlugin:
    """
    A plugin that safely executes Python code in an isolated environment.
    """

    def execute_code(self, code: str) -> str:
        """
        Executes provided Python code in a restricted environment.
        Returns the local variables modified by the executed code.
        """
        try:
            # Save the code to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as temp_file:
                temp_file.write(code.encode())
                temp_file_path = temp_file.name

            # Log the generated code
            logger.info(f"Generated code:\n{code}")

            # Save the generated code to a file
            with open("generated_code.py", "w") as file:
                file.write(code)

            # Restricted execution: No built-in functions, no access to external modules
            safe_globals = {"__builtins__": {}}  # Block built-ins
            safe_locals = {}  # Create a local execution scope

            # Read the code from the temporary file and execute it safely
            with open(temp_file_path, "r") as file:
                exec(file.read(), safe_globals, safe_locals)

            # Return only defined variables (not execution metadata)
            return str(
                {
                    key: safe_locals[key]
                    for key in safe_locals
                    if not key.startswith("__")
                }
            )
        except Exception as e:
            return f"Error executing code: {e}"


async def main():
    message = input("Enter your message: ")

    # Instantiate the Kernel
    kernel = Kernel()

    # Add AzureChatCompletion service for the agent.
    kernel.add_service(
        AzureChatCompletion(
            service_id="coder_agent",
            # ad_token_provider=auth_callback_factory(
            #     "https://cognitiveservices.azure.com/.default"
            # ),
            endpoint=azure_openai_endpoint,
            deployment_name=azure_openai_deployment,
            api_key=azure_openai_api_key,
            api_version=azure_openai_api_version,
        )
    )

    if USE_CODE_INTERPRETER_SESSIONS_TOOL:
        # Add the code interpreter sessions pool to the Kernel
        kernel.add_plugin(
            plugin_name="CodeInterpreterSessionsTool",
            plugin=SessionsPythonTool(
                auth_callback=auth_callback_factory("https://dynamicsessions.io/.default"),
                pool_management_endpoint=pool_management_endpoint,
            ),
        )
    else:
        kernel.add_plugin(plugin_name="CodeExecutionPlugin", plugin=CodeExecutionPlugin())

    # Create the agent with specific instructions
    coder_agent = ChatCompletionAgent(
        kernel=kernel,
        service_id="coder_agent",
        name="coder_agent",
        instructions="""
            You are a Python Code agent.
            Your task is to solve the user's prompts by writing Python code and executing the code using the provided tool.
            Your output should be the result from executing the generated Python code.
            This code will be executed in a sandbox, resulting in result, stdout, or stderr.
            All necessary libraries have already been installed.
            Ensure the response to the user is readable and does not contain any code.
        """,
        execution_settings=AzureChatPromptExecutionSettings(
            service_id="coder_agent",
            temperature=0.0,
            max_tokens=1000,
            function_choice_behavior=FunctionChoiceBehavior.Required(
                filters={"included_plugins": ["CodeInterpreterSessionsTool"]} if USE_CODE_INTERPRETER_SESSIONS_TOOL else {"included_plugins": ["CodeExecutionPlugin"]}
            ),
        ),
    )

    chat_history = ChatHistory()

    # Main logical flow to invoke the agent for code execution
    try:
        log_separator()
        log_message("Received chat message")
        log_flow("User", "")
        print(f"{message}\n")

        # Invoke coder agent
        log_separator()
        log_message("Invoking coder agent")
        execution_result = await invoke_agent(
            coder_agent, "User", message, chat_history
        )

        response = {
            "execution_result": str(execution_result),
        }

        log_separator()
        logger.info(f"Returning response: {str(response)}")

        # Print the response
        print(response)

        # Save the response to a local file
        with open("execution_result.txt", "w") as file:
            file.write(str(response))

    except Exception as e:
        logger.error(f"Kernel invocation failed: {e}")
        response = {"error": str(e)}

        # Print the error response
        print(response)

        # Save the error response to a local file
        with open("execution_result.txt", "w") as file:
            file.write(str(response))

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
