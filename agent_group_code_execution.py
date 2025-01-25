import asyncio
import datetime
import os
import dotenv
import logging
import tempfile

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential
from functools import reduce
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies.selection.kernel_function_selection_strategy import (
    KernelFunctionSelectionStrategy,
)
from semantic_kernel.agents.strategies.termination.kernel_function_termination_strategy import (
    KernelFunctionTerminationStrategy,
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
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.core_plugins.sessions_python_tool.sessions_python_plugin import (
    SessionsPythonTool,
)
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_from_prompt import KernelFunctionFromPrompt
from semantic_kernel.exceptions.function_exceptions import FunctionExecutionException
from logging_utils import log_message, log_flow, log_from_agent, log_separator
from local_python_plugin import LocalPythonPlugin

# Load environment variables
dotenv.load_dotenv()

# Config
USE_CODE_INTERPRETER_SESSIONS_TOOL = False  # Set to False to use LocalCodeExecutionTool
azure_code_interpreter_pool_endpoint = os.getenv("AZURE_CODE_INTERPRETER_POOL_ENDPOINT")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

CODEWRITER_NAME = "CodeWriter"
CODEEXECUTOR_NAME = "CodeExecutor"

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


def _create_kernel_with_chat_completion(service_id: str) -> Kernel:
    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            service_id=service_id,
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
                pool_management_endpoint=azure_code_interpreter_pool_endpoint,
            ),
        )
    else:
        kernel.add_plugin(plugin_name="LocalCodeExecutionTool", plugin=LocalPythonPlugin())
    
    return kernel

async def main():
    agent_writer = ChatCompletionAgent(
        service_id=CODEWRITER_NAME,
        kernel=_create_kernel_with_chat_completion(CODEWRITER_NAME),
        name=CODEWRITER_NAME,
        instructions=f"""
            You are a {CODEWRITER_NAME} agent. 
            You use your coding skill to solve problems. 
            You output only valid python code. 
            This valid code will be executed in a sandbox, resulting in result, stdout, or stderr. 
            All necessary libraries have already been installed.
            You are entering a work session with other agents: {CODEEXECUTOR_NAME}.
            Do NOT execute code. Only return the code you write for it to be executed by the {CODEEXECUTOR_NAME} agent.
        """,
        execution_settings=AzureChatPromptExecutionSettings(
            service_id=CODEWRITER_NAME,
            temperature=0.0,
            max_tokens=1000,
            function_choice_behavior=FunctionChoiceBehavior.NoneInvoke(),
        ),
    )

    agent_executor = ChatCompletionAgent(
        service_id=CODEEXECUTOR_NAME,
        kernel=_create_kernel_with_chat_completion(CODEEXECUTOR_NAME),
        name=CODEEXECUTOR_NAME,
        instructions=f"""
            You are a {CODEEXECUTOR_NAME} agent.
            You have access to an IPython kernel to execute Python code. 
            Your output should be the result from executing valid python code. 
            This valid code will be executed in a sandbox, resulting in result, stdout, or stderr. 
            All necessary libraries have already been installed.
            You are entering a work session with other agents: {CODEWRITER_NAME}.
            Execute the code given to you, using the output, return a chat response to the user.
            Ensure the response to the user is readable to a human and there is not any code.
            If you do not call a function, do not hallucinate the response of a code execution, 
            instead if you cannot run code simply say you cannot run code.
        """,
        execution_settings=AzureChatPromptExecutionSettings(
            service_id=CODEEXECUTOR_NAME,
            temperature=0.0,
            max_tokens=1000,
            function_choice_behavior=FunctionChoiceBehavior.Required(
                filters={"included_plugins": ["CodeInterpreterSessionsTool"]} if USE_CODE_INTERPRETER_SESSIONS_TOOL else {"included_plugins": ["LocalCodeExecutionTool"]}
            ),
        ),
    )

    selection_function = KernelFunctionFromPrompt(
        function_name="selection",
        prompt=f"""
        Determine which participant takes the next turn in a conversation based on the most recent participant.
        State only the name of the participant to take the next turn.
        No participant should take more than one turn in a row.

        Choose only from these participants:
        - {CODEWRITER_NAME}
        - {CODEEXECUTOR_NAME}

        Always follow these rules when selecting the next participant:
        - After user input, it is {CODEWRITER_NAME}'s turn.
        - After {CODEWRITER_NAME} replies, it is {CODEEXECUTOR_NAME}'s turn.
        - After {CODEEXECUTOR_NAME} replies, it is done.

        History:
        {{{{$history}}}}
        """,
    )

    TERMINATION_KEYWORD = "yes"

    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=f"""
            Examine the RESPONSE and determine whether the content has been deemed satisfactory.
            If content is satisfactory, respond with a single word without explanation: {TERMINATION_KEYWORD}.
            If specific suggestions are being provided, it is not satisfactory.
            If no correction is suggested, it is satisfactory.

            RESPONSE:
            {{{{$history}}}}
            """,
    )

    chat = AgentGroupChat(
        agents=[agent_writer, agent_executor],
        selection_strategy=KernelFunctionSelectionStrategy(
            function=selection_function,
            kernel=_create_kernel_with_chat_completion("selection"),
            result_parser=lambda result: str(result.value[0]) if result.value is not None else CODEWRITER_NAME,
            agent_variable_name="agents",
            history_variable_name="history",
        ),
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[agent_executor],
            function=termination_function,
            kernel=_create_kernel_with_chat_completion("termination"),
            result_parser=lambda result: TERMINATION_KEYWORD in str(result.value[0]).lower(),
            history_variable_name="history",
            maximum_iterations=10,
        ),
    )

    is_complete: bool = False
    while not is_complete:
        user_input = input("User:> ")
        if not user_input:
            continue

        if user_input.lower() == "exit":
            is_complete = True
            break

        if user_input.lower() == "reset":
            await chat.reset()
            print("[Conversation has been reset]")
            continue

        if user_input.startswith("@") and len(user_input) > 1:
            file_path = user_input[1:]
            try:
                if not os.path.exists(file_path):
                    print(f"Unable to access file: {file_path}")
                    continue
                with open(file_path) as file:
                    user_input = file.read()
            except Exception:
                print(f"Unable to access file: {file_path}")
                continue

        log_separator()
        log_message("Received chat message")
        log_flow("User", "")
        print(f"{user_input}\n")

        await chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=user_input))

        async for response in chat.invoke():
            log_separator()
            log_message(f"Invoking {response.name} agent")
            log_from_agent(response.name)
            print(f"\033[94m{response.content}'\n")

        if chat.is_complete:
            is_complete = True
            print(chat.history)
            break

if __name__ == "__main__":
    asyncio.run(main())
