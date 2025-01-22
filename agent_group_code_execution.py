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
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_function_from_prompt import KernelFunctionFromPrompt
from semantic_kernel.exceptions.function_exceptions import FunctionExecutionException

# Load environment variables
dotenv.load_dotenv()

# Config
streaming = False
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

def log_message(message):
    COLORS = {"MESSAGE": "\033[95m", "ENDC": "\033[0m"}  # Reset
    print(f"{COLORS['MESSAGE']}{message}{COLORS['ENDC']}")

def log_flow(from_agent, to_agent):
    COLORS = {
        "FROM_AGENT": "\033[94m",  # Blue
        "TO_AGENT": "\033[92m",  # Green
        "ENDC": "\033[0m",  # Reset
    }
    print(
        f"{COLORS['FROM_AGENT']}{from_agent.capitalize()}{COLORS['ENDC']} (to {COLORS['TO_AGENT']}{to_agent.capitalize() or '*'}{COLORS['ENDC']}): \n"
    )

def log_separator():
    YELLOW = "\033[93m"
    ENDC = "\033[0m"
    print(
        f"{YELLOW}>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>{ENDC}\n"
    )

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

class CodeExecutionPlugin:
    """
    A plugin that safely executes Python code in an isolated environment.
    """

    def execute_code(self, code: str) -> str:
        """
        Executes provided Python code in a restricted environment.
        Returns the local variables modified by the executed code.
        """
        logger.info("CodeExecutionPlugin: Executing code")
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
            logger.error(f"CodeExecutionPlugin: Error executing code: {e}")
            return f"Error executing code: {e}"

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
    return kernel

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
            function_choice_behavior=FunctionChoiceBehavior.Auto(
                filters={"included_plugins": ["CodeExecutionPlugin"]}
            ),
        ),
    )

    selection_function = KernelFunctionFromPrompt(
        function_name="selection",
        prompt=f"""
        Determine which participant takes the next turn in a conversation based on the the most recent participant.
        State only the name of the participant to take the next turn.
        No participant should take more than one turn in a row.

        Choose only from these participants:
        - {CODEWRITER_NAME}
        - {CODEEXECUTOR_NAME}

        Always follow these rules when selecting the next participant:
        - After user input, it is {CODEWRITER_NAME}'s turn.
        - After {CODEWRITER_NAME} replies, it is {CODEEXECUTOR_NAME}'s turn.
        - After {CODEEXECUTOR_NAME} provides feedback, it is {CODEWRITER_NAME}'s turn.

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

        if user_input.startswith("@") and len(input) > 1:
            file_path = input[1:]
            try:
                if not os.path.exists(file_path):
                    print(f"Unable to access file: {file_path}")
                    continue
                with open(file_path) as file:
                    user_input = file.read()
            except Exception:
                print(f"Unable to access file: {file_path}")
                continue

        await chat.add_chat_message(ChatMessageContent(role=AuthorRole.USER, content=user_input))

        async for response in chat.invoke():
            print(f"\n# {response.role} - {response.name or '*'}: '{response.content}'")

        if chat.is_complete:
            is_complete = True
            break

if __name__ == "__main__":
    asyncio.run(main())
