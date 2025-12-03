from dataclasses import dataclass
from typing import List

from busline.event.message.avro_message import AvroMessageMixin


@dataclass
class RangeMessage(AvroMessageMixin):
    first_number: int
    second_number: int


@dataclass
class PrimeNumbersMessage(AvroMessageMixin):
    prime_numbers: List[int]