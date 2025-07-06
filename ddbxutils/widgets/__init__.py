from .core import WidgetImpl

_widget_impl_instance: WidgetImpl = None


def init(dbutils):
    """
    widgets 모듈을 초기화합니다.
    이 함수는 반드시 dbutils 객체와 함께 한 번 호출되어야 합니다.

    :param dbutils: dbutils
    :return: None
    """
    global _widget_impl_instance
    _widget_impl_instance = WidgetImpl(dbutils)


def get(widget_name: str):
    """
    초기화된 인스턴스에서 위젯 값을 가져옵니다.
    init()이 호출되지 않았다면 예외를 발생시킵니다.

    :param widget_name: widget key
    :return: resolved widget value
    """
    if _widget_impl_instance is None:
        raise RuntimeError('ddbxutils.widgets가 초기화되지 않았습니다. `ddbxutils.widgets.init(dbutils)`를 먼저 호출하세요.')
    return _widget_impl_instance.get(widget_name)


def refresh(dbutils):
    """
    위젯 값을 새로 고칩니다.

    :param dbutils: dbutils
    :return: None
    """
    if _widget_impl_instance is None:
        raise RuntimeError('ddbxutils.widgets가 초기화되지 않았습니다. `ddbxutils.widgets.init(dbutils)`를 먼저 호출하세요.')
    if dbutils is None:
        raise RuntimeError('dbutils is required.')
    _widget_impl_instance.refresh(dbutils)
