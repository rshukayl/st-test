# Локальный DevOps-стенд

Nginx принимает HTTPS на `https://localhost:443` и проксирует в Python/Flask
backend на `8080`. Backend выполняет SQL-запрос к PostgreSQL 15 и хранит счётчик
посещений сессии в Redis. PostgreSQL, Redis и backend не публикуют порты на хосте.

## Запуск — 5 команд

Нужны Docker Engine с доступом к daemon, Docker Compose v2+ и OpenSSL.
Выполните из каталога проекта:

```sh
cp -n .env.example .env
./gen-certs.sh
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 180
curl --cacert certs/localhost.crt --cookie-jar /tmp/devops-lab.cookies --cookie /tmp/devops-lab.cookies https://localhost/
```

Первая команда создаёт `.env` из `.env.example`, если файла ещё нет.
Перед запуском контейнеров задайте в `.env` локальные пароли вместо заглушек.
Compose автоматически читает
`.env`. Пароли и приватный ключ исключены из Git. Генератор не перезаписывает
существующий сертификат: для повторной генерации удалите оба файла в `certs`.
В браузере self-signed сертификат вызывает предупреждение; curl выше проверяет
его через явно указанный сертификат. Если порт занят, задайте `HTTPS_PORT=8443`
в `.env` и используйте `https://localhost:8443/`.

## Проверка

- `docker compose ps` — четыре сервиса должны иметь статус `healthy`.
- `curl --cacert certs/localhost.crt https://localhost/healthz` — проверка backend,
  реального подключения к БД и Redis. Healthcheck Nginx проверяет отдельный
  локальный HTTP endpoint, PostgreSQL — `pg_isready`, Redis — авторизованный PING.
- Для проверки сессий выполните следующую команду несколько раз:

  ```sh
  curl --cacert certs/localhost.crt --cookie-jar /tmp/devops-lab.cookies --cookie /tmp/devops-lab.cookies https://localhost/
  ```

  Значение `session_visits` будет увеличиваться. Команда читает cookie из файла
  `/tmp/devops-lab.cookies` и сохраняет туда полученную cookie. Удалите файл
  командой `rm -f /tmp/devops-lab.cookies`, чтобы следующий запрос создал новую
  сессию со счётчиком `1`. TTL продлевается при каждом посещении `/`. Redis здесь
  намеренно неперсистентный: после его пересоздания счётчики сессий теряются.
- JSON показывает `forwarded`: `proto=https`, исходный Host и IP клиента,
  видимый Nginx (в Docker он может быть адресом NAT). Nginx на публичной границе
  перезаписывает входной X-Forwarded-For, чтобы клиент не мог подделать цепочку.
- Лимит — 10 запросов/с на IP, без burst; превышение возвращает `429`.
  Лимит тела — `10m` (10 MiB в терминах Nginx); превышение возвращает `413`.
  Проверка rate limiting, требующая curl и xargs:
  `seq 1 40 | xargs -P 20 -I '{}' curl --cacert certs/localhost.crt -s -o /dev/null -w '%{http_code}\n' https://localhost/`
- Логи: `docker compose logs --tail=100`.

## Остановка и данные

`docker compose down` удаляет контейнеры и сеть, сохраняя данные PostgreSQL в
именованном volume. `docker compose down -v` также **удаляет данные БД**.
Изменение пароля PostgreSQL в `.env` не меняет пароль в уже созданной БД:
нужно изменить его SQL-командой либо пересоздать volume, если данные не нужны.

Это локальный стенд: PostgreSQL использует одного пользователя для приложения
и инициализации. В production потребуются отдельная роль приложения, управление
секретами, backup/restore, HA и доверенный TLS-сертификат.
