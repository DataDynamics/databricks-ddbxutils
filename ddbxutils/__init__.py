from databricks.sdk import WorkspaceClient

from . import widgets

w = WorkspaceClient()
widgets.init(w.dbutils)
