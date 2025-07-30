import glob
import json
import logging
import os
import sys
import time
from typing import cast, List

import keyring
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from .AiRegistry import AiRegistry, AiModel
from  .keprompt_functions import DefinedFunctions, readfile
from .AiPrompt import AiTextPart, AiImagePart, AiCall, AiResult, AiPrompt, AiMessage, MAX_LINE_LENGTH
from  .keprompt_util import TOP_LEFT, BOTTOM_LEFT, VERTICAL, HORIZONTAL, TOP_RIGHT, RIGHT_TRIANGLE, \
    LEFT_TRIANGLE, \
    HORIZONTAL_LINE, BOTTOM_RIGHT, CIRCLE, backup_file
from .keprompt_logger import KepromptLogger, LogMode

console = Console()
terminal_width = console.size.width

FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]",
                    handlers=[RichHandler(console=console, rich_tracebacks=True, )])

log = logging.getLogger(__file__)

# Global routines
def print_prompt_code(prompt_files: list[str]) -> None:
    table = Table(title="Execution Messages")
    table.add_column("Prompt", style="cyan bold", no_wrap=True)
    table.add_column("Lno", style="blue bold", no_wrap=True)
    table.add_column("Cmd", style="green bold", no_wrap=True)
    table.add_column("Params", style="dark_green bold")

    for prompt_file in prompt_files:
        # console.print(f"{prompt_file}")
        try:
            # Create minimal global variables for parsing
            from .keprompt import create_global_variables
            global_vars = create_global_variables()
            vm: VM = VM(prompt_file, global_vars)
            vm.parse_prompt()
        except Exception as e:
            console.print(f"[bold red]Error parsing file {prompt_file} : {str(e)}[/bold red]")
            console.print_exception()
            sys.exit(1)
        title = os.path.basename(prompt_file)
        if vm.statements:
            for stmt in vm.statements:
                table.add_row(title, f"{stmt.msg_no:03}", stmt.keyword, stmt.value)
                title = ''
            table.add_row('───────────────', '───', '─────────', '──────────────────────────────')
    console.print(table)


class StmtSyntaxError(Exception):
    pass

