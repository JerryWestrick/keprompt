import glob
import json
import logging
import os
import re
import sys
import time
import uuid
from contextlib import contextmanager

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import FunctionSpace
from .config import get_config
from rich.logging import RichHandler
from rich.table import Table

from .ModelManager import ModelManager, AiModel
from .AiPrompt import (AiTextPart, AiImagePart, AiPrompt, AiMessage, AiLdmPart, AiGuardPart, LDM_ROLE,
                       GUARD_ROLE, MAX_LINE_LENGTH)
from  .keprompt_util import VERTICAL, RIGHT_TRIANGLE, LEFT_TRIANGLE, HORIZONTAL_LINE, CIRCLE
from .keprompt_logger import StandardLogger, LogMode
from .terminal_output import terminal_output

console = Console()
terminal_width = console.size.width

FORMAT = "%(message)s"
logging.basicConfig(level="NOTSET", format=FORMAT, datefmt="[%X]",
                    handlers=[RichHandler(console=console, rich_tracebacks=True, )])

log = logging.getLogger(__file__)

# Multi-line quote (heredoc), standard semantics. `<<<ID` anywhere on a statement line opens a block
# that is consumed verbatim until a line that is exactly `>>>ID`. As in shell, the opener does not
# have to end the line -- `cat <<EOF > out.txt` keeps parsing the command -- while the terminator
# must stand alone. Text following the opener is the statement's "tail" and stays in its value.
#
# Fixed literals, resolved entirely at parse time -- deliberately NOT bound to the Prefix/Postfix
# substitution variables, which are runtime state. Because they resolve at parse time, quoted text is
# never re-parsed: substituted content containing `>>>ID` cannot close a quote.
#
# `<<<'ID'` (quoted identifier) is reserved for a future non-interpolating form and rejected today.
# The identifier is any run of non-space characters, delimited by whitespace or end of line.
HEREDOC_OPEN = re.compile(
    r"<<<(?:(?P<quote>['\"])(?P<qid>\S+?)(?P=quote)|(?P<id>\S+))")


def heredoc_terminator(identifier: str) -> str:
    """The line that closes a multi-line quote opened with `<<<identifier`."""
    return f">>>{identifier}"


# A leading underscore at the root of the variable dictionary marks a name as keprompt's own.
# It hides the name from wildcard enumeration, but never from an explicit path and never from
# serialisation -- internals must survive save/restore or replay breaks.
RESERVED_PREFIX = '_'
RESERVED_ROOT = '_prompt'
QUESTION_SUBSYSTEM = 'question'
# `#` -> `_prompt.guard`: guards, one per channel. `_cmdargs`, `_userinput` and `_include` are the
# runtime's channels; any other `_` name is user-defined, chosen per call with `guard=`; a name without
# `_` is a function's.
GUARD_SUBSYSTEM = 'guard'
GUARD_CMDARGS = '_cmdargs'
GUARD_USERINPUT = '_userinput'
GUARD_INCLUDE = '_include'
# Set-level in a guard: its fail condition, a Python expression over the guard's answer paths.
GUARD_FAIL_KEY = '_fail'
# The registry's `mode` for a decision model: it answers `.evaluate`, where a `chat` model answers
# `.exec`. Pointing a statement at the wrong kind is refused rather than sent.
LDM_MODE = 'ldm'
# Where each execution unit's model lives in memory. The LLM (`.exec`) and the LDM (`.evaluate`) do
# not share one: a prompt that uses both would otherwise have to re-set it at every switch.
LLM_MODEL_PATH = f'{RESERVED_ROOT}.llm_model'
LDM_MODEL_PATH = f'{RESERVED_ROOT}.ldm_model'
# `model` is the deprecated spelling of `$.llm_model`. Every use is redirected there, with a warning.
DEPRECATED_MODEL = 'model'
# Set-level: the question set's model. The `.question` line and the `.evaluate` line both write it, and
# it stays for later `.evaluate`s of that set, as `.exec`'s line model stays in `$.llm_model`.
SET_MODEL_KEY = '_model'
# The model that answered the last call: the model asked for, unless the provider identified another.
# A temporary output, `$._provider_selected_model` for `.exec` and `?.<name>._provider_selected_model`
# for `.evaluate`.
PROVIDER_SELECTED_KEY = '_provider_selected_model'
# Reserved inside a question set, so set-level metadata (`_model`, `_usage`) and a question's
# `_definition` can never be shadowed by a question that happens to share the name.
DEFINITION_KEY = '_definition'


# Global routines
class StmtSyntaxError(Exception):
    pass

class PromptResolutionError(Exception):
    pass

class VMExecutionError(Exception):
    """Raised when a statement fails during VM execution.
    Carries the original exception and the statement index."""
    def __init__(self, message: str, stmt_index: int, original_error: Exception):
        super().__init__(message)
        self.stmt_index = stmt_index
        self.original_error = original_error


_LEGACY_TOP_LEVEL_LLM_OPTIONS = ('temperature', 'max_tokens', 'top_p', 'top_k')


def split_guard_param(text: str) -> tuple[str | None, str]:
    """A leading `guard=<path>` names the guard for this one call: `.include guard=#._intent file`."""
    text = text.strip()
    if not text.startswith('guard='):
        return None, text
    guard, _, rest = text[len('guard='):].partition(' ')
    return guard, rest.strip()


def split_line_params(text: str, keyword: str) -> tuple[str, str]:
    """Split an execute line into its JSON params and whatever follows them.

    `.exec` and `.evaluate` take the same params: a JSON object at the start of the operand. Its
    closing brace ends it, so text may follow -- `.evaluate`'s inline state does. Returns the params
    text (empty when there are none) and the rest.
    """
    stripped = text.lstrip()
    if not stripped.startswith('{'):
        return '', text
    try:
        _, end = json.JSONDecoder().raw_decode(stripped)
    except json.JSONDecodeError as e:
        raise StmtSyntaxError(f"{keyword} syntax: invalid JSON params '{stripped}': {e}")
    return stripped[:end], stripped[end:]


def parse_line_params(vm, params_text: str, keyword: str, substitute: bool = True) -> dict:
    """Parse the JSON params split off by `split_line_params`, substituting first unless the
    caller already has."""
    try:
        params = json.loads(vm.substitute(params_text) if substitute else params_text)
    except json.JSONDecodeError as e:
        vm.logger.log_error(f"{keyword} params parse error: {e}")
        raise StmtSyntaxError(f"{keyword} syntax: invalid JSON '{params_text}': {e}")
    if not isinstance(params, dict):
        raise StmtSyntaxError(f"{keyword} syntax: params must be a JSON object: '{params_text}'")
    return params


def _reject_legacy_top_level_llm_options(source: dict) -> None:
    found = [key for key in _LEGACY_TOP_LEVEL_LLM_OPTIONS if key in source]
    if found:
        names = ', '.join(found)
        raise StmtSyntaxError(
            f".exec error: {names} must be moved into llm_options for this version to work"
        )


def prompt_name_for(filename: str | None) -> str:
    """A prompt is named by its file's basename; a VM with no file is "chat"."""
    if filename:
        return os.path.splitext(os.path.basename(filename))[0]
    return "chat"


