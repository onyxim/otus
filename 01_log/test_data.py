# Специальные данные для проверки того, что логи спарсены корректно
test_report_data = """[{"count": 1, "count_perc": 5.26, "time_avg": 0.627, "time_max": 0.627, "time_med": 0.627, "time_perc": 7.22, "time_sum": 0.627, "url": "/api/v2/group/5500840/banners"}, {"count": 1, "count_perc": 5.26, "time_avg": 2.285, "time_max": 2.285, "time_med": 2.285, "time_perc": 26.3, "time_sum": 2.285, "url": "/agency/campaigns/6933936/banners/bulk_read/"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.15, "time_max": 0.15, "time_med": 0.15, "time_perc": 1.73, "time_sum": 0.15, "url": "/api/1/campaigns/?id=6761497"}, {"count": 3, "count_perc": 15.79, "time_avg": 0.002, "time_max": 0.003, "time_med": 0.002, "time_perc": 0.08, "time_sum": 0.007, "url": "/export/appinstall_raw/2017-06-29/"}, {"count": 3, "count_perc": 15.79, "time_avg": 0.001, "time_max": 0.001, "time_med": 0.001, "time_perc": 0.02, "time_sum": 0.002, "url": "/export/appinstall_raw/2017-06-30/"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.143, "time_max": 0.143, "time_med": 0.143, "time_perc": 1.65, "time_sum": 0.143, "url": "/api/v2/banner/17461445"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.143, "time_max": 0.143, "time_med": 0.143, "time_perc": 1.65, "time_sum": 0.143, "url": "/api/1/campaigns/?id=1166366"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.141, "time_max": 0.141, "time_med": 0.141, "time_perc": 1.62, "time_sum": 0.141, "url": "/api/1/campaigns/?id=6353951"}, {"count": 1, "count_perc": 5.26, "time_avg": 1.41, "time_max": 1.41, "time_med": 1.41, "time_perc": 16.23, "time_sum": 1.41, "url": "/api/v2/banner/22479951"}, {"count": 1, "count_perc": 5.26, "time_avg": 1.049, "time_max": 1.049, "time_med": 1.049, "time_perc": 12.07, "time_sum": 1.049, "url": "/api/v2/banner/25769978"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.145, "time_max": 0.145, "time_med": 0.145, "time_perc": 1.67, "time_sum": 0.145, "url": "/api/1/campaigns/?id=998432"}, {"count": 1, "count_perc": 5.26, "time_avg": 1.715, "time_max": 1.715, "time_med": 1.715, "time_perc": 19.74, "time_sum": 1.715, "url": "/agency/campaigns/5399558/banners/bulk_read/"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.493, "time_max": 0.493, "time_med": 0.493, "time_perc": 5.67, "time_sum": 0.493, "url": "/api/v2/group/5543119/banners"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.158, "time_max": 0.158, "time_med": 0.158, "time_perc": 1.82, "time_sum": 0.158, "url": "/api/1/campaigns/?id=623792"}, {"count": 1, "count_perc": 5.26, "time_avg": 0.22, "time_max": 0.22, "time_med": 0.22, "time_perc": 2.53, "time_sum": 0.22, "url": "/api/1/flash_banners/list/?server_name=AndreySergeevich"}]"""