class VM:
    """Class to hold Prompt Virtual Machine execution state"""

    def __init__(self, filename: str, global_vars: dict[str, any], log_mode: LogMode = LogMode.PRODUCTION, log_identifier: str = None):
        self.filename = filename
        self.log_mode = log_mode
        self.ip: int = 0
        
        # Use the provided global variables (no defaults, no conditionals)
        self.vdict = global_vars.copy()  # Copy to avoid modifying original
        
        self.llm: dict[str, any] = dict()
        self.statements: list[StmtPrompt] = []
        self.prompt: AiPrompt = AiPrompt(self)
        self.header: dict[str, any] = {}
        self.data: str = ''
        
        # Extract prompt name for logger
        prompt_name = os.path.splitext(os.path.basename(filename))[0]
        
        # Initialize the new structured logger
        self.logger = KepromptLogger(prompt_name=prompt_name, mode=log_mode, log_identifier=log_identifier)
        
        # Keep old console for backward compatibility during transition
        self.console = Console(width=terminal_width)  # Console for terminal
        self.file_console = None  # Console for file, initialized in execute
        self.model: AiModel = None
        self.model_name: str = ""
        self.company: str = ""
        self.system_value: str = ""
        self.toks_in = 0
        self.cost_in = 0
        self.toks_out = 0
        self.cost_out = 0
        self.total = 0
        self.api_key: str = ''
        self.interaction_no: int = 0

    def print(self, *args, **kwargs):
        """Print method to output to both console and file."""
        self.console.print(*args, **kwargs)  # Print to terminal
        if self.file_console:  # Ensure file is open
            self.file_console.print(*args, **kwargs)  # Print to file

    def debug_print(self, elements: list[str]) -> None:
        """Pretty prints the Virtual Machine class state for debugging"""

        if 'all' in elements:
            elements = ['header', 'llm', 'messages', 'statements', 'variables']

        if 'header' in elements:
            table = Table(title=f"Header Debug Info for {self.filename}")
            table.add_column("VM Property", style="cyan", no_wrap=True, width=35)
            table.add_column("Value", style="green", no_wrap=True)

            table.add_row("Filename", self.filename)
            table.add_row("Log Mode:", str(self.log_mode))
            table.add_row("IP", str(self.ip))
            table.add_row("url", str(self.llm['url']))
            table.add_row("header", str(self.header))
            table.add_row("data", str(self.data))

            console.print(table)

        # print varname: value
        if 'llm' in elements:
            table = Table(title=f"LLM Debug Info for {self.filename}")

            # Basic info section
            table.add_column("LLM Property", style="cyan", no_wrap=True, width=35)
            table.add_column("Value", style="green", no_wrap=True)

            if self.llm:
                for key, value in self.llm.items():
                    if key == 'API_KEY':
                        value = '... top secret ...'
                    table.add_row(key, str(value))
            else:
                table.add_row("LLM Config", "Not Set")
            console.print(table)

        # Variables dictionary
        # Messages
        if 'messages' in elements:
            table = Table(title=f"Messages Debug Info for {self.filename}")
            # Basic info section
            table.add_column("Mno", style="cyan", no_wrap=True)
            table.add_column("Role", style="blue", no_wrap=True)
            table.add_column("Pno", style="green", no_wrap=True)
            table.add_column("Part", style="green", no_wrap=True, max_width=terminal_width - 25)
            colors = {'user': "[bold steel_blue3]",
                      'assistant': "[bold yellow]",
                      'model': "[bold yellow]",
                      'system': "[bold magenta]",
                      "function": "[bold dark_green]",
                      "result": "[bold dark_green]"}
            if self.prompt:
                for msg_no, msg in enumerate(self.prompt.messages):
                    role = f"{colors[msg.role]}{msg.role}[/]"
                    msg_no_str = f"{msg_no:02}"
                    for pno, part in enumerate(msg.content):
                        part_no = f"{colors[msg.role]}{pno:02}[/]"
                        for substring in str(part).split('\n'):
                            t = f"{colors[msg.role]}{substring}[/]"
                            table.add_row(msg_no_str, role, part_no, t)
                            msg_no_str = ""
                            role = ''
                            part_no = ''
            else:
                table.add_row("", "", "", "Empty")
            console.print(table)

        # Statements
        if 'statements' in elements:
            table = Table(title=f"Statements Debug Info for {self.filename}")
            # Basic info section
            table.add_column("Sno", style="cyan", no_wrap=True)
            table.add_column("Keyword", style="blue", no_wrap=True)
            table.add_column("Value", style="green", no_wrap=True)
            if self.statements:
                last_idx = None
                for idx, stmt in enumerate(self.statements):
                    # input_string = stmt.value.replace('\n', '\\n')
                    hdr = stmt.keyword
                    for substring in stmt.value.split('\n'):
                        if last_idx != idx:
                            str_idx = f"{idx:02}"
                        else:
                            str_idx = ''
                        table.add_row(str_idx, hdr, substring)
                        hdr = ''
                        last_idx = idx
            else:
                table.add_row("00", "", "Empty")
            console.print(table)

        if 'variables' in elements:
            table = Table(title=f"Variables for {self.filename}")
            # Basic info section
            table.add_column("Name", style="cyan", no_wrap=True, width=35)
            table.add_column("Value", style="green", no_wrap=True)
            if self.vdict:
                for key, value in self.vdict.items():
                    table.add_row(key, str(value))
            else:
                table.add_row("Variables", "Empty")
            console.print(table)

    def set_variable(self, key: str, value: any):
        """Set variable with automatic logging."""
        self.vdict[key] = value
        self.logger.log_variable_assignment(key, str(value))

    def get_variable(self, key: str):
        """Get variable with automatic logging."""
        value = self.vdict[key]
        self.logger.log_variable_retrieval(key, str(value))
        return value

    def substitute(self, text: str):
        """
        Substitute variables in text using configurable prefix and postfix delimiters.
        Gets delimiters directly from dictionary for future subroutine scoping compatibility.
        """
        # Get delimiters directly from dictionary (supports future variable stack for subroutines)
        prefix = self.vdict.get('Prefix', '<<')
        postfix = self.vdict.get('Postfix', '>>')
        
        while postfix in text:
            front, back = text.split(postfix, 1)
            if prefix not in front:
                return text  # No matching begin marker found

            last_begin = front.rfind(prefix)
            if last_begin == -1:
                return text  # No begin marker found

            # Extract variable name
            variable_name = front[last_begin + len(prefix):]

            # Handle nested dictionaries
            keys = variable_name.split('.')
            value = self.vdict
            try:
                for key in keys:
                    value = value[key]
            except (KeyError, TypeError):
                raise ValueError(f"Variable '{variable_name}' is not defined")

            # Log variable retrieval (substitution)
            self.logger.log_variable_retrieval(variable_name, str(value))
            
            # Replace the matched part with the value
            text = front[:last_begin] + str(value) + back

        return text

    def parse_prompt(self) -> None:
        """Parse the prompt file and create a list of statements.
            parse according to rules in docs/PromptLanguage.md
        """

        lines: list[str]

        # read .prompt file
        with open(self.filename, 'r') as file:
            lines = file.readlines()

        # Delete all trailing blank lines
        while lines[-1][0].strip() == '': lines.pop()

        for lno, line in enumerate(lines):
            try:
                line = line.strip()  # remove trailing blanks
                if not line: continue  # skip blank lines

                # Get Keyword and Value in all cases.

                if line[0] != '.':  # No Dot in col 1
                    keyword, value = '.text', line
                else:
                    # has '.' in col 1
                    if ' ' in line:  # has space therefore has .keyword<space>value
                        keyword, value = line.split(' ', 1)
                    else:  # No space therefore only .keyword
                        keyword, value = line, ''

                    if keyword not in keywords:  # last case have .keyword but it is not a valid keyword
                        keyword, value = '.text', line

                # okay concatenate .text
                if lno and keyword == '.text':
                    last = self.statements[-1]
                    if last.keyword in ['.assistant', '.system', '.text', '.user']:
                        last.value = f"{last.value}\n{value}".strip()
                        continue

                self.statements.append(make_statement(self, len(self.statements), keyword=keyword, value=value))

            except Exception as e:
                raise StmtSyntaxError(
                    f"{VERTICAL} [red]Error parsing file {self.filename}:{lno} error: {str(e)}.[/]\n\n")

        # Implicit .exec
        if lines[-1][0:5] != '.exec':
            self.statements.append(make_statement(self, len(self.statements), keyword='.exec', value=''))

        return

    def print_exception(self) -> None:
        """Print exception information to both console and file outputs."""
        self.console.print()
        self.console.print_exception(show_locals=True, width=terminal_width)  # Print to terminal
        if self.file_console:  # Ensure file is open
            self.file_console.print_exception()  # Print to file

    def load_llm(self, parms: dict[str, str]) -> None:

        if 'model' not in parms:
            raise StmtSyntaxError(f".llm syntax error: model not defined")
        self.model_name = parms['model']

        if self.model_name not in AiRegistry.models:
            raise StmtSyntaxError(f"Not Defined Error: Model {self.model_name} is not defined")
        self.model = AiRegistry.get_model(self.model_name)

        if self.model.company == '':
            raise StmtSyntaxError(f"Bad Model Definition error: company not defined for model {self.model_name}")
        self.company = self.model.company

        # copy parms to vdict
        for k, v in parms.items():
            self.vdict[k] = v

        self.vdict['company'] = self.company
        self.vdict['filename'] = self.filename
        self.vdict['model'] = self.model

    def execute(self) -> None:
        """Execute the statements in the prompt file using the new structured logging system."""
        
        # Use structured logging based on mode
        if self.log_mode in [LogMode.LOG, LogMode.DEBUG]:
            # Logging/Debug mode - use structured logger with rich UI
            self.logger.print_header(self.filename)

            for stmt_no, stmt in enumerate(self.statements):
                try:
                    stmt.execute(self)
                except Exception as e:
                    self.logger.log_error(f"Error executing statement {stmt_no}: {str(e)}")
                    sys.exit(9)

                if stmt.keyword == '.exit':
                    break

            self.logger.print_footer()
            self.logger.close()
        else:
            # Production mode - clean execution, minimal output
            for stmt_no, stmt in enumerate(self.statements):
                try:
                    stmt.execute(self)
                except Exception as e:
                    # Errors go to stderr in production mode
                    print(f"Error: {str(e)}", file=sys.stderr)
                    sys.exit(9)

                if stmt.keyword == '.exit':
                    break

    def print_with_wrap(self, is_response: bool, line: str) -> None:
        line_len = terminal_width - 23

        color = '[bold green]'
        if is_response:
            color = '[bold blue]'

        print_line = line.replace('\n', '\\n')[:line_len]  # Truncate if longer
        print_line = f"{print_line:<{line_len + 8}}"  # Ensure it is exactly line_len wide with spaces

        if is_response:
            hdr = f"[bold white]{VERTICAL}[/]{color}   {LEFT_TRIANGLE}{HORIZONTAL_LINE * 5}{CIRCLE}  "
        else:
            hdr = f"[bold white]{VERTICAL}[/]{color}   {CIRCLE}{HORIZONTAL_LINE * 5}{RIGHT_TRIANGLE}  "

        self.print(f"{hdr}[/]:{print_line}[bold white]{VERTICAL}[/]")

    def log_conversation(self, call_id: str = None):
        """Log conversation using the new logger system."""
        messages = self.prompt.to_json()
        
        # Add call_id to the conversation metadata if provided
        if call_id:
            conversation_data = {
                "call_id": call_id,
                "messages": messages
            }
        else:
            conversation_data = messages
            
        self.logger.log_conversation(conversation_data)

    def print_json(self,    label: str, data: dict) -> None:
        """Print a JSON object to the console"""
        self.print(f"{label}:")
        pdict = {}
        for k, v in data.items():
            if isinstance(v, str):
                pdict[k] = v.replace('\n', '\\n')
                if len(v) > MAX_LINE_LENGTH:
                    pdict[k] = f"{v[:MAX_LINE_LENGTH - 3]}..."
                else:
                    pdict[k] = v
            else:
                pdict[k] = v
        self.print(json.dumps(pdict, indent=2, sort_keys=True))