class VM:
    """Class to hold Prompt Virtual Machine execution state"""

    def __init__(self, filename: str | None = None, global_vars: dict[str, any] | None = None,
                 prompt_ref: str | None = None, params: dict[str, any] | None = None,
                 log_mode: LogMode = LogMode.PRODUCTION, log_identifier: str = None, vm_debug: bool = False, exec_debug: bool = False):
        # Resolve filename either from direct path or logical prompt reference
        resolved_filename = filename
        if not resolved_filename and prompt_ref:
            resolved_filename = self._resolve_prompt_ref(prompt_ref)

        self.filename = resolved_filename
        self.log_mode = log_mode
        self.vm_debug = vm_debug
        self.exec_debug = exec_debug
        self.ip: int = 0
        
        # Generate unique prompt instance UUID
        self.prompt_uuid = str(uuid.uuid4())[:8]  # Use first 8 chars for readability
        
        # Build variables with explicit defaults, then merge caller-provided dicts
        self.vdict = self.default_globals()

        self.llm: dict[str, any] = dict()
        self.statements: list[StmtPrompt] = []
        self.prompt: AiPrompt = AiPrompt(self)
        self.header: dict[str, any] = {}
        self.data: str = ''
        
        # The prompt's name is its file's basename; it names the log and the chat and cost records
        self.prompt_name: str = prompt_name_for(self.filename)

        # Initialize the new standard logger
        self.logger = StandardLogger(prompt_name=self.prompt_name, mode=log_mode, log_identifier=log_identifier)
        
        # Caller-provided values (command line, --set-from-json) enter memory through one path.
        self.accept_cmdargs({**(global_vars or {}), **(params or {})})

        # Keep old console for backward compatibility during transition
        self.console = Console(width=terminal_width)  # Console for terminal
        self.file_console = None  # Console for file, initialized in execute
        self.model: AiModel = None
        self.model_name: str = ""
        self.provider: str = ""
        self.system_value: str = ""
        self.toks_in = 0
        self.cost_in = 0
        self.toks_out = 0
        self.cost_out = 0
        self.total = 0
        self.api_key: str = ''
        self.interaction_no: int = 0
        
        # Prompt metadata fields for versioning and cost tracking
        self.prompt_version: str = ""
        self.expected_params: dict = {}
        self.pending_costs: list = []
        self.api_time: float = 0.0  # Accumulated API request time
        self.tool_time: float = 0.0  # Accumulated function execution time
        self.round_trip_count: int = 0  # Billed API round trips (interaction_no counts executes)
        # The last round-trip number used per statement. A statement's billed requests are numbered
        # from one counter, because a guard can bill requests inside another statement's execute.
        self.round_trips_used: dict[int, int] = {}
        self.allowed_functions: list[str] | None = None  # None = no .functions statement = no functions (safe default)

        # Automatically parse if filename provided
        if self.filename:
            self.parse_prompt()

    @staticmethod
    def default_globals() -> dict:
        return {
            'Prefix': '<<',
            'Postfix': '>>',
            'Debug': False,
            'Verbose': False,
            'llm_options': {},
            # `_` at the root is keprompt's. `_prompt.question` holds the LDM subsystem:
            # one branch per named question set, each carrying its questions' definitions and, once
            # evaluated, their answers. The rest of the machinery (VM, prefix/suffix) has not been
            # migrated under `_prompt` yet -- that is a separate breaking change.
            '_prompt': {'question': {}, 'guard': {}},
        }

    @staticmethod
    def expand_sigils(name: str) -> str:
        """`$` -> `_prompt`, `?` -> `_prompt.question`, `#` -> `_prompt.guard`. Fixed literals."""
        if name == '$' or name.startswith('$.'):
            return RESERVED_ROOT + name[1:]
        if name == '?' or name.startswith('?.'):
            return f"{RESERVED_ROOT}.{QUESTION_SUBSYSTEM}" + name[1:]
        if name == '#' or name.startswith('#.'):
            return f"{RESERVED_ROOT}.{GUARD_SUBSYSTEM}" + name[1:]
        return name

    def walk_path(self, path: str, create: bool = False) -> tuple[dict, str]:
        """Resolve a dotted path to (containing dict, final key). Sigils are expanded first."""
        keys = self.expand_sigils(path).split('.')
        node = self.vdict
        for key in keys[:-1]:
            if key not in node or not isinstance(node[key], dict):
                if not create:
                    raise ValueError(f"'{path}' is not defined")
                node[key] = {}
            node = node[key]
        return node, keys[-1]

    def set_path(self, path: str, value: any) -> None:
        """Assign through a dotted path, creating intermediate dicts. `.set` cannot do this."""
        node, key = self.walk_path(path, create=True)
        node[key] = value
        self.logger.log_variable_assignment(path, str(value))

    def get_path(self, path: str) -> any:
        node, key = self.walk_path(path)
        if key not in node:
            raise ValueError(f"'{path}' is not defined")
        return node[key]

    def _resolve_prompt_ref(self, prompt_ref: str) -> str:
        """Resolve a logical prompt name to a single .prompt file inside prompts/.
        Accepts either an existing file path ending with .prompt or a logical name.
        Raises PromptResolutionError on 0 or >1 matches.
        """
        from pathlib import Path
        import os as _os

        # Direct file path
        if _os.path.isfile(prompt_ref) and prompt_ref.endswith('.prompt'):
            return prompt_ref

        # Logical name → glob in prompts/
        name = prompt_ref
        # Strip .prompt suffix if user included it
        if name.endswith('.prompt'):
            name = name[:-7]
        base = Path('prompts')

        # Try case-insensitive exact match first
        for f in base.iterdir():
            if f.is_file() and f.name.lower() == f"{name.lower()}.prompt":
                return str(f)

        # Fall back to wildcard match
        if '*' in name:
            pattern = base / f"{name}.prompt"
        else:
            pattern = base / f"{name}*.prompt"
        matches = sorted(Path('.').glob(str(pattern)))
        if not matches:
            raise PromptResolutionError(f"Prompt '{name}' not found (pattern: {pattern})")
        if len(matches) > 1:
            raise PromptResolutionError(f"Multiple prompts match '{name}': {[str(p) for p in matches]}")
        return str(matches[0])


    def serialize_statements(self) -> list[dict]:
        """Serialize statements to a list of dictionaries for saving."""
        return [
            {
                'msg_no': stmt.msg_no,
                'keyword': stmt.keyword,
                'value': stmt.value
            }
            for stmt in self.statements
        ]

    def deserialize_statements(self, statements_data: list[dict]):
        """Deserialize statements from list of dictionaries."""
        self.statements = []
        for data in statements_data:
            stmt = make_statement(
                vm=self,
                msg_no=data['msg_no'],
                keyword=data['keyword'],
                value=data['value']
            )
            self.statements.append(stmt)

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

    def canonical_name(self, name: str) -> str:
        """The path a name refers to: sigils expanded, and `model` redirected to `$.llm_model`."""
        if name == DEPRECATED_MODEL:
            self.logger.log_warning(f"'{DEPRECATED_MODEL}' is deprecated; it is treated as '$.llm_model'")
            return LLM_MODEL_PATH
        return self.expand_sigils(name)

    def assign(self, name: str, value: any) -> None:
        """Write any memory: a plain name, a dotted path, or a `$.`/`?.` path."""
        path = self.canonical_name(name)
        if '.' in path:
            self.set_path(path, value)
        else:
            self.set_variable(path, value)

    def has_path(self, path: str) -> bool:
        try:
            self.get_path(path)
            return True
        except ValueError:
            return False

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
        Supports both regular variables and VM namespace (VM.*) for read-only VM state access.
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

            # Handle VM namespace (read-only access to VM properties)
            if variable_name.startswith('VM.'):
                vm_property = variable_name[3:]  # Remove 'VM.' prefix
                value = self._get_vm_property(vm_property)
                if value is None:
                    raise ValueError(f"VM property '{vm_property}' is not available")
                
                # Log VM property access
                self.logger.log_variable_retrieval(variable_name, str(value))
                
                # Replace the matched part with the value
                text = front[:last_begin] + str(value) + back
                continue

            # Handle regular variables and nested dictionaries. `$` and `?` are fixed-literal
            # shorthands for the reserved roots, expanded before the path is walked.
            keys = self.canonical_name(variable_name).split('.')
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

    def _get_vm_property(self, property_name: str):
        """
        Get VM property value for VM namespace access (VM.*).
        Returns None if property is not available.
        """
        # Map of available VM properties to their actual VM attributes
        vm_properties = {
            'chat_id': self.prompt_uuid,
            'model_name': self.model_name,
            'provider': self.provider,
            'interaction_no': self.interaction_no,
            'cost_in': self.cost_in,
            'cost_out': self.cost_out,
            'total_cost': self.cost_in + self.cost_out,
            'toks_in': self.toks_in,
            'toks_out': self.toks_out,
            'total_tokens': self.toks_in + self.toks_out,
            'filename': self.filename or "",
            'ip': self.ip,
            'prompt_name': self.prompt_name,
            'prompt_version': self.prompt_version,
            'api_key': "***HIDDEN***",  # Never expose actual API key
        }
        
        return vm_properties.get(property_name)


    def add_statement(self, keyword=None, value=None, heredoc=None) -> 'StmtPrompt':
        """Add a new statement to the prompt."""
        stmt = make_statement(self, len(self.statements), keyword=keyword, value=value, heredoc=heredoc)
        self.statements.append(stmt)
        return stmt

    def emit_statement(self, keyword: str, value: str, lno: int, heredoc: str | None = None) -> None:
        """Add a statement, folding a continuation line into the previous message statement."""
        if lno and keyword == '.text' and self.statements:
            last = self.statements[-1]
            if last.keyword in ['.assistant', '.system', '.text', '.user']:
                last.value = f"{last.value}\n{value}".strip()
                return

        self.add_statement(keyword=keyword, value=value, heredoc=heredoc)

    def parse_prompt(self) -> None:
        """Parse the prompt file and create a list of statements.
            parse according to rules in docs/PromptLanguage.md
        """

        if not self.filename:
            # No prompt file to parse (chat mode)
            return

        lines: list[str]

        # read .prompt file
        with open(self.filename, 'r') as file:
            lines = file.readlines()

        # Delete all trailing blank lines
        while lines[-1][0].strip() == '': lines.pop()

        # Check that first non-empty line is a .prompt statement
        first_statement_found = False
        for line in lines:
            line = line.strip()
            if not line:  # skip blank lines
                continue
            if not first_statement_found:
                first_statement_found = True
                if not line.startswith('.prompt '):
                    raise StmtSyntaxError(
                        f"{VERTICAL} [red]Error: First statement in {self.filename} must be a .prompt statement with name and version.[/]\n"
                        f"Example: .prompt \"name\":\"My Prompt\", \"version\":\"1.0.0\"\n\n")
                break

        heredoc_id: str | None = None        # identifier of the open quote, None if closed
        heredoc_head: tuple[str, str, str] = ()  # (keyword, text before the marker, text after it)
        heredoc_body: list[str] = []
        heredoc_lno: int = 0

        for lno, line in enumerate(lines):
            try:
                # Inside a multi-line quote the line is content, not syntax: consumed verbatim with
                # no strip, no blank-line skip and no dot-keyword dispatch, until the terminator.
                if heredoc_id is not None:
                    if line.rstrip() == heredoc_terminator(heredoc_id):
                        keyword, before, tail = heredoc_head
                        body = "\n".join(heredoc_body)
                        stmt_class = StatementTypes.get(keyword)
                        if stmt_class is None or stmt_class.heredoc_as_value:
                            # The operand simply is the text: splice the body in at the marker.
                            self.emit_statement(keyword, before + body + tail, heredoc_lno)
                        else:
                            # The statement parses its own line: keep the body off it.
                            self.emit_statement(keyword, (before + tail).strip(), heredoc_lno,
                                                heredoc=body)
                        heredoc_id, heredoc_head, heredoc_body = None, (), []
                    else:
                        heredoc_body.append(line.rstrip('\r\n'))
                    continue

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

                # Multi-line quote opener: <<<ID as the last thing on the line.
                opener = HEREDOC_OPEN.search(value)
                if opener:
                    if opener.group('quote'):
                        raise StmtSyntaxError(
                            f"{VERTICAL} [red]Error: {self.filename}:{lno + 1} non-interpolating "
                            f"multi-line quote <<<'{opener.group('qid')}' is reserved and not yet "
                            f"supported. Use <<<{opener.group('qid')} instead.[/]\n\n")
                    heredoc_id = opener.group('id')
                    heredoc_head = (keyword, value[:opener.start()], value[opener.end():])
                    heredoc_body = []
                    heredoc_lno = lno
                    continue

                self.emit_statement(keyword, value, lno)

            except StmtSyntaxError:
                raise
            except Exception as e:
                raise StmtSyntaxError(
                    f"{VERTICAL} [red]Error parsing file {self.filename}:{lno} error: {str(e)}.[/]\n\n")

        if heredoc_id is not None:
            raise StmtSyntaxError(
                f"{VERTICAL} [red]Error: {self.filename}:{heredoc_lno + 1} multi-line quote "
                f"<<<{heredoc_id} is never closed; expected a line containing exactly "
                f"{heredoc_terminator(heredoc_id)}.[/]\n\n")

        # Validate that we have a .prompt statement and it was processed
        if not self.statements or self.statements[0].keyword != '.prompt':
            raise StmtSyntaxError(
                f"{VERTICAL} [red]Error: {self.filename} must start with a .prompt statement.[/]\n"
                f"Example: .prompt \"name\":\"My Prompt\", \"version\":\"1.0.0\"\n\n")

        # Apply completion logic based on last statement
        if self.statements:
            last_stmt = self.statements[-1]
            
            if last_stmt.keyword == '.exit':
                # 1. Already ends with .exit - do nothing
                pass
            elif last_stmt.keyword == '.exec':
                # 2. Ends with .exec - add exit
                self.statements.append(make_statement(self, len(self.statements), keyword='.exit', value=''))
            else:
                # 3. Ends with anything else - add exec and exit
                self.statements.append(make_statement(self, len(self.statements), keyword='.exec', value=''))
                self.statements.append(make_statement(self, len(self.statements), keyword='.exit', value=''))

        return

    def print_exception(self) -> None:
        """Print exception information to both console and file outputs."""
        self.console.print()
        self.console.print_exception(show_locals=True, width=terminal_width)  # Print to terminal
        if self.file_console:  # Ensure file is open
            self.file_console.print_exception()  # Print to file

    @property
    def current_msg_no(self) -> int:
        """The statement executing now. `StmtPrompt.execute` advances `ip` before the work."""
        return self.ip - 1

    def next_round_trip(self) -> int:
        """Number the next billed request of the statement executing now."""
        msg_no = self.current_msg_no
        self.round_trips_used[msg_no] = self.round_trips_used.get(msg_no, 0) + 1
        return self.round_trips_used[msg_no]

    # --- guards --------------------------------------------------------------------------------

    def accept_cmdargs(self, values: dict) -> None:
        """Caller-provided values (`--set`, `--set-from-json`) entering memory, on create or reply.

        They are kept as they arrived -- the text `#._cmdargs` judges -- and, if that guard is already
        declared (a reply), judged before any of them enters memory. On create the guard is declared
        later, and judges them when its `.guard` statement runs. They go through the same assignment
        as `.set`, so `$.` paths and the deprecated `model` behave identically wherever they come from.
        """
        self.cmdargs = dict(values)
        if self.cmdargs:
            self.guard(GUARD_CMDARGS, json.dumps(self.cmdargs, ensure_ascii=False, default=str))
        for name, value in self.cmdargs.items():
            self.assign(name, value)

    def guard(self, channel: str, text: str, guard: str | None = None) -> None:
        """Run the guard for external text arriving by `channel`, before it may enter the context.

        `guard` names a guard for this one call (`guard=#._intent`), replacing the channel's. A channel
        with no guard declared passes. A rejection, or a guard call that fails, stops execution.
        """
        if guard:
            path = self.expand_sigils(guard)
            if not self.has_path(path):
                raise StmtSyntaxError(f"guard '{guard}' is not defined; declare it with .guard first")
        else:
            path = f"{RESERVED_ROOT}.{GUARD_SUBSYSTEM}.{channel}"
            if not self.has_path(path):
                return
        GuardRun(self, self.current_msg_no, '.guard', path).judge(self, path, channel, text)

    @contextmanager
    def execute_unit_preserved(self):
        """Keep the execute in progress intact while a guard runs inside it.

        A guard can fire in the middle of another execute -- on a tool result inside an `.exec`'s
        tool loop -- and an execute works through `vm.prompt` and the VM's model registers.
        """
        prompt = self.prompt
        saved_vm = (self.model, self.model_name, self.provider, self.api_key)
        saved_prompt = (prompt.provider, prompt.model, prompt.model_lookup_key, prompt.api_key,
                        prompt.round_trips, getattr(prompt, '_current_call_id', None))
        saved_prompt_id = getattr(self.logger, 'prompt_id', None)
        try:
            yield
        finally:
            self.model, self.model_name, self.provider, self.api_key = saved_vm
            (prompt.provider, prompt.model, prompt.model_lookup_key, prompt.api_key,
             prompt.round_trips, prompt._current_call_id) = saved_prompt
            self.logger.set_prompt_id(saved_prompt_id)

    # A `$.`, `?.` or `#.` path inside an expression. `#` starts a Python comment, so paths are
    # replaced by their values before the expression is evaluated.
    _CONDITION_PATH = re.compile(r'(?<![\w.])([$?#])\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)')

    def evaluate_condition(self, expression: str) -> bool:
        """Evaluate a Python condition over memory paths, e.g. a guard's `fail:`."""
        values: dict[str, any] = {}

        def bind(match: re.Match) -> str:
            name = f"__v{len(values)}"
            values[name] = self.get_path(f"{match.group(1)}.{match.group(2)}")
            return name

        return bool(eval(self._CONDITION_PATH.sub(bind, expression), {'__builtins__': {}}, values))

    def load_model(self, model_name: str) -> None:
        """Make `model_name` the model the next execute runs on. The registry is the only authority."""
        try:
            model = ModelManager.get_model(model_name)
        except ValueError:
            raise StmtSyntaxError(f"Not Defined Error: Model {model_name} is not defined")
        if model.provider == '':
            raise StmtSyntaxError(f"Bad Model Definition error: provider not defined for model {model_name}")
        self.model_name = model_name
        self.model = model
        self.provider = model.provider

    def execute(self) -> None:
        """Execute the statements in the prompt file using the new standard logging system."""

        # Record wall clock start time
        self.wall_start = time.time()

        # Set initial prompt ID for logging context
        initial_prompt_id = f"{self.prompt_uuid}-init"
        self.logger.set_prompt_id(initial_prompt_id)

        # Execute all statements
        while self.ip < len(self.statements):
            stmt = self.statements[self.ip]
        # for self.ip, stmt in enumerate(self.statements):
            try:
                # VM DEBUG: Log before executing statement (only when --vm-debug flag is used)
                if self.vm_debug:
                    print(f"VM-DEBUG BEFORE EXEC: IP={self.ip}, Statement={stmt.keyword} '{stmt.value[:50]}{'...' if len(stmt.value) > 50 else ''}'", file=sys.stderr)
                    print(f"VM-DEBUG BEFORE EXEC: Total statements={len(self.statements)}", file=sys.stderr)
                    for i, s in enumerate(self.statements):
                        marker = " <-- CURRENT" if i == self.ip else ""
                        print(f"VM-DEBUG   [{i:02d}] {s.keyword} '{s.value[:30]}{'...' if len(s.value) > 30 else ''}'{marker}", file=sys.stderr)
                
                stmt.execute(self)
                
                # VM DEBUG: Log after executing statement (only when --vm-debug flag is used)
                if self.vm_debug:
                    print(f"VM-DEBUG AFTER EXEC: IP={self.ip}, Statement={stmt.keyword} completed", file=sys.stderr)
                    print(f"VM-DEBUG AFTER EXEC: Total statements={len(self.statements)}", file=sys.stderr)
                    for i, s in enumerate(self.statements):
                        marker = " <-- JUST EXECUTED" if i == self.ip else ""
                        print(f"VM-DEBUG   [{i:02d}] {s.keyword} '{s.value[:30]}{'...' if len(s.value) > 30 else ''}'{marker}", file=sys.stderr)
                    
            except Exception as e:
                self.logger.log_error(f"Error executing statement {self.ip}: {str(e)}")
                raise VMExecutionError(
                    f"Error executing statement {self.ip}: {str(e)}",
                    stmt_index=self.ip,
                    original_error=e,
                )

            if stmt.keyword == '.exit':
                break


        # Log chat end and cleanup
        if self.log_mode in [LogMode.LOG, LogMode.DEBUG]:
            self.logger.log_info(f"Completed execution")
            self.logger.close()

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

    def log_chat(self, call_id: str = None):
        """Log chat using the new logger system."""
        messages = self.prompt.to_json()
        
        # Add call_id to the chat metadata if provided
        if call_id:
            chat_data = {
                "call_id": call_id,
                "messages": messages
            }
        else:
            chat_data = messages
            
        self.logger.log_chat(chat_data)

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


    def execute_from(self, start_index: int = 0):
        """Execute statements starting from specified index"""
        # Set initial prompt ID for logging context
        initial_prompt_id = f"{self.prompt_uuid}-resume"
        self.logger.set_prompt_id(initial_prompt_id)
        
        # Log chat start
        if self.log_mode in [LogMode.LOG, LogMode.DEBUG]:
            header_name = self.filename or "chat"
            self.logger.log_info(f"Resuming execution of {header_name} from statement {start_index}")

        # Execute statements from start_index
        for stmt_no in range(start_index, len(self.statements)):
            stmt = self.statements[stmt_no]
            try:
                stmt.execute(self)
            except Exception as e:
                self.logger.log_error(f"Error executing statement {stmt_no}: {str(e)}")
                raise VMExecutionError(
                    f"Error executing statement {stmt_no}: {str(e)}",
                    stmt_index=stmt_no,
                    original_error=e,
                )

            if stmt.keyword == '.exit':
                break

        # Log chat end and cleanup
        if self.log_mode in [LogMode.LOG, LogMode.DEBUG]:
            self.logger.log_info(f"Completed resumed execution")
            self.logger.close()

    def apply_completion_logic(self):
        """Apply completion logic to the current statements"""
        if self.statements:
            last_stmt = self.statements[-1]
            
            if last_stmt.keyword == '.exit':
                # 1. Already ends with .exit - do nothing
                pass
            elif last_stmt.keyword == '.exec':
                # 2. Ends with .exec - add exit
                self.statements.append(make_statement(self, len(self.statements), keyword='.exit', value=''))
            else:
                # 3. Ends with anything else - add exec and exit
                self.statements.append(make_statement(self, len(self.statements), keyword='.exec', value=''))
                self.statements.append(make_statement(self, len(self.statements), keyword='.exit', value=''))

