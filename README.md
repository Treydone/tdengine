
```
docker compose up -d
```


```
docker exec -it tdengine taos
SHOW DATABASES;
USE sensors;
SHOW TABLES;
SHOW STREAMS;
```

Grafana:
- Exposé sur **[http://localhost:3000](http://localhost:3000)**.
- Login : `admin`, Password : `admin`.