class StmtPrompt:

    def __init__(self, vm: VM, msg_no: int, keyword: str, value: str):
        self.msg_no = msg_no
        self.keyword = keyword
        self.value = value
        self.vm = vm

    def console_str(self) -> str:
        line_len = terminal_width - 14
        header = f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] "
        value = self.value
        if len(value) == 0:
            value = " "
        lines = value.split("\n")

        rtn = ""
        for line in lines:
            while len(line) > 0:
                print_line = f"{line:<{line_len}}[bold white]{VERTICAL}[/]"
                rtn = f"{rtn}\n{header}[green]{print_line}[/]"
                header = f"[bold white]{VERTICAL}[/]            "
                line = line[line_len:]

        return rtn[1:]

    def __str__(self):
        return self.console_str()

    def execute(self, vm: VM) -> None:
        vm.logger.print_statement(self.msg_no, self.keyword, self.value)
        vm.logger.log_statement(self.msg_no, self.keyword, self.value)


class StmtAssistant(StmtPrompt):
    """
    Handles the execution of an assistant-related statement in the VM.

    This class represents a `.assistant` keyword statement from the prompt file. 
    It adds a message with the role of 'assistant' to the AI prompt context. 
    If no value is provided, an empty message is created for the assistant role.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.assistant').
        value (str): The value/content of the statement.

    Methods:
        execute(vm: VM): Executes the statement and updates the VM's prompt with an assistant's message.
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)
        if not self.value:
            vm.prompt.add_message(vm=vm, role='assistant', content=[])
        else:
            vm.prompt.add_message(vm=vm, role='assistant', content=[AiTextPart(vm=vm, text=self.value)])


class StmtClear(StmtPrompt):
    """
    Handles the execution of a clear statement in the VM.

    This class represents a `.clear` keyword statement which is used to delete
    specific files or patterns of files from the system, as specified in the prompt file.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.clear').
        value (str): The value/content of the statement, expected to be a JSON-encoded list of file patterns.

    Methods:
        execute(vm: VM): Executes the `.clear` statement by deleting the specified files.
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)

        try:
            parms = json.loads(self.value)
        except Exception as e:
            vm.logger.log_error(f"Error parsing .clear parameters: {str(e)}")
            vm.logger.print_exception()
            sys.exit(9)

        if not isinstance(parms, list):
            vm.logger.log_error(f"Error parsing .clear parameters expected list, but got {type(parms).__name__}: {self.value}")
            sys.exit(9)

        for k in parms:
            try:
                log_files = glob.glob(k)  # Use glob to find all files matching the pattern

                for file_path in log_files:
                    if os.path.isfile(file_path):  # Ensure that it's a file
                        try:
                            os.remove(file_path)
                            vm.logger.log_warning(f"File {file_path} deleted successfully.")
                        except OSError as e:
                            vm.logger.log_error(f"Error deleting file {file_path}: {str(e)}")
            except OSError as e:
                vm.logger.log_error(f"Error deleting file {k}: {str(e)}")


