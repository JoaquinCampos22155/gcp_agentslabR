-- Chart: requests and average backend latency by category and outcome.
SELECT
  TIMESTAMP_TRUNC(timestamp, MINUTE) AS minute,
  JSON_VALUE(json_payload, "$.category") AS category,
  JSON_VALUE(json_payload, "$.outcome") AS outcome,
  COUNT(*) AS requests,
  AVG(CAST(JSON_VALUE(json_payload, "$.latency_ms") AS FLOAT64)) AS avg_latency_ms
FROM `responsible-api-lab.global._Default._Default`
WHERE JSON_VALUE(json_payload, "$.message") = "request_completed"
GROUP BY minute, category, outcome
ORDER BY minute
