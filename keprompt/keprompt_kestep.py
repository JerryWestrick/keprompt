
import copy
import glob
import json
import logging
import os
import sys
import threading
import time
import typing
from time import sleep

import keyring
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from keprompt.keprompt_aiprompt import AiTextPart, AiImagePart, AiToolPart, AiToolResult, AiPrompt, AiMessage
from keprompt.keprompt_api_config import api_config
from keprompt.keprompt_functions import DefinedFunctions, readfile
from keprompt.keprompt_util import TOP_LEFT, BOTTOM_LEFT, VERTICAL, HORIZONTAL, TOP_RIGHT, RIGHT_TRIANGLE, LEFT_TRIANGLE, \
    HORIZONTAL_LINE, BOTTOM_RIGHT, CIRCLE, backup_file

FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])

log = logging.getLogger(__file__)



# My Version of a seperate configuration file.
models_config: dict[str, any]

json_path = os.path.join(os.path.dirname(__file__), 'keprompt_models.json')

with open(json_path, "r") as json_file:
    models_config = json.load(json_file)


# Global Variables
console = Console()
terminal_width = console.size.width
stop_event = threading.Event()  # Event to signal when to stop the thread

# Global routines
def print_step_code(step_files: list[str]) -> None:
    table = Table(title="Execution Messages")
    table.add_column("Step", style="cyan bold", no_wrap=True)
    table.add_column("Lno", style="blue bold", no_wrap=True)
    table.add_column("Cmd", style="green bold", no_wrap=True)
    table.add_column("Params", style="dark_green bold")

    for step_file in step_files:
        # console.print(f"{step_file}")
        try:
            step: KeStep = KeStep(step_file)
            step.parse_prompt()
        except Exception as e:
            console.print(f"[bold red]Error parsing file {step_file} : {str(e)}[/bold red]")
            console.print_exception()
            sys.exit(1)
        title = os.path.basename(step_file)
        if step.statements:
            for stmt in step.statements:
                table.add_row(title, f"{stmt.msg_no:03}", stmt.keyword, stmt.value)
                title = ''
            table.add_row('───────────────', '───', '─────────', '──────────────────────────────')
    console.print(table)


class PromptSyntaxError(Exception):
    pass


