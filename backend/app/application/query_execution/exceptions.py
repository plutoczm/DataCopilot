class QueryExecutionError(RuntimeError):
    status_code = 500
    code = "query_execution_error"


class QueryExecutionDisabledError(QueryExecutionError):
    status_code = 503
    code = "query_execution_disabled"


class DataSourceNotFoundError(QueryExecutionError):
    status_code = 404
    code = "datasource_not_found"


class DataSourceUnavailableError(QueryExecutionError):
    status_code = 503
    code = "datasource_unavailable"


class QueryRejectedError(QueryExecutionError):
    status_code = 400
    code = "query_rejected"


class QueryTimeoutError(QueryExecutionError):
    status_code = 408
    code = "query_timeout"