class StmtPrompt:

    # Whether a multi-line quote's body becomes part of this statement's value. True for statements
    # whose operand simply is the text (.system, .user, .set, ...). A statement that parses its own
    # line -- and so must not have pages of quoted text spliced into it -- sets this False and reads
    # the body from self.heredoc instead.
    heredoc_as_value = True

    def __init__(self, vm: VM, msg_no: int, keyword: str, value: str, heredoc: str | None = None):
        self.msg_no = msg_no
        self.keyword = keyword
        self.value = value
        self.heredoc = heredoc
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
        # Use new standard logging methods
        vm.logger.log_statement(self.msg_no, self.keyword, self.value)
        vm.ip += 1  # Increment the ip...


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


class StmtToolCall(StmtPrompt):
    """
    Handles the execution of a tool call statement in the VM.
    
    Creates an AiMessage with role='assistant' containing an AiCall.
    This represents the LLM requesting to execute a tool/function.
    
    Syntax: .tool_call function_name(param=value,...) id=call_id
    
    Example:
        .tool_call readfile(filename="data.txt") id=call_abc123
    
    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.tool_call').
        value (str): The tool call specification.
    
    Methods:
        execute(vm: VM): Parses the tool call and creates an assistant message with AiCall.
    """
    
    def execute(self, vm: VM) -> None:
        super().execute(vm)
        
        # Parse the statement value
        # Format: "function_name(param1=value1, param2=value2) id=call_id"
        
        # Extract call_id
        if ' id=' not in self.value:
            raise StmtSyntaxError(f".tool_call syntax error: missing id=call_id in '{self.value}'")
        
        func_part, id_part = self.value.rsplit(' id=', 1)
        call_id = id_part.strip()
        
        # Extract function name and arguments
        if '(' not in func_part:
            raise StmtSyntaxError(f".tool_call syntax error: missing function arguments in '{func_part}'")
        
        function_name, args_str = func_part.split('(', 1)
        function_name = function_name.strip()
        args_str = args_str.rstrip(')')
        
        # Parse arguments (simple key=value parsing)
        arguments = {}
        if args_str.strip():
            # Split by comma, but be careful with quoted strings
            import re
            # Simple parsing: split on commas not inside quotes
            args_list = []
            current_arg = ""
            in_quotes = False
            quote_char = None
            
            for char in args_str + ',':
                if char in ('"', "'") and (not in_quotes or char == quote_char):
                    in_quotes = not in_quotes
                    quote_char = char if in_quotes else None
                    current_arg += char
                elif char == ',' and not in_quotes:
                    if current_arg.strip():
                        args_list.append(current_arg.strip())
                    current_arg = ""
                else:
                    current_arg += char
            
            for arg in args_list:
                if '=' not in arg:
                    raise StmtSyntaxError(f".tool_call syntax error: invalid argument '{arg}'")
                
                key, value = arg.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Handle quoted strings
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                # Try to parse as boolean
                elif value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                # Try to parse as number
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass  # Keep as string
                
                arguments[key] = value
        
        # Create AiCall and add to messages
        from .AiPrompt import AiCall
        tool_call = AiCall(vm=vm, name=function_name, arguments=arguments, id=call_id)
        
        # Add as assistant message
        vm.prompt.add_message(vm=vm, role='assistant', content=[tool_call])


