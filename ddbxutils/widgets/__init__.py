from .core import WidgetImpl

_widget_impl_instance: WidgetImpl = None


def get_instance():
    """
    widgets 모듈을 초기화합니다.
    이 함수는 반드시 dbutils 객체와 함께 한 번 호출되어야 합니다.

    :return: None
    """
    global _widget_impl_instance
    if _widget_impl_instance is None:
        _widget_impl_instance = WidgetImpl()
    return _widget_impl_instance


def get(widget_name: str):
    """
    초기화된 인스턴스에서 위젯 값을 가져옵니다.
    init()이 호출되지 않았다면 예외를 발생시킵니다.

    :param widget_name: widget key
    :return: resolved widget value
    """
    widget_impl = get_instance()
    # if _widget_impl_instance is None:
    #     raise RuntimeError('ddbxutils.widgets가 초기화되지 않았습니다. `ddbxutils.widgets.init(dbutils)`를 먼저 호출하세요.')
    return widget_impl.get(widget_name)


def refresh():
    """
    위젯 값을 새로 고칩니다.

    :param dbutils: dbutils
    :return: None
    """
    widget_impl = get_instance()
    # if _widget_impl_instance is None:
    #     raise RuntimeError('ddbxutils.widgets가 초기화되지 않았습니다. `ddbxutils.widgets.init(dbutils)`를 먼저 호출하세요.')
    # if dbutils is None:
    #     raise RuntimeError('dbutils is required.')
    widget_impl.refresh()
