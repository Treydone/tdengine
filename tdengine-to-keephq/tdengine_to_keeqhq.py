import json
import time
import signal
import os
import sys
import requests
from taos.tmq import Consumer, TmqConsumer, TmqError

tdengine_ip=os.getenv('TDENGINE_IP')
tdengine_port=int(os.getenv('TDENGINE_PORT'))
tdengine_user=os.getenv('TDENGINE_USER')
tdengine_password=os.getenv('TDENGINE_PASSWORD')
tdengine_db=os.getenv('TDENGINE_DB')
tdengine_topic=os.getenv('TDENGINE_TOPIC')
keephq_webhook_url=os.getenv('KEEPHQ_WEBHOOK_URL')

# Configuration du consumer
config = {
    "td.connect.user": tdengine_user,
    "td.connect.pass": tdengine_password,
    "td.connect.ip": tdengine_ip,  # ou l'adresse de votre serveur TDengine
    "td.connect.port": tdengine_port,
    "group.id": "python_high_temp_consumer",
    "client.id": "python_client",
    "auto.offset.reset": "latest",  # 'earliest' pour lire depuis le début
    "enable.auto.commit": "true",
    "msg.with.table.name": "true"
}

# Gestionnaire de signal pour arrêter proprement
running = True

def signal_handler(sig, frame):
    global running
    print("Arrêt du consumer...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

def main():
    try:
        # Créer un consumer
        consumer = Consumer(config)

        # S'abonner au topic

        consumer.subscribe([("%s" % tdengine_topic)])
        print("Abonnement au topic " + tdengine_topic + " réussi")

        # Boucle de consommation
        while running:
            try:
                # Récupérer les messages (timeout en ms)
                messages = consumer.poll(1000)

                if messages:
                    for message in messages:
                        # Récupérer les informations du message
                        topic_name = message.topic_name()
                        table_name = message.get_table_name()
                        db_name = message.get_db_name()

                        # Parcourir les données du message
                        for i in range(message.get_rows_num()):
                            # Récupérer les valeurs des colonnes pour chaque ligne
                            row_data = {}
                            for j in range(message.get_fields_num()):
                                field_name = message.get_field_name(j)
                                field_value = message.get_value(i, j)
                                row_data[field_name] = field_value

                            # Afficher les données
                            print(f"Topic: {topic_name}, DB: {db_name}, Table: {table_name}")
                            print(f"Alerte température élevée: {json.dumps(row_data, default=str)}")

                            # Traitement des alertes
                            payload = {
                                "alert": "Température élevée détectée",
                                "details": f"Température max : {row_data['max_temperature']} °C",
                                "timestamp": row_data["start_time"],
                            }
                            # Envoyer la requête POST au webhook
                            response = requests.post(keephq_webhook_url, json=payload)
                            if response.status_code == 200:
                                print("Alerte envoyée avec succès à KeeqHQ.")
                            else:
                                print(f"Erreur : {response.status_code} - {response.text}")

                    # Committer les offsets après traitement
                    consumer.commit()

                # Petite pause pour éviter de surcharger le CPU
                time.sleep(0.1)

            except TmqError as e:
                print(f"Erreur TMQ: {e}")
                time.sleep(1)  # Pause avant de réessayer

    except Exception as e:
        print(f"Erreur: {e}")
    finally:
        # Fermer proprement le consumer
        if 'consumer' in locals():
            consumer.unsubscribe()
            consumer.close()
            print("Consumer fermé")

if __name__ == "__main__":
    main()