class StmtToolResult(StmtPrompt):
    """
    Handles the execution of a tool result statement in the VM.
    
    Creates an AiMessage with role='tool' containing an AiResult.
    This represents the result of a tool/function execution being sent back to the LLM.
    
    Syntax: .tool_result id=call_id name=function_name
            result content (can be multi-line)
    
    Example:
        .tool_result id=call_abc123 name=readfile
        File contents: Lorem ipsum dolor sit amet...
    
    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.tool_result').
        value (str): The tool result specification and content.
    
    Methods:
        execute(vm: VM): Parses the tool result and creates a tool message with AiResult.
    """
    
    def execute(self, vm: VM) -> None:
        super().execute(vm)
        
        # Parse the statement value
        # First line: "id=call_id name=function_name"
        # Rest: result content
        
        lines = self.value.split('\n', 1)
        header = lines[0]
        result_content = lines[1] if len(lines) > 1 else ""
        
        # Parse header
        if 'id=' not in header:
            raise StmtSyntaxError(f".tool_result syntax error: missing id=call_id in '{header}'")
        if 'name=' not in header:
            raise StmtSyntaxError(f".tool_result syntax error: missing name=function_name in '{header}'")
        
        # Extract id and name using simple parsing
        parts = header.split()
        call_id = None
        function_name = None
        
        for part in parts:
            if part.startswith('id='):
                call_id = part[3:].strip()
            elif part.startswith('name='):
                function_name = part[5:].strip()
        
        if not call_id or not function_name:
            raise StmtSyntaxError(f".tool_result syntax error: could not parse id and name from '{header}'")
        
        # Create AiResult and add to messages
        from .AiPrompt import AiResult
        tool_result = AiResult(vm=vm, name=function_name, id=call_id, result=result_content)
        
        # Add as tool message
        vm.prompt.add_message(vm=vm, role='tool', content=[tool_result])


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
            params = json.loads(self.value)
        except Exception as e:
            vm.logger.log_error(f"Error parsing .clear parameters: {str(e)}")
            vm.logger.print_exception()
            sys.exit(9)

        if not isinstance(params, list):
            vm.logger.log_error(f"Error parsing .clear parameters expected list, but got {type(params).__name__}: {self.value}")
            sys.exit(9)

        for k in params:
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

    This class represents a `.cmd` keyword statement in the prompt file. 
    The statement specifies a function to be executed along with arguments.
    
    Syntax:
        .cmd function_name(param=value,...)
        .cmd function_name(param=value,...) as variable_name
    
    When "as variable_name" is specified:
        - Result is stored in the named variable
        - Result is NOT appended to the current message
        - Result is still available in <<last_response>>
    
    When "as variable_name" is omitted:
        - Result is appended to the current message content
        - Result is stored in <<last_response>>

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


        if self.vm.vm_debug:
            print(f"VM-DEBUG .cmd EXEC: {FunctionSpace.functions.tools_array}",file=sys.stderr)

        # Check for optional "as variable_name" clause
        variable_name = None
        guard, value = split_guard_param(self.value)

        if ' as ' in value:
            # Split on " as " to separate function call from variable assignment
            func_part, variable_name = value.rsplit(' as ', 1)
            variable_name = variable_name.strip()
            
            # Validate variable name is not empty
            if not variable_name:
                raise StmtSyntaxError(f"{vm.filename}:{self.msg_no} .cmd syntax error: variable name required after 'as'")
            
            # Validate variable name follows Python naming rules
            import re
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', variable_name):
                raise StmtSyntaxError(f"{vm.filename}:{self.msg_no} .cmd syntax error: invalid variable name '{variable_name}'")
            
            value = func_part.strip()

        # Parse the function call
        function_name, args = value.split('(', maxsplit=1)
        function_name = function_name.strip()
        args = args[:-1]
        args_list = args.split(",")
        function_args = {}

        if args:
            for arg in args_list:
                name, arg_value = arg.split("=", maxsplit=1)
                function_args[name.strip()] = arg_value.strip()

        # Check if function exists in function_array
        function_exists = any(f['name'] == function_name for f in FunctionSpace.functions.function_array)
        
        if not function_exists:
            vm.print(
                f"[bold red]Error executing {function_name}({function_args}): {function_name} is not defined.[/bold red]")
            raise Exception(f"{function_name} is not defined.")

        try:
            # Use FunctionSpace.call() method which handles both internal and external functions
            text = FunctionSpace.functions.call(function_name, function_args)
        except Exception as err:
            vm.print(f"Error executing {function_name}({function_args})): {str(err)}")
            raise err

        vm.guard(function_name, text, guard)

        # Store in last_response (always)
        vm.set_variable('last_response', text)

        # Conditional: append to message OR store in custom variable
        if variable_name:
            # Store in custom variable only
            vm.set_variable(variable_name, text)
        else:
            # Original behavior: append to current message
            last_msg = vm.prompt.current_message()
            if last_msg:
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
        super().execute(vm)

        if not self.value:
            self.value = '["all"]'

        if self.value[0] != '[':
            self.value = f"[{self.value}]"

        # vm.print(self.value)
        try:
            params = json.loads(self.value)
        except Exception as e:
            vm.print(f"{VERTICAL} [white on red]Error parsing .debug parameters: {str(e)}[/]\n\n")
            vm.print_exception()
            sys.exit(9)

        if not isinstance(params, list):
            vm.print(
                f"{VERTICAL} [white on red]Error parsing .debug parameters expected list, but got {type(params).__name__}: {self.value}")
            sys.exit(9)

        vm.debug_print(elements=params)


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
        """One execute: resolve the model, call it through its provider, record the round trips.

        This is the whole execute for every kind of model. `.evaluate` is a subclass that differs
        only in the hooks below -- which model, which kind of model, and what its content is.
        """
        super().execute(vm)
        self.run(vm)

    def run(self, vm: VM) -> None:
        """The execute itself. A guard runs it without being a statement of the program."""
        header = f"[bold white]{VERTICAL}[/][white]{self.msg_no:02}[/] [cyan]{self.keyword:<8}[/]"

        model_name = self.resolve_model(vm)

        # Load the model (single point of instantiation)
        try:
            vm.load_model(model_name)
        except Exception as e:
            vm.logger.log_error(f"{self.keyword} error: {e}")
            raise StmtSyntaxError(f"{self.keyword} error: {e}")

        self.refuse_wrong_mode(vm)
        self.model_loaded(vm)

        # Get API key for this provider
        config = get_config()
        api_key = config.get_api_key(vm.provider)
        if not api_key:
            error_msg = config.get_missing_key_error(vm.provider)
            vm.logger.log_error(error_msg)
            sys.exit(1)

        vm.api_key = api_key

        # Sync prompt object with VM state
        vm.prompt.api_key = vm.api_key
        vm.prompt.provider = vm.provider
        vm.prompt.model = vm.model.model
        vm.prompt.model_lookup_key = vm.model_name  # Set the lookup key for ModelManager

        start_time = time.time()

        # Generate unique call identifier using UUID with exec format
        vm.interaction_no += 1
        call_id = f"{vm.prompt_uuid}-exec{vm.interaction_no:03d}"

        # Set the prompt ID in the logger for all subsequent log entries
        vm.logger.set_prompt_id(call_id)

        self.before_call(vm)

        try:
            responses = vm.prompt.ask(label=header, call_id=call_id)
        except Exception as e:
            # Round trips that completed before the failure were still billed. Record them
            # instead of losing them with the exception; save_chat() flushes pending_costs
            # on the error path too.
            self._record_round_trips(vm, call_id, list(getattr(vm.prompt, 'round_trips', [])),
                                     success=False, error_message=str(e))
            raise
        elapsed_time = time.time() - start_time

        # Per-round-trip usage recorded by the provider during ask(). One entry per billed
        # API request -- a tool loop produces several. The statement total is their sum;
        # counting only the last one was DEFECT-001.
        round_trips = list(getattr(vm.prompt, 'round_trips', []))

        self.after_call(vm, responses, round_trips)
        if round_trips:
            vm.set_path(f"{self.output_scope(vm)}.{PROVIDER_SELECTED_KEY}",
                        round_trips[-1]['provider_selected_model'])

        if round_trips:
            tokens_in, tokens_out, cost_in, cost_out = self._record_round_trips(vm, call_id, round_trips)

            # Log tokens and costs (statement totals)
            vm.logger.log_llm_tokens_and_cost(call_id, tokens_in, tokens_out, cost_in, cost_out)

        # Log the exec completion to statements.log (only this one, not the initial empty one)
        exec_completion_msg = f"{vm.model.provider}::{vm.model_name} {call_id} completed in {elapsed_time:.2f} seconds"
        vm.logger.log_statement(self.msg_no, self.keyword, exec_completion_msg)

        # Format the execution timing to match the table structure
        timing_msg = f"{vm.model.provider}::{vm.model_name} completed in {elapsed_time:.2f} seconds"
        # Use same width calculation as other timing lines
        content_len = vm.logger.terminal_width - 14  # Same as statement lines
        padded_content = f"{timing_msg:<{content_len}}"
        final_line = f"[white]{VERTICAL}[/]            {padded_content}[white]{VERTICAL}[/]"
        vm.logger.log_execution(final_line)
        
        # Log the response using structured logging
        vm.logger.log_llm_call(f"Response from {vm.model.provider} API completed", call_id)

        # Note: chat logging is now handled incrementally through log_message_exchange
        # No need to log the entire chat again here

    # --- what differs between an LLM (.exec) and an LDM (.evaluate) ---------------------------

    def resolve_model(self, vm: VM) -> str:
        """The model on the `.exec` line, otherwise `$.llm_model`. A line model is kept in memory."""
        _reject_legacy_top_level_llm_options(vm.vdict)

        if not self.value.strip():
            if not vm.has_path(LLM_MODEL_PATH):
                raise StmtSyntaxError(
                    f".exec error: No model specified. Set $.llm_model via:\n"
                    f"  .prompt \"params\":{{\"$.llm_model\":\"...\"}}\n"
                    f"  .set $.llm_model <model_name>\n"
                    f"  --set '$.llm_model' <model_name>"
                )
            return vm.get_path(LLM_MODEL_PATH)

        # `.exec`'s whole operand may come from a variable, so it is substituted before it is split.
        value = vm.substitute(self.value.strip())
        params_text, rest = split_line_params(value, self.keyword)
        if params_text:
            if rest.strip():
                raise StmtSyntaxError(f".exec syntax: unexpected text after params: '{rest.strip()}'")
            params = parse_line_params(vm, params_text, self.keyword, substitute=False)
        else:
            params = {'llm_model': value}
        _reject_legacy_top_level_llm_options(params)

        # `llm_model` on the line is this unit's model; anything else is ordinary memory.
        if 'llm_model' in params:
            vm.set_path(LLM_MODEL_PATH, params.pop('llm_model'))
        for name, val in params.items():
            vm.assign(name, val)
        if not vm.has_path(LLM_MODEL_PATH):
            raise StmtSyntaxError(f".exec syntax: no model in '{self.value}'")
        return vm.get_path(LLM_MODEL_PATH)

    def refuse_wrong_mode(self, vm: VM) -> None:
        # A decision model selects from fixed options and never emits text, so it cannot answer a
        # conversation. Refusing here is cheaper than a provider error that would not explain why.
        if getattr(vm.model, 'mode', 'chat') == LDM_MODE:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].exec error: '{vm.model.model}' is a decision model (LDM), not a "
                f"chat model. It answers .evaluate, not .exec.[/]\n\n")

    def model_loaded(self, vm: VM) -> None:
        """The LLM's registers: simple, JSON-safe metadata prompts can read."""
        vm.vdict['provider'] = vm.provider
        vm.vdict['filename'] = vm.filename
        # Full model metadata so prompts can read fields like <<model_info.max_input_tokens>>
        from dataclasses import asdict
        vm.vdict['model_info'] = asdict(vm.model) if vm.model else {}

    def before_call(self, vm: VM) -> None:
        """An LLM is sent the conversation as it stands; nothing to add."""

    def output_scope(self, vm: VM) -> str:
        """Where this unit's outputs such as `_provider_selected_model` land: the prompt."""
        return RESERVED_ROOT

    def after_call(self, vm: VM, responses: list, round_trips: list) -> None:
        """The reply text becomes `last_response`; context occupancy is refreshed."""
        last_response_text = ""
        for response in responses:
            if hasattr(response, 'content') and response.content:
                for part in response.content:
                    if isinstance(part, AiTextPart):
                        last_response_text += part.text
        vm.set_variable('last_response', last_response_text)

        if round_trips:
            # Context occupancy is a property of the LAST round trip, not of the statement
            # total: it answers "how full is the context right now", not "what did this cost".
            last_rt = round_trips[-1]
            max_in = (vm.model.max_input_tokens or vm.model.max_tokens) if vm.model else 0
            max_out = (vm.model.max_output_tokens or vm.model.max_tokens) if vm.model else 0
            vm.vdict['context_usage'] = {
                'input_pct': round(last_rt['tokens_in'] / max_in * 100, 1) if max_in else 0,
                'output_pct': round(last_rt['tokens_out'] / max_out * 100, 1) if max_out else 0,
                'input_tokens': last_rt['tokens_in'],
                'output_tokens': last_rt['tokens_out'],
                'max_input': max_in,
                'max_output': max_out,
            }

    def _record_round_trips(self, vm: VM, call_id: str, round_trips: list,
                            success: bool = True, error_message: str = None) -> tuple:
        """Fold a statement's billed round trips into the VM totals and the cost ledger.

        One `cost_tracking` row per round trip, each describing exactly one API request:
        its own tokens, its own cost, its own elapsed time. Returns the statement totals
        (tokens_in, tokens_out, cost_in, cost_out).
        """
        if not round_trips:
            return 0, 0, 0.0, 0.0

        tokens_in = sum(rt['tokens_in'] for rt in round_trips)
        tokens_out = sum(rt['tokens_out'] for rt in round_trips)
        cost_in = sum(rt['cost_in'] for rt in round_trips)
        cost_out = sum(rt['cost_out'] for rt in round_trips)

        # Update VM totals
        vm.toks_in += tokens_in
        vm.toks_out += tokens_out
        vm.cost_in += cost_in
        vm.cost_out += cost_out
        vm.total = vm.cost_in + vm.cost_out
        vm.tool_time += sum(rt['tool_time'] for rt in round_trips)
        vm.round_trip_count += len(round_trips)
        # vm.api_time is accumulated per request in AiProvider.make_api_request

        # Get model configuration parameters
        context_length = vm.llm.get('context_length') if vm.llm else None
        parameters_json = json.dumps(vm.vdict, default=str) if vm.vdict else None

        for seq, rt in enumerate(round_trips, start=1):
            cost_data = {
                'call_id': f"{call_id}-{rt['label']}",
                'tokens_in': rt['tokens_in'],
                'tokens_out': rt['tokens_out'],
                'cost_in': float(rt['cost_in']),
                'cost_out': float(rt['cost_out']),
                'estimated_costs': float(rt['cost_in'] + rt['cost_out']),
                'elapsed_time': float(rt['api_time']),
                'tool_time': float(rt['tool_time']),
                'model': rt.get('model') or vm.model_name,
                'provider': rt.get('provider') or vm.provider,
                'provider_selected_model': rt.get('provider_selected_model'),
                # These round trips completed and were billed; success reflects whether the
                # statement they belong to went on to fail.
                'success': success,
                'error_message': error_message,
                'prompt_semantic_name': vm.prompt_name,
                'prompt_version_tracking': vm.prompt_version,
                'expected_params': json.dumps(vm.expected_params) if vm.expected_params else None,
                'execution_mode': vm.log_mode.name.lower() if hasattr(vm.log_mode, 'name') else 'production',
                # vdict is statement-scoped, not round-trip-scoped, and carries the whole
                # last_response. Record it once per .exec rather than once per request.
                'parameters': parameters_json if seq == 1 else None,
                'environment': os.getenv('ENVIRONMENT', 'development'),
                'context_length': context_length
            }
            vm.pending_costs.append((self.msg_no, rt['round_trip'], cost_data))

        return tokens_in, tokens_out, cost_in, cost_out


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
        super().execute(vm)
        
        # Log total costs when exiting
        if vm.toks_in > 0 or vm.toks_out > 0:
            wall_time = time.time() - getattr(vm, 'wall_start', time.time())
            vm.logger.log_total_costs(vm.toks_in, vm.toks_out, vm.cost_in, vm.cost_out, vm.provider, vm.model_name, vm.prompt_uuid, vm.interaction_no, wall_time=wall_time, api_time=vm.api_time, context_usage=vm.vdict.get('context_usage'))




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
        super().execute(vm)
        guard, value = split_guard_param(self.value)
        filename = vm.substitute(value)

        # Support glob patterns in .include
        if any(c in filename for c in ('*', '?', '[')):
            files = sorted(glob.glob(filename, recursive=True))
            if not files:
                vm.logger.log_warning(f".include glob pattern matched no files: {filename}")
                return
        else:
            files = [filename]
        for f in files:
            lines = FunctionSpace.functions.call('readfile', {'filename': f})
            vm.guard(GUARD_INCLUDE, lines, guard)
            last_msg = vm.prompt.current_message()
            last_msg.content.append(AiTextPart(vm=vm, text=lines))


