from prometheus_client import Histogram, Counter, Summary, Gauge

# S3 Operation Counters
s3_copy_operations_total = Counter(
    "storage_broker_s3_copy_operations_total",
    "Total number of S3 copy operations",
    ["source_bucket", "destination_bucket", "status"]
)

s3_head_object_operations_total = Counter(
    "storage_broker_s3_head_object_operations_total", 
    "Total number of S3 head object operations",
    ["bucket", "status"]
)

s3_presigned_url_requests_total = Counter(
    "storage_broker_s3_presigned_url_requests_total",
    "Total number of presigned URL generation requests",
    ["bucket", "status"]
)

s3_client_errors_total = Counter(
    "storage_broker_s3_client_errors_total",
    "Total number of S3 client errors",
    ["operation", "error_code"]
)

# S3 Operation Timing Histograms
s3_copy_duration_seconds = Histogram(
    "storage_broker_s3_copy_duration_seconds",
    "Time taken for S3 copy operations",
    ["source_bucket", "destination_bucket"]
)

s3_head_object_duration_seconds = Histogram(
    "storage_broker_s3_head_object_duration_seconds",
    "Time taken for S3 head object operations",
    ["bucket"]
)

s3_presigned_url_generation_duration_seconds = Histogram(
    "storage_broker_s3_presigned_url_generation_duration_seconds",
    "Time taken to generate S3 presigned URLs",
    ["bucket"]
)

# S3 Object Size Metrics
s3_object_size_bytes = Summary(
    "storage_broker_s3_object_size_bytes",
    "Size of S3 objects being processed",
    ["bucket", "operation"]
)

# S3 Connection and Health Metrics
s3_active_connections = Gauge(
    "storage_broker_s3_active_connections",
    "Number of active S3 connections"
)

s3_connection_pool_size = Gauge(
    "storage_broker_s3_connection_pool_size",
    "Current S3 connection pool size"
)

# S3 Throughput Metrics
s3_bytes_transferred_total = Counter(
    "storage_broker_s3_bytes_transferred_total",
    "Total bytes transferred to/from S3",
    ["bucket", "operation"]
)

s3_objects_processed_total = Counter(
    "storage_broker_s3_objects_processed_total",
    "Total number of S3 objects processed",
    ["bucket", "operation", "status"]
)

# S3 Error Rate Metrics
s3_error_rate = Gauge(
    "storage_broker_s3_error_rate",
    "Current S3 error rate (errors per minute)",
    ["operation"]
)

# S3 Retry Metrics
s3_retry_attempts_total = Counter(
    "storage_broker_s3_retry_attempts_total",
    "Total number of S3 operation retry attempts",
    ["operation", "bucket"]
) 
