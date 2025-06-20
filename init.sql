CREATE DATABASE IF NOT EXISTS sensors PRECISION 'ms';

USE sensors;

CREATE STABLE IF NOT EXISTS readings (ts TIMESTAMP,temperature FLOAT,humidity FLOAT) TAGS (sensor_id INT,location BINARY(50));

CREATE STREAM IF NOT EXISTS hourly_aggregations INTO hourly_aggregation AS SELECT FIRST(ts) AS start_time, LAST(ts) AS end_time, AVG(temperature) AS avg_temperature, MIN(temperature) AS min_temperature, MAX(temperature) AS max_temperature, AVG(humidity) AS avg_humidity, MIN(humidity) AS min_humidity, MAX(humidity) AS max_humidity, sensor_id FROM readings partition by sensor_id INTERVAL(1s) SLIDING(1s);

CREATE TOPIC IF NOT EXISTS high_temperature_topic AS SELECT * FROM hourly_aggregation WHERE max_temperature > 26;