class StmtImage(StmtPrompt):
    """
    Handles the execution of an image-related statement in the VM.

    This class represents a `.image` keyword statement that adds an image
    to the AI prompt context. It incorporates a provided image file into the
    chat as an input element.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.image').
        value (str): The value associated with the statement, typically the image file path.

    Methods:
        execute(vm: VM): Adds the specified image to the VM's prompt context for processing.
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)
        filename = self.value
        vm.prompt.add_message(vm=vm, role="user", content=[AiImagePart(vm=self.vm, filename=filename)])


class StmtSystem(StmtPrompt):
    """
    Handles the execution of a system message in the Virtual Machine (VM).

    This class represents a `.system` keyword statement in the prompt file and
    allows for adding a system role message into the AI chat context.
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
    chat context.

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
        current = vm.prompt.current_message()
        if current and current.role in ['assistant', 'system', 'user']:
            current.content.append(AiTextPart(vm=vm, text=self.value))
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

    # Set when the text is external: a `chat reply` message arrives by the `_userinput` channel.
    channel: str | None = None
    # A reply's `--set` / `--set-from-json` values, which arrive with its message.
    cmdargs: dict | None = None

    def execute(self, vm: VM) -> None:
        super().execute(vm)
        if self.cmdargs:
            vm.accept_cmdargs(self.cmdargs)
        if not self.value:
            vm.prompt.add_message(vm=vm, role='user', content=[])
        else:
            # Substitute variables in the user message
            substituted_text = vm.substitute(self.value)
            if self.channel:
                vm.guard(self.channel, substituted_text)
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
        md = Markdown(output_text)
        # Route through the unified terminal output channel so:
        # - pretty mode: this prints normally to stdout
        # - --json mode: this is captured into the JSON envelope's `stdout`
        terminal_output.print(
            Panel(
                md,
                title=f"[bold cyan]chat {vm.prompt_uuid}:{vm.interaction_no}[/bold cyan]",
                border_style="cyan",
                padding=(0, 0),
                expand=False,
                highlight=True,
            ),
            markup=True,
            soft_wrap=True,
        )


