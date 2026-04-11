"""
Prometheus 监控指标定义和收集
"""

from functools import wraps

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import time

# 创建注册表
registry = CollectorRegistry()

# ============ 会话相关指标 ============
session_created = Counter(
    'agent_sessions_created_total',
    'Total sessions created',
    registry=registry
)

session_archived = Counter(
    'agent_sessions_archived_total',
    'Total sessions archived',
    registry=registry
)

active_sessions = Gauge(
    'agent_active_sessions_count',
    'Number of currently active sessions',
    registry=registry
)

# ============ API 性能指标 ============
request_duration = Histogram(
    'agent_request_duration_seconds',
    'Request duration in seconds',
    labelnames=['endpoint'],
    registry=registry
)

request_count = Counter(
    'agent_requests_total',
    'Total requests',
    labelnames=['endpoint', 'status'],
    registry=registry
)

# ============ 模型响应时间 ============
model_response_time = Histogram(
    'agent_model_response_time_seconds',
    'Model response generation time',
    labelnames=['model'],
    registry=registry
)

# ============ 存储相关指标 ============
session_storage_errors = Counter(
    'agent_session_storage_errors_total',
    'Session storage errors',
    labelnames=['error_type'],
    registry=registry
)

memory_usage = Gauge(
    'agent_memory_mb',
    'Memory usage in MB',
    registry=registry
)

# ============ 数据库相关指标 ============
db_query_duration = Histogram(
    'agent_db_query_duration_seconds',
    'Database query duration',
    labelnames=['query_type'],
    registry=registry
)

db_connection_errors = Counter(
    'agent_db_connection_errors_total',
    'Database connection errors',
    registry=registry
)

# ============ Celery 任务指标 ============
celery_task_count = Counter(
    'agent_celery_tasks_total',
    'Total Celery tasks executed',
    labelnames=['task_name', 'status'],
    registry=registry
)

celery_task_duration = Histogram(
    'agent_celery_task_duration_seconds',
    'Celery task execution duration',
    labelnames=['task_name'],
    registry=registry
)


def render_metrics() -> bytes:
    """渲染 Prometheus 指标输出。"""
    return generate_latest(registry)


def set_active_sessions_count(count: int) -> None:
    active_sessions.set(max(count, 0))


def record_request_metrics(endpoint: str, status: str, duration: float) -> None:
    request_count.labels(endpoint=endpoint, status=status).inc()
    request_duration.labels(endpoint=endpoint).observe(duration)


def record_model_response(model: str, duration: float) -> None:
    model_response_time.labels(model=model).observe(duration)


def record_celery_task(task_name: str, status: str, duration: float) -> None:
    celery_task_count.labels(task_name=task_name, status=status).inc()
    celery_task_duration.labels(task_name=task_name).observe(duration)


def track_request(endpoint):
    """HTTP 请求计时装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            except Exception:
                status = "error"
                raise
            finally:
                duration = time.time() - start
                record_request_metrics(endpoint=endpoint, status=status, duration=duration)
        return wrapper
    return decorator


def track_db_query(query_type):
    """数据库查询计时"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                db_query_duration.labels(query_type=query_type).observe(duration)
        return wrapper
    return decorator
