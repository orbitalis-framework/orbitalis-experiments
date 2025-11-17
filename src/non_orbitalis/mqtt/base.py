from dataclasses import dataclass, field
from abc import ABC
import paho.mqtt.client as mqtt



@dataclass
class BaseMqtt(ABC):
    client: mqtt.Client

    @property
    def identifier(self) -> str:
        return self.client._client_id.decode()