class StmtPromptMeta(StmtPrompt):
    """
    Handles the execution of a prompt metadata statement in the VM.

    This class represents a `.prompt` keyword statement in the prompt file. It 
    defines metadata about the prompt: version and expected parameters. The prompt is named
    by its file's basename; a 'name' field is ignored with a warning.
    This statement must be the first statement in a prompt file and version is required.

    Attributes:
        msg_no (int): The message number in the execution sequence.
        keyword (str): The keyword associated with the statement (e.g., '.prompt').
        value (str): JSON-like format: "version":"1.0.0", "params":{...}

    Methods:
        execute(vm: VM): Parses prompt metadata and stores it in VM for cost tracking.
    """

    def execute(self, vm: VM) -> None:
        # Log the prompt statement execution to development channels (STDERR)
        super().execute(vm)
        
        # Parse JSON-like content
        if not self.value.strip():
            raise StmtSyntaxError(f".prompt syntax error: metadata required")
        
        # Wrap in braces to make valid JSON
        json_content = "{" + self.value + "}"
        
        try:
            prompt_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            raise StmtSyntaxError(f".prompt syntax error: invalid JSON format: {e}")
        
        # Validate required fields
        if "name" in prompt_data:
            vm.logger.log_warning(f".prompt 'name' is ignored; the prompt is named '{vm.prompt_name}' after its file")
        if "version" not in prompt_data:
            raise StmtSyntaxError(f".prompt syntax error: missing required 'version' field")
        
        # Store prompt metadata in VM for cost tracking
        vm.prompt_version = prompt_data["version"]
        vm.expected_params = prompt_data.get("params", {})
        
        # Set variables from params for substitution (only if not already set by command line)
        if "params" in prompt_data:
            for key, value in prompt_data["params"].items():
                path = vm.canonical_name(key)
                if not vm.has_path(path):
                    vm.assign(path, value)
                elif path == "llm_options" and vm.vdict[path] == {}:
                    vm.assign(path, value)
        
        # Log the prompt metadata
        vm.logger.log_info(f"Prompt metadata: {vm.prompt_name} v{vm.prompt_version}")


