#Пояснения по заданию
Для сервера выбрал архитектуру с асинхронными воркерами в раздельных процессах. Для работы требуется `python3.7`. Все 
тесты проходят.

# Результаты нагрузочного тестирования
Нагрузку давал с другой машины в той локальной сети. В своем сервере и в nginx настроил 4 воркера.

## Результаты nginx
```
$ ab -n50000 -c100 -r http://192.168.199.103:8080/httptest/dir2/
This is ApacheBench, Version 2.3 <$Revision: 1807734 $>

Server Software:        nginx/1.15.4
Server Hostname:        192.168.199.103
Server Port:            8080

Document Path:          /httptest/dir2/
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   11.203 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      13250000 bytes
HTML transferred:       1700000 bytes
Requests per second:    4462.98 [#/sec] (mean)
Time per request:       22.407 [ms] (mean)
Time per request:       0.224 [ms] (mean, across all concurrent requests)
Transfer rate:          1154.97 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        2   11  24.4     10    1033
Processing:     2   11   7.5     11     225
Waiting:        2   10   7.5     10     224
Total:          5   22  25.8     21    1053

Percentage of the requests served within a certain time (ms)
  50%     21
  66%     22
  75%     23
  80%     23
  90%     25
  95%     27
  98%     36
  99%     58
 100%   1053 (longest request)
```
## Результаты самописного сервера
```
 $ ab -n50000 -c100 -r http://192.168.199.103:8080/httptest/dir2/
This is ApacheBench, Version 2.3 <$Revision: 1807734 $>

Server Software:        Otus
Server Hostname:        192.168.199.103
Server Port:            8080

Document Path:          /httptest/dir2/
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   17.480 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8350000 bytes
HTML transferred:       1700000 bytes
Requests per second:    2860.39 [#/sec] (mean)
Time per request:       34.960 [ms] (mean)
Time per request:       0.350 [ms] (mean, across all concurrent requests)
Transfer rate:          466.49 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        1    4   4.4      3      82
Processing:     2   31  23.5     24     139
Waiting:        2   28  21.3     22     131
Total:          3   35  24.1     28     166

Percentage of the requests served within a certain time (ms)
  50%     28
  66%     39
  75%     47
  80%     53
  90%     70
  95%     83
  98%     99
  99%    110
 100%    166 (longest request)
```

#Как запустить сервер?

Для запуска сервера, нужно выполнить `python httpd.py` со следующими настройками:
```bash
HTTP async web server.

optional arguments:
  -h, --help            show this help message and exit
  -w WORKERS, --workers WORKERS
                        Number of workers used to work with server.
  -c CHECKALIVE, --checkalive CHECKALIVE
                        Timeout to check that workers processes is alive.
  -rt READ_TIMEOUT, --read_timeout READ_TIMEOUT
                        Set timeout to read for a request.
  -r DOCUMENT_ROOT, --document_root DOCUMENT_ROOT
                        Root folder from which will be serve data.
  -p PORT, --port PORT  Port for listening web server.
  --host HOST           Host for listening web server.
```