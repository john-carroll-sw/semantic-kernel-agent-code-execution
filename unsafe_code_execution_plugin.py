import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class UnsafeCodeExecutionPlugin:
    """
    A plugin that executes Python code with fewer restrictions, allowing Internet access and file saving.
    """

    def execute_code(self, code: str) -> str:
        """
        Executes provided Python code with fewer restrictions.
        Returns the local variables modified by the executed code.
        """
        logger.info("UnsafeCodeExecutionPlugin: Executing code")
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

            # Execute the code with fewer restrictions
            safe_globals = {"__builtins__": __builtins__}  # Allow built-ins
            safe_locals = {}  # Create a local execution scope

            # Read the code from the temporary file and execute it
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
            logger.error(f"UnsafeCodeExecutionPlugin: Error executing code: {e}")
            return f"Error executing code: {e}"