class StmtCmd(StmtPrompt):
    """
    Handles the execution of a command defined in a prompt file.

    This class represents a `.cmd` keyword statement in the prompt file. The statement 
    specifies a function to be executed along with arguments. The `execute` method 
    parses the command, validates it against the available functions in `DefinedFunctions`, 
    executes the function, and appends the function's output to the AI prompt context.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.cmd').
        value (str): The command string containing the function name and arguments.

    Methods:
        execute(vm: VM): Parses, validates, executes the specified function, and integrates
                         its output into the Virtual Machine's prompt context.
    """

    def execute(self, vm: VM) -> None:
        """Execute a command that was defined in a prompt file (.prompt)"""
        super().execute(vm)

        function_name, args = self.value.split('(', maxsplit=1)
        args = args[:-1]
        args_list = args.split(",")
        function_args = {}

        for arg in args_list:
            name, value = arg.split("=", maxsplit=1)
            function_args[name] = value

        if function_name not in DefinedFunctions:
            vm.print(
                f"[bold red]Error executing {function_name}({function_args}): {function_name} is not defined.[/bold red]")
            raise Exception(f"{function_name} is not defined.")

        try:
            text = DefinedFunctions[function_name](**function_args)
        except Exception as err:
            vm.print(f"Error executing {function_name}({function_args})): {str(err)}")
            raise err

        last_msg = vm.prompt.messages[-1]
        last_msg.content.append(AiTextPart(vm=vm, text=text))