class StmtFunctions(StmtPrompt):
    """
    Declares which functions the model can use during .exec calls.

    If no .functions statement is present, the model gets NO functions (safe default).

    Syntax: .functions readfile, writefile, wwwget
    """

    def execute(self, vm: VM) -> None:
        super().execute(vm)

        value = self.value.strip()
        if not value:
            raise StmtSyntaxError(".functions syntax error: at least one function name required")

        # Parse comma-separated list
        names = [name.strip() for name in value.split(',')]
        names = [n for n in names if n]  # Remove empty strings

        # Resolve specs: bare names, module.*, module.func
        try:
            resolved = FunctionSpace.functions.resolve_function_names(names)
        except ValueError as e:
            raise StmtSyntaxError(f".functions error: {e}")

        vm.allowed_functions = resolved


class StmtQuestion(StmtPrompt):
    """Declares a named question set for an LDM.

    Syntax:
        .question <SetName> [model] <<<ID
            <question-name>: <choice|score|noul>
                instructions: what is being asked
                <option>: what that option means
        >>>ID

    The body arrives in a multi-line quote rather than as continuation lines, because criteria are
    two levels deep and the continuation rule strips indentation. Criteria are the substance: both
    Jev trials turned on them, and they are the bulk of the tokens, so a criterion may run over
    several lines -- a deeper line that is not `key: value` continues the previous one.
    """

    heredoc_as_value = False

    PRIMITIVES = ('choice', 'score', 'noul')
    INSTRUCTIONS_KEY = 'instructions'

    def parse_body(self, body: str) -> dict:
        """Indented body -> {question-name: {type, instructions, criteria}}."""
        questions: dict[str, dict] = {}
        current: dict | None = None
        current_key: str | None = None
        question_indent: int | None = None

        for lno, raw in enumerate(body.split('\n'), start=1):
            if not raw.strip():
                continue
            indent = len(raw) - len(raw.lstrip())
            line = raw.strip()

            if question_indent is None:
                question_indent = indent

            if indent <= question_indent:
                name, _, primitive = line.partition(':')
                name, primitive = name.strip(), primitive.strip()
                if not name or primitive not in self.PRIMITIVES:
                    raise StmtSyntaxError(
                        f"{VERTICAL} [red].question body line {lno}: expected "
                        f"'<name>: <{'|'.join(self.PRIMITIVES)}>', got '{line}'.[/]\n\n")
                if name in questions:
                    raise StmtSyntaxError(
                        f"{VERTICAL} [red].question body line {lno}: question '{name}' "
                        f"is defined twice.[/]\n\n")
                if name.startswith(RESERVED_PREFIX):
                    raise StmtSyntaxError(
                        f"{VERTICAL} [red].question body line {lno}: '{name}' is reserved; "
                        f"a question name may not start with '{RESERVED_PREFIX}'.[/]\n\n")
                current = {'type': primitive, 'instructions': '', 'criteria': {}}
                questions[name] = current
                current_key = None
                continue

            if current is None:
                raise StmtSyntaxError(
                    f"{VERTICAL} [red].question body line {lno}: '{line}' appears before any "
                    f"question is declared.[/]\n\n")

            key, sep, text = line.partition(':')
            key, text = key.strip(), text.strip()
            if not sep or not key:
                # Continuation of the previous criterion or of the instructions.
                if current_key is None:
                    raise StmtSyntaxError(
                        f"{VERTICAL} [red].question body line {lno}: expected '<key>: <text>', "
                        f"got '{line}'.[/]\n\n")
                if current_key == self.INSTRUCTIONS_KEY:
                    current['instructions'] = f"{current['instructions']} {line}".strip()
                else:
                    current['criteria'][current_key] = \
                        f"{current['criteria'][current_key]} {line}".strip()
                continue

            if key == self.INSTRUCTIONS_KEY:
                current['instructions'] = text
            else:
                current['criteria'][key] = text
            current_key = key

        if not questions:
            raise StmtSyntaxError(f"{VERTICAL} [red].question: no questions defined.[/]\n\n")

        for name, spec in questions.items():
            # A `score` rubric is an ordered list of levels, not a mapping: the API keys its
            # probabilities positionally ("0", "1", ...) and returns its own legend, so the author's
            # keys are labels for reading, not scores. Converted here rather than at send time so
            # that `_definition` records exactly what was sent.
            if spec['type'] == 'score':
                spec['criteria'] = list(spec['criteria'].values())
            if spec['type'] == 'noul' and spec['criteria']:
                raise StmtSyntaxError(
                    f"{VERTICAL} [red].question: '{name}' is a noul and takes no options; it asks "
                    f"whether its instructions are true of the state.[/]\n\n")
        return questions

    def execute(self, vm: VM) -> None:
        super().execute(vm)

        parts = self.value.split()
        if not parts:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].question syntax error: a set name is required.[/]\n\n")
        set_name, model = parts[0], (parts[1] if len(parts) > 1 else None)

        if set_name.startswith(RESERVED_PREFIX):
            raise StmtSyntaxError(
                f"{VERTICAL} [red].question: '{set_name}' is reserved; a set name may not start "
                f"with '{RESERVED_PREFIX}'.[/]\n\n")
        if self.heredoc is None:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].question '{set_name}': the questions must be given in a "
                f"multi-line quote, e.g. .question {set_name} <<<END ... >>>END.[/]\n\n")

        questions = self.parse_body(self.heredoc)
        vm.set_path(f"{RESERVED_ROOT}.{QUESTION_SUBSYSTEM}.{set_name}",
                    self.question_set(questions, model))

    @staticmethod
    def question_set(questions: dict, model: str | None) -> dict:
        """The set as memory holds it. Definitions live a level down so the definition's `type` (the
        primitive asked for) cannot collide with the answer's `type` (the primitive that answered)."""
        question_set = {name: {DEFINITION_KEY: spec} for name, spec in questions.items()}
        if model:
            question_set[SET_MODEL_KEY] = model
        return question_set


class StmtGuard(StmtQuestion):
    """Declares a guard: a question set with a fail condition, run on external text as it arrives.

    Syntax:
        .guard <name> <model> <<<ID
            <question-name>: <choice|score|noul>
                instructions: what is being asked
                <option>: what that option means
            fail: <Python condition over #.<name>.<question>.value / .confidence / ...>
        >>>ID

    The same as `.question`, with two differences: it has a fail condition, and no `.evaluate` runs
    it -- the runtime does, when its channel delivers text (`VM.guard`). The model is required, with
    no fallback. `_cmdargs` guards text that is already in memory, so it runs as soon as it is
    declared. Stored at `#.<name>`.
    """

    FAIL_MARKER = 'fail'

    def parse_body(self, body: str) -> dict:
        """The questions, plus the one top-level `fail:` line, returned under GUARD_FAIL_KEY."""
        lines = body.split('\n')
        indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
        top = min(indents) if indents else 0
        fail_lines = [i for i, l in enumerate(lines)
                      if l.strip() and len(l) - len(l.lstrip()) == top
                      and l.strip().partition(':')[0].strip() == self.FAIL_MARKER]
        if len(fail_lines) != 1:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].guard: exactly one top-level '{self.FAIL_MARKER}:' line is "
                f"required; found {len(fail_lines)}.[/]\n\n")
        fail = lines[fail_lines[0]].strip().partition(':')[2].strip()
        if not fail:
            raise StmtSyntaxError(f"{VERTICAL} [red].guard: '{self.FAIL_MARKER}:' has no condition.[/]\n\n")
        questions = super().parse_body('\n'.join(l for i, l in enumerate(lines) if i != fail_lines[0]))
        return {**questions, GUARD_FAIL_KEY: fail}

    def execute(self, vm: VM) -> None:
        StmtPrompt.execute(self, vm)

        parts = self.value.split()
        if len(parts) != 2:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].guard syntax error: a name and a model are required, e.g. "
                f".guard _userinput typesafe/jev-latest <<<END ... >>>END.[/]\n\n")
        name, model = parts
        if self.heredoc is None:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].guard '{name}': the questions must be given in a multi-line "
                f"quote, e.g. .guard {name} {model} <<<END ... >>>END.[/]\n\n")

        body = self.parse_body(self.heredoc)
        fail = body.pop(GUARD_FAIL_KEY)
        guard = {**self.question_set(body, model), GUARD_FAIL_KEY: fail}
        vm.set_path(f"{RESERVED_ROOT}.{GUARD_SUBSYSTEM}.{name}", guard)

        if name == GUARD_CMDARGS and vm.cmdargs:
            vm.guard(GUARD_CMDARGS, json.dumps(vm.cmdargs, ensure_ascii=False, default=str))


