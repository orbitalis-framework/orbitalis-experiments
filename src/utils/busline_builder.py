from busline.client.pubsub_client import PubSubClient, PubSubClientBuilder
from busline.local.eventbus.local_eventbus import LocalEventBus
from busline.local.local_publisher import LocalPublisher
from busline.local.local_subscriber import LocalSubscriber
from busline.mqtt.mqtt_publisher import MqttPublisher
from busline.mqtt.mqtt_subscriber import MqttSubscriber


def build_new_local_client() -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(LocalSubscriber(eventbus=LocalEventBus())).with_publisher(
        LocalPublisher(eventbus=LocalEventBus())).build()


def build_new_mqtt_client(hostname: str, port: int) -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(MqttSubscriber(hostname=hostname, port=port)).with_publisher(
        MqttPublisher(hostname=hostname, port=port)).build()
