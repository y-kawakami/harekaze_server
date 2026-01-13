-- 元のクエリ（個別のレコードを取得）- 日本時間（JST）表示
SELECT
  time,
  date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:%i:%s JST') as jst_time,
  client_ip,
  elb_status_code,
  target_status_code,
  request_url,
  response_processing_time
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
ORDER BY time DESC;

-- 1時間ごとの集計クエリ (日本時間JST)
SELECT
  date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:00:00 JST') as hour_bucket_jst,
  COUNT(*) as request_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
GROUP BY date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:00:00 JST')
ORDER BY hour_bucket_jst DESC;

-- 1分ごとの集計クエリ (日本時間JST)
SELECT
  date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:%i:00 JST') as minute_bucket_jst,
  COUNT(*) as request_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
GROUP BY date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:%i:00 JST')
ORDER BY minute_bucket_jst DESC;

-- 5分毎の集計クエリ (日本時間JST)
SELECT
  date_format(
    date_add(
      'minute',
      5 * floor(extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))) / 5) - extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))),
      date_add('hour', 9, from_iso8601_timestamp(time))
    ),
    '%Y-%m-%d %H:%i:00 JST'
  ) as five_minute_bucket_jst,
  COUNT(*) as request_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
GROUP BY date_format(
  date_add(
    'minute',
    5 * floor(extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))) / 5) - extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))),
    date_add('hour', 9, from_iso8601_timestamp(time))
  ),
  '%Y-%m-%d %H:%i:00 JST'
)
ORDER BY five_minute_bucket_jst DESC;

-- 5分毎のtarget_status_codeごとの集計クエリ (日本時間JST)
SELECT
  date_format(
    date_add(
      'minute',
      5 * floor(extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))) / 5) - extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))),
      date_add('hour', 9, from_iso8601_timestamp(time))
    ),
    '%Y-%m-%d %H:%i:00 JST'
  ) as five_minute_bucket_jst,
  target_status_code,
  COUNT(*) as request_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
GROUP BY
  date_format(
    date_add(
      'minute',
      5 * floor(extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))) / 5) - extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))),
      date_add('hour', 9, from_iso8601_timestamp(time))
    ),
    '%Y-%m-%d %H:%i:00 JST'
  ),
  target_status_code
ORDER BY five_minute_bucket_jst DESC, target_status_code ASC;

-- 5分毎のステータスコード別（全体、200、4xx、5xx）集計クエリ (日本時間JST) - ハイフン対応版
SELECT
  date_format(
    date_add(
      'minute',
      5 * floor(extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))) / 5) - extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))),
      date_add('hour', 9, from_iso8601_timestamp(time))
    ),
    '%Y-%m-%d %H:%i:00 JST'
  ) as five_minute_bucket_jst,
  COUNT(*) as total_requests,
  SUM(CASE WHEN target_status_code = '200' THEN 1 ELSE 0 END) as status_200_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '4%' THEN 1
      ELSE 0
  END) as status_4xx_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '5%' THEN 1
      ELSE 0
  END) as status_5xx_count,
  SUM(CASE WHEN target_status_code = '-' THEN 1 ELSE 0 END) as status_hyphen_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
GROUP BY date_format(
  date_add(
    'minute',
    5 * floor(extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))) / 5) - extract(minute from date_add('hour', 9, from_iso8601_timestamp(time))),
    date_add('hour', 9, from_iso8601_timestamp(time))
  ),
  '%Y-%m-%d %H:%i:00 JST'
)
ORDER BY five_minute_bucket_jst DESC;

-- 1分毎のステータスコード別（全体、200、4xx、5xx）集計クエリ (日本時間JST) - ハイフン対応版
SELECT
  date_format(
    date_add('hour', 9, from_iso8601_timestamp(time)),
    '%Y-%m-%d %H:%i:00 JST'
  ) as one_minute_bucket_jst,
  COUNT(*) as total_requests,
  SUM(CASE WHEN target_status_code = '200' THEN 1 ELSE 0 END) as status_200_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '4%' THEN 1
      ELSE 0
  END) as status_4xx_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '5%' THEN 1
      ELSE 0
  END) as status_5xx_count,
  SUM(CASE WHEN target_status_code = '-' THEN 1 ELSE 0 END) as status_hyphen_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
GROUP BY date_format(
  date_add('hour', 9, from_iso8601_timestamp(time)),
  '%Y-%m-%d %H:%i:00 JST'
)
ORDER BY one_minute_bucket_jst DESC;

