import copy
import glob
import json
import logging
import os
import sys
import threading
import time
from stat import ST_MTIME
from typing import cast
from time import sleep

import keyring
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# from keprompt.keprompt_api_config import api_config
from keprompt.keprompt_functions import DefinedFunctions, readfile
from keprompt.keprompt_prompt import AiTextPart, AiImagePart, AiCall, AiResult, AiPrompt, AiMessage
from keprompt.keprompt_util import TOP_LEFT, BOTTOM_LEFT, VERTICAL, HORIZONTAL, TOP_RIGHT, RIGHT_TRIANGLE, \
    LEFT_TRIANGLE, \
    HORIZONTAL_LINE, BOTTOM_RIGHT, CIRCLE, backup_file

console = Console()
terminal_width = console.size.width

FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]",
                    handlers=[RichHandler(console=console, rich_tracebacks=True, )])

log = logging.getLogger(__file__)

# My Version of a seperate configuration file.
models_config: dict[str, any]

json_path = os.path.join(os.path.dirname(__file__), 'keprompt_models.json')

with open(json_path, "r") as json_file:
    models_config = json.load(json_file)

# Global Variables
stop_event = threading.Event()  # Event to signal when to stop the thread


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
            vm: VM = VM(prompt_file)
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

    def __init__(self, filename: str, debug: bool = False, vdict: dict[str, any] = None):
        self.filename = filename
        self.debug = debug
        self.ip: int = 0
        if vdict:
            self.vdict = vdict
        else:
            self.vdict = dict()
        self.llm: dict[str, any] = dict()
        self.statements: list[StmtPrompt] = []
        # self.messages: list[KeMessage] = []
        self.prompt: AiPrompt = AiPrompt(self)
        self.header: dict[str, any] = {}
        self.data: str = ''
        self.console = Console(width=terminal_width)  # Console for terminal
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
        self.api_key: str = ''
        self.interaction_no: int = 0

        if debug:
            log.info(f'Instantiated VM(filename="{filename}",debug="{debug}")')

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

    def substitute(self, text: str):

        while ']>' in text:
            front, back = text.split(']>', 1)
            if '<[' not in front:
                return text  # No matching begin marker found

            last_begin = front.rfind('<[')
            if last_begin == -1:
                return text  # No begin marker found

            # Extract variable name
            variable_name = front[last_begin + 2:]

            # Handle nested dictionaries
            keys = variable_name.split('.')
            value = self.vdict
            try:
                for key in keys:
                    value = value[key]
            except (KeyError, TypeError):
                raise ValueError(f"Variable '{keys}' is not defined")

            # Replace the matched part with the value
            text = front[:last_begin] + str(value) + back

        return text

    def parse_prompt(self) -> None:
        """Parse the prompt file and create a list of statements.
            parse according to rules in docs/PromptLanguage.md
        """

        if self.debug: log.info(f'parse_prompt()')
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

        if self.model_name not in models_config:
            raise StmtSyntaxError(f"keprompt_models.json error: model {self.model_name} is not defined")
        self.model = models_config[self.model_name]

        if 'company' not in self.model:
            raise StmtSyntaxError(f"keprompt_models.json error: company not defined for model {self.model_name}")
        self.company = self.model['company']

        # copy parms to vdict
        for k, v in parms.items():
            self.vdict[k] = v
        self.vdict['company'] = self.company
        self.vdict['filename'] = self.filename
        self.vdict['model'] = self.model

    def execute(self) -> None:
        """Execute the statements in the prompt file"""
        if self.debug: log.info(f'execute({self.filename} with {len(self.statements)} statements)')

        base_name = os.path.splitext(os.path.basename(self.filename))[0]
        logfile_name = backup_file(f"logs/{base_name}.log", backup_dir='logs', extension='.log')
        with open(logfile_name, 'w') as file:
            self.file_console = Console(file=file, record=True)  # Open file for writing

            self.print(
                f"[bold white]{TOP_LEFT}{HORIZONTAL * 2}[/][bold white]{os.path.basename(self.filename):{HORIZONTAL}<{terminal_width - 4}}{TOP_RIGHT}[/]"
            )

            for stmt_no, stmt in enumerate(self.statements):
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
            console.print(f"Wrote {logfile_name_html} to disk")

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

    def log_conversation(self):
        base_name = os.path.splitext(os.path.basename(self.filename))[0]
        logfile_name = backup_file(f"logs/{base_name}_messages.json", backup_dir='logs', extension='.json')
        with open(logfile_name, 'w') as file:
            file.write(json.dumps(self.prompt.to_json()))

    def log_last_json(self, data: dict[str, any]):
        base_name = os.path.splitext(os.path.basename(self.filename))[0]
        logfile_name = backup_file(f"logs/{base_name}_last_msgs.json", backup_dir='logs', extension='.json')
        with open(logfile_name, 'w') as file:
            file.write(json.dumps(data, indent=2, sort_keys=True))


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
        vm.print(self.console_str())