class KeStep:
    """Class to hold Step execution state and implement its machine"""

    def __init__(self, filename: str, debug: bool = False):
        self.filename = filename
        self.debug = debug
        self.ip: int = 0
        self.llm: dict[str, any] = {}
        self.vdict: dict[str, str] = {}
        self.statements: list[_PromptStatement] = []
        # self.messages: list[KeMessage] = []
        self.prompt: AiPrompt = AiPrompt(self)
        self.header: dict[str, any] = {}
        self.data: str = ''
        self.console = Console(record=True)  # Console for terminal
        self.file_console = None  # Console for file, initialized in execute
        self.model: dict[str, any] = {}
        self.model_name: str = ""
        self.company: str = ""
        self.system_value: str = ""
        self.toks_in = 0
        self.cost_in = 0
        self.toks_out = 0
        self.cost_out = 0
        self.total = 0

        if debug:
            log.info(f'Instantiated PromptStep(filename="{filename}",debug="{debug}")')


    def print(self, *args, **kwargs):
        """Print method to output to both console and file."""
        self.console.print(*args, **kwargs)  # Print to terminal
        if self.file_console:  # Ensure file is open
            self.file_console.print(*args, **kwargs)  # Print to file

    def debug_print(self, elements: list[str]) -> None:
        """Pretty prints the PromptStep class state for debugging"""

        if 'all' in elements:
            elements = ['llm', 'variables', 'statements', 'messages', 'header']

        if 'header' in elements:
            table = Table(title=f"Header Debug Info for {self.filename}")
            table.add_column("Step Property", style="cyan", no_wrap=True, width=35)
            table.add_column("Value", style="green", no_wrap=True)

            table.add_row("Filename", self.filename)
            table.add_row("Debug Mode", str(self.debug))
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
        if 'variables' in elements:
            table = Table(title=f"Variables Debug Info for {self.filename}")
            # Basic info section
            table.add_column("Variable Name", style="cyan", no_wrap=True, width=35)
            table.add_column("Value", style="green", no_wrap=True)
            if self.vdict:
                for key, value in self.vdict.items():
                    table.add_row(key, str(value))
            else:
                table.add_row("Variables", "Empty")
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
                            table.add_row(msg_no_str,role, part_no, t)
                            msg_no_str = ""
                            role = ''
                            part_no = ''
            else:
                table.add_row("", "", "", "Empty")
            console.print(table)

    def parse_prompt(self)-> None:
        if self.debug: log.info(f'parse_prompt()')
        lines: list[str]

        # read .prompt file
        with open(self.filename, 'r') as file:
            lines = file.readlines()

        # Delete trailing blank lines
        while lines[-1][0].strip() == '':
            lines.pop()

        # If Missing.. Add implied .exec at end of lines
        if lines[-1][0:5] != '.exec':
            lines.append('.exec')

        # Storage for multiline cmds: .system .user .assistant
        last_keyword = None
        last_value = ''

        for lno, line in enumerate(lines):
            try:
                line = line.strip()

                # skip blank lines
                if not line:
                    continue

                # Process all lines that do not start with .
                if line[0] != '.':
                    if not last_keyword:
                        raise PromptSyntaxError(f"Parse Error {self.filename}:{lno}> Missing .system, .user or .assistant")

                    last_value += f"{line}\n"
                    continue

                # Line starts with '.', now get keyword (Begining of line to first space, or end of line)
                if ' ' in line:
                    keyword, rest = line.split(' ', 1)
                else:
                    keyword = line
                    rest = ''

                # Process all lines that start with '.' but are not a keyword...
                if keyword not in keywords:
                    if not last_keyword:
                        raise PromptSyntaxError(f"Parse Error {self.filename}:{lno}> Missing .system, .user or .assistant")

                    last_value += f"{line}\n"
                    continue

                # We got us a valid dot keyword!!!
                # Now we need to decide what to do with any last_value text we got stored up...
                if last_value:
                    # Okay Lets add it to msg list
                    self.statements.append(make_statement(self, len(self.statements), last_keyword, last_value[:-1]))
                    last_value = ''

                # Does this represent the end of a Multi Line?
                if keyword in ['.assistant', '.user', '.system']:
                    last_keyword = keyword
                    last_value = ''
                    continue  # .user, .system, .assistant do not have info on the line...

                # and now for the single line dot keywords
                self.statements.append(make_statement(self, len(self.statements), keyword, rest))

            except Exception as e:
                raise PromptSyntaxError(
                    f"{VERTICAL} [red]Error parsing file {self.filename}:{lno} error: {str(e)}.[/]\n\n")

        return

    def print_exception(self) -> None:
        """Print exception information to both console and file outputs."""
        self.console.print_exception(show_locals=True)  # Print to terminal
        if self.file_console:  # Ensure file is open
            self.file_console.print_exception()  # Print to file

    def load_llm(self, parms: dict[str, str]) -> None:

        if 'model' not in parms:
            raise PromptSyntaxError(f".llm syntax error: model not defined")
        self.model_name = parms['model']

        if self.model_name not in models_config:
            raise PromptSyntaxError(f"kestep_models.json error: model {self.model_name} is not defined")
        self.model = models_config[self.model_name]

        if 'company' not in self.model:
            raise PromptSyntaxError(f"kestep_models.json error: company not defined for model {self.model_name}")
        self.company = self.model['company']

        if self.company not in api_config:
            raise PromptSyntaxError(f"kestep_models.json error: unknown company {self.company}")

        # copy over llm from kestep_api_config.py
        self.llm = copy.deepcopy(api_config[self.company])

        # over write values placed in .llm line
        for k, v in parms.items():
            self.llm[k] = v

    def execute(self) -> None:
        if self.debug: log.info(f'execute({self.filename} with {len(self.statements)} statements)')

        base_name = os.path.splitext(os.path.basename(self.filename))[0]
        logfile_name = backup_file(f"logs/{base_name}.log", backup_dir='logs', extension='.log')
        with open(logfile_name, 'w') as file:
            self.file_console = Console(file=file, record=True)  # Open file for writing

            self.print(
                f"[bold white]{TOP_LEFT}{HORIZONTAL * 2}[/][bold white]{os.path.basename(self.filename):{HORIZONTAL}<{terminal_width - 4}}{TOP_RIGHT}[/]"
            )

            for stmt_no, stmt in enumerate(self.statements):
                if self.company == 'Anthropic' and stmt.keyword == '.system':
                    self.system_value = stmt.value
                    # continue

                try:
                    stmt.execute(self)
                except Exception as e:
                    self.print(f"{VERTICAL} [bold red]Error executing statement above : {str(e)}[/bold red]\n\n")
                    self.print(f"{BOTTOM_LEFT}{HORIZONTAL * (terminal_width - 2)}{VERTICAL}")
                    self.print_exception()
                    self.print(f"{BOTTOM_LEFT}{HORIZONTAL * (terminal_width - 2)}{VERTICAL}")
                    sys.exit(9)

                if stmt.keyword == '.exit':
                    break


            self.print(f"{BOTTOM_LEFT}{HORIZONTAL * (terminal_width - 2)}{BOTTOM_RIGHT}")

            self.file_console.file.close()  # Close file console at end
            logfile_name_html = backup_file(f"logs/{base_name}.svg", backup_dir='logs', extension='.svg')
            self.console.save_svg(logfile_name_html)
            print(f"Wrote {logfile_name_html} to disk")

    def print_with_wrap(self, is_response: bool, line: str) -> None:
        line_len = terminal_width - 14
        color = '[bold green]'
        if is_response:
            color = '[bold blue]'

        line = f"{line}{' ' * line_len}"
        print_line = line.replace('\n', '\\n')[:line_len]

        if is_response:
            hdr = f"[bold white]{VERTICAL}[/]{color}   {LEFT_TRIANGLE}{HORIZONTAL_LINE * 5}{CIRCLE}  "
        else:
            hdr = f"[bold white]{VERTICAL}[/]{color}   {CIRCLE}{HORIZONTAL_LINE * 5}{RIGHT_TRIANGLE}  "

        lead, trail = print_line.split(':', 1)
        self.print(f"{hdr}{lead}[/]:{trail}[bold white]{VERTICAL}[/]")

    def log_conversation(self):
        base_name = os.path.splitext(os.path.basename(self.filename))[0]
        logfile_name = backup_file(f"logs/{base_name}_messages.json", backup_dir='logs', extension='.json')
        with open(logfile_name, 'w') as file:
            file.write(json.dumps(self.prompt.to_json()))