class StmtEvaluate(StmtExec):
    """Runs a declared question set against a state, using an LDM.

    Syntax:
        .evaluate ?.SetName [{"ldm_model":"..."}] <state>
        .evaluate ?.SetName [{"ldm_model":"..."}] <<<ID
        ...state...
        >>>ID

    The optional params are the same JSON params `.exec` takes; `ldm_model` is the only one.

    An execute like `.exec`, through the same provider path, record and totals. What differs is
    the content: `.question` has saved the question set in memory, `.evaluate` adds the state and
    puts both into an LDM message, and the answers come back into that message and into the set,
    where the prompt reads them: `?.Intent.action.value`.

    The model is the set's own, `?.Intent._model`, otherwise `$.ldm_model`. `ldm_model` in this
    line's params writes the set's model, as the `.question` line does; it stays for later calls.
    """

    heredoc_as_value = False

    def resolve_model(self, vm: VM) -> str:
        path, _, rest = self.value.strip().partition(' ')
        if not path:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].evaluate syntax error: a question set is required, "
                f"e.g. .evaluate ?.Intent <<<STATE.[/]\n\n")

        params_text, rest = split_line_params(rest, self.keyword)
        params = parse_line_params(vm, params_text, self.keyword) if params_text else {}
        unknown = set(params) - {'ldm_model'}
        if unknown:
            raise StmtSyntaxError(
                f".evaluate syntax: unknown params {sorted(unknown)}; the only one is 'ldm_model'")
        line_model = params.get('ldm_model')

        if self.heredoc is not None:
            if rest.strip():
                raise StmtSyntaxError(
                    f".evaluate syntax: unexpected text '{rest.strip()}' before a quoted state")
            state = self.heredoc
        else:
            state = rest.strip()
        state = vm.substitute(state)
        if not state.strip():
            raise VMExecutionError(f".evaluate {path}: no state to evaluate", self.msg_no,
                                   ValueError("empty state"))

        try:
            question_set = vm.get_path(path)
        except ValueError as e:
            raise VMExecutionError(
                f".evaluate: question set '{path}' is not defined; declare it with .question first",
                self.msg_no, e)
        if not isinstance(question_set, dict):
            raise VMExecutionError(f".evaluate: '{path}' is not a question set", self.msg_no,
                                   TypeError(type(question_set).__name__))

        questions = {name: branch[DEFINITION_KEY]
                     for name, branch in question_set.items()
                     if isinstance(branch, dict) and DEFINITION_KEY in branch}
        if not questions:
            raise VMExecutionError(f".evaluate: '{path}' defines no questions", self.msg_no,
                                   ValueError("empty question set"))

        if line_model:
            vm.set_path(f"{vm.expand_sigils(path)}.{SET_MODEL_KEY}", line_model)
        model = line_model or question_set.get(SET_MODEL_KEY)
        if not model:
            if not vm.has_path(LDM_MODEL_PATH):
                raise StmtSyntaxError(
                    f".evaluate error: No LDM model specified. Name one on the .evaluate or "
                    f".question line, or set $.ldm_model via:\n"
                    f"  .prompt \"params\":{{\"$.ldm_model\":\"...\"}}\n"
                    f"  .set $.ldm_model <model_name>\n"
                    f"  --set '$.ldm_model' <model_name>"
                )
            model = vm.get_path(LDM_MODEL_PATH)

        self.target, self.state, self.questions = vm.expand_sigils(path), state, questions
        return vm.substitute(model)

    def refuse_wrong_mode(self, vm: VM) -> None:
        # A chat model generates text instead of selecting; it cannot answer a question set.
        if getattr(vm.model, 'mode', 'chat') != LDM_MODE:
            raise StmtSyntaxError(
                f"{VERTICAL} [red].evaluate error: '{vm.model.model}' is a chat model (LLM), not a "
                f"decision model. It answers .exec, not .evaluate.[/]\n\n")

    def model_loaded(self, vm: VM) -> None:
        """The LLM's registers (`provider`, `model_info`) are not the LDM's to overwrite."""

    def before_call(self, vm: VM) -> None:
        """The content: an LDM message holding the question set and the state."""
        part = AiLdmPart(vm=vm, set_path=self.target, questions=self.questions,
                         state=self.state, model=vm.model_name)
        # Appended, never merged: every LDM call is its own message.
        vm.prompt.messages.append(AiMessage(vm=vm, role=LDM_ROLE, content=[part],
                                            model_name=vm.model_name, provider=vm.provider,
                                            stmt_no=self.msg_no))

    def after_call(self, vm: VM, responses: list, round_trips: list) -> None:
        """The answers land in the set, where the prompt reads them."""
        part = next(p for p in responses[-1].content if isinstance(p, AiLdmPart))
        for name, answer in part.answers.items():
            for field, val in answer.items():
                vm.set_path(f"{self.target}.{name}.{field}", val)
        vm.set_path(f"{self.target}._usage", part.usage)

    def output_scope(self, vm: VM) -> str:
        """An LDM's outputs land in its question set, not in the prompt."""
        return self.target


class PromptInjectionDetected(Exception):
    """A guard's fail condition held: the text it judged never enters the context."""


class GuardRun(StmtEvaluate):
    """One guard execution. An execute like `.evaluate` -- same provider path, record and totals --
    but started by the runtime when external text arrives, not by a statement. Its record is a
    `guard` message, never sent to an LLM; its answers land in the guard, `#.<name>`."""

    def judge(self, vm: VM, path: str, channel: str, text: str) -> None:
        """Run the guard on `text`; raise if its fail condition holds."""
        self.target, self.channel, self.state = path, channel, text
        with vm.execute_unit_preserved():
            self.run(vm)
        # Evaluated after the execute has recorded its billed request, so an error here loses nothing.
        try:
            self.part.failed = vm.evaluate_condition(self.fail)
        except Exception as e:
            raise StmtSyntaxError(f"guard '{path}': fail condition '{self.fail}': {e}")
        if self.part.failed:
            name = '#' + path[len(f"{RESERVED_ROOT}.{GUARD_SUBSYSTEM}"):]
            raise PromptInjectionDetected(
                f"prompt injection detected: guard '{name}' rejected text from '{channel}'")

    def resolve_model(self, vm: VM) -> str:
        guard = vm.get_path(self.target)
        self.questions = {name: branch[DEFINITION_KEY] for name, branch in guard.items()
                          if isinstance(branch, dict) and DEFINITION_KEY in branch}
        self.fail = guard[GUARD_FAIL_KEY]
        return guard[SET_MODEL_KEY]

    def before_call(self, vm: VM) -> None:
        """The content: a guard message holding the questions and the text judged."""
        self.part = AiGuardPart(vm=vm, set_path=self.target, questions=self.questions,
                                state=self.state, model=vm.model_name, channel=self.channel,
                                fail=self.fail)
        vm.prompt.messages.append(AiMessage(vm=vm, role=GUARD_ROLE, content=[self.part],
                                            model_name=vm.model_name, provider=vm.provider,
                                            stmt_no=self.msg_no))



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
        
        # Substitute variables in the value before storing
        substituted_value = vm.substitute(var_value)
        
        # Any memory: a plain name, a dotted path, or a `$.`/`?.` path
        vm.assign(var_name, substituted_value)




# Create a _PromptStatement subclass depending on keyword
StatementTypes: dict[str, type(StmtPrompt)] = {
    '.#': StmtComment,
    '.assistant': StmtAssistant,
    '.clear': StmtClear,
    '.cmd': StmtCmd,
    '.debug': StmtDebug,
    '.evaluate': StmtEvaluate,
    '.exec': StmtExec,
    '.exit': StmtExit,
    '.functions': StmtFunctions,
    '.guard': StmtGuard,
    '.image': StmtImage,
    '.include': StmtInclude,
    '.print': StmtPrint,
    '.prompt': StmtPromptMeta,
    '.question': StmtQuestion,
    '.set': StmtSet,
    '.system': StmtSystem,
    '.text': StmtText,
    '.tool_call': StmtToolCall,
    '.tool_result': StmtToolResult,
    '.user': StmtUser,
}

keywords = StatementTypes.keys()

def make_statement(vm: VM, msg_no: int, keyword: str, value: str,
                   heredoc: str | None = None) -> StmtPrompt:
    my_class = StatementTypes[keyword]
    return my_class(vm, msg_no, keyword, value, heredoc)