-- 特定時間帯（2025-03-28 06:00-07:00 UTC）のエラーレコード検索クエリ（ステータスコード > 200）- 日本時間（JST）表示
SELECT
  time,
  date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:%i:%s JST') as jst_time,
  client_ip,
  elb_status_code,
  target_status_code,
  request_url,
  response_processing_time
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-28T06:00:00Z' and '2025-03-28T07:00:00Z'
and (
    (target_status_code != '200' and target_status_code != '-')
    OR
    (try_cast(target_status_code as integer) > 200)
)
ORDER BY time DESC;

-- target_processing_timeが5秒以上またはタイムアウト(-1)のレコード検索クエリ - 日本時間（JST）表示
SELECT
  time,
  date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:%i:%s JST') as jst_time,
  client_ip,
  elb_status_code,
  target_status_code,
  request_url,
  request_processing_time,
  target_processing_time,
  response_processing_time
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
and (target_processing_time >= 5000 or target_processing_time = -1)  -- 5秒以上またはタイムアウト(-1)
ORDER BY
  CASE
    WHEN target_processing_time = -1 THEN 1  -- タイムアウトを最優先表示
    ELSE 2
  END,
  target_processing_time DESC  -- 処理時間の降順でソート


-- タイムアウト（target_processing_time = -1）のレコードのみ検索するクエリ - 日本時間（JST）表示
SELECT
  time,
  date_format(date_add('hour', 9, from_iso8601_timestamp(time)), '%Y-%m-%d %H:%i:%s JST') as jst_time,
  client_ip,
  elb_status_code,
  target_status_code,
  request_url,
  request_processing_time,
  target_processing_time,
  response_processing_time
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
and target_processing_time = -1  -- タイムアウトのみ
ORDER BY time DESC;

-- target_status_codeごとの集計クエリ (日本時間JST)
SELECT
  target_status_code,
  COUNT(*) as total_requests,
  SUM(CASE WHEN target_status_code = '200' THEN 1 ELSE 0 END) as status_200_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '4%' THEN 1
      ELSE 0
  END) as status_4xx_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '5%' THEN 1
      ELSE 0
  END) as status_5xx_count,
  SUM(CASE WHEN target_status_code = '-' THEN 1 ELSE 0 END) as status_hyphen_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-17T01:00:00Z' and '2025-03-28T07:00:00Z'
GROUP BY target_status_code
ORDER BY
  CASE
    WHEN target_status_code = '200' THEN 1
    WHEN target_status_code LIKE '4%' THEN 2
    WHEN target_status_code LIKE '5%' THEN 3
    WHEN target_status_code = '-' THEN 4
    ELSE 5
  END,
  target_status_code ASC;

-- 日本時間（JST）での1日ごとのステータスコード集計クエリ
SELECT
  date_format(
    date_add('hour', 9, from_iso8601_timestamp(time)),
    '%Y-%m-%d'
  ) as day_jst,
  COUNT(*) as total_requests,
  SUM(CASE WHEN target_status_code = '200' THEN 1 ELSE 0 END) as status_200_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '4%' THEN 1
      ELSE 0
  END) as status_4xx_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '5%' THEN 1
      ELSE 0
  END) as status_5xx_count,
  SUM(CASE WHEN target_status_code = '-' THEN 1 ELSE 0 END) as status_hyphen_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url = 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/entire'
and time between '2025-03-16T21:00:00Z' and '2025-04-02T15:00:00Z'
GROUP BY date_format(
  date_add('hour', 9, from_iso8601_timestamp(time)),
  '%Y-%m-%d'
)
ORDER BY day_jst DESC;


-- 日本時間（JST）での1日ごとのステータスコード集計クエリ (stem)
SELECT
  date_format(
    date_add('hour', 9, from_iso8601_timestamp(time)),
    '%Y-%m-%d'
  ) as day_jst,
  COUNT(*) as total_requests,
  SUM(CASE WHEN target_status_code = '200' THEN 1 ELSE 0 END) as status_200_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '4%' THEN 1
      ELSE 0
  END) as status_4xx_count,
  SUM(CASE
      WHEN target_status_code = '-' THEN 0
      WHEN target_status_code LIKE '5%' THEN 1
      ELSE 0
  END) as status_5xx_count,
  SUM(CASE WHEN target_status_code = '-' THEN 1 ELSE 0 END) as status_hyphen_count
FROM api_alb_access_logs
WHERE response_processing_time is not Null
and request_url like 'https://kb6rvv06ctr2.com:443/sakura_camera/api/tree/%/tengusu'
and time between '2025-03-16T21:00:00Z' and '2025-04-02T15:00:00Z'
GROUP BY date_format(
  date_add('hour', 9, from_iso8601_timestamp(time)),
  '%Y-%m-%d'
)
ORDER BY day_jst DESC;