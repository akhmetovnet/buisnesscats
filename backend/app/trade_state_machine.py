from __future__ import annotations

from dataclasses import dataclass


class TradeState:
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    COUNTERED = "COUNTERED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


ALL_STATES = {
    TradeState.DRAFT,
    TradeState.PENDING,
    TradeState.COUNTERED,
    TradeState.ACCEPTED,
    TradeState.REJECTED,
    TradeState.NEEDS_CLARIFICATION,
    TradeState.AWAITING_CLARIFICATION,
    TradeState.CANCELLED,
    TradeState.EXPIRED,
}

TERMINAL_STATES = {
    TradeState.ACCEPTED,
    TradeState.REJECTED,
    TradeState.CANCELLED,
    TradeState.EXPIRED,
}


class TradeAction:
    SEND = "send"
    ACCEPT = "accept"
    REJECT = "reject"
    COUNTER = "counter"
    REQUEST_CLARIFICATION = "request_clarification"
    CLARIFY = "clarify"
    CANCEL = "cancel"
    EXPIRE = "expire"


ALL_ACTIONS = {
    TradeAction.SEND,
    TradeAction.ACCEPT,
    TradeAction.REJECT,
    TradeAction.COUNTER,
    TradeAction.REQUEST_CLARIFICATION,
    TradeAction.CLARIFY,
    TradeAction.CANCEL,
    TradeAction.EXPIRE,
}


@dataclass(frozen=True)
class TransitionResult:
    from_state: str
    action: str
    to_state: str


class InvalidTradeTransition(ValueError):
    pass


TRANSITIONS: dict[tuple[str, str], str] = {
    (TradeState.DRAFT, TradeAction.SEND): TradeState.PENDING,

    (TradeState.PENDING, TradeAction.ACCEPT): TradeState.ACCEPTED,
    (TradeState.PENDING, TradeAction.REJECT): TradeState.REJECTED,
    (TradeState.PENDING, TradeAction.COUNTER): TradeState.COUNTERED,
    (TradeState.PENDING, TradeAction.REQUEST_CLARIFICATION): TradeState.NEEDS_CLARIFICATION,
    (TradeState.PENDING, TradeAction.CANCEL): TradeState.CANCELLED,
    (TradeState.PENDING, TradeAction.EXPIRE): TradeState.EXPIRED,

    (TradeState.COUNTERED, TradeAction.ACCEPT): TradeState.ACCEPTED,
    (TradeState.COUNTERED, TradeAction.REJECT): TradeState.REJECTED,
    (TradeState.COUNTERED, TradeAction.COUNTER): TradeState.COUNTERED,
    (TradeState.COUNTERED, TradeAction.REQUEST_CLARIFICATION): TradeState.NEEDS_CLARIFICATION,
    (TradeState.COUNTERED, TradeAction.CANCEL): TradeState.CANCELLED,
    (TradeState.COUNTERED, TradeAction.EXPIRE): TradeState.EXPIRED,

    (TradeState.NEEDS_CLARIFICATION, TradeAction.CLARIFY): TradeState.PENDING,
    (TradeState.NEEDS_CLARIFICATION, TradeAction.CANCEL): TradeState.CANCELLED,
    (TradeState.NEEDS_CLARIFICATION, TradeAction.EXPIRE): TradeState.EXPIRED,

    (TradeState.AWAITING_CLARIFICATION, TradeAction.CLARIFY): TradeState.PENDING,
    (TradeState.AWAITING_CLARIFICATION, TradeAction.CANCEL): TradeState.CANCELLED,
    (TradeState.AWAITING_CLARIFICATION, TradeAction.EXPIRE): TradeState.EXPIRED,
}


def is_terminal(state: str) -> bool:
    return state in TERMINAL_STATES


def can_transition(state: str, action: str) -> bool:
    return (state, action) in TRANSITIONS


def transition_state(state: str, action: str) -> TransitionResult:
    if state not in ALL_STATES:
        raise InvalidTradeTransition(f"unknown_state:{state}")
    if action not in ALL_ACTIONS:
        raise InvalidTradeTransition(f"unknown_action:{action}")
    key = (state, action)
    if key not in TRANSITIONS:
        raise InvalidTradeTransition(f"invalid_transition:{state}->{action}")
    return TransitionResult(from_state=state, action=action, to_state=TRANSITIONS[key])