class StmtAssistant(StmtPrompt):

    def execute(self, vm: VM) -> None:
        if vm.debug:
            vls = self.value.split('\n')
            vl = vls.pop(0)
            vm.print(f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] [green]{vl}[/]")
            for vl in vls:
                vm.print(f"[bold white]{VERTICAL}[/]            [green]{vl}[/]")
        vm.print(self.console_str())
        if not self.value:
            vm.prompt.add_message(vm=vm, role='assistant', content=[])
        else:
            vm.prompt.add_message(vm=vm, role='assistant', content=[AiTextPart(vm=vm, text=self.value)])


class StmtClear(StmtPrompt):

    def execute(self, vm: VM) -> None:
        if vm.debug:
            vm.print(
                f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] [green]{self.value}[/]")

        try:
            parms = json.loads(self.value)
        except Exception as e:
            vm.print(f"{VERTICAL} [white on red]Error parsing .clear parameters: {str(e)}[/]\n\n")
            vm.print_exception()
            sys.exit(9)
            # raise PromptSyntaxError(f"Error parsing .clear parameters: {str(e)}")

        if not isinstance(parms, list):
            vm.print(
                f"{VERTICAL} [white on red]Error parsing .clear parameters expected list, but got {type(parms).__name__}: {self.value}")
            sys.exit(9)

        for k in parms:
            try:
                log_files = glob.glob(k)  # Use glob to find all files matching the pattern

                for file_path in log_files:
                    if os.path.isfile(file_path):  # Ensure that it's a file
                        if vm.debug:
                            vm.print(f"{VERTICAL} [bold green] Deleting {k}[/bold green]")
                        try:
                            os.remove(file_path)
                            vm.print(f"File {file_path} deleted successfully.")
                        except OSError as e:
                            vm.print(f"Error deleting file {file_path}: {str(e)}")

                    if vm.debug:
                        vm.print(f"{VERTICAL} [bold green]File {k} deleted successfully.[/bold green]")
            except OSError as e:
                vm.print(f"{VERTICAL} [white or red]Error deleting file {k}: {str(e)}[/]\n\n")


class StmtCmd(StmtPrompt):

    def execute(self, vm: VM) -> None:
        """Execute a command that was defined in a prompt file (.prompt)"""

        function_name, args = self.value.split('(', maxsplit=1)
        args = args[:-1]
        args_list = args.split(",")
        function_args = {}

        if function_name == 'askuser':
            vm.print(self.console_str() + ': ', end='')
        else:
            vm.print(self.console_str())

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
    pass