class StmtComment(StmtPrompt):
    """
    Handles the execution of a comment in the prompt file.

    This class represents a `.comment` or `.#` keyword statement in the prompt file. 
    The statement is added for informational purposes and has no effect on the Virtual Machine's state.
    """

    def execute(self, vm: VM) -> None:
        """
        Executes the comment statement by printing it for informational display.
        """
        super().execute(vm)


class StmtDebug(StmtPrompt):
    """
    Handles the execution of a debug command in the prompt file.

    This class represents a `.debug` keyword statement in the prompt file. It is used to inspect
    the internal state of the Virtual Machine (VM) during runtime for debugging purposes.
    The `.debug` command accepts a list of elements to display or inspects the entire state 
    if 'all' is passed.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.debug').
        value (str): The value/content of the statement, specifying which elements of the VM's 
                     state to debug.

    Methods:
        execute(vm: VM): Parses the debugging parameters, validates the input, and outputs the 
                         requested state information of the VM through its debug_print method.
    """

    def execute(self, vm: VM) -> None:
        vm.logger.print_statement(self.msg_no, self.keyword, self.value)

        if not self.value:
            self.value = '["all"]'

        if self.value[0] != '[':
            self.value = f"[{self.value}]"

        # vm.print(self.value)
        try:
            parms = json.loads(self.value)
        except Exception as e:
            vm.print(f"{VERTICAL} [white on red]Error parsing .debug parameters: {str(e)}[/]\n\n")
            vm.print_exception()
            sys.exit(9)

        if not isinstance(parms, list):
            vm.print(
                f"{VERTICAL} [white on red]Error parsing .debug parameters expected list, but got {type(parms).__name__}: {self.value}")
            sys.exit(9)

        vm.debug_print(elements=parms)


