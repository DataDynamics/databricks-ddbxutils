import base64
from dataclasses import dataclass

import cloudpickle
from pyspark.sql.datasource import DataSource, DataSourceReader, InputPartition
from pyspark.sql.types import StructType, StructField, IntegerType


@dataclass
class PythonFunctionPartition(InputPartition):
    """
    Partition 정의: 각 파티션의 시작과 끝 범위
    """
    start: int
    end: int


class PythonFunctionReader(DataSourceReader):
    """
    DataSourceReader 구현
    """

    def __init__(self, schema: StructType, options: dict, serialized_func_b64):
        self.schema = schema
        self.options = options
        self.func = cloudpickle.loads(base64.b64decode(serialized_func_b64))

    def partitions(self):
        lower = int(self.options.get('lowerLimit', '0'))
        upper = int(self.options.get('upperLimit', '0'))
        num_parts = int(self.options.get('numPartitions', '1'))
        step = (upper - lower) // num_parts if num_parts > 0 else (upper - lower)
        # print(f'step={step}')
        parts = []
        start = lower
        for i in range(num_parts):
            end = upper if i == num_parts - 1 else start + step
            parts.append(PythonFunctionPartition(start, end))
            start = end
        return parts

    def read(self, partition: PythonFunctionPartition):
        for x in range(partition.start, partition.end):
            # yield (self.func(x),)
            yield self.func(x)


class PythonFunctionDataSource(DataSource):
    """
    DataSource 구현

    .. versionadded: 0.3.0

    Notes
    -----
    user defined function 은 tuple, list, `pyspark.sql.types.Row`, `pyarrow.RecordBatch` 중에 하나의 type 을 가져야 합니다.

    Examples
    --------
    >>> spark = ...

    Use the default input partition implementation:

    >>> def partitions(self):
    ...     return [PythonFunctionPartition(1, 3)]

    Subclass the input partition class:

    >>> def partitions(self):
    ...     return [PythonFunctionPartition(1, 3), PythonFunctionPartition(4, 6)]

    Example in PySpark Shell 에서 `pyspark.sql.Row` 를 return 하는 함수를 사용하는 방법입니다.

    >>> import base64
    >>> import cloudpickle
    >>> from ddbxutils.datasources.pyfunc import PythonFunctionDataSource
    >>> spark.dataSource.register(PythonFunctionDataSource)
    >>> # ...
    >>> from pyspark.sql import Row
    >>> def user_function_row(x) -> Row:
    ...     from datetime import datetime
    ...     from pytz import timezone
    ...     return Row(str(x), str(x * x), datetime.now(timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S"))
    ...
    >>> df = (spark.read.format("pyfunc").
    ...         schema('value1 string, value2 string, ts string').
    ...         option("lowerLimit", "0").
    ...         option("upperLimit", "10").
    ...         option("numPartitions", "100").
    ...         option("func", base64.b64encode(cloudpickle.dumps(user_function_row)).decode('utf-8')).
    ...         load())
    >>> df.show()

    Example in PySpark Shell 에서 array 를 return 하는 함수를 사용하는 방법입니다.

    >>> def user_function_row(x):
    ...     from datetime import datetime
    ...     from pytz import timezone
    ...     return [str(x), str(x * x), datetime.now(timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")]
    ...
    >>> df = (spark.read.format("pyfunc").
    ...         schema('value1 string, value2 string, ts string').
    ...         option("lowerLimit", "0").
    ...         option("upperLimit", "10").
    ...         option("numPartitions", "100").
    ...         option("func", base64.b64encode(cloudpickle.dumps(user_function_row)).decode('utf-8')).
    ...         load())
    >>> df.show()
    """

    @classmethod
    def name(cls):
        return 'pyfunc'

    def schema(self):
        return StructType([StructField('value', IntegerType(), nullable=False)])

    def reader(self, schema: StructType):
        # options는 문자열이므로 필요시 변환하세요
        # func = self.options.get('func', None)
        func = self.options['func']
        return PythonFunctionReader(self.schema(), self.options, func)
