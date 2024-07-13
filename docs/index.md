# Miniset

A Jinja2 template processor for interacting with an SQL engine.

(Forked from [apache/superset](https://github.com/apache/superset) and [sripathikrishnan/jinjasql](https://github.com/sripathikrishnan/jinjasql/))

## Requirements

- Python 3.9+

## Installation

```bash
pip install mini-set
```

## Basic Usage

First, import `JinjaTemplateProcessor` class from `miniset` and create a processor.

```py
from miniset import JinjaTemplateProcessor

p = JinjaTemplateProcessor()
```

Next, call `prepare_query` method with a Jinja2 template and keyword arguments. Keyword arguments are passed to a Jinja2 context.

The method returns:

- `query` is the generated SQL query. Variables are replaced by `%s`.
- `bind_params` is a list of parameters corresponding to the `%s`.

```py
query, bind_params = p.prepare_query(
    "SELECT * FROM {{ table | sql_safe }} WHERE name = {{ name }} OR project_id IN {{ project_ids | where_in }}",
    name="foo",
    project_ids=[1, 2],
    table="projects",
)
```

**query**

```sql
SELECT * FROM projects WHERE name = %s OR project_id IN (%s,%s)
```

**bind_params**

```py
["foo", 1, 2]
```

## Multiple Param Styles

A placeholder for a bind param can be specified in multiple ways.

- `format`: where name = `%s`. This is the default.
- `qmark`: where name = `?`.
- `numeric`: where name = `:1` and last_name = `:2`.
- `named`: where name = `:name` and last_name = `:last_name`.
- `pyformat`: where name = `%(name)s` and last_name = `%(last_name)s`.
- `asyncpg`: where name = `$1` and last_name = `$2`.

!!! note

    You need to escape `%` by `%%` if you want to use `%` literal in your query with `format`. (e.g., `column LIKE '%%blah%%'`)

!!! note

    See [Working Along With SQLAlchemy](#working-along-with-sqlalchemy-v2) to use this library with SQLAlchemy v2.

You can pass the optional constructor argument `param_style` to control the style of query parameter.

```py
p = JinjaTemplateProcessor(param_style="named")
```

In case of `named` and `pyformat`, `prepare_query` returns `dict` instead of `list`.

```py
p = JinjaTemplateProcessor(param_style="named")

query, bind_params = p.prepare_query(
    "SELECT * FROM {{ table | sql_safe }} WHERE name = {{ name }} OR project_id IN {{ project_ids | where_in }}",
    name="foo",
    project_ids=[1, 2],
    table="projects",
)
```

**query**

```sql
SELECT * FROM projects WHERE name = :name_1 OR project_id IN (:where_in_2,:where_in_3)
```

**bind_params**

```py
{"name_1": "foo", "where_in_2": 1, "where_in_3": 2}
```

## Built-in Filters

Miniset provides the following built-in Jinja2 filters.

### where_in

`where_in` filter builds a parenthesis list suitable for an `IN` expression.

```sql
SELECT * FROM projects WHERE project_id IN {{ project_ids | where_in }}
```

For example,

```py
query, bind_params = p.prepare_query(
    "SELECT * FROM projects WHERE project_id IN {{ project_ids | where_in }}",
    project_ids=[1, 2, 3],
)
```

**query**

```sql
SELECT * FROM projects WHERE project_id IN (%s,%s,%s)
```

**bind_params**

```py
[1, 2, 3]
```

### sql_safe

Table and columns names are usually not allowed in bind params.

In such case, you can use `sql_safe` filter.

```sql
SELECT {{ column | sql_safe }} FROM {{ table | sql_safe }}
```

For example,

```python
query, bind_params = p.prepare_query(
    "SELECT {{ column | sql_safe }} FROM {{ table | sql_safe }}",
    column="id",
    table="projects",
)
```

**query**

```sql
SELECT id FROM projects
```

!!! warning

    You have a responsibility to ensure that there is no SQL injection if you use `sql_safe` filter.

### identifier

`identifier` filter quotes a value to make it a named object.

```sql
SELECT * from {{ table | identifier }}
```

You can use `identifier_quote_character` constructor argument to control the quote character for the identifier. (Defaults to `"`)

```py
p = JinjaTemplateProcessor(identifier_quote_character="`")

query, bind_params = p.prepare_query(
    "SELECT * FROM {{ table | identifier }}",
    table="projects",
)
```

**query**

```sql
SELECT * FROM `projects`
```

## Working Along With SQLAlchemy v2

You cannot use `format` and `pyformat` param styles with SQLAlchemy v2 because of [this change](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#execute-method-more-strict-execution-options-are-more-prominent).

Alternatively, you can use `named`, `qmark`, `numeric` and `asyncpg`.

**named**

```py
p = JinjaTemplateProcessor(param_style="named")

query, bind_params = p.prepare_query(
    "SELECT * FROM hero WHERE id = {{ id }}",
    id=1,
)

with engine.connect() as conn:
    res = conn.execute(text(query), bind_params)
```

**others** (`qmark`, `numeric` and `asyncpg`)

```py

p = JinjaTemplateProcessor(param_style="qmark")

query, bind_params = p.prepare_query(
    "SELECT * FROM hero WHERE id = {{ id }}",
    id=1,
)

with engine.connect() as conn:
    res = conn.exec_driver_sql(query, tuple(bind_params))
```
