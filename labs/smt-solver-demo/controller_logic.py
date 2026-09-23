"""Executable controller fragments mirrored by the classroom SMT model."""


def tank_sensor(h_true: int, bias: int) -> int:
    return h_true + bias


def tank_inlet_open(h_reported: int) -> bool:
    return h_reported < 80


def tank_unsafe(h_true: int) -> bool:
    return h_true >= 90


def feeder_sensor(true_current: int, bias: int) -> int:
    return true_current + bias


def feeder_relay_trip(reported_current: int) -> bool:
    return reported_current >= 100


def feeder_next_breaker_closed(closed: bool, trip: bool) -> bool:
    return closed and not trip