class StmtExec(StmtPrompt):
    """
    Handles the execution of an API call to a Language Learning Model (LLM).

    This class represents a `.exec` statement, which is responsible for 
    sending a constructed prompt to the configured LLM, processing the response, 
    and logging the execution details to the system, both for output monitoring 
    and for debugging purposes.

    Attributes:
        vm (VM): The virtual machine instance that contains the program's state.
        msg_no (int): The statement number in the execution sequence.
        keyword (str): The statement keyword (e.g., '.exec').
        value (str): The statement's content or command.
    """

    def execute(self, vm: VM) -> None:
        """
        Sends the current prompt context to the LLM, handles the response, and 
        logs execution details such as timing and tokens usage.

        Args:
            vm (VM): The virtual machine context in which the statement is executed.

        Returns:
            None: The execution modifies the VM's state directly by adding the response to 
                  the prompt context and logging the conversation data.
        """
        # Print the exec statement for execution.log (but don't log to statements.log yet)
        vm.logger.print_statement(self.msg_no, self.keyword, self.value)
        
        header = f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/]"

        start_time = time.time()
        
        # Generate unique call identifier
        vm.interaction_no += 1
        call_id = f"call-{vm.interaction_no:03d}"
        
        responses = vm.prompt.ask(label=header, call_id=call_id)
        elapsed_time = time.time() - start_time

        # Extract last response text for variable substitution
        last_response_text = ""
        for response in responses:
            if hasattr(response, 'content') and response.content:
                for part in response.content:
                    if isinstance(part, AiTextPart):
                        last_response_text += part.text
        
        # Store last response using centralized method with automatic logging
        vm.set_variable('last_response', last_response_text)

        # Log the exec completion to statements.log (only this one, not the initial empty one)
        exec_completion_msg = f"{vm.company}::{vm.model_name} {call_id} completed in {elapsed_time:.2f} seconds"
        vm.logger.log_statement(self.msg_no, self.keyword, exec_completion_msg)

        # Format the execution timing to match the table structure
        timing_msg = f"{vm.company}::{vm.model_name} completed in {elapsed_time:.2f} seconds"
        # Use same width calculation as other timing lines
        content_len = vm.logger.terminal_width - 14  # Same as statement lines
        padded_content = f"{timing_msg:<{content_len}}"
        final_line = f"[white]{VERTICAL}[/]            {padded_content}[white]{VERTICAL}[/]"
        vm.logger.log_execution(final_line)
        
        # Log the response using structured logging
        vm.logger.log_llm_call(f"Response from {vm.company} API completed", call_id)

        vm.log_conversation(call_id)


class StmtExit(StmtPrompt):
    """
    Handles the execution of the exit statement in the prompt file.

    This class represents a `.exit` keyword statement used to terminate the prompt execution process. 
    When executed, it halts the further processing of statements in the Virtual Machine (VM).

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.exit').
        value (str): The value associated with the statement, which is generally unused for '.exit'.
    
    Methods:
        execute(vm: VM): Terminates the statement processing by exiting from the Virtual Machine's execution context.
    """

    def execute(self, vm: VM) -> None:
        vm.logger.print_statement(self.msg_no, self.keyword, self.value)


class StmtInclude(StmtPrompt):
    """
    Handles the execution of an include statement in the prompt file.

    This class represents the `.include` keyword statement, which loads the 
    content from another file and appends it to the last message in the prompt. 
    The statement supports dynamic filename substitution using variables in the 
    Virtual Machine's variable dictionary.

    Attributes:
        vm (VM): The instance of the Virtual Machine holding execution state.
        msg_no (int): The message number in the execution sequence.
        keyword (str): The statement keyword (e.g., '.include').
        value (str): The file name or path to be included, supporting substitution.

    Methods:
        execute(vm: VM): Resolves the filename, reads its content, and appends
                         it as text to the last message in the prompt.
    """

    def execute(self, vm: VM) -> None:
        filename = vm.substitute(self.value)
        vm.logger.print_statement(self.msg_no, self.keyword, self.value)
        lines = readfile(filename=filename)
        last_msg = vm.prompt.messages[-1]
        last_msg.content.append(AiTextPart(vm=vm, text=lines))


class StmtImage(StmtPrompt):
    """
    Handles the execution of an image-related statement in the VM.

    This class represents a `.image` keyword statement that adds an image
    to the AI prompt context. It incorporates a provided image file into the
    conversation as an input element.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.image').
        value (str): The value associated with the statement, typically the image file path.

    Methods:
        execute(vm: VM): Adds the specified image to the VM's prompt context for processing.
    """

    def execute(self, vm: VM) -> None:
        vm.logger.print_statement(self.msg_no, self.keyword, self.value)
        filename = self.value
        vm.prompt.add_message(vm=vm, role="user", content=[AiImagePart(vm=self.vm, filename=filename)])


