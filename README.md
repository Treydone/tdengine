
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

select * from sensors.hourly_aggregation;


https://webhook.site/#!/view/720f0c42-aaee-4c1f-baf2-00b6a4f46b21/0e3ee9f7-62d0-4ead-8dac-74a307a91ab1/1