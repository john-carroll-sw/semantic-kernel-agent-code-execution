import logging
import os
import re
import tempfile
from io import BytesIO
from typing import Annotated

from semantic_kernel.kernel_pydantic import KernelBaseModel
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.exceptions.function_exceptions import FunctionExecutionException

logger = logging.getLogger(__name__)

class LocalPythonPlugin(KernelBaseModel):
    """
    A plugin that executes Python code locally with unrestricted access to built-in functions.
    WARNING: This plugin allows unrestricted access to built-in functions and should be used with caution.
    """

    # region Helper Methods
    def _sanitize_input(self, code: str) -> str:
        """Sanitize input to the python REPL.

        Remove whitespace, backtick & python (if llm mistakes python console as terminal).

        Args:
            code (str): The query to sanitize
        Returns:
            str: The sanitized query
        """
        # Removes `, whitespace & python from start
        code = re.sub(r"^(\s|`)*(?i:python)?\s*", "", code)
        # Removes whitespace & ` from end
        return re.sub(r"(\s|`)*$", "", code)

    def _construct_remote_file_path(self, remote_file_path: str) -> str:
        """Construct the remote file path.

        Args:
            remote_file_path (str): The remote file path.

        Returns:
            str: The remote file path.
        """
        if not remote_file_path.startswith("/tmp/"):
            remote_file_path = f"/tmp/{remote_file_path}"
        return remote_file_path

    # endregion

    # region Kernel Functions
    @kernel_function(
        description="""Executes the provided Python code.
                     Start and end the code snippet with double quotes to define it as a string.
                     Insert \\n within the string wherever a new line should appear.
                     Add spaces directly after \\n sequences to replicate indentation.
                     Use \" to include double quotes within the code without ending the string.
                     Keep everything in a single line; the \\n sequences will represent line breaks
                     when the string is processed or displayed.
                     WARNING: This plugin allows unrestricted access to built-in functions and should be used with caution.
                     """,
        name="execute_code",
    )
    def execute_code(self, code: Annotated[str, "The valid Python code to execute"]) -> str:
        """Executes the provided Python code.

        Args:
            code (str): The valid Python code to execute
        Returns:
            str: The result of the Python code execution in the form of Result, Stdout, and Stderr
        Raises:
            FunctionExecutionException: If the provided code is empty.
        """
        if not code:
            raise FunctionExecutionException("The provided code is empty")

        code = self._sanitize_input(code)

        logger.info(f"Executing Python code: {code}")

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
                
            print(f"Generated code:\n{code}")

            # Unrestricted execution: Allow all built-in functions
            safe_globals = {"__builtins__": __builtins__}  # Allow all built-ins
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
            logger.error(f"LocalPythonPlugin: Error executing code: {e}")
            return f"Error executing code: {e}"

    # endregion
