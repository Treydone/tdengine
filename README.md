
```
docker compose up -d
```


```
docker compose exec -it tdengine taos
SHOW DATABASES;
USE sensors;
SHOW STABLES;
SHOW STREAMS;
show create table readings;
```

Grafana:
- Exposé sur **[http://localhost:3000](http://localhost:3000)**.
- Login : `admin`, Password : `admin`.


select ts, temperature from sensors.readings where ts > $from and ts < $to

select _wstart, avg(temperature) from sensors.readings where ts > $from and ts < $to INTERVAL(1s) SLIDING(1s);

-- Grouper par intervalle de 100ms (1/10 de seconde)
SELECT
FLOOR(ts/(1000*0.1))*(1000*0.1) AS time_bucket,
AVG(temperature) AS avg_temp
FROM sensors.readings
GROUP BY time_bucket
ORDER BY time_bucket;


select * from sensors.hourly_aggregation;

https://webhook.site/#!/view/720f0c42-aaee-4c1f-baf2-00b6a4f46b21/0e3ee9f7-62d0-4ead-8dac-74a307a91ab1/1


TODO
- Live query pour Grafana
- Administration > User and access > Service accounts
  - Add service account
    - Role Editor
  - Add service account token
  - 
- select * from sensors.hourly_aggregation where ts > $from and ts < $to interval($interval)


npm install -g wscat
wscat -c ws://localhost:3000/api/live/push/scope/namespace/path -H "Authorization: Bearer glsa_zmJ1QdjoncVQ7pryY6l8cRWTeU8bBP8R_64b18473"

USE sensors;
DROP TOPIC high_temperature_topic;
DROP STREAM hourly_aggregations;
DROP STABLE readings;
DROP DATABASE sensors;

## Operations

### Rebuild 

```
docker-compose up -d --force-recreate --build mqtt-to-tdengine
```