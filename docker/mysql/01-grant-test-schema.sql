-- Lets the application user create and drop its own test schemas.
--
-- tests/conftest.py forces MYSQL_DATABASE to a name ending in `_test`, then
-- calls init_db(), which CREATEs the database and DROPs every table. Without
-- this grant the developer's own credentials cannot do that and `pytest` fails
-- with "Access denied ... to database 'coisascomgosto_test'".
--
-- The grant is deliberately limited to the `_test` suffix: the same account
-- gains no rights over any other database on the server.
--
-- MySQL runs everything in /docker-entrypoint-initdb.d ONLY when the data
-- directory is first created. On an existing volume, apply it by hand:
--   docker compose exec db mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
--     < db/init/01-grant-test-schema.sql
GRANT ALL PRIVILEGES ON `%\_test`.* TO 'coisascomgosto'@'%';
FLUSH PRIVILEGES;
