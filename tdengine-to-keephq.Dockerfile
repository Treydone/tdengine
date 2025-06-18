FROM tdengine/tdengine:3.3.6.9

# Installation des dépendances Python
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    python3 -m venv /usr/src/env && \
    . /usr/src/env/bin/activate && \
    pip install requests taospy==2.8.1

# Copie du script
COPY ./tdengine-to-keephq/tdengine_to_keephq.py /usr/src/tdengine_to_keephq.py
RUN chmod +x /usr/src/tdengine_to_keephq.py

# Script d'entrée qui sera exécuté au démarrage
COPY ./tdengine-to-keephq/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]