class StmtLlm(StmtPrompt):
    """
    Handles the execution of an LLM (Language Learning Model) setup in the Virtual Machine (VM).

    This class represents a `.llm` keyword statement in the prompt file. 
    It is responsible for configuring the LLM's model parameters, fetching the API key, 
    and ensuring required settings are loaded into the VM for interaction with the defined LLM.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The statement keyword (e.g., '.llm').
        value (str): The parameters for the LLM's configuration, typically in JSON format.

    Methods:
        execute(vm: VM): Parses the parameters for the LLM, validates the configuration, 
                         loads the model into the VM, and retrieves the necessary API key.
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)
        try:
            if vm.llm:
                raise (StmtSyntaxError(f".llm syntax: only one .lls statement allowed in vm {vm.filename}"))

            if self.value[0] != '{':
                self.value = "{" + self.value + "}"

            value = self.vm.substitute(self.value)

            try:
                parms = json.loads(value)
            except Exception as e:
                vm.logger.log_error(f"Error parsing .llm parameters: {str(e)}")
                vm.logger.print_exception()
                sys.exit(9)

            if not isinstance(parms, dict):
                raise (StmtSyntaxError(
                    f".llm syntax: parameters expected dict, but got {type(parms).__name__}: {self.value}"))

            if 'model' not in parms:
                raise (StmtSyntaxError(f".llm syntax:  'model' parameter is required but missing {self.value}"))

            vm.load_llm(parms)

        except Exception as err:
            vm.logger.print_exception()
            sys.exit(9)

        # Now we that we have loaded the LLM,  we will load the API_KEY
        try:
            api_key = keyring.get_password('keprompt', username=vm.company)
        except keyring.errors.PasswordDeleteError:
            vm.logger.log_error(f"Error accessing keyring ('keprompt', username={vm.company})")
            api_key = None

        if api_key is None:
            api_key = console.input(f"Please enter your {vm.company} API key: ")
            keyring.set_password("keprompt", username=vm.company, password=api_key)
        if not api_key:
            vm.logger.log_error("API key cannot be empty.")
            sys.exit(1)

        vm.llm['API_KEY'] = api_key
        vm.api_key = api_key
        vm.prompt.api_key = vm.api_key
        vm.prompt.company = vm.company
        vm.prompt.model = vm.model_name


class StmtSystem(StmtPrompt):
    """
    Handles the execution of a system message in the Virtual Machine (VM).

    This class represents a `.system` keyword statement in the prompt file and
    allows for adding a system role message into the AI conversation context.
    A system role is used to provide instructions or contextual rules for the AI.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.system').
        value (str): The value/content of the statement, which is the system message.

    Methods:
        execute(vm: VM): Adds a system message to the VM's prompt context. If no 
                         message is specified, an empty system message is added.
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)
        if not self.value:
            vm.prompt.add_message(vm=vm, role='system', content=[])
        else:
            vm.prompt.add_message(vm=vm, role='system', content=[AiTextPart(vm=vm, text=self.value)])


class StmtText(StmtPrompt):
    """
    Handles the execution of a text statement in the Virtual Machine (VM).

    This class represents a `.text` keyword statement in the prompt file. It is 
    responsible for handling user-provided text and appending it as part of the 
    conversation context.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.text').
        value (str): The value/content of the statement, representing the text input.

    Methods:
        execute(vm: VM): Adds the text to the last message in the VM's prompt context 
                         or creates a new message if no prior context exists.
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)
        if vm.prompt.messages[-1].role in ['assistant', 'system', 'user']:
            vm.prompt.messages[-1].content.append(AiTextPart(vm=vm, text=self.value))
        else:
            vm.prompt.add_message(vm=vm, role='user', content=[AiTextPart(vm=vm, text=self.value)])


class StmtUser(StmtPrompt):
    """
    Handles the execution of a user-related statement in the VM.

    This class represents a `.user` keyword statement in the prompt file. It 
    allows adding user role messages to the AI prompt context, creating or 
    appending new messages as needed.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.user').
        value (str): The value/content of the statement, representing the user's input.

    Methods:
        execute(vm: VM): Adds the user's text input to the prompt context or 
                         appends it as a new user message if no prior context exists.
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)
        if not self.value:
            vm.prompt.add_message(vm=vm, role='user', content=[])
        else:
            # Substitute variables in the user message
            substituted_text = vm.substitute(self.value)
            vm.prompt.add_message(vm=vm, role='user', content=[AiTextPart(vm=vm, text=substituted_text)])