class StmtDebug(StmtPrompt):

    def execute(self, vm: VM) -> None:

        vm.print(self.console_str())

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

    def execute2(self, vm: VM) -> None:
        """Execute a request to an LLM"""

        response: AiMessage | None = None

        vm.print(f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] ", end='')

        continue_conversation: bool = True
        header = f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] "
        label = ''
        vm.interaction_no = 0
        while continue_conversation:
            vm.interaction_no += 1
            continue_conversation = False
            label = f"{header}[bold blue underline]Requesting {vm.company}::{vm.model_name}[/][white] Call {vm.interaction_no}:"
            vm.llm['model'] = vm.model_name
            start_time = time.time()
            elapsed_time = 0
            try:
                response: AiMessage = vm.prompt.ask(label=label)
            except Exception as err:
                vm.print_exception()
                sys.exit(9)

            finally:
                elapsed_time = time.time() - start_time

            try:
                # Got a good response from LLM, add it to Prompexecutet
                vm.prompt.messages.append(response)

                vm.toks_in += vm.prompt.toks_in
                vm.cost_in += vm.toks_in * vm.model['input']
                vm.toks_out += vm.prompt.toks_out
                vm.cost_out += vm.toks_out * vm.model['output']
                vm.total += vm.cost_in + vm.cost_out

                pline = f" {elapsed_time:.2f} secs output tokens {vm.prompt.toks_out} at {vm.prompt.toks_out / elapsed_time:.2f} tps"
                used_bytes = 13 + 11 + len(vm.company) + 2 + len(vm.model_name) + 9
                no_bytes_remaining = terminal_width - used_bytes
                vm.print(f"{label}[/]{pline:<{no_bytes_remaining}}[bold white]{VERTICAL}[/]")

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

                    match msg.type:
                        case "call":
                            tc: AiCall = cast(AiCall, msg)
                            function_name = tc.name
                            if type(tc.arguments) is str:
                                function_args = json.loads(tc.arguments)
                            else:
                                function_args = tc.arguments
                            function_id = tc.id

                            vm.print_with_wrap(is_response=True, line=str(tc))
                            ret = DefinedFunctions[function_name](**function_args)

                            tr = AiResult(vm=vm, name=function_name, id=function_id, result=ret)
                            vm.print_with_wrap(is_response=False, line=str(tr))

                            call_returns.append(tr)
                        case "text":
                            tp = cast(AiTextPart, msg)
                            vm.print_with_wrap(is_response=True, line=str(tp))

                        case _:
                            raise ValueError(f"Execution returned unexpected type {type(msg)}")

                if call_returns:
                    continue_conversation = True
                    vm.prompt.add_message(vm=vm, role="result", content=call_returns)

            except Exception as e:
                vm.print(f"[white on red]error while handling response:[/]")
                vm.log_conversation()
                vm.print_exception()
                exit(9)

            header = f"[bold white]{VERTICAL}[/]            "

        if vm.debug:
            vm.print(f"[bold blue]Response from {vm.company} API:[/bold blue]")
            vm.print(response)

        pline = f"Tokens In={vm.toks_in}(${vm.cost_in:06.4f}), Out={vm.toks_out}(${vm.cost_out:06.4f}) Total=${vm.total:06.4f}"
        vm.print(f"{header}{pline:<{terminal_width - 14}}[bold white]{VERTICAL}[/]")

        vm.log_conversation()

    def execute(self, vm: VM) -> None:
        """Execute a request to an LLM"""
        response: AiMessage | None = None

        vm.print(f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] ", end='')

        continue_conversation: bool = True
        header = f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/] "
        label = ''
        vm.interaction_no = 0
        while continue_conversation:
            vm.interaction_no += 1
            continue_conversation = False
            label = f"{header}[bold blue underline]Requesting {vm.company}::{vm.model_name}[/][white] Call {vm.interaction_no}:"

            vm.llm['model'] = vm.model_name

            # Create a thread to run the print_dot function in the background
            stop_event.clear()  # Clear Signal to stop the thread
            # dot_thread = DotThread()
            start_time = time.time()
            elapsed_time = 0
            try:
                # dot_thread.start()  # Start the thread
                response: AiMessage = vm.prompt.ask(label=label)
            except Exception as err:
                # vm.print(f"{VERTICAL} [white on red]Error during request: {str(err)}[/]\n\n")
                vm.print_exception()
                sys.exit(9)

            finally:
                elapsed_time = time.time() - start_time
                # dot_thread.stop()  # Signal the thread to stop
                # dot_thread.join()  # Wait for the thread to finish

            try:
                # Got a good response from LLM, add it to Prompexecutet
                vm.prompt.messages.append(response)

                vm.toks_in += vm.prompt.toks_in
                vm.cost_in += vm.toks_in * vm.model['input']
                vm.toks_out += vm.prompt.toks_out
                vm.cost_out += vm.toks_out * vm.model['output']
                vm.total += vm.cost_in + vm.cost_out

                pline = f" {elapsed_time:.2f} secs output tokens {vm.prompt.toks_out} at {vm.prompt.toks_out / elapsed_time:.2f} tps"
                used_bytes = 13 + 11 + len(vm.company) + 2 + len(vm.model_name) + 9
                no_bytes_remaining = terminal_width - used_bytes
                vm.print(f"{label}[/]{pline:<{no_bytes_remaining}}[bold white]{VERTICAL}[/]")

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

                    match msg.type:
                        case "call":
                            tc: AiCall = cast(AiCall, msg)
                            function_name = tc.name
                            if type(tc.arguments) is str:
                                function_args = json.loads(tc.arguments)
                            else:
                                function_args = tc.arguments
                            function_id = tc.id

                            vm.print_with_wrap(is_response=True, line=str(tc))
                            ret = DefinedFunctions[function_name](**function_args)

                            tr = AiResult(vm=vm, name=function_name, id=function_id, result=ret)
                            vm.print_with_wrap(is_response=False, line=str(tr))

                            call_returns.append(tr)
                        case "text":
                            tp = cast(AiTextPart, msg)
                            vm.print_with_wrap(is_response=True, line=str(tp))

                        case _:
                            raise ValueError(f"Execution returned unexpected type {type(msg)}")

                if call_returns:
                    continue_conversation = True
                    vm.prompt.add_message(vm=vm, role="result", content=call_returns)

            except Exception as e:
                vm.print(f"[white on red]error while handling response:[/]")
                vm.log_conversation()
                vm.print_exception()
                exit(9)

            header = f"[bold white]{VERTICAL}[/]            "

        if vm.debug:
            vm.print(f"[bold blue]Response from {vm.company} API:[/bold blue]")
            vm.print(response)

        pline = f"Tokens In={vm.toks_in}(${vm.cost_in:06.4f}), Out={vm.toks_out}(${vm.cost_out:06.4f}) Total=${vm.total:06.4f}"
        vm.print(f"{header}{pline:<{terminal_width - 14}}[bold white]{VERTICAL}[/]")

        vm.log_conversation()


