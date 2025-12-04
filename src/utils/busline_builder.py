from busline.client.pubsub_client import PubSubClient, PubSubClientBuilder
from busline.local.eventbus.async_local_eventbus import AsyncLocalEventBus
from busline.local.local_publisher import LocalPublisher
from busline.local.local_subscriber import LocalSubscriber
from busline.mqtt.mqtt_publisher import MqttPublisher
from busline.mqtt.mqtt_subscriber import MqttSubscriber

LOCAL_EVENTBUS = AsyncLocalEventBus(fire_and_forget=False)
LOCAL_EVENTBUS_FF = AsyncLocalEventBus(fire_and_forget=True)


def build_new_local_client(fire_and_forget: bool) -> PubSubClient:
    eventbus = LOCAL_EVENTBUS_FF if fire_and_forget else LOCAL_EVENTBUS
    return PubSubClientBuilder().with_subscriber(LocalSubscriber(eventbus=eventbus)).with_publisher(
        LocalPublisher(eventbus=eventbus)).build()


def build_new_mqtt_client(hostname: str, port: int) -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(MqttSubscriber(hostname=hostname, port=port)).with_publisher(
        MqttPublisher(hostname=hostname, port=port)).build()
