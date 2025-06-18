-- Créer une base de données si elle n'existe pas
CREATE DATABASE IF NOT EXISTS sensors;

-- Accéder à la base de données
USE sensors;

-- Créer une super-table permettant des données provenant de plusieurs capteurs
CREATE STABLE IF NOT EXISTS readings (
    ts TIMESTAMP,          -- Timestamp de la donnée
    temperature FLOAT,     -- Température
    humidity FLOAT         -- Humidité
) TAGS (
    sensor_id INT,         -- ID unique du capteur
    location BINARY(50)    -- Localisation du capteur (nom de ville, chaîne de caractères)
);

-- Créer un STREAM pour l'agrégation des températures et humidités toutes les heures
CREATE STREAM hourly_aggregation AS
SELECT
    FIRST(ts) AS start_time,               -- Timestamp de début de la période
    LAST(ts) AS end_time,                  -- Timestamp de fin de la période
    AVG(temperature) AS avg_temperature,   -- Moyenne des températures
    MIN(temperature) AS min_temperature,   -- Température minimale
    MAX(temperature) AS max_temperature,   -- Température maximale
    AVG(humidity) AS avg_humidity,         -- Moyenne de l'humidité
    MIN(humidity) AS min_humidity,         -- Humidité minimale
    MAX(humidity) AS max_humidity          -- Humidité maximale
FROM readings
    INTERVAL(1h)                               -- Intervalle d'une heure
    SLIDING(30m);                              -- Fenêtre coulissante toutes les heures

-- Créer un topic pour les températures élevées
CREATE TOPIC high_temperature_topic AS
SELECT *
FROM hourly_aggregation
WHERE max_temperature > 30;

-- Créer une subscription pour pousser dans MQTT
CREATE SUBSCRIPTION high_temp_alerts_mqtt ON high_temperature_topic USING MQTT
     ENDPOINT "tcp://mqtt-broker:1883"
     TOPIC "alerts/high_temperature";