class StmtExit(StmtPrompt):

    def execute(self, vm: VM) -> None:
        vm.print(self.console_str())


class StmtInclude(StmtPrompt):
    # Read a file and add its content to last_msg

    def execute(self, vm: VM) -> None:
        filename = vm.substitute(self.value)
        vm.print(self.console_str())
        lines = readfile(filename=filename)
        last_msg = vm.prompt.messages[-1]
        last_msg.content.append(AiTextPart(vm=vm, text=lines))


class StmtImage(StmtPrompt):
    # Read an Image file and add its content to last_msg

    def execute(self, vm: VM) -> None:
        vm.print(self.console_str())
        filename = self.value
        vm.prompt.add_message(vm=vm, role="user", content=[AiImagePart(vm=self.vm, filename=filename)])


class StmtLlm(StmtPrompt):

    def execute(self, vm: VM) -> None:
        vm.print(self.console_str())
        try:
            if vm.llm:
                raise (StmtSyntaxError(f".llm syntax: only one .lls statement allowed in vm {vm.filename
                }"))

            if self.value[0] != '{':
                self.value = "{" + self.value + "}"

            value = self.vm.substitute(self.value)

            try:
                parms = json.loads(value)
            except Exception as e:
                vm.print(f"{VERTICAL} [white on red]Error parsing .llm parameters: {str(e)}[/]\n\n")
                vm.print_exception()
                sys.exit(9)

            if not isinstance(parms, dict):
                raise (StmtSyntaxError(
                    f".llm syntax: parameters expected dict, but got {type(parms).__name__}: {self.value}"))

            if 'model' not in parms:
                raise (StmtSyntaxError(f".llm syntax:  'model' parameter is required but missing {self.value}"))

            vm.load_llm(parms)

        except Exception as err:
            vm.print_exception()
            sys.exit(9)

        # Now we that we have loaded the LLM,  we will load the API_KEY
        try:
            api_key = keyring.get_password('keprompt', username=vm.company)
        except keyring.errors.PasswordDeleteError:
            vm.print(f"[bold red]Error accessing keyring ('keprompt', username={vm.company})[/bold red]")
            api_key = None

        if api_key is None:
            api_key = console.input(f"Please enter your {vm.company} API key: ")
            keyring.set_password("keprompt", username=vm.company, password=api_key)
        if not api_key:
            vm.print("[bold red]API key cannot be empty.[/bold red]")
            sys.exit(1)

        vm.llm['API_KEY'] = api_key
        vm.api_key = api_key
        vm.prompt.api_key = vm.api_key
        vm.prompt.company = vm.company
        vm.prompt.model = vm.model_name


class StmtSystem(StmtPrompt):

    def execute(self, vm: VM) -> None:
        vm.print(self.console_str())
        if not self.value:
            vm.prompt.add_message(vm=vm, role='assistant', content=[])
        else:
            vm.prompt.add_message(vm=vm, role='assistant', content=[AiTextPart(vm=vm, text=self.value)])


class StmtText(StmtPrompt):

    def execute(self, vm: VM) -> None:
        vm.print(self.console_str())
        if vm.prompt.messages[-1].role in ['assistant', 'system', 'user']:
            vm.prompt.messages[-1].content.append(AiTextPart(vm=vm, text=self.value))
        else:
            vm.prompt.add_message(vm=vm, role='user', content=[AiTextPart(vm=vm, text=self.value)])


class StmtUser(StmtPrompt):

    def execute(self, vm: VM) -> None:
        vm.print(self.console_str())
        if not self.value:
            vm.prompt.add_message(vm=vm, role='user', content=[])
        else:
            vm.prompt.add_message(vm=vm, role='user', content=[AiTextPart(vm=vm, text=self.value)])


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
    '.system': StmtSystem,
    '.text': StmtText,
    '.user': StmtUser,
}

keywords = StatementTypes.keys()


def make_statement(vm: VM, msg_no: int, keyword: str, value: str) -> StmtPrompt:
    my_class = StatementTypes[keyword]
    return my_class(vm, msg_no, keyword, value)
