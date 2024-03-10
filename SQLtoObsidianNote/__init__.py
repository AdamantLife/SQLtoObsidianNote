import sqlglot
from sqlglot import exp

from dataclasses import dataclass
import pathlib
import typing

## TODO: sqlite allows for rowid aliases and consequently for rowid/the rowid alias to
##        interchangeably, which means that pages will not be correctly linked. This
##        can be at least partially addressed by searching the rest of the schema for
##        the rowid alias in order to link to the correct page. It is not clear if this
##        is fixable for partial schemas.

ConstraintName = str
ConstraintArgs = list[typing.Any]
ColumnConstraints = list[tuple[ConstraintName,ConstraintArgs]]
ConstraintFormatter = typing.Callable[[ConstraintName, ConstraintArgs], str]
ConstraintLookup = dict[ConstraintName, ConstraintFormatter]

@dataclass
class Page():
    name: str
    tags: list

    @property
    def CONSTRAINTFORMATS(self)->ConstraintLookup:
        raise NotImplementedError

    def stringifyconstraint(self, constraintname: ConstraintName, constraintargs: ConstraintArgs)->str:
        if not constraintargs:
          return constraintname
        return self.CONSTRAINTFORMATS[constraintname](constraintname, constraintargs)

    def stringify(self, dialect:str|None=None)->str:
        raise NotImplementedError
    

ColumnName = str
@dataclass
class TablePage(Page):
    expression: exp.Create
    columns: dict[ColumnName, "ColumnPage"]
    constraints: ColumnConstraints

    def getfilename(self)->str:
        return f"{self.name}.md"

    @property
    def CONSTRAINTFORMATS(self)-> ConstraintLookup:
        return {
          "Primary Key": lambda name, args: f"Primary Key Group: {", ".join(args)}",
          "Check": lambda name, args: str(args[0]),
          "Unique": lambda name, args: f"Unique Column Group: ({", ".join(args)})",
        }

    def stringify(self, dialect:str|None=None,
                  pretty: bool = True, pad: int|None = None, indent:int|None = None,
                  normalize_functions: bool|typing.Literal["upper"]|typing.Literal["lower"] = False,
                  max_text_width: int|None=None)->str:
        """ Returns a string representation of the table page
        
        Args:
            dialect (str|None, optional): The SQL dialect to use. Defaults to None.
            ** The Follow arguements are fed to the sqlglot sql generator.
            ** Any args (except where noted) not provided will use sqlglot's defaults
            ** For more information on these args, see https://sqlglot.com/sqlglot/generator.html#Generator
            pretty (bool, optional): Defaults to True.
            pad (int|None, optional): The number of spaces to pad the output with. Defaults to None.
            indent (int|None, optional)
            normalize_functions (bool|typing.Literal["upper"]|typing.Literal["lower"], optional):
                Defaults to False to better reflect initial sql schema. Set to None to use sqlglot's default. Defaults to False.
            max_text_width (int|None, optional)
        """
        out = ""
        for tag in self.tags:
            out += f"#{tag} "
        out += "\n\n"
        out += "### Columns:\n"
        for columnname in self.columns:
            out += f"[[{self.name}-{columnname}|{columnname}]]\n"

        out += "\n"
        out += "### Constraints:\n"
        for [constraintname, constraintargs] in self.constraints:
          result = self.stringifyconstraint(constraintname, constraintargs)
          out += f"* {result}\n"

        out+="\n"
        out+="### SQL\n"

        opts = {}
        opts['pretty'] = pretty
        if pad is not None: opts["pad"] = pad
        if indent is not None: opts["indent"] = indent
        if normalize_functions is not None: opts["normalize_functions"] = normalize_functions
        if max_text_width is not None: opts["max_text_width"] = max_text_width

        out += f"```{dialect if dialect else ""}\n{self.expression.sql(dialect=dialect,**opts)}\n```"
        return out


