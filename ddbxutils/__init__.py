from . import widgets
from .config import EnvConfig

# lazy evaluation 위해 () 로 감싸서 generator 를 return 하도록 변경
generator = (widgets.get_instance() for x in range(1))
