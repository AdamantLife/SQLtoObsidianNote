""" sample.py

  Demonstrates how SQLtoObsidianNote parses a Table declaration which includes column definitions and table constraints.

"""

import SQLtoObsidianNote
import sqlglot

teststring = """
CREATE TABLE season(
    seasonid INTEGER AUTOINCREMENT,
    season TEXT,
    series INT,
    seriesname TEXT,
    medium TEXT REFERENCES mediums(mediumid),
    episodes INT,
    PRIMARY KEY(seasonid),
    FOREIGN KEY(series, seriesname) REFERENCES series(seriesid, name),
    CHECK(season > 0),
    UNIQUE(season, series)
)
"""

## Uncomment to verify the sqlglot parse tree for the sample SQL string
## (The version at the bottom of the file should be up to date)
#print(sqlglot.parse(teststring, dialect='sqlite'))
#raise Exception()

def taboutput(_string: str, level:int = 1, tabsize=4)->str:
    s = _string.split("\n")
    s = [f"{' '*tabsize*level}{x}" for x in s]
    return "\n".join(s)

parsed = SQLtoObsidianNote.parse_sql(teststring, dialect='sqlite')
print("\n--------\n")
print(f"[{parsed[0].getfilename()}]")
print(parsed[0].stringify())
print("\n--------\n")
for column in parsed[0].columns.values():
    print(taboutput(f"[{column.getfilename(parsed[0])}]"))
    print(taboutput(column.stringify()))
    print(taboutput("\n--------\n"))

## Below is the sqlglot parse tree for the sample SQL string for reference
"""
Create(
  this=Schema(
    this=Table(
      this=Identifier(this=season, quoted=False)),     
    expressions=[
      ColumnDef(
        this=Identifier(this=seasonid, quoted=False),  
        kind=DataType(this=Type.INT, nested=False),    
        constraints=[
          ColumnConstraint(
            kind=AutoIncrementColumnConstraint())]),   
      ColumnDef(
        this=Identifier(this=season, quoted=False),    
        kind=DataType(this=Type.TEXT, nested=False)),  
      ColumnDef(
        this=Identifier(this=series, quoted=False),    
        kind=DataType(this=Type.INT, nested=False)),   
      ColumnDef(
        this=Identifier(this=seriesname, quoted=False),
        kind=DataType(this=Type.TEXT, nested=False)),  
      ColumnDef(
        this=Identifier(this=medium, quoted=False),
        kind=DataType(this=Type.TEXT, nested=False),
        constraints=[
          ColumnConstraint(
            kind=Reference(
              this=Schema(
                this=Table(
                  this=Identifier(this=mediums, quoted=False)),
                expressions=[
                  Identifier(this=mediumid, quoted=False)])))]),
      ColumnDef(
        this=Identifier(this=episodes, quoted=False),
        kind=DataType(this=Type.INT, nested=False)),
      PrimaryKey(
        expressions=[
          Identifier(this=seasonid, quoted=False)]),
      ForeignKey(
        expressions=[
          Identifier(this=series, quoted=False),
          Identifier(this=seriesname, quoted=False)],
        reference=Reference(
          this=Schema(
            this=Table(
              this=Identifier(this=series, quoted=False)),
            expressions=[
              Identifier(this=seriesid, quoted=False),
              Identifier(this=name, quoted=False)]))),
      CheckColumnConstraint(
        this=GT(
          this=Column(
            this=Identifier(this=season, quoted=False)),
          expression=Literal(this=0, is_string=False))),
      UniqueColumnConstraint(
        this=Schema(
          expressions=[
            Identifier(this=season, quoted=False),
            Identifier(this=series, quoted=False)]))]),
  kind=TABLE)
  """