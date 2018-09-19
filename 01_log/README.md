# Примечания по заданию
1. Наверное можно было бы еще по кодам ответа фильтровать. При желании, можно без проблем сделать, потому что regex 
полностью строку разбирает.
1. regex мог бы сделать еще хитрее (есть и уже более менее готовые варианты в сети, но в учебном задании разумно 
самостоятельно по практиковаться по хардкору), если необходимо - расширю.
1. Могу написать больше тестов, но вроде написано, что без фанатизма, так что ограничился главным функциональным и 
небольшим числом юнитов.

# Как запустить анализатор логов со своим конфигом?
Чтобы считать настройки из кастомного конфига, необходимо передать путь к файлу конфигу вместе с его названием после 
флага `-c` или `--config`. Если после флага не будет указан путь до конфига, будет предпринята попытка считать конфиг
 из директории по умолчанию: `./config.yml` (относительно директории, где находится `log_analyzer.py`).

Конфиг может содержать элементы как в шаблоне конфига. При этом необязательно все эти параметры должны быть 
заданы  в вашем конфиге.  Если что-то будет не указано - будет использован вариант по-умолчанию. Шаблон конфига 
находится в файле `./config_template.yml`.


Подробнее поддерживаемая структура конфига описана по ссылке:
https://docs.python.org/3/library/configparser.html#supported-ini-file-structure