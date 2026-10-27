-- Runs once when the Postgres volume is first initialised.
-- The test suite drops and recreates the schema of this database on every run,
-- so it must never point at the development database.
CREATE DATABASE ipp_test OWNER ipp;
