from ddbxutils.functions import add_days, add_datetime
from jinja2 import Environment

environment = Environment()
environment.globals['add_days'] = add_days
environment.globals['add_datetime'] = add_datetime


class WidgetImpl:
    dbutils = None
    rendered_widget_values = None

    def __init__(self, dbutils):
        self.refresh(dbutils)

    def refresh(self, dbutils):
        """
        위젯의 값을 설정하거나 추가합니다.
        """
        self.dbutils = dbutils
        widget_values = self.dbutils.widgets.getAll()
        self.rendered_widget_values = {key: environment.from_string(value).render(widget_values) for key, value in widget_values.items()}

    def get(self, widget_name: str):
        """
        이름으로 위젯의 값을 가져옵니다.
        """
        # 저장된 값 반환, 없으면 None 반환
        return self.rendered_widget_values.get(widget_name)
