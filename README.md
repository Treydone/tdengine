
```
docker compose up -d
```


```
docker compose exec -it tdengine taos
SHOW DATABASES;
USE sensors;
SHOW STABLES;
SHOW STREAMS;
```

Grafana:
- Exposé sur **[http://localhost:3000](http://localhost:3000)**.
- Login : `admin`, Password : `admin`.


select _wstart as ts, avg_temperature as current from sensors.hourly_aggregation;

