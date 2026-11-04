from psycopg import sql


if not hasattr(sql.Composed, "seq"):
    sql.Composed.seq = property(lambda self: self._obj)

if not hasattr(sql.Identifier, "strings"):
    sql.Identifier.strings = property(lambda self: self._obj)