log_data = """1.169.137.128 -  - [29/Jun/2017:04:15:18 +0300] "GET /api/v2/group/5500840/banners HTTP/1.1" 200 
2232 "-" "Configovod" "-" "1498698917-2118016444-4707-9840679" "712e90144abee9" 0.627
1.168.229.112 545a7b821307935d  - [29/Jun/2017:04:15:18 +0300] "GET /agency/campaigns/6933936/banners/bulk_read/ HTTP/1.1" 200 21022 "-" "python-requests/2.13.0" "-" "1498698916-743364018-4707-9840657" "-" 2.285
1.133.1.240 f032b48fb33e1e692  - [29/Jun/2017:04:15:18 +0300] "GET /api/1/campaigns/?id=6761497 HTTP/1.1" 200 621 "-" "-" "-" "1498698918-75908569-4707-9840685" "-" 0.150
1.141.250.208 -  - [29/Jun/2017:04:15:18 +0300] "GET /export/appinstall_raw/2017-06-29/ HTTP/1.0" 200 31433 "-" "Mozilla/5.0 (Windows; U; Windows NT 6.0; ru; rv:1.9.0.12) Gecko/2009070611 Firefox/3.0.12 (.NET CLR 3.5.30729)" "-" "-" "-" 0.002
1.141.250.208 -  - [29/Jun/2017:04:15:18 +0300] "GET /export/appinstall_raw/2017-06-30/ HTTP/1.0" 404 162 "-" "Mozilla/5.0 (Windows; U; Windows NT 6.0; ru; rv:1.9.0.12) Gecko/2009070611 Firefox/3.0.12 (.NET CLR 3.5.30729)" "-" "-" "-" 0.001
1.169.137.128 -  - [29/Jun/2017:04:15:18 +0300] "GET /api/v2/banner/17461445 HTTP/1.1" 200 2230 "-" "Configovod" "-" "1498698918-2118016444-4708-9763296" "712e90144abee9" 0.143
1.202.56.176 -  - [29/Jun/2017:04:15:18 +0300] "0" 400 166 "-" "-" "-" "-" "-" 0.001
1.133.1.240 f032b48fb33e1e692  - [29/Jun/2017:04:15:18 +0300] "GET /api/1/campaigns/?id=1166366 HTTP/1.1" 200 620 "-" "-" "-" "1498698918-75908569-4707-9840686" "-" 0.143
1.133.1.240 f032b48fb33e1e692  - [29/Jun/2017:04:15:18 +0300] "GET /api/1/campaigns/?id=6353951 HTTP/1.1" 200 638 "-" "-" "-" "1498698918-75908569-4707-9840687" "-" 0.141
1.126.153.80 -  - [29/Jun/2017:04:15:18 +0300] "GET /api/v2/banner/22479951 HTTP/1.1" 200 1111 "-" "-" "-" "1498698917-48424485-4707-9840673" "1835ae0f17f" 1.410
1.141.86.192 -  - [29/Jun/2017:04:15:18 +0300] "GET /export/appinstall_raw/2017-06-29/ HTTP/1.0" 200 31433 "-" "Mozilla/5.0 (Windows; U; Windows NT 6.0; ru; rv:1.9.0.12) Gecko/2009070611 Firefox/3.0.12 (.NET CLR 3.5.30729)" "-" "-" "-" 0.002
1.141.86.192 -  - [29/Jun/2017:04:15:18 +0300] "GET /export/appinstall_raw/2017-06-30/ HTTP/1.0" 404 162 "-" "Mozilla/5.0 (Windows; U; Windows NT 6.0; ru; rv:1.9.0.12) Gecko/2009070611 Firefox/3.0.12 (.NET CLR 3.5.30729)" "-" "-" "-" 0.000
1.126.153.80 -  - [29/Jun/2017:04:15:18 +0300] "GET /api/v2/banner/25769978 HTTP/1.1" 200 917 "-" "-" "-" "1498698917-48424485-4708-9763295" "1835ae0f17f" 1.049
1.133.1.240 f032b48fb33e1e692  - [29/Jun/2017:04:15:18 +0300] "GET /api/1/campaigns/?id=998432 HTTP/1.1" 200 656 "-" "-" "-" "1498698918-75908569-4707-9840688" "-" 0.145
1.168.229.112 545a7b821307935d  - [29/Jun/2017:04:15:18 +0300] "GET /agency/campaigns/5399558/banners/bulk_read/ HTTP/1.1" 200 8400 "-" "python-requests/2.13.0" "-" "1498698917-743364018-4707-9840672" "-" 1.715
1.139.106.144 -  - [29/Jun/2017:04:15:18 +0300] "GET /export/appinstall_raw/2017-06-29/ HTTP/1.0" 200 31433 "-" "Mozilla/5.0 (Windows; U; Windows NT 6.0; ru; rv:1.9.0.12) Gecko/2009070611 Firefox/3.0.12 (.NET CLR 3.5.30729)" "-" "-" "-" 0.003
1.139.106.144 -  - [29/Jun/2017:04:15:18 +0300] "GET /export/appinstall_raw/2017-06-30/ HTTP/1.0" 404 162 "-" "Mozilla/5.0 (Windows; U; Windows NT 6.0; ru; rv:1.9.0.12) Gecko/2009070611 Firefox/3.0.12 (.NET CLR 3.5.30729)" "-" "-" "-" 0.001
1.169.137.128 -  - [29/Jun/2017:04:15:18 +0300] "GET /api/v2/group/5543119/banners HTTP/1.1" 200 2339 "-" "Configovod" "-" "1498698918-2118016444-4708-9763298" "712e90144abee9" 0.493
1.133.1.240 f032b48fb33e1e692  - [29/Jun/2017:04:15:18 +0300] "GET /api/1/campaigns/?id=623792 HTTP/1.1" 200 620 "-" "-" "-" "1498698918-75908569-4707-9840690" "-" 0.158
1.140.178.176 3b81f63526fa8  - [29/Jun/2017:04:15:19 +0300] "GET /api/1/flash_banners/list/?server_name=AndreySergeevich HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498698918-1643579065-4708-9763300" "-" 0.220"""
