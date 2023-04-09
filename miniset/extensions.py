# Forked from https://github.com/sripathikrishnan/jinjasql
# The original version was created by Sripathi Krishnan and HashedIn Technologies Pvt. Ltd.
# https://github.com/sripathikrishnan/jinjasql/blob/master/LICENSE
from typing import Generator, List

from jinja2.ext import Extension
from jinja2.lexer import Token, TokenStream


class SqlExtension(Extension):
    """SQL extension for Jinja2"""

    def extract_param_name(self, tokens: List[Token]) -> str:
        """Extract param names

        Args:
            tokens (list[Token]): Tokens

        Returns:
            str: Param name
        """
        name: str = ""

        for token in tokens:
            if token.test("variable_begin"):
                continue
            elif token.test("name"):
                name += token.value
            elif token.test("dot"):
                name += token.value
            else:
                break

        if not name:
            name = "bind#0"

        return name

    def filter_stream(self, stream: TokenStream) -> Generator[Token, None, None]:
        """Convert `{{ some.variable | filter1 | filter 2 }}` to `{{ ( some.variable | filter1 | filter 2 ) | bind }}` for all variable declarations in the template

        Note the extra ( and ). We want the | bind to apply to the entire value, not just the last value.
        The parentheses are mostly redundant, except in expressions like `{{ '%' ~ myval ~ '%' }}`

        This function is called by Jinja2 immediately after the lexing stage, but before the parser is called.

        Args:
            stream (TokenStream): Token stream

        Yields:
            Generator[Token, None, None]: Converted token stream
        """

        while not stream.eos:
            token = next(stream)
            if token.test("variable_begin"):
                var_expr: List[Token] = []

                while not token.test("variable_end"):
                    var_expr.append(token)
                    token = next(stream)

                variable_end = token

                last_token = var_expr[-1]
                lineno = last_token.lineno
                # don't bind twice
                if not last_token.test("name") or last_token.value not in (
                    "bind",
                    "where_in",
                    "sql_safe",
                ):
                    param_name = self.extract_param_name(var_expr)

                    var_expr.insert(1, Token(lineno, "lparen", "("))
                    var_expr.append(Token(lineno, "rparen", ")"))
                    var_expr.append(Token(lineno, "pipe", "|"))
                    var_expr.append(Token(lineno, "name", "bind"))
                    var_expr.append(Token(lineno, "lparen", "("))
                    var_expr.append(Token(lineno, "string", param_name))
                    var_expr.append(Token(lineno, "rparen", ")"))

                var_expr.append(variable_end)

                for token in var_expr:
                    yield token
            else:
                yield token