class _PromptStatement:

    def __init__(self, step: KeStep, msg_no: int, keyword: str, value: str):
        self.msg_no = msg_no
        self.keyword = keyword
        self.value = value
        self.step = step

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

    def execute(self, step: KeStep) -> None:
        step.print(self.console_str())


class _Assistant(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        if step.debug:
            vls = self.value.split('\n')
            vl = vls.pop(0)
            step.print(f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] [green]{vl}[/]")
            for vl in vls:
                step.print(f"[bold white]{VERTICAL}[/]            [green]{vl}[/]")
        step.print(self.console_str())
        step.prompt.add_message('assistant', [AiTextPart(self.value)])


class _Clear(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        if step.debug:
            step.print(
                f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] [green]{self.value}[/]")

        try:
            parms = json.loads(self.value)
        except Exception as e:
            step.print(f"{VERTICAL} [white on red]Error parsing .clear parameters: {str(e)}[/]\n\n")
            step.print_exception()
            sys.exit(9)
            # raise PromptSyntaxError(f"Error parsing .clear parameters: {str(e)}")

        if not isinstance(parms, list):
            step.print(
                f"{VERTICAL} [white on red]Error parsing .clear parameters expected list, but got {type(parms).__name__}: {self.value}")
            sys.exit(9)

        for k in parms:
            try:
                log_files = glob.glob(k)  # Use glob to find all files matching the pattern

                for file_path in log_files:
                    if os.path.isfile(file_path):  # Ensure that it's a file
                        if step.debug:
                            step.print(f"{VERTICAL} [bold green] Deleting {k}[/bold green]")
                        try:
                            os.remove(file_path)
                            step.print(f"File {file_path} deleted successfully.")
                        except OSError as e:
                            step.print(f"Error deleting file {file_path}: {str(e)}")

                    if step.debug:
                        step.print(f"{VERTICAL} [bold green]File {k} deleted successfully.[/bold green]")
            except OSError as e:
                step.print(f"{VERTICAL} [white or red]Error deleting file {k}: {str(e)}[/]\n\n")


class _Cmd(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        """Execute a command that was defined in a prompt file (.prompt)"""

        function_name, args = self.value.split('(', maxsplit=1)
        args = args[:-1]
        args_list = args.split(",")
        function_args = {}

        if function_name == 'askuser':
            step.print(self.console_str() + ': ', end='')
        else:
            step.print(self.console_str())

        for arg in args_list:
            name, value = arg.split("=", maxsplit=1)
            function_args[name] = value

        if function_name not in DefinedFunctions:
            step.print(
                f"[bold red]Error executing {function_name}({function_args}): {function_name} is not defined.[/bold red]")
            raise Exception(f"{function_name} is not defined.")

        try:
            text = DefinedFunctions[function_name](**function_args)
        except Exception as err:
            step.print(f"Error executing {function_name}({function_args})): {str(err)}")
            raise err

        last_msg = step.prompt.messages[-1]
        last_msg.content.append(AiTextPart(text))


class _Comment(_PromptStatement):
    pass


class _Debug(_PromptStatement):

    def execute(self, step: KeStep) -> None:

        step.print(self.console_str())

        if not self.value:
            self.value = '["all"]'

        if self.value[0] != '[':
            self.value = f"[{self.value}]"

        # step.print(self.value)
        try:
            parms = json.loads(self.value)
        except Exception as e:
            step.print(f"{VERTICAL} [white on red]Error parsing .debug parameters: {str(e)}[/]\n\n")
            step.print_exception()
            sys.exit(9)

        if not isinstance(parms, list):
            step.print(
                f"{VERTICAL} [white on red]Error parsing .debug parameters expected list, but got {type(parms).__name__}: {self.value}")
            sys.exit(9)

        step.debug_print(elements=parms)


class DotThread(threading.Thread):
    def __init__(self):
        super(DotThread, self).__init__()
        self.stop_event = threading.Event()
        self.count = 0
        self.is_running = False

    def run(self):
        self.is_running = True
        self.stop_event.clear()
        self.count = 0
        while not self.stop_event.is_set():
            console.print('.', end='')
            self.count += 1
            sleep(1)
        self.is_running = False

    def start(self):
        if not self.is_running:
            super(DotThread, self).start()

    def stop(self):
        if self.is_running:
            self.stop_event.set()


class _Exec(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        """Execute a request to an LLM"""
        first_time = True
        step.print(f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] ", end='')

        continue_conversation: bool = True
        header = f"[bold white]{VERTICAL}[/]            "
        while continue_conversation:
            continue_conversation = False
            if first_time:
                first_time = False
                step.print(f"[bold blue underline]Requesting {step.company}::{step.model_name}", end='')
            else:
                step.print(f"{header}[bold blue underline]Requesting {step.company}::{step.model_name}", end='')

            step.llm['model'] = step.model_name

            # Create a thread to run the print_dot function in the background
            stop_event.clear()  # Clear Signal to stop the thread
            dot_thread = DotThread()
            start_time = time.time()
            elapsed_time = 0
            try:
                dot_thread.start()  # Start the thread
                response: AiMessage = step.prompt.ask()
            except Exception as err:
                # step.print(f"{VERTICAL} [white on red]Error during request: {str(err)}[/]\n\n")
                step.print_exception()
                sys.exit(9)

            finally:
                elapsed_time = time.time() - start_time
                dot_thread.stop()  # Signal the thread to stop
                dot_thread.join()  # Wait for the thread to finish

            try:
                # Got a good response from LLM, add it to Prompt
                step.prompt.messages.append(response)

                step.toks_in += step.prompt.toks_in
                step.cost_in += step.toks_in * step.model['input']
                step.toks_out += step.prompt.toks_out
                step.cost_out += step.toks_out * step.model['output']
                step.total += step.cost_in + step.cost_out

                pline = f" {elapsed_time:.2f} secs output tokens {step.prompt.toks_out} at {step.prompt.toks_out / elapsed_time:.2f} tps"
                used_bytes = 13 + 11 + len(step.company) + 2 + len(step.model_name) + dot_thread.count + 1
                no_bytes_remaining = terminal_width - used_bytes
                step.print(f"{pline:<{no_bytes_remaining}}[bold white]{VERTICAL}[/]")

                continue_conversation = False

                call_returns = []
                llm_parts = []
                if response.content:
                    for c in response.content:
                        llm_parts.append(c)

                if response.tool_calls:
                    for t in response.tool_calls:
                        llm_parts.append(t)

                for msg in llm_parts:
                    # if msg.type == 'text':
                    #     call_returns.append(AiTextPart(msg.text))

                    if type(msg) is AiToolPart:
                        tc: AiToolPart = typing.cast(AiToolPart, msg)
                        function_name = tc.name
                        if type(tc.arguments) is str:
                            function_args = json.loads(tc.arguments)
                        else:
                            function_args = tc.arguments
                        function_id = tc.id

                        step.print_with_wrap(is_response=True, line=f"Call {function_name}:({function_args})")
                        ret = DefinedFunctions[function_name](**function_args)
                        step.print_with_wrap(is_response=False, line=f"Call returned: {ret}")

                        call_returns.append(AiToolResult(name=function_name, id=function_id, result=ret))

                if call_returns:
                    continue_conversation = True
                    step.prompt.add_message(role="result", content=call_returns)


            except Exception as e:
                step.print(f"[white on red]error while handling response:[/]")
                step.log_conversation()
                step.print_exception()
                exit(9)

        if step.debug:
            step.print(f"[bold blue]Response from {step.llm['company']} API:[/bold blue]")
            step.print(response)

        pline = f"Tokens In={step.toks_in}(${step.cost_in:06.4f}), Out={step.toks_out}(${step.cost_out:06.4f}) Total=${step.total:06.4f}"
        step.print(f"{header}{pline:<{terminal_width - 14}}[bold white]{VERTICAL}[/]")

        step.log_conversation()


class _Include(_PromptStatement):
    # Read a file and add its content to last_msg

    def execute(self, step: KeStep) -> None:
        step.print(self.console_str())
        lines = readfile(filename=self.value)
        last_msg = step.prompt.messages[-1]
        last_msg.content.append(AiTextPart(lines))


class _Image(_PromptStatement):
    # Read an Image file and add its content to last_msg

    def execute(self, step: KeStep) -> None:
        step.print(self.console_str())
        filename = self.value
        step.prompt.add_message("user", [AiImagePart(filename=filename)])


class _Llm(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        step.print(self.console_str())
        try:
            if step.llm:
                raise (PromptSyntaxError(f".llm syntax: only one .lls statement allowed in step {step.filename
                }"))

            if self.value[0] != '{':
                self.value = "{" + self.value + "}"

            try:
                parms = json.loads(self.value)
            except Exception as e:
                step.print(f"{VERTICAL} [white on red]Error parsing .llm parameters: {str(e)}[/]\n\n")
                step.print_exception()
                sys.exit(9)

            if not isinstance(parms, dict):
                raise (PromptSyntaxError(
                    f".llm syntax: parameters expected dict, but got {type(parms).__name__}: {self.value}"))

            if 'model' not in parms:
                raise (PromptSyntaxError(f".llm syntax:  'model' parameter is required but missing {self.value}"))

            step.load_llm(parms)

        except Exception as err:
            step.print_exception()
            sys.exit(9)

        # Now we that we have loaded the LLM,  we will load the API_KEY
        try:
            api_key = keyring.get_password('kestep', username=step.company)
        except keyring.errors.PasswordDeleteError:
            step.print(f"[bold red]Error accessing keyring ('kestep', username={step.company})[/bold red]")
            api_key = None

        if api_key is None:
            api_key = console.input(f"Please enter your {step.company} API key: ")
            keyring.set_password("kestep", username=step.company, password=api_key)
        if not api_key:
            step.print("[bold red]API key cannot be empty.[/bold red]")
            sys.exit(1)

        step.llm['API_KEY'] = api_key
        step.api_key = api_key
        step.prompt.api_key = step.api_key
        step.prompt.company = step.company
        step.prompt.model = step.model_name


class _System(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        step.print(self.console_str())
        step.prompt.add_message('system', [AiTextPart(self.value)])


class _User(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        step.print(self.console_str())
        step.prompt.add_message('user', content=[AiTextPart(self.value)])


class _Exit(_PromptStatement):

    def execute(self, step: KeStep) -> None:
        step.print(self.console_str())


# Create a _PromptStatement subclass depending on keyword
StatementTypes: dict[str, type(_PromptStatement)] = {
    '.#': _Comment,
    '.assistant': _Assistant,
    '.clear': _Clear,
    '.cmd': _Cmd,
    '.debug': _Debug,
    '.exec': _Exec,
    '.image': _Image,
    '.include': _Include,
    '.system': _System,
    '.user': _User,
    '.llm': _Llm,
    '.exit': _Exit,
}

keywords = StatementTypes.keys()


def make_statement(step: KeStep, msg_no: int, keyword: str, value: str) -> _PromptStatement:
    my_class = StatementTypes[keyword]
    return my_class(step, msg_no, keyword, value)