class StmtPrint(StmtPrompt):
    """
    Handles the execution of a print statement in the VM.

    This class represents a `.print` keyword statement in the prompt file. It 
    outputs text directly to STDOUT for production use, separate from development
    logging which goes to STDERR.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.print').
        value (str): The value/content to print to STDOUT.

    Methods:
        execute(vm: VM): Outputs the text to STDOUT after variable substitution.
    """

    def execute(self, vm: VM) -> None:
        # Log the print statement execution to development channels (STDERR)
        super().execute(vm)
        
        # Substitute variables and print to STDOUT (production channel)
        output_text = vm.substitute(self.value)
        print(output_text)  # Add newline for clean output


class StmtSet(StmtPrompt):
    """
    Handles the execution of a set statement in the VM.

    This class represents a `.set` keyword statement in the prompt file. It 
    allows setting variables in the VM's variable dictionary, including special
    configuration variables like Prefix and Postfix for variable substitution.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.set').
        value (str): The value/content in format "variable_name value".

    Methods:
        execute(vm: VM): Parses the variable name and value, stores them in vm.vdict.
    """

    def execute(self, vm: VM) -> None:
        # Log the set statement execution to development channels (STDERR)
        super().execute(vm)
        
        # Parse the variable name and value
        if not self.value.strip():
            raise StmtSyntaxError(f".set syntax error: variable name and value required")
        
        # Split on first space to separate variable name from value
        parts = self.value.split(' ', 1)
        if len(parts) < 2:
            raise StmtSyntaxError(f".set syntax error: both variable name and value required: {self.value}")
        
        var_name = parts[0].strip()
        var_value = parts[1].strip()
        
        if not var_name:
            raise StmtSyntaxError(f".set syntax error: variable name cannot be empty")
        
        # Store the variable using centralized method with automatic logging
        vm.set_variable(var_name, var_value)


# Create a _PromptStatement subclass depending on keyword
StatementTypes: dict[str, type(StmtPrompt)] = {
    '.#': StmtComment,
    '.assistant': StmtAssistant,
    '.clear': StmtClear,
    '.cmd': StmtCmd,
    '.debug': StmtDebug,
    '.exec': StmtExec,
    '.exit': StmtExit,
    '.image': StmtImage,
    '.include': StmtInclude,
    '.llm': StmtLlm,
    '.print': StmtPrint,
    '.set': StmtSet,
    '.system': StmtSystem,
    '.text': StmtText,
    '.user': StmtUser,
}

keywords = StatementTypes.keys()

def make_statement(vm: VM, msg_no: int, keyword: str, value: str) -> StmtPrompt:
    my_class = StatementTypes[keyword]
    return my_class(vm, msg_no, keyword, value)

def print_statement_types():
    from rich.table import Table
    from rich.console import Console
    console = Console()
    table = Table(title="Supported Statement Types", show_header=True, header_style="bold cyan", width=terminal_width,)

    table.add_column("Keyword", style="green")
    table.add_column("Description", style="yellow")

    # Custom descriptions for better documentation
    descriptions = {
        '.#': 'Comment statement - ignored during execution',
        '.assistant': 'Add an assistant message to the conversation context',
        '.clear': 'Delete specified files or file patterns from the system',
        '.cmd': 'Execute a defined function with specified arguments',
        '.debug': 'Display VM state information for debugging purposes',
        '.exec': 'Execute the current prompt context with the configured LLM',
        '.exit': 'Terminate prompt execution',
        '.image': 'Add an image file to the conversation context',
        '.include': 'Include content from another file into the current context',
        '.llm': 'Configure the Language Learning Model and its parameters',
        '.print': 'Output text to STDOUT with variable substitution (production output)',
        '.set': 'Set variables including Prefix/Postfix for configurable substitution delimiters',
        '.system': 'Add a system message to the conversation context',
        '.text': 'Add text content to the current message context',
        '.user': 'Add a user message to the conversation context',
    }

    for k, v in StatementTypes.items():
        description = descriptions.get(k, v.__doc__ or 'No description available')
        table.add_row(k, description)
        

    console.print(table)
