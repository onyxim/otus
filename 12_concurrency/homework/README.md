# Описание архитектуры решения

Реализация находится в `memc_load2.py`. Нужное количество memcached поднимается через docker.

Отркрытие и обработка строк происходит в пуле процессов (количество по числу доступных ядер CPU). 
Отправка в memcached в потоках. Максимлаьное количество процессов можно задавать при запуске.

Коммуникация между потоками и процессами происходит с помощью очередей.