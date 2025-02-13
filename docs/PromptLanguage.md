# The _.prompt_ language Syntax

Here I explain the syntax of prompt language based on a set of Rules:

### R1: Line based
    Each line is one statement.

### R2: Empty lines are ignored.
    lines containg white space are ignored.

### R3: Each line starts with a keyword in first column

    Each line starts with a keyword in col 1, 
    optionally followed by a space and a value (rest of line).

  Keywords:

    '.#', '.assistant', '.clear', '.cmd', '.debug', '.exec', '.exit', 
    '.image', '.include', '.llm', '.system',  '.text', '.user'

### R4: Implicit '.text':

    Lines without a valid keyword in column one, are assumed to be of type '.text'

### R5: Concatenation of '.text' statements
    '.text' statements are concatenated to the previous statement 
    if the previous statement is one of: '.assistant', '.system', '.text', '.user'

### R6: Implicit '.exec' statement
    if the last statement is not '.exec' then 
    an '.exec' statement appended to the end.

