""" Contexto del pago """

from src.base import (
    save_payment_data,
    AMOUNT, PAYMENT_METHOD, STATUS, STATUS_REGISTRADO, STATUS_PAGADO, STATUS_FALLIDO
)
from src.states import RegisteredState, PaidState, FailedState

class PaymentContext:
    def __init__(self, payment_id, amount, payment_method, status):
        self.payment_id = str(payment_id)
        self.amount = amount
        self.payment_method = payment_method
        self.status = status
        self._state = self._get_state(status)

    def _get_state(self, status):
        if status == STATUS_REGISTRADO:
            return RegisteredState()
        elif status == STATUS_PAGADO:
            return PaidState()
        elif status == STATUS_FALLIDO:
            return FailedState()
        else:
            raise ValueError("Estado desconocido")

    def set_state(self, state):
        self._state = state

    def pay(self):
        self._state.pay(self)

    def update(self, amount, method):
        self._state.update(self, amount, method)

    def revert(self):
        self._state.revert(self)

    def _persist(self):
        save_payment_data(self.payment_id, {
            AMOUNT: self.amount,
            PAYMENT_METHOD: self.payment_method,
            STATUS: self.status
        })
