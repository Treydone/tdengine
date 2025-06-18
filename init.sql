CREATE DATABASE IF NOT EXISTS sensors;

USE sensors;

CREATE STABLE IF NOT EXISTS readings (ts TIMESTAMP,temperature FLOAT,humidity FLOAT) TAGS (sensor_id INT,location BINARY(50));

CREATE STREAM IF NOT EXISTS hourly_aggregations INTO hourly_aggregation AS SELECT FIRST(ts) AS start_time, LAST(ts) AS end_time, AVG(temperature) AS avg_temperature, MIN(temperature) AS min_temperature, MAX(temperature) AS max_temperature, AVG(humidity) AS avg_humidity, MIN(humidity) AS min_humidity, MAX(humidity) AS max_humidity FROM readings INTERVAL(1h) SLIDING(30m);

CREATE TOPIC IF NOT EXISTS high_temperature_topic AS SELECT * FROM hourly_aggregation WHERE max_temperature > 26;
