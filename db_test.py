import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# Lade die URL aus der Umgebung, genau wie es die Tests tun würden
db_url_str = os.getenv("DATABASE_URL", "sqlite://")
print(f"Connecting to: {db_url_str}")

try:
    # Erstelle die Engine
    url = URL.create(db_url_str)
    engine = create_engine(url)

    # Versuche, eine Verbindung herzustellen
    with engine.connect() as connection:
        print("Connection successful!")
        result = connection.execute("SELECT 1")
        print("Test query successful!")

except Exception as e:
    print("AN ERROR OCCURRED:")
    print(e)