@dataclass
class ColumnPage(Page):
    type: str
    constraints: ColumnConstraints

    def getfilename(self, tablepage: TablePage)->str:
        return f"{tablepage.name}-{self.name}.md"

    @property
    def CONSTRAINTFORMATS(self)->ConstraintLookup:
        return {
          "Primary Key": lambda name, args: "Primary Key",
          "Auto Increment": lambda name, args: "Auto Increment",
          "Not Null": lambda name, args: "Not Null",
          "Default": lambda name, args: f"Default {args[0]}",
          "Unique": lambda name, args: "Unique",
          "Check": lambda name, args: f"Check {args[0]}",
          "References": lambda name, args: f"References [[{args[0]}-{args[1]}|{args[0]}.{args[1]}]]"
        }

    def stringify(self, dialect:str|None=None)->str:
        out = ""
        for tag in self.tags:
            out += f"#{tag} "
        out += "\n\n"
        out += f"### Name:\n{self.name}\n"
        out += f"### Type:\n{self.type}\n"
        out += "\n"
        out += "### Constraints:\n"
        for [constraintname, constraintargs] in self.constraints:
          result = self.stringifyconstraint(constraintname, constraintargs)
          out += f"* {result}\n"
        return out

def parse_sql(inputstring: str, dialect: str|None = None) -> list[TablePage]:
  """ Parses the SQL string and returns a list of TablePage objects

  Args:
      inputstring (str): The SQL string to parse
      dialect (str|None, optional): The SQL dialect to use. Defaults to None.
  """
  tablepages: list[TablePage] = []

  for expression in sqlglot.parse(inputstring, dialect='sqlite'):
      if not isinstance(expression, exp.Create): continue
      if expression.key != "create" or expression.kind != "TABLE": continue
      schema = expression.find(exp.Schema)
      if not schema: raise RuntimeError("No schema found")
      table = expression.find(exp.Table)
      if not table: raise RuntimeError("No table found")
      name = str(table.this)
      tags = ["sql", "table"]
      expression = expression
      columns: dict[ColumnName, ColumnPage] = {}
      constraints: list[typing.Any] = []
      
      ## c are Table Constraints: we will need to retroactively
      ## apply these constraints to the columns
      c = []
      for child in schema.expressions:
          if isinstance(child, exp.ColumnDef):
              columnpage = parse_column(child)
              columns[columnpage.name] = columnpage
          else: c.append(child)

      ## Now that all columns have been parse, we can handle table constraints
      for child in c:
          if isinstance(child, exp.PrimaryKey):
              identifiers = list(child.find_all(exp.Identifier))
              if len(identifiers) > 1:
                constraints.append(("Primary Key", [str(ident) for ident in identifiers]))
              else:
                columnname = str(identifiers[0])
                columns[columnname].tags.append("primarykey")
                columns[columnname].constraints.append(("Primary Key", []))
          elif isinstance(child, exp.ForeignKey):
              thiscolumns = [ ident for ident in child.find_all(exp.Identifier) if ident.parent == child]
              schema = child.find(exp.Schema)
              if not schema: raise RuntimeError("No foreign schema found")
              table = schema.find(exp.Table)
              if not table: raise RuntimeError("No foreign table found")
              foreignname = str(table.this)
              foreigncolumns = [ident for ident in schema.find_all(exp.Identifier) if ident.parent == schema]
              if len(thiscolumns) != len(foreigncolumns): raise RuntimeError(f"Foreign key mismatch: {[str(ident) for ident in thiscolumns]} != {[str(ident) for ident in foreigncolumns]}")
              for i in range(len(thiscolumns)):
                columnname = str(thiscolumns[i])
                columns[columnname].tags.append("foreignkey")
                columns[columnname].constraints.append(("References", [foreignname, str(foreigncolumns[i])]))
          elif isinstance(child, exp.CheckColumnConstraint):
              constraints.append(("Check", [str(child)]))
          elif isinstance(child, exp.UniqueColumnConstraint):
              identifiers = list(child.find_all(exp.Identifier))
              if len(identifiers) > 1:
                  constraints.append(("Unique", [str(ident) for ident in identifiers]))
              else:
                columnname = str(identifiers[0])
                columns[columnname].tags.append("isunique")
                columns[columnname].constraints.append(("Unique", []))
              
      tablepages.append(TablePage(name=name, tags=tags, columns=columns, expression=expression, constraints=constraints))
              

  return tablepages

def parse_column(column: exp.ColumnDef) -> ColumnPage:
    """ Parses the column and returns a ColumnPage object
    
    Args:
        column (exp.ColumnDef): The column to parse

    Returns:
        ColumnPage: The parsed column
    """
    name = str(column.this)
    tags = ["sql", "column"]
    type = ""
    if column.kind:
        type = str(column.kind.this.name)
    constraints: ColumnConstraints = []
    for constraint in column.constraints:
        if isinstance(constraint.kind, exp.PrimaryKeyColumnConstraint):
            constraints.append(("Primary Key", []))
            tags.append("primarykey")
        elif isinstance(constraint.kind, exp.AutoIncrementColumnConstraint):
            constraints.append(("Auto Increment", []))
            tags.append("autoincrement")
        elif isinstance(constraint.kind, exp.NotNullColumnConstraint):
            constraints.append(("Not Null", []))
            tags.append("notnull")
        elif isinstance(constraint.kind, exp.DefaultColumnConstraint):
            constraints.append(("Default", [constraint.kind.this,]))
            tags.append("hasdefault")
        elif isinstance(constraint.kind, exp.UniqueColumnConstraint):
            constraints.append(("Unique", []))
            tags.append("isunique")
        elif isinstance(constraint.kind, exp.CheckColumnConstraint):
            constraints.append(("Check", [constraint.kind.this],))
            tags.append("hascheck")
        elif isinstance(constraint.kind, exp.Reference):
            table = constraint.kind.this.find(exp.Table)
            if not table: raise RuntimeError("No table found")
            tablename = str(table.this)
            columnname = str(constraint.kind.this.find(exp.Identifier))
            ## TODO: Shouldn't be formatting here, should be done in the stringify method
            constraints.append(("References",[tablename,columnname]))
            tags.append("foreignkey-reference")
    return ColumnPage(name=name, tags=tags, type=type, constraints=constraints)

def write_obsidianpages(tablepages: list[TablePage], path: str|pathlib.Path, dialect: str|None = None, **opts):
    """ Writes the table and column pages to the specified path
    
    Args:
        tablepages (list[TablePage]): The list of table pages to write
        path (str|pathlib.Path): The path to write the pages to
        dialect (str|None, optional): The SQL dialect to use. Defaults to None.
        **opts: Arguements for the stringify method of the TablePage class
    """
    path = pathlib.Path(path).resolve()

    if not path.exists():
        path.mkdir(parents = True, exist_ok = True)

    tablesub = path / "tables"
    if not tablesub.exists():
        tablesub.mkdir(parents = True, exist_ok = True)

    columnsub = path / "columns"
    if not columnsub.exists():
        columnsub.mkdir(parents = True, exist_ok = True)

    for tablepage in tablepages:
      with open(tablesub/tablepage.getfilename(), "w") as file:
          file.write(tablepage.stringify(dialect=dialect, **opts))

      for columnpage in tablepage.columns.values():
          with open(columnsub/columnpage.getfilename(tablepage), "w") as file:
              file.write(columnpage.stringify(dialect=dialect))

def parse_from_file(path: str|pathlib.Path, dialect: str|None = None) -> list[TablePage]:
    """ Reads the SQL from the file and returns the table pages
    
    Args:
        path (str|pathlib.Path): The path to the file
        dialect (str, optional): The SQL dialect to use. Defaults to "sqlite".

    Returns:
        list[TablePage]: The list of table pages
    """
    with open(path, "r") as file:
        return parse_sql(file.read(), dialect=dialect)
    
def generate_markdown_from_file(inputpath: str|pathlib.Path, outputpath: str|pathlib.Path|None, dialect: str|None = None, **opts):
    """ Generates markdown files from the SQL file
    
    Args:
        inputpath (str|pathlib.Path): The path to the SQL file
        outputpath (str|pathlib.Path|None): The path to the output directory. If not provided, outputs to the parent directory of the input file.
        dialect (str|None, optional): The SQL dialect to use. Defaults to None.
        **opts: Arguements for the stringify method of the TablePage class
    """
    tablepages = parse_from_file(inputpath, dialect=dialect)
    if outputpath is None:
        outputpath = pathlib.Path(inputpath).parent
    else:
        outputpath = pathlib.Path(outputpath)
    if not outputpath.exists():
        outputpath.mkdir(parents = True, exist_ok = True)
    write_obsidianpages(tablepages, outputpath, dialect=dialect, **opts